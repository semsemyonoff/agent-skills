#!/usr/bin/env python3
"""Read-only plan snapshots and strict current-version reviewer validation (stdlib)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import sys
import time

MAX_RESULT = 32 * 1024 * 1024
INPUT_TIMEOUT = 30


class InvalidReview(Exception):
    pass


def strict_json(text):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise InvalidReview("Duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise InvalidReview("Non-finite JSON constant")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidReview("Invalid, truncated or ambiguous review JSON") from None


def snapshot(plan):
    # Keep the original absolute pathname, not its symlink target. Approval of an
    # alias is not approval of a different path, even when the bytes happen to match.
    path = os.path.abspath(os.path.expanduser(os.fspath(plan)))
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise InvalidReview("Plan must be a regular UTF-8 file")
        data = source.read()
        after = os.fstat(source.fileno())
        current = os.stat(path)
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size,
                              info.st_mtime_ns, info.st_ctime_ns)
    if signature(before) != signature(after) or signature(after) != signature(current):
        raise InvalidReview("Plan changed while collecting its snapshot")
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise InvalidReview("Plan must be UTF-8") from None
    return {"plan_path": path, "plan_version": hashlib.sha256(data).hexdigest(), "plan_text": text}


def read_result(stream):
    if stream.isatty():
        raise InvalidReview("Provide reviewer JSON on finite stdin, not an interactive terminal")
    deadline = time.monotonic() + INPUT_TIMEOUT
    content = bytearray()
    if stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        content.extend(stream.read(MAX_RESULT + 1))
    else:
        with selectors.DefaultSelector() as poll:
            try:
                poll.register(stream, selectors.EVENT_READ)
            except (OSError, ValueError):
                raise InvalidReview("Reviewer stdin cannot be monitored") from None
            while True:
                seconds = deadline - time.monotonic()
                if seconds <= 0:
                    raise InvalidReview("Reviewer stdin did not reach EOF within 30 seconds")
                if not poll.select(seconds):
                    continue
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > MAX_RESULT:
                    break
    if len(content) > MAX_RESULT:
        raise InvalidReview("Reviewer JSON exceeds the 32 MiB input limit")
    try:
        return content.decode("utf-8")
    except UnicodeError:
        raise InvalidReview("Reviewer JSON must be UTF-8") from None


def exact_fields(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise InvalidReview(f"{label} must contain exactly its canonical fields")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(result, current, expected):
    exact_fields(result, ("verdict", "plan_path", "plan_version", "findings", "unknowns"), "Review")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise InvalidReview("Expected version must be a lowercase SHA-256 hex digest")
    if result["plan_path"] != current["plan_path"]:
        raise InvalidReview("Review path does not exactly match the original plan path")
    if result["plan_version"] != expected or current["plan_version"] != expected:
        raise InvalidReview("Review version is stale or does not match the expected snapshot")
    if result["verdict"] not in ("APPROVE", "NEEDS REVISION"):
        raise InvalidReview("Unsupported review verdict")
    if not isinstance(result["findings"], list) or not isinstance(result["unknowns"], list):
        raise InvalidReview("Findings and unknowns must be arrays")
    blocking = False
    for finding in result["findings"]:
        exact_fields(finding, ("severity", "section", "evidence", "impact", "fix"), "Finding")
        if finding["severity"] not in ("blocker", "nonblocking"):
            raise InvalidReview("Unsupported finding severity")
        if not all(nonempty(finding[key]) for key in ("section", "evidence", "impact", "fix")):
            raise InvalidReview("Finding section, evidence, impact and fix must be nonempty strings")
        blocking = blocking or finding["severity"] == "blocker"
    for unknown in result["unknowns"]:
        exact_fields(unknown, ("blocking", "detail"), "Unknown")
        if type(unknown["blocking"]) is not bool or not nonempty(unknown["detail"]):
            raise InvalidReview("Unknown requires boolean blocking and nonempty detail")
        blocking = blocking or unknown["blocking"]
    if (result["verdict"] == "APPROVE") == blocking:
        raise InvalidReview("Verdict contradicts blocking findings or unknowns")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("snapshot", allow_abbrev=False)
    collect.add_argument("plan", type=Path)
    check = commands.add_parser("validate", allow_abbrev=False)
    check.add_argument("plan", type=Path)
    check.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(args.plan)
        else:
            review = strict_json(read_result(sys.stdin.buffer))
            # Read after finite stdin completes: a report waiting in a pipe must
            # never validate against a snapshot collected before intervening edits.
            result = validate(review, snapshot(args.plan), args.version)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except InvalidReview as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, OverflowError, RecursionError):
        print("Plan or reviewer input could not be read or validated", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
