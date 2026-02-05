import argparse
import json
import sys
from pathlib import Path

import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="Ingestion API base URL")
    parser.add_argument("--jobs", required=True, help="Path to jobs JSON file")
    args = parser.parse_args()

    jobs_path = Path(args.jobs)
    if not jobs_path.exists():
        print(f"jobs file not found: {jobs_path}")
        return 1

    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    if not isinstance(jobs, list):
        print("jobs file must be a list")
        return 1

    for job in jobs:
        required = {"tenant_id", "source", "source_id", "url"}
        if not required.issubset(job):
            print(f"job missing fields: {job}")
            continue
        resp = requests.post(
            f"{args.api.rstrip('/')}/pull",
            json=job,
            timeout=30,
        )
        if resp.status_code >= 300:
            print(f"job failed: {job} -> {resp.status_code} {resp.text}")
        else:
            print(f"job ok: {job} -> {resp.json()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
