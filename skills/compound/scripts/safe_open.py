"""Fail-closed, descriptor-based opening for repository-relative source files.

Only the POSIX implementation is enabled. Windows path-based opens cannot
provide the required component-by-component no-reparse guarantee with the
stdlib APIs used here; do not replace the Windows rejection without validating
handle-relative Win32 opens and final-path containment on real Windows.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _open_windows_nofollow(root: os.PathLike[str] | str, relative: str) -> int:
    """Reject Windows until a tested handle-relative implementation exists."""
    del root, relative
    raise OSError("safe no-reparse file access is unavailable on Windows")


def open_regular_nofollow(root: os.PathLike[str] | str, relative: str) -> int:
    """Return a read-only fd for a regular file below *root*, or fail closed.

    The caller supplies a canonical absolute root and owns the returned descriptor.
    POSIX paths are walked from the filesystem root through pinned directory
    descriptors with O_NOFOLLOW on every component; no source bytes are read.
    """
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise OSError("unsafe relative path")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise OSError("unsafe relative path")

    if os.name == "nt":
        return _open_windows_nofollow(root, relative)
    if os.name != "posix":
        raise OSError("safe no-follow file access is unavailable")
    if os.open not in getattr(os, "supports_dir_fd", set()) or not hasattr(
        os, "O_NOFOLLOW"
    ):
        raise OSError("safe no-follow file access is unavailable")

    try:
        canonical_root = Path(root)
        if not canonical_root.is_absolute() or ".." in canonical_root.parts:
            raise OSError("root must be a canonical absolute path")
    except (TypeError, ValueError) as error:
        raise OSError("canonical root is unavailable") from error

    nofollow = os.O_NOFOLLOW
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    common_flags = os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0)
    directory_fd = os.open(canonical_root.anchor, common_flags)
    try:
        if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
            raise OSError("root is not a directory")
        for part in (*canonical_root.parts[1:], *parts[:-1]):
            child_fd = os.open(part, common_flags, dir_fd=directory_fd)
            try:
                if not stat.S_ISDIR(os.fstat(child_fd).st_mode):
                    raise OSError("path component is not a directory")
            except BaseException:
                os.close(child_fd)
                raise
            os.close(directory_fd)
            directory_fd = child_fd
        file_flags = os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
        file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                raise OSError("not a regular file")
            return file_fd
        except BaseException:
            os.close(file_fd)
            raise
    finally:
        os.close(directory_fd)


__all__ = ["open_regular_nofollow"]
