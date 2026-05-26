import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock


_LOCKS = {}
_LOCKS_GUARD = RLock()


def _normalize_path(path: Path) -> str:
    return str(Path(path).resolve())


def _get_lock(path: Path) -> RLock:
    key = _normalize_path(path)
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = RLock()
            _LOCKS[key] = lock
        return lock


@contextmanager
def locked_json_path(path: Path):
    lock = _get_lock(path)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def read_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=path.parent,
            suffix=".tmp",
            encoding="utf-8",
        ) as tmp_file:
            json.dump(payload, tmp_file, ensure_ascii=False, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            temp_path = Path(tmp_file.name)

        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
