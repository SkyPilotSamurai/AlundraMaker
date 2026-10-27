"""Higher-quality music renderer (2026-10-12), used by the editor preview and the
remake's extracted music. Same sequence/bank decoding as music_preview, plus:

* 4-point interpolation (Catmull-Rom, close to the SPU's Gaussian filter)
  instead of nearest-sample, so instruments are not harsh or aliased;
* pitch bend applied over the whole note (it was ignored);
* channel volume / expression changes during a note (only the start was used);
* modulation wheel (CC1) as gentle vibrato;
* a stereo reverb like the console's (the music is mixed for it).
Needs numpy.
"""
import math
import numpy as np
import music_preview as mp

REVERB_SECONDS = 1.6
REVERB_WET = 0.22


def _histories(timeline):
    ch = [dict(bend=[(0.0, 0)], vol=[(0.0, 100)], expr=[(0.0, 127)], mod=[(0.0, 0)]) for _ in range(16)]
    for time, status, a, b in timeline:
        c = ch[status & 15]; kind = status & 0xF0
        if kind == 0xE0:
            c['bend'].append((time, ((b << 7) | a) - 8192 if (a or b) else 0))
        elif kind == 0xB0:
            if a == 7: c['vol'].append((time, b))
            elif a == 11: c['expr'].append((time, b))
            elif a == 1: c['mod'].append((time, b))
    return ch


def _step_curve(history, times):
    t = np.array([h[0] for h in history]); v = np.array([h[1] for h in history], dtype=np.float64)
    idx = np.searchsorted(t, times, side='right') - 1
    return v[np.clip(idx, 0, len(v) - 1)]


def _wrap(pos, size, loop_start):
    if loop_start is not None and size > loop_start:
        span = size - loop_start
        over = pos >= size
        pos = pos.copy(); pos[over] = loop_start + np.mod(pos[over] - loop_start, span)
        return pos, None
    return pos, pos < size - 1


def _reverb(left, right, rate):
    n = int(REVERB_SECONDS * rate)
    rng = np.random.default_rng(7)
    t = np.arange(n) / rate
    decay = np.exp(-t * 6.9 / REVERB_SECONDS)          # -60 dB at REVERB_SECONDS
    pre = int(0.02 * rate)
    out = []
    for sig, seed in ((left, 1), (right, 2)):
        ir = rng.standard_normal(n) * decay; ir[:pre] = 0
        ir /= np.sqrt(np.sum(ir ** 2)) * 3.0
        size = 1 << int(math.ceil(math.log2(len(sig) + n)))
        wet = np.fft.irfft(np.fft.rfft(sig, size) * np.fft.rfft(ir, size), size)[:len(sig)]
        out.append(sig * (1 - REVERB_WET) + wet * REVERB_WET * 2.5)
    return out[0], out[1]


def render(seq, header, body, seconds=60.0, rate=44100, reverb=True):
    bank = mp.Bank(header, body)
    timeline = mp.schedule(seq, seconds)
    notes, _ = mp.collect_notes(timeline, bank)
    hist = _histories(timeline)
    length = int(seconds * rate) + rate
    left = np.zeros(length); right = np.zeros(length)
    master = bank.mvol / 127 if bank.mvol else 1.0
    pcm_cache = {}
    for start, ch, note, velocity, program, _cv, channel_pan, stop in notes:
        if start >= seconds:
            continue
        for tone in bank.tones.get(program, []):
            if not tone['low'] <= note <= tone['high']:
                continue
            pcm, loop_start, loops = bank.sample(tone['vag'])
            if not pcm:
                continue
            if tone['vag'] not in pcm_cache: pcm_cache[tone['vag']] = np.asarray(pcm, dtype=np.float64)
            data = pcm_cache[tone['vag']]; size = len(data)
            prog = bank.programs[program]
            amp = (velocity / 127) * (tone['vol'] / 127) * (prog['vol'] / 127 if prog['vol'] else 1) * master
            pan = max(0.0, min(1.0, (channel_pan + tone['pan'] - 64) / 127))
            gl, gr = math.cos(pan * math.pi / 2), math.sin(pan * math.pi / 2)
            env = mp.envelope_points(tone['adsr1'], tone['adsr2'], max(0.0, stop - start), rate)
            duration = min(env[-1][0], seconds - start + 0.5)
            first = int(start * rate)
            count = min(int(duration * rate), length - first)
            if count <= 1:
                continue
            times = start + np.arange(count) / rate
            h = hist[ch]
            bend = _step_curve(h['bend'], times)
            brange = np.where(bend >= 0, tone['pbmax'] or 2, tone['pbmin'] or 2)
            semis = note - tone['center'] + tone['fine'] / 128 + bend / 8192 * brange
            mod = _step_curve(h['mod'], times)
            if mod.any():
                semis = semis + (mod / 127) * 0.5 * np.sin(2 * np.pi * 5.5 * (times - start))
            step = np.power(2.0, semis / 12) * mp.SPU_RATE / rate
            pos = np.concatenate(([0.0], np.cumsum(step[:-1])))
            pos, valid = _wrap(pos, size, loop_start)
            if valid is not None and not valid.all():
                count = int(np.argmin(valid)) if not valid[0] is False else 0
                if count <= 1:
                    continue
                pos = pos[:count]; times = times[:count]
            i = pos.astype(np.int64); f = pos - i
            def at(k):
                k = k.copy()
                if loop_start is not None and size > loop_start:
                    over = k >= size; k[over] = loop_start + (k[over] - loop_start) % (size - loop_start)
                return data[np.clip(k, 0, size - 1)]
            p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
            sample = p1 + 0.5 * f * (p2 - p0 + f * (2 * p0 - 5 * p1 + 4 * p2 - p3 + f * (3 * (p1 - p2) + p3 - p0)))
            et, ev = zip(*env)
            level = np.interp(times - start, et, ev)
            cv = _step_curve(h['vol'], times) * _step_curve(h['expr'], times) / (127 * 127)
            out = sample * level * cv * amp
            left[first:first + len(out)] += out * gl; right[first:first + len(out)] += out * gr
    end = int(seconds * rate)
    left, right = left[:end], right[:end]
    if reverb:
        left, right = _reverb(left, right, rate)
    stereo = np.empty(end * 2); stereo[0::2] = left; stereo[1::2] = right
    return rate, stereo
