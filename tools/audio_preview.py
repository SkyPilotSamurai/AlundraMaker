"""Play music tracks and sound effects from any editor menu, at a chosen volume.

The volume (0-100 %) is one shared setting, remembered in the editor
preferences. Previews are peak-normalised and then scaled by that volume, so
music and sound effects play at a similar loudness. Music and sounds come from the Alundra remake's game-accurate renders
(assets/engine/audio: music_game NN.ogg, sfx NNN.ogg), played with pygame -
in the editor itself if its Python has pygame, otherwise through
music_player.py run by a Python that has it (the remake's). Without
those files or pygame, music is rendered by music_preview (first
MUSIC_SECONDS seconds, following the track's loop) and played with winsound.
"""
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'game' / 'editor-audio-cache'
MUSIC_SECONDS = 90
SLOW_SECONDS = 40  # without numpy the pure-Python renderer is slower
DEFAULT_VOLUME = 40


def volume_var(editor):
    var = getattr(editor, 'audio_volume_var', None)
    if var is None:
        from editor_preferences import load_preferences
        try:
            value = int(load_preferences().get('preview_volume', DEFAULT_VOLUME))
        except (TypeError, ValueError):
            value = DEFAULT_VOLUME
        var = tk.IntVar(master=editor.root, value=max(0, min(100, value)))
        editor.audio_volume_var = var

        def remember(*_):
            try:
                from editor_preferences import save_preferences
                save_preferences({'preview_volume': int(var.get())})
            except (OSError, ValueError, tk.TclError):
                pass
        var.trace_add('write', remember)
    return var


def volume(editor):
    try:
        return max(0, min(100, int(volume_var(editor).get()))) / 100
    except (ValueError, tk.TclError):
        return DEFAULT_VOLUME / 100


def _winsound():
    try:
        import winsound
    except ImportError:
        raise ValueError('Audio preview playback needs Windows') from None
    return winsound


REMAKE_AUDIO = ROOT / 'assets' / 'engine' / 'audio'
_player = {'proc': None, 'python': None}


def remake_file(kind, number):
    """The remake's render of a music track or sound record, if it exists."""
    path = REMAKE_AUDIO / ('music_game' if kind == 'music' else 'sfx') / (f'{number:02d}.ogg' if kind == 'music' else f'{number:03d}.ogg')
    return path if path.is_file() else None


def _inprocess_pygame():
    try:
        import os
        os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100)
        return pygame
    except Exception:
        return None


def _helper_python():
    """A Python with pygame for music_player.py (found once, then remembered)."""
    if _player['python'] is not None:
        return _player['python'] or None
    import shutil, subprocess, sys
    try:   # remembered from an earlier session: no slow search on every start
        from editor_preferences import load_preferences
        saved = load_preferences().get('audio_helper_python')
        if saved and Path(saved[0]).is_file():
            _player['python'] = saved
            return saved
    except Exception:
        pass
    # The exe build's sys.executable is Alundra Maker itself, not a Python.
    candidates = [] if getattr(sys, 'frozen', False) or not Path(sys.executable).name.lower().startswith('python') else [[sys.executable]]
    for name in ('pythonw', 'python', 'pyw', 'py'):
        found = shutil.which(name)
        if found:
            candidates.append([found, '-3'] if name in ('py', 'pyw') else [found])
    flags = 0x08000000 if sys.platform == 'win32' else 0   # no console window
    for cmd in candidates:
        try:
            ok = subprocess.run(cmd + ['-c', 'import pygame'], capture_output=True, timeout=20, creationflags=flags).returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        if ok:
            _player['python'] = cmd
            try:
                from editor_preferences import save_preferences
                save_preferences({'audio_helper_python': cmd})
            except Exception:
                pass
            return cmd
    _player['python'] = []
    return None


def warm_up():
    """Find the audio player once, in the background, so the first Play is instant."""
    def work():
        if _inprocess_pygame() is None:
            _helper_python()
    threading.Thread(target=work, daemon=True).start()


