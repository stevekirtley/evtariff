#!/usr/bin/env python3
"""Switch the site between VAT states as the UK's temporary 0% electricity VAT window opens and closes.

VAT on domestic electricity in Great Britain is 5%, cut to 0% from 1 October 2026
to 31 March 2027, then 5% again. vat.config.json holds, for every line of copy
that carries a VAT-sensitive figure, one variant per state:

  pre   5% VAT, with a bracketed note showing the rate that applies from 1 Oct
  zero  the 0% VAT window - figures shown ex-VAT, notes removed
  post  5% VAT again, notes removed

The regional table in each page's JavaScript needs no rewriting: REGION_DATA is
stored ex-VAT and vatFactor() applies the right multiplier at render time.

Usage:
  python3 scripts/apply-vat.py             # decide from today's date
  python3 scripts/apply-vat.py --state zero
  python3 scripts/apply-vat.py --check     # report drift, change nothing
  python3 scripts/apply-vat.py --date 2026-10-01
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "vat.config.json"
ORDER = ["pre", "zero", "post"]


def today_in(tz):
    if ZoneInfo is None:
        return date.today()
    return datetime.now(ZoneInfo(tz)).date()


def state_for(states, today):
    for name in ORDER:
        spec = states[name]
        lo = date.fromisoformat(spec["from"]) if "from" in spec else None
        hi = date.fromisoformat(spec["until"]) if "until" in spec else None
        if (lo is None or today >= lo) and (hi is None or today < hi):
            return name
    raise SystemExit("no VAT state matches %s" % today)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", choices=ORDER + ["auto"], default="auto")
    ap.add_argument("--date", help="Pretend today is this ISO date (for testing)")
    ap.add_argument("--check", action="store_true", help="Report only; make no changes")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    today = date.fromisoformat(args.date) if args.date else today_in(cfg["timezone"])
    want_state = state_for(cfg["states"], today) if args.state == "auto" else args.state
    print(f"Date {today} ({cfg['timezone']}) -> VAT state '{want_state}'")

    changed, problems = [], []
    for name, entries in cfg["replacements"].items():
        path = ROOT / name
        original = text = path.read_text(encoding="utf-8")
        for e in entries:
            want = e[want_state]
            if want in text:
                continue
            others = [e[s] for s in ORDER if s != want_state and e[s] != want]
            found = [o for o in others if o in text]
            if len(found) == 1:
                text = text.replace(found[0], want)
            elif not found:
                problems.append(f"{name}: no variant found for {want[:70]!r}")
            else:
                text = text.replace(found[0], want)
        if text != original:
            changed.append(name)
            if not args.check:
                path.write_text(text, encoding="utf-8")

    if problems:
        print("\nPROBLEMS:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2

    label = ", ".join(changed) if changed else "nothing"
    print(("Needs updating: " if args.check else "Updated: ") + label)
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
