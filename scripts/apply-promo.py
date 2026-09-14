#!/usr/bin/env python3
"""Toggle the EDF promotional referral bonus copy on or off, based on today's date.

Reads promo.config.json, which pairs each piece of normal copy ("off") with its
promotional wording ("on"). While today falls inside the promo window every
"off" string is rewritten to its "on" form; once the window closes they are
rewritten back. Safe to run repeatedly — it is a no-op when the files already
match the required state.

Usage:
  python3 scripts/apply-promo.py            # decide from today's date
  python3 scripts/apply-promo.py --state on # force a state (on|off|auto)
  python3 scripts/apply-promo.py --check    # report drift, change nothing (exit 1 if drifted)
  python3 scripts/apply-promo.py --date 2026-10-07
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "promo.config.json"


def today_in(tz_name):
    if ZoneInfo is None:
        return date.today()
    return datetime.now(ZoneInfo(tz_name)).date()


def promo_is_live(promo, today):
    start = date.fromisoformat(promo["start"])
    end = date.fromisoformat(promo["end"])
    if promo.get("end_inclusive", True):
        end += timedelta(days=1)
    return start <= today < end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--date", help="Pretend today is this ISO date (for testing)")
    ap.add_argument("--check", action="store_true", help="Report only; make no changes")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    promo = cfg["promo"]
    fields = {k: v for k, v in promo.items() if isinstance(v, str)}

    today = date.fromisoformat(args.date) if args.date else today_in(promo["timezone"])
    if args.state == "auto":
        want_on = promo_is_live(promo, today)
    else:
        want_on = args.state == "on"

    print(f"Date {today} ({promo['timezone']}) -> promo {'ON' if want_on else 'OFF'}")

    changed, problems = [], []
    for name, pairs in cfg["replacements"].items():
        path = ROOT / name
        original = text = path.read_text(encoding="utf-8")
        for pair in pairs:
            off = pair["off"]
            on = pair["on"].format(**fields)
            want, other = (on, off) if want_on else (off, on)
            if want in text:
                if other in text:
                    problems.append(f"{name}: both states present for {want[:60]!r}")
                continue
            if other in text:
                text = text.replace(other, want)
            else:
                problems.append(f"{name}: no match for {other[:70]!r}")
        if text != original:
            changed.append(name)
            if not args.check:
                path.write_text(text, encoding="utf-8")

    if problems:
        print("\nPROBLEMS:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2

    if args.check:
        print("Needs updating: " + (", ".join(changed) if changed else "nothing"))
        return 1 if changed else 0

    print("Updated: " + (", ".join(changed) if changed else "nothing (already correct)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
