#!/usr/bin/env python3
"""Example publisher command adapter.

Reads draft JSON from stdin and returns publish result JSON to stdout.
Replace internals with your ETtoday automation integration.
"""

import json
import sys
import datetime as dt
import hashlib


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"status": "failed", "message": "empty stdin"}, ensure_ascii=False))
        return 1

    draft = json.loads(raw)

    # TODO: call your real ETtoday publisher API / selenium adapter here.
    external_id = hashlib.md5((draft.get("title") or "").encode("utf-8")).hexdigest()[:12]

    result = {
        "status": "ok",
        "external_id": external_id,
        "message": f"prototype publish accepted at {dt.datetime.utcnow().isoformat()}Z",
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
