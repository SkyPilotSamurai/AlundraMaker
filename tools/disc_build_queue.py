"""Serialize temporary disc builds across editor and QA processes."""
import os
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def build_slot(path,progress=lambda text:None,timeout=1200):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        def lock():
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        started=time.monotonic();announced=False
        while True:
            try:lock();break
            except OSError:
                if not announced:
                    progress('Waiting for another game build to finish…');announced=True
                if time.monotonic()-started>=timeout:
                    raise ValueError('Another game build is still running. Try again after it finishes.')
                time.sleep(.1)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_UN)
        # Keep the lock file: removing it could let two processes lock different
        # files at the same pathname. The OS releases ownership on process exit.
