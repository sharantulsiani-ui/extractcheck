"""Command-line entry point."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import build_synthetic_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="extractcheck")
    subparsers = parser.add_subparsers(dest="command", required=True)
    synthetic = subparsers.add_parser("synthetic", help="run the privacy-free four-format proof")
    synthetic.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "synthetic":
        report = build_synthetic_report(args.output)
        print(json.dumps({
            "all_passed": report["all_passed"],
            "network_attempts": report["network_attempts"],
            "report_sha256": report["report_sha256"],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
