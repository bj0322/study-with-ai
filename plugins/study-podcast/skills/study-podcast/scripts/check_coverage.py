"""Check that report.md has a section for every extracted unit.

Usage:
    python check_coverage.py <units.json> <report.md> [--min-chars 150]

A section starts with "<!-- unit: N -->" and runs until the next marker.
Exit code 0 = every unit covered; 1 = missing or suspiciously thin sections.
Units whose source text is itself short (low_text) are held to a lower bar.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("units")
    ap.add_argument("report")
    ap.add_argument("--min-chars", type=int, default=150)
    args = ap.parse_args()

    units = json.loads(Path(args.units).read_text(encoding="utf-8"))
    report = Path(args.report).read_text(encoding="utf-8")

    parts = re.split(r"<!--\s*unit:\s*(\d+)\s*-->", report)
    sections = {}
    for i in range(1, len(parts), 2):
        uid = int(parts[i])
        sections[uid] = sections.get(uid, "") + parts[i + 1]

    expected = {u["id"]: u for u in units}
    missing = [uid for uid in expected if uid not in sections]
    unknown = [uid for uid in sections if uid not in expected]
    thin = []
    for uid, body in sections.items():
        u = expected.get(uid)
        if not u:
            continue
        bar = 40 if (u["low_text"] and not u["images"]) else args.min_chars
        size = len(re.sub(r"\s+", "", body))
        if size < bar:
            thin.append((uid, size))

    print(f"Units: {len(expected)}  Sections found: {len(sections)}")
    if missing:
        print(f"MISSING units: {missing}")
    if unknown:
        print(f"Sections for unknown unit ids: {unknown}")
    if thin:
        print("THIN sections (unit, chars): " + ", ".join(f"{u}:{c}" for u, c in thin))
    if missing or thin:
        sys.exit(1)
    print("OK - every unit is covered.")


if __name__ == "__main__":
    main()
