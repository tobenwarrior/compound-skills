"""Replay a saved accepted refactor's source edits as one patch without running its code."""
from __future__ import annotations

from collections import Counter
from difflib import unified_diff
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from tempfile import TemporaryDirectory

from common import RESULTS, WORK, git

RUN = "2ce1bb32"
FIXTURE = WORK / "fixtures/shopkit"
PATHS = ("src/shopkit/payments.py", "src/shopkit/webhooks.py", "src/shopkit/retrying.py")


def source_edits(events: bytes):
    """Yield each saved Edit or Write once, with the message that issued it."""
    seen = set()
    for line in events.splitlines():
        message = json.loads(line.split(b"\t", 1)[1]).get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for tool in content:
            if tool.get("type") != "tool_use" or tool["name"] not in {"Edit", "Write"} or tool["id"] in seen:
                continue
            seen.add(tool["id"])
            name = PurePosixPath(tool["input"]["file_path"]).name
            if name in {PurePosixPath(path).name for path in PATHS}:
                yield message["id"], tool["name"], name, tool["input"]


def replay():
    folder = RESULTS / "v016b"
    record_bytes = (folder / f"{RUN}.json").read_bytes()
    events = (folder / f"{RUN}.stream").read_bytes()
    record = json.loads(record_bytes)
    if not record["valid"] or not record["outcome"]["success"] or record["task"] != "refactor-retry":
        raise ValueError("Expected the accepted saved retry refactor")
    head = git(FIXTURE, "rev-parse", "HEAD", check=True).strip()
    if head != record["fixture_head"] or git(FIXTURE, "status", "--porcelain", check=True).strip():
        raise ValueError("Expected the clean pinned shopkit fixture")
    names = {PurePosixPath(path).name: path for path in PATHS}
    original = {path: git(FIXTURE, "show", f"HEAD:{path}", check=True) for path in PATHS[:-1]}
    edited = dict(original)
    operations = Counter()
    messages = set()
    for message, tool, name, arguments in source_edits(events):
        messages.add(message)
        operations[tool] += 1
        path = names[name]
        if tool == "Write":
            if path in edited:
                raise ValueError(f"Expected a new file: {path}")
            edited[path] = arguments["content"]
        else:
            old = arguments["old_string"]
            if arguments.get("replace_all") or edited[path].count(old) != 1:
                raise ValueError(f"Saved replacement is not unique: {path}")
            edited[path] = edited[path].replace(old, arguments["new_string"], 1)
    if set(edited) != set(PATHS) or len(messages) != 1:
        raise ValueError("Expected one source-edit message covering the three source files")

    patch = "".join(
        line for path in PATHS for line in unified_diff(
            original.get(path, "").splitlines(keepends=True), edited[path].splitlines(keepends=True),
            fromfile=f"a/{path}" if path in original else "/dev/null", tofile=f"b/{path}",
        )
    ).encode()
    with TemporaryDirectory(prefix="compound-patch-replay-") as folder_path, tarfile.open(folder / f"{RUN}.final.tgz") as archive:
        scratch = Path(folder_path)
        for path, text in original.items():
            output = scratch / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text)
        subprocess.run(["git", "apply", "-"], cwd=scratch, input=patch, check=True)
        for path in PATHS:
            member = archive.getmember(path)
            if not member.isfile():
                raise ValueError(f"Expected a regular saved source file: {path}")
            with archive.extractfile(member) as saved:
                if (scratch / path).read_bytes() != saved.read():
                    raise ValueError(f"Replayed patch differs from the accepted file: {path}")

    return {
        "scope": "Source-edit phase only. Test edits and checks stay separate. No saved commands, project code or model ran.",
        "run_id": RUN,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "events_sha256": hashlib.sha256(events).hexdigest(),
        "fixture_head": head,
        "source_files": list(PATHS),
        "saved_source_edit_messages": len(messages),
        "saved_source_tool_calls": dict(sorted(operations.items())),
        "replay_patch_applications": 1,
        "byte_identical_source_files": len(PATHS),
        "saved_result_accepted": True,
    }


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
