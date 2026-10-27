"""Play one of the remake's game-accurate audio renders (OGG) and exit.

  python remake_audio_player.py PATH VOLUME(0-1) music|sfx

Used by the editor's previews when the editor's own Python has no pygame:
it is started with a Python that has pygame (the one the remake uses) and
stopped by the editor (Stop, or another preview). Music loops; a sound plays once.
"""
import os, sys, time
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


def main(path, level, kind):
    pygame.mixer.init(frequency=44100)
    if kind == "music":
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(level)
        pygame.mixer.music.play(loops=-1)
        limit = time.time() + 15 * 60
        while pygame.mixer.music.get_busy() and time.time() < limit:
            time.sleep(0.1)
    else:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(level)
        channel = sound.play()
        while channel is not None and channel.get_busy():
            time.sleep(0.05)


if __name__ == "__main__":
    main(sys.argv[1], max(0.0, min(1.0, float(sys.argv[2]))), sys.argv[3])