def _play_remake(editor, path, kind, level):
    """True if the remake's render is playing."""
    pygame = _player.get('pygame')
    if pygame is None:
        pygame = _player['pygame'] = _inprocess_pygame() or False
    if pygame is not None:
        try:
            if kind == 'music':
                pygame.mixer.music.load(str(path)); pygame.mixer.music.set_volume(level); pygame.mixer.music.play(loops=-1)
            else:
                sound = pygame.mixer.Sound(str(path)); sound.set_volume(level); sound.play()
                _player['sound'] = sound
            return True
        except Exception:
            pass
    cmd = _helper_python()
    if not cmd:
        return False
    import subprocess, sys
    flags = 0x08000000 if sys.platform == 'win32' else 0
    try:
        _player['proc'] = subprocess.Popen(cmd + [str(ROOT / 'tools' / 'music_player.py'), str(path), f'{level:.3f}', kind],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        return True
    except OSError:
        return False


def _stop_remake():
    proc = _player.get('proc')
    if proc is not None and proc.poll() is None:
        try:
            proc.kill()   # hard stop: pygame ignores a polite terminate
        except OSError:
            pass
    _player['proc'] = None
    try:
        import sys
        pygame = sys.modules.get('pygame')
        if pygame is not None and pygame.mixer.get_init():
            pygame.mixer.music.stop(); pygame.mixer.stop()
    except Exception:
        pass


def stop(editor=None):
    _stop_remake()
    try:
        _winsound().PlaySound(None, 0)
    except ValueError:
        pass
    if editor is not None:
        editor.audio_request = getattr(editor, 'audio_request', 0) + 1


def _play_wav(data, name='preview.wav'):
    winsound = _winsound()
    CACHE.mkdir(parents=True, exist_ok=True)
    winsound.PlaySound(None, 0)
    path = CACHE / name
    path.write_bytes(data)
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def _status(editor, text):
    status = getattr(editor, 'status', None)
    if status is not None:
        try:
            status.set(text)   # main thread only
        except (tk.TclError, RuntimeError):
            pass


def play_sound(editor, sound_id):
    path = remake_file('sfx', int(sound_id))
    if path is not None:
        stop(editor)
        if _play_remake(editor, path, 'sfx', volume(editor)):
            return
    from sound_database import library_for_editor
    import music_preview
    library = library_for_editor(editor)
    if library is None:
        raise ValueError('Open game data to preview its sounds')
    pcm = library.pcm(int(sound_id))
    stereo = [v for value in pcm for v in (value, value)]
    _winsound()
    stop(editor)
    _play_wav(music_preview.to_wav(44100, stereo, volume(editor)))


def preview_seconds():
    try:
        import numpy  # noqa: F401
        return MUSIC_SECONDS
    except ImportError:
        return SLOW_SECONDS


def music_audio(editor, track):
    """(rate, stereo) for one track, cached per game data."""
    from sound_database import library_for_editor
    from music_database import music_rows
    import music_preview
    library = library_for_editor(editor)
    if library is None:
        raise ValueError('Open game data to preview its music')
    cache = library.__dict__.setdefault('music_preview_cache', {})
    if track not in cache:
        row = music_rows(library.exe, library.sound)[track]
        sound = library.sound
        cache[track] = music_preview.render(sound[row['sequence_offset']:row['header_offset']],
                                            sound[row['header_offset']:row['body_offset']],
                                            sound[row['body_offset']:row['end_offset']], preview_seconds())
    return cache[track]


def play_music(editor, track):
    track = int(track)
    stop(editor)
    if track <= 0:
        _status(editor, 'No Music: nothing to play.')
        return
    path = remake_file('music', track)
    if path is not None:
        from game_audio_names import music_name
        name = music_name(editor.database.document, track); level = volume(editor)
        request = getattr(editor, 'audio_request', 0)
        _status(editor, f'Playing {track:03d} - {name}…')
        if _player.get('pygame'):   # in-process: immediate
            if _play_remake(editor, path, 'music', level):
                _status(editor, f'Playing {track:03d} - {name}.')
                return
        else:   # start the player off the main thread so the editor never freezes
            done = {}
            def start():
                if getattr(editor, 'audio_request', 0) == request:
                    done['ok'] = _play_remake(editor, path, 'music', level)
            def check():
                if getattr(editor, 'audio_request', 0) != request:return
                if 'ok' not in done:editor.root.after(50, check);return
                if done['ok']:_status(editor, f'Playing {track:03d} - {name}.')
                else:_render_and_play(editor, track)
            threading.Thread(target=start, daemon=True).start()
            editor.root.after(50, check)
            return
    _render_and_play(editor, track)


def _render_and_play(editor, track):
    _winsound()
    request = editor.audio_request
    level = volume(editor)
    from game_audio_names import music_name
    name = music_name(editor.database.document, track)
    _status(editor, f'Preparing music preview: {name}…')

    result = {}

    def work():
        # Rendering only; Tk and playback stay on the main thread.
        import music_preview
        try:
            rate, stereo = music_audio(editor, track)
            result['wav'] = music_preview.to_wav(rate, stereo, level)
        except Exception as exc:
            result['error'] = exc

    def poll():
        if getattr(editor, 'audio_request', 0) != request:
            return
        if 'error' in result:
            _status(editor, f'Music preview failed: {result["error"]}')
        elif 'wav' in result:
            _play_wav(result['wav'])
            _status(editor, f'Playing {track:03d} - {name} (preview, first {preview_seconds()} s).')
        else:
            editor.root.after(100, poll)
    threading.Thread(target=work, daemon=True).start()
    editor.root.after(100, poll)


class PreviewBar:
    """Play / Stop / Volume controls. get_id returns the selected track or sound ID."""

    def __init__(self, parent, editor, kind, get_id):
        self.editor = editor; self.kind = kind; self.get_id = get_id
        self.frame = ttk.Frame(parent)
        ttk.Button(self.frame, text='Play', width=7, command=lambda: editor.guard(self.play)).pack(side='left')
        ttk.Button(self.frame, text='Stop', width=7, command=lambda: stop(editor)).pack(side='left', padx=(4, 10))
        ttk.Label(self.frame, text='Volume').pack(side='left')
        var = volume_var(editor)
        ttk.Scale(self.frame, from_=0, to=100, orient='horizontal', length=120,
                  command=lambda value: var.set(round(float(value)))).pack(side='left', padx=4)
        self.frame.winfo_children()[-1].set(var.get())
        ttk.Label(self.frame, textvariable=var, width=3).pack(side='left')
        ttk.Label(self.frame, text='%').pack(side='left')

    def play(self):
        value = self.get_id()
        if value is None or value == '':
            raise ValueError('Choose a track first' if self.kind == 'music' else 'Choose a sound first')
        (play_music if self.kind == 'music' else play_sound)(self.editor, int(value))


import atexit
atexit.register(_stop_remake)   # never leave the music player running after the editor exits
