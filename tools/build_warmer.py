"""Get the next build ready while you work (user 2026-10-16: "whatever makes the
program function better").

When the editor has been left alone for a few seconds after an edit, a
background thread compiles the project's events exactly as Build does, into the
same per-map cache (event_group_cache). Build & test then finds every unchanged
map ready and only compiles what changed since.
* Nothing is written but that cache: no project file, no game data, no Tk.
* It works on a snapshot taken on the UI thread (game data + Database), the same
  snapshot Build takes, so the cache keys match.
* It steps aside between maps while you click, type or scroll, while the editor
  is busy, and stops for good when a build starts, another game is opened or the
  edits change again (the next quiet moment starts over).
* Build and the warm-up never compile at the same moment (new_event_compile
  COMPILE_LOCK; the per-thread stock-map hint in stock_donors)."""
import json
import threading
import time
import hashlib

IDLE_SECONDS = 4.0      # this long without a click / key / scroll before warming
CHECK_EVERY_MS = 1000


class Stop(Exception):
    pass


class BuildWarmer:
    def __init__(self, editor):
        self.editor = editor
        self.thread = None
        self.cancel = threading.Event()
        self.last_key = None          # edits the last finished warm-up was made for
        self.running_key = None
        self.last_activity = time.monotonic()
        self.result = None
        self.ui_tick = time.monotonic()

    # -- UI thread -----------------------------------------------------------
    def user_active(self):
        self.last_activity = time.monotonic()

    def heartbeat(self):
        """Every 100 ms on the UI thread: a late beat means the editor is busy."""
        self.ui_tick = time.monotonic()
        try:
            self.editor.root.after(100, self.heartbeat)
        except Exception:
            pass

    def tick(self):
        """Called every second on the UI thread."""
        e = self.editor
        try:
            if self.thread is not None and self.thread.is_alive():
                return
            if getattr(e, 'build_running', False) or getattr(e, 'memory_loading', False):
                return
            if time.monotonic() - self.last_activity < IDLE_SECONDS:
                return
            session = getattr(e, 'session', None); database = getattr(e, 'database', None)
            if session is None or database is None or not database.document.get('event_graphs'):
                return
            if getattr(self, 'checked_activity', None) == self.last_activity and self.last_key is not None:
                return    # nothing done since the last look: no need to look again
            self.checked_activity = self.last_activity
            key = self.edits_key()
            if key == self.last_key:
                return
            self.start(key)
        finally:
            try:
                e.root.after(CHECK_EVERY_MS, self.tick)
            except Exception:
                pass

    def edits_key(self):
        s = self.editor.session
        stacks = [(len(s.undo_stack), id(s.undo_stack[-1]) if s.undo_stack else None)]
        stacks += [(n, len(x.undo_stack), id(x.undo_stack[-1]) if x.undo_stack else None)
                   for n, x in sorted(getattr(s, 'extra_files', {}).items())]
        db = json.dumps(self.editor.database.document, sort_keys=True, default=str)
        return (id(s), tuple(stacks), hashlib.sha1(db.encode()).hexdigest())

    def start(self, key):
        from mod_export import build_snapshot
        e = self.editor
        snapshot = build_snapshot(e.session, e.database.to_json())
        # the chest flags Build fixes before it compiles (on the snapshot's copy only)
        try:
            from new_event_compile import chest_flag_for
            doc = snapshot.content_database
            for graph in doc.get('event_graphs', []):
                if any(p.get('contained_item_class_id') for p in graph.get('pages', [])):
                    chest_flag_for(doc, graph['id'])
        except Exception:
            pass
        self.cancel.clear(); self.running_key = key
        session = e.session
        self.thread = threading.Thread(target=self.run, args=(snapshot, key, session), daemon=True, name='build-warmer')
        self.thread.start()

    def stop(self):
        self.cancel.set()

    # -- worker thread -------------------------------------------------------
    def pause(self, session):
        e = self.editor
        while True:
            if self.cancel.is_set() or getattr(e, 'build_running', False) or getattr(e, 'session', None) is not session:
                raise Stop()
            now = time.monotonic()
            busy = now - self.last_activity < 0.5 or now - self.ui_tick > 0.25
            busy = busy or getattr(e, 'map_loading', False)
            job = getattr(e, 'background_preload', None)
            if job is not None and not job.finished:
                busy = busy or job.busy_until > job.clock()   # a map is loading
            if not busy:
                return
            time.sleep(0.05)

    def run(self, snapshot, key, session):
        from event_export import _prepare_native_event_export
        import compile_yield
        started = time.monotonic()
        compile_yield.HOOK.pause = lambda: self.pause(session)
        try:
            exported = _prepare_native_event_export(snapshot, best_effort=True, pause=lambda: self.pause(session))
            self.result = {'events': len(getattr(exported, 'native_event_export_ids', ()) or ()),
                           'seconds': round(time.monotonic() - started, 1)}
            self.last_key = key
        except Stop:
            self.result = {'stopped': True}
        except Exception as exc:   # the warm-up never matters for correctness: Build compiles anyway
            self.result = {'error': str(exc)}
            self.last_key = key        # do not retry the same edits over and over
        finally:
            compile_yield.HOOK.pause = None
            self.running_key = None
