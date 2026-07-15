#!/usr/bin/env python
# Project:     GenAIDemo
# Component:   Infrastructure validation report generator
# Description: Runs the infrastructure integration tests and writes a Markdown report
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import subprocess
import sys
import time
from pathlib import Path

REPORT_PATH = Path("docs/architecture/sprint0-validation.md")
TEST_PATH = Path("tests/integration/test_infra.py")


def run_tests() -> tuple[str, float]:
    """Run the infrastructure integration tests and return raw pytest output and duration."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(TEST_PATH), "-v", "--tb=short"],
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - start
    return result.stdout + result.stderr, duration


def parse_results(output: str) -> list[dict[str, str]]:
    """Parse pytest verbose output into per-test status rows."""
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if "::" not in line or " " not in line:
            continue
        parts = line.split()
        test_id = parts[0]
        status = next((token for token in parts[1:] if token in {"PASSED", "FAILED", "ERROR", "SKIPPED"}), None)
        if status is None:
            continue
        test_name = test_id.split("::")[-1]
        rows.append({"name": test_name, "status": status})
    return rows


def write_report(rows: list[dict[str, str]], duration: float) -> None:
    """Write the Markdown validation report to docs/architecture/sprint0-validation.md."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Sprint 0 — Infrastructure Validation Report",
        "",
        "| Test Name | Status | Duration | Notes |",
        "|---|---|---|---|",
    ]
    for row in rows:
        notes = "OK" if row["status"] == "PASSED" else "See pytest output for details"
        lines.append(f"| {row['name']} | {row['status']} | {duration:.2f}s (total) | {notes} |")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Run infra validation tests and write the Markdown report; return the process exit code."""
    output, duration = run_tests()
    rows = parse_results(output)
    write_report(rows, duration)

    failed = [row for row in rows if row["status"] != "PASSED"]
    print(output)
    print(f"Report written to {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
