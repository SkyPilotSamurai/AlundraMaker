"""Load the rest of the game into memory in the background, after the map shows.

The editor opens the start map and the database properties first; everything
else (sprites, textures, scripts, dialogue of every map, class previews) is
loaded by one background thread. Whatever you open or do comes first:
* the thread pauses while you click, type or scroll, and while a map loads;
* the thread also waits whenever the editor itself is busy (opening the
  database, drawing a map...): the UI thread ticks every 50 ms, and a late
  tick means it is working, so the thread steps aside until it ticks again;
* a map you open (and the classes, when you open the database) move to the
  front of the queue, so what is still missing for them loads next.
The thread only fills caches; it never touches Tk (the status text is read by
the UI thread with a timer)."""
import struct
import threading
import time
from collections import deque

QUIET_SECONDS = 0.35   # pause this long after any click, key or scroll
UI_STALL = 0.12        # no UI tick for this long: the editor is busy, wait


class BackgroundPreload:
    def __init__(self, editor, session, database, sleep=time.sleep, clock=time.monotonic):
        from editor_asset_preload import preload_plan
        self.editor, self.session = editor, session
        self.sleep, self.clock = sleep, clock
        session._full_asset_preload = True
        self.queue = deque(preload_plan(session, database))
        self.total = len(self.queue); self.done = 0; self.errors = []
        self.lock = threading.Lock(); self.busy_until = 0.0
        self.stopped = False; self.finished = False; self.thread = None
        self.ui_tick = None   # set by the UI thread (tick); None = not watched yet

    # -- UI thread ---------------------------------------------------------
    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name='background-preload')
        self.thread.start(); return self

    def user_active(self, seconds=QUIET_SECONDS):
        self.busy_until = max(self.busy_until, self.clock() + seconds)

    def tick(self):
        self.ui_tick = self.clock()

    def prioritize(self, group):
        """Move every waiting step of `group` (('map', id) or 'class') to the front."""
        with self.lock:
            first = [item for item in self.queue if item[0] == group]
            if not first:
                return 0
            rest = [item for item in self.queue if item[0] != group]
            self.queue = deque(first + rest)
            return len(first)

    def stop(self):
        self.stopped = True

    def status_text(self):
        if self.finished:
            return ''
        return f'Loading in background {100 * self.done // max(1, self.total)}%'

    # -- worker thread -----------------------------------------------------
    def next_item(self):
        with self.lock:
            return self.queue.popleft() if self.queue else None

    def run(self):
        while not self.stopped:
            if getattr(self.editor, 'session', None) is not self.session:
                return   # another game or project was opened
            now = self.clock()
            if getattr(self.editor, 'map_loading', False):
                self.sleep(0.02); continue   # a map is opening: it gets the CPU until it shows (user 2026-10-27)
            wait = self.busy_until - now
            if wait > 0:
                self.sleep(min(wait, 0.1)); continue
            if self.ui_tick is not None and now - self.ui_tick > UI_STALL:
                self.sleep(0.02); continue   # the editor is busy: give it the CPU
            item = self.next_item()
            if item is None:
                break
            group, label, action = item
            try:
                action()
            except Exception as exc:   # one broken asset never stops the rest
                self.errors.append({'asset': label, 'error': str(exc)})
            self.done += 1
            self.sleep(0.001)   # let the UI thread run between steps
        if not self.stopped and not self.queue:
            result = {'processed': self.done, 'total': self.total, 'errors': self.errors}
            self.session.asset_preload_result = result
            self.editor.asset_preload_stats = result
            self.finished = True
