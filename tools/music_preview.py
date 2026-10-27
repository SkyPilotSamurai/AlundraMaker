"""Offline preview renderer for native music (Sony pQES sequence + pBAV bank).

Each music track in SOUND.BIN is a sequence and its own VAB instrument bank
(boundaries from music_database.music_rows). This module plays the sequence
like a small SPU: VAG ADPCM samples with their loop points, tone key ranges,
pitch, velocity/volume/expression/pan controllers, pitch bend, the hardware
ADSR envelope and the sequence loop markers (CC99 20/30). Reverb, vibrato
and portamento are not simulated, so this is a preview, not an emulator.

numpy is used when installed (44.1 kHz); otherwise a pure-Python path renders
at 22.05 kHz.
"""
import io
import math
import struct
import wave

FILTERS = ((0, 0), (60, 0), (115, -52), (98, -55), (122, -60))
SPU_RATE = 44100


# ---- VAG / VAB ---------------------------------------------------------------------------
def decode_vag(data):
    """Decode PS1 ADPCM. Returns (samples, loop_start or None, loops)."""
    out = []; s1 = s2 = 0; loop_start = None; loops = False
    for block in range(len(data) // 16):
        o = block * 16
        shift = data[o] & 15; filt = min(4, data[o] >> 4); flags = data[o + 1]
        if flags & 4 and loop_start is None:
            loop_start = len(out)
        a, b = FILTERS[filt]
        for byte in data[o + 2:o + 16]:
            for nib in (byte & 15, byte >> 4):
                v = nib - 16 if nib & 8 else nib
                v = ((v << 12) >> shift) + ((s1 * a + s2 * b + 32) >> 6)
                v = -32768 if v < -32768 else 32767 if v > 32767 else v
                s2, s1 = s1, v; out.append(v)
        if flags & 1:
            loops = bool(flags & 2)
            break
    if not loops:
        loop_start = None
    return out, loop_start, loops


class Bank:
    def __init__(self, header, body):
        if header[:4] != b'pBAV':
            raise ValueError('Music instrument bank header not recognised')
        (self.programs_count, self.tones_count, self.vags_count, self.mvol, self.mpan) = (
            struct.unpack_from('<H', header, 0x12)[0], struct.unpack_from('<H', header, 0x14)[0],
            struct.unpack_from('<H', header, 0x16)[0], header[0x18], header[0x19])
        if not 1 <= self.programs_count <= 128:
            raise ValueError('Invalid instrument count')
        self.programs = []
        for p in range(128):
            o = 0x20 + p * 16
            self.programs.append(dict(tones=header[o], vol=header[o + 1], pan=header[o + 4]))
        tones_base = 0x20 + 128 * 16
        self.tones = {}
        for p in range(self.programs_count):
            rows = []
            for t in range(16):
                o = tones_base + (p * 16 + t) * 32
                vol, pan, center, fine, low, high = header[o + 2], header[o + 3], header[o + 4], header[o + 5], header[o + 6], header[o + 7]
                pbmin, pbmax = header[o + 12], header[o + 13]
                adsr1, adsr2, prog, vag = struct.unpack_from('<HHhh', header, o + 16)
                if vag <= 0 or low > high:
                    continue
                rows.append(dict(vol=vol, pan=pan, center=center, fine=fine, low=low, high=high,
                                 pbmin=pbmin, pbmax=pbmax, adsr1=adsr1, adsr2=adsr2, vag=vag))
            self.tones[p] = rows[:max(0, self.programs[p]['tones'])] if self.programs[p]['tones'] else rows
        table = tones_base + self.programs_count * 16 * 32
        self.lengths = struct.unpack_from('<256H', header, table)
        self.body = body; self.cache = {}

    def sample(self, vag):
        if vag not in self.cache:
            start = sum(self.lengths[:vag]) * 8; length = self.lengths[vag] * 8
            if length <= 0 or start + length > len(self.body):
                self.cache[vag] = ([], None, False)
            else:
                self.cache[vag] = decode_vag(self.body[start:start + length])
        return self.cache[vag]


# ---- sequence -----------------------------------------------------------------------------
def parse_sequence(seq):
    """Return (resolution, tempo_us, events) with events (tick, status, a, b)."""
    if seq[:4] != b'pQES':
        raise ValueError('Music sequence header not recognised')
    resolution = struct.unpack_from('>H', seq, 8)[0] or 480
    tempo = int.from_bytes(seq[10:13], 'big') or 500000
    p = 15; running = None; tick = 0; events = []
    while p < len(seq):
        delta = 0
        while True:
            c = seq[p]; p += 1; delta = (delta << 7) | (c & 127)
            if c < 128:
                break
        tick += delta
        status = seq[p]
        if status >= 0x80:
            p += 1
        else:
            status = running
            if status is None:
                raise ValueError('Music sequence data is malformed')
        if status == 0xFF:
            kind = seq[p]; p += 1
            if kind == 0x51:
                events.append((tick, 0x51, int.from_bytes(seq[p:p + 3], 'big'), 0)); p += 3; running = 0xFF; continue  # Sony SEQ: running status also repeats tempo events
            if kind == 0x2F:
                events.append((tick, 0x2F, 0, 0)); break
            raise ValueError(f'Unsupported sequence meta event {kind:02X}')
        running = status; high = status & 0xF0
        if high in (0xC0, 0xD0):
            events.append((tick, status, seq[p], 0)); p += 1
        else:
            events.append((tick, status, seq[p], seq[p + 1])); p += 2
    return resolution, tempo, events


def schedule(seq, seconds):
    """Flatten the sequence into timed note/controller events, following its loop."""
    resolution, tempo, events = parse_sequence(seq)
    loop_index = None; end_index = None
    for i, (tick, status, a, b) in enumerate(events):
        if status & 0xF0 == 0xB0 and a == 99:
            if b == 20 and loop_index is None:
                loop_index = i
            elif b == 30:
                end_index = i
    out = []; now = 0.0; last_tick = events[0][0] if events else 0; i = 0; passes = 0
    while i < len(events) and now < seconds:
        tick, status, a, b = events[i]
        now += (tick - last_tick) * tempo / resolution / 1e6; last_tick = tick
        if status == 0x51:
            tempo = a
        elif status == 0x2F:
            break
        else:
            out.append((now, status, a, b))
        if i == end_index and loop_index is not None and passes < 50:
            passes += 1; i = loop_index; last_tick = events[i][0]; continue
        i += 1
    return out


# ---- envelope -----------------------------------------------------------------------------
def _rate(rate, increase, exponential):
    """(samples per step, step) for one SPU ADSR rate."""
    shift = rate >> 2
    cycles = 1 << max(0, shift - 11)
    step = (7 - (rate & 3)) if increase else (-8 + (rate & 3))
    step <<= max(0, 11 - shift)
    return cycles, step


def envelope_points(adsr1, adsr2, hold, rate):
    """Piecewise-linear (time, level 0..1) approximation of the SPU envelope.

    hold is the key-on duration in seconds; the release follows it."""
    scale = SPU_RATE / rate
    attack_exp = bool(adsr1 & 0x8000); attack = (adsr1 >> 8) & 0x7F
    decay = (adsr1 >> 4) & 15; sustain_level = min(1.0, ((adsr1 & 15) + 1) * 0x800 / 0x7FFF)
    sustain_exp = bool(adsr2 & 0x8000); sustain_down = bool(adsr2 & 0x4000)
    sustain_rate = (adsr2 >> 6) & 0x7F; release_exp = bool(adsr2 & 0x20); release = adsr2 & 31

    def linear_time(rate_value, increase, span, exponential=False):
        cycles, step = _rate(rate_value, increase, exponential)
        if step == 0:
            return 1e9
        samples = abs(span * 0x7FFF / step) * cycles
        if exponential and increase:
            samples *= 1.75  # above 0x6000 the SPU rises 4x slower
        return samples / SPU_RATE

    def exp_time(rate_value, start, end):
        cycles, step = _rate(rate_value, False, True)
        k = abs(step) / 0x8000  # fraction lost per step
        if k <= 0 or start <= end:
            return 0.0
        if k >= 1:
            return cycles / SPU_RATE
        return math.log(max(end, 1e-4) / start) / math.log(1 - k) * cycles / SPU_RATE

    points = [(0.0, 0.0)]
    t = linear_time(attack, True, 1.0, attack_exp); points.append((t, 1.0))
    t2 = t + exp_time(decay * 4, 1.0, sustain_level); points.append((t2, sustain_level))
    level = sustain_level
    if t2 < hold:
        if sustain_down:
            span = exp_time(sustain_rate, level, 0.001) if sustain_exp else linear_time(sustain_rate, False, level)
            end_level = 0.0 if span <= hold - t2 else level * (1 - (hold - t2) / max(span, 1e-9))
            if sustain_exp and span > 0:
                end_level = level * (0.001 / level) ** min(1.0, (hold - t2) / span)
            points.append((hold, max(0.0, end_level))); level = max(0.0, end_level)
        else:
            span = linear_time(sustain_rate, True, 1 - level, sustain_exp)
            end_level = min(1.0, level + (1 - level) * (hold - t2) / max(span, 1e-9))
            points.append((hold, end_level)); level = end_level
    else:
        points = [(pt, lv) for pt, lv in points if pt <= hold]
        prev = points[-1]
        points.append((hold, prev[1] if prev[0] == hold else min(1.0, prev[1] + 0.0)))
        level = points[-1][1]
    if release_exp:
        rel = exp_time(release * 4, max(level, 1e-4), 0.001)
        # approximate the exponential tail with a few segments
        for f in (0.25, 0.5, 1.0):
            points.append((hold + rel * f, level * (0.001 / max(level, 1e-4)) ** f if level > 0 else 0.0))
    else:
        points.append((hold + linear_time(release * 4, False, level), 0.0))
    return points


# ---- rendering ----------------------------------------------------------------------------
class Voice:
    __slots__ = ('start', 'end', 'note', 'velocity', 'tone', 'channel')


def collect_notes(timeline, bank):
    """Pair note-ons with note-offs; also returns per-channel controller histories."""
    channels = [dict(program=0, volume=100, expression=127, pan=64, bend=[(0.0, 0)]) for _ in range(16)]
    active = {}; notes = []
    for time, status, a, b in timeline:
        ch = status & 15; kind = status & 0xF0; state = channels[ch]
        if kind == 0xC0:
            state['program'] = a
        elif kind == 0xB0:
            if a == 7: state['volume'] = b
            elif a == 11: state['expression'] = b
            elif a == 10: state['pan'] = b
        elif kind == 0xE0:
            value = ((b << 7) | a) - 8192 if b or a else 0
            state['bend'].append((time, value))
        elif kind == 0x90 and b > 0:
            key = (ch, a)
            if key in active:
                notes.append(active.pop(key) + (time,))
            active[key] = (time, ch, a, b, state['program'], state['volume'] * state['expression'] / (127 * 127), state['pan'])
        elif kind in (0x80, 0x90):
            key = (ch, a)
            if key in active:
                notes.append(active.pop(key) + (time,))
    end = timeline[-1][0] if timeline else 0.0
    for start in active.values():
        notes.append(start + (end,))
    return notes, channels


def _bend_at(history, time):
    value = 0
    for t, v in history:
        if t > time:
            break
        value = v
    return value


def render_basic(seq, header, body, seconds=60.0, rate=None):
    """Return (rate, interleaved int16 stereo samples as a list or numpy array)."""
    try:
        import numpy as np
    except ImportError:
        np = None
    rate = rate or (44100 if np is not None else 22050)
    bank = Bank(header, body)
    timeline = schedule(seq, seconds)
    notes, channels = collect_notes(timeline, bank)
    length = int(seconds * rate) + rate
    master = bank.mvol / 127 if bank.mvol else 1.0
    if np is not None:
        left = np.zeros(length, dtype=np.float64); right = np.zeros(length, dtype=np.float64)
    else:
        left = [0.0] * length; right = [0.0] * length
    for start, ch, note, velocity, program, channel_volume, channel_pan, stop in notes:
        if start >= seconds:
            continue
        for tone in bank.tones.get(program, []):
            if not tone['low'] <= note <= tone['high']:
                continue
            pcm, loop_start, loops = bank.sample(tone['vag'])
            if not pcm:
                continue
            program_row = bank.programs[program]
            amp = (velocity / 127) * (tone['vol'] / 127) * (program_row['vol'] / 127 if program_row['vol'] else 1) * channel_volume * master
            pan = max(0.0, min(1.0, (channel_pan + tone['pan'] - 64) / 127))
            gl, gr = amp * math.cos(pan * math.pi / 2), amp * math.sin(pan * math.pi / 2)
            env = envelope_points(tone['adsr1'], tone['adsr2'], max(0.0, stop - start), rate)
            duration = min(env[-1][0], seconds - start + 0.5)
            count = int(duration * rate)
            if count <= 0:
                continue
            bend = _bend_at(channels[ch]['bend'], start)
            bend_range = tone['pbmax'] if bend >= 0 else tone['pbmin']
            semis = note - tone['center'] + tone['fine'] / 128  # sample's own pitch is center - fine/128 (measured) + (bend / 8192) * (bend_range or 2)
            step = 2 ** (semis / 12) * SPU_RATE / rate
            first = int(start * rate)
            count = min(count, length - first)
            if count <= 0:
                continue
            size = len(pcm)
            if np is not None:
                pos = np.arange(count, dtype=np.float64) * step
                if loop_start is not None and size > loop_start:
                    span = size - loop_start
                    over = pos >= size
                    pos[over] = loop_start + np.mod(pos[over] - loop_start, span)
                    idx = pos.astype(np.int64)
                else:
                    idx = pos.astype(np.int64); valid = idx < size
                    count = int(valid.sum()) if not valid.all() else count
                    idx = idx[:count]
                if count <= 0:
                    continue
                data = np.asarray(pcm, dtype=np.float64)[idx]
                times = np.arange(count) / rate
                et, ev = zip(*env)
                data *= np.interp(times, et, ev)
                left[first:first + count] += data * gl; right[first:first + count] += data * gr
            else:
                pts = env; seg = 0
                for k in range(count):
                    p = k * step
                    if p >= size:
                        if loop_start is None:
                            break
                        p = loop_start + (p - loop_start) % (size - loop_start)
                    t = k / rate
                    while seg + 1 < len(pts) - 1 and pts[seg + 1][0] < t:
                        seg += 1
                    (t0, v0), (t1, v1) = pts[seg], pts[min(seg + 1, len(pts) - 1)]
                    level = v1 if t >= t1 or t1 <= t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
                    sample = pcm[int(p)] * level
                    left[first + k] += sample * gl; right[first + k] += sample * gr
    end = int(seconds * rate)
    if np is not None:
        left = left[:end]; right = right[:end]
        stereo = np.empty(end * 2); stereo[0::2] = left; stereo[1::2] = right
        return rate, stereo
    stereo = []
    for l, r in zip(left[:end], right[:end]):
        stereo.extend((l, r))
    return rate, stereo


def render(seq, header, body, seconds=60.0, rate=None):
    try:
        import music_render_hq
        return music_render_hq.render(seq, header, body, seconds, rate or 44100)
    except ImportError:
        return render_basic(seq, header, body, seconds, rate)


def to_wav(rate, stereo, volume):
    """Peak-normalise, apply the listening volume (0..1) and pack as a WAV file."""
    if not 0 <= volume <= 1:
        raise ValueError('Preview volume must be 0..100%')
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None and not isinstance(stereo, list):
        peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
        gain = (0.9 * 32767 / peak if peak else 0.0) * volume
        frames = np.clip(np.round(stereo * gain), -32768, 32767).astype('<i2').tobytes()
    else:
        peak = max((abs(v) for v in stereo), default=0.0)
        gain = (0.9 * 32767 / peak if peak else 0.0) * volume
        frames = struct.pack('<' + 'h' * len(stereo), *(max(-32768, min(32767, round(v * gain))) for v in stereo))
    out = io.BytesIO()
    with wave.open(out, 'wb') as writer:
        writer.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        writer.writeframes(frames)
    return out.getvalue()
