"""Run v0 E2E suites against the current local client and server checkouts."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import unittest
import uuid

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("contract", "agent", "all"), default="all")
    parser.add_argument("--server-repo", type=Path, default=ROOT.parent / "arepa-mcp")
    parser.add_argument("--server-python", default=sys.executable)
    parser.add_argument("--env-file", type=Path, default=ROOT / "workshop/sample-code/.env")
    args = parser.parse_args()
    if "/" in args.server_python:
        args.server_python = os.path.abspath(os.path.expanduser(args.server_python))

    if args.suite in ("agent", "all"):
        values = dotenv_values(args.env_file) if args.env_file.is_file() else {}
        for key in ("FOUNDRY_ENDPOINT", "FOUNDRY_API_KEY", "FOUNDRY_MODEL_DEPLOYMENT"):
            if key not in os.environ and values.get(key):
                os.environ[key] = values[key]
            value = os.environ.get(key, "")
            if not value or "<" in value:
                parser.error(f"{key} must be configured for the model-backed suite; use --env-file")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifacts = ROOT / ".e2e-artifacts" / f"{stamp}-{uuid.uuid4().hex[:8]}"
    artifacts.mkdir(parents=True)
    os.environ.update({
        "AREPA_SERVER_REPO": str(args.server_repo.resolve()),
        "AREPA_SERVER_PYTHON": args.server_python,
        "AREPA_E2E_ARTIFACTS": str(artifacts),
    })
    sys.path.insert(0, str(Path(__file__).parent))
    suite = unittest.TestSuite()
    for name in ("contract", "agent") if args.suite == "all" else (args.suite,):
        suite.addTests(unittest.defaultTestLoader.discover(
            str(Path(__file__).parent), pattern=f"test_{name}.py",
        ))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {
        "suite": args.suite,
        "server_repo": str(args.server_repo.resolve()),
        "client_repo": str(ROOT),
        "tests_run": result.testsRun,
        "failures": [str(test) for test, _ in result.failures],
        "errors": [str(test) for test, _ in result.errors],
        "skipped": [str(test) for test, _ in result.skipped],
        "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped,
    }
    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\nE2E artifacts: {artifacts}", flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
