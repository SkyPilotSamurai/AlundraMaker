"""Let the build warm-up (build_warmer.py) step aside inside long compile work, so the
editor stays responsive (user 2026-10-27: map changes lagged). Only the thread that set
HOOK.pause is affected; Build itself never sets it."""
import threading

HOOK = threading.local()


def step():
    pause = getattr(HOOK, 'pause', None)
    if pause is not None:
        pause()
