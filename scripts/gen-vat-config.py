#!/usr/bin/env python3
"""Regenerate vat.config.json from the current HTML.

Run this after any edit that changes a VAT-sensitive figure - a rate, a
regional range, or the wording around them. apply-vat.py matches whole lines,
so if the HTML moves and this is not re-run, the 1 October / 1 April switch
fails and the site is left showing the wrong VAT basis.

TOK maps each including-VAT figure to its excluding-VAT counterpart. Keep it in
step with the pages; every entry must appear somewhere in the HTML or it is
silently inert.

The pages may be in either state when this runs. If the VAT callout is the
0% wording the HTML is read as the "zero" state and the 5% variants are
reconstructed from it; otherwise it is read as the "pre" state as before.
"""

import collections
import io
import json
import re

ROOT = __file__.rsplit("/", 2)[0] + "/"
FILES = ["index.html", "best-octopus-go-alternative.html",
         "best-octopus-intelligent-go-alternatives.html"]

# including VAT at 5%  ->  excluding VAT (what you pay in the 0% window)
TOK = [
    ("6.99p", "6.66p"),      # EDF Go Electric off-peak
    ("9.87p", "9.40p"),      # Octopus Go off-peak
    ("8.40p", "8.00p"),      # Intelligent Octopus Go off-peak
    ("37–41p", "35–39p"),    # Octopus Go peak range
    ("35–39p", "33–37p"),    # EDF 12m peak range
    ("39–44p", "37–42p"),    # Intelligent Octopus Go peak range
    ("33–37p", "31–35p"),    # EDF Go Electric 18m peak range
    ("43–69p", "41–65p"),    # Octopus Go standing charge range
    ("45–72p", "43–68p"),    # Intelligent Octopus Go standing charge range
    ("50–76p", "48–73p"),    # EDF 12m standing charge range
    ("45–71p", "43–67p"),    # EDF 18m standing charge range
]

HINT_RE = re.compile(r'<span class="vat-note">[^<]*</span>')

VAT_PRE = (" All figures include VAT at 5%. Note that VAT on domestic electricity in Great Britain "
           "drops from 5% to 0% between 1 October 2026 and 31 March 2027, which will cut every rate "
           "here by about 4.8% — suppliers' own quotes may already be shown at 0%.")
VAT_ZERO = (" All figures are shown at 0% VAT: the Government cut VAT on domestic electricity in Great "
            "Britain from 5% to 0% on 1 October 2026, and it is due to return to 5% on 1 April 2027.")
VAT_POST = (" All figures include VAT at 5%, which is the rate that resumed on 1 April 2027 after the "
            "temporary 0% window.")

CALL_ZERO = ('      <p><strong>VAT on domestic electricity is currently 0%.</strong> Every figure below is '
             'shown at 0% VAT, which is what you actually pay. The Government cut VAT on domestic '
             'electricity in Great Britain from 5% to 0% on 1 October 2026; it is due to return to 5% on '
             '1 April 2027, at which point these rates rise by about 5%.</p>')
CALL_PRE = ('      <p><strong>Heads up &#8212; VAT on electricity drops to 0% on 1 October 2026.</strong> The '
            'figures below include VAT at 5%. From 1 October until 31 March 2027 the Government has cut VAT '
            'on domestic electricity in Great Britain to 0%, so every rate here falls by about 4.8%. This '
            'page switches over automatically on the day.</p>')
CALL_POST = ('      <p><strong>VAT on domestic electricity returned to 5% on 1 April 2027.</strong> Every '
             'figure below includes VAT at 5%. The temporary 0% rate applied between 1 October 2026 and '
             '31 March 2027 and has now ended.</p>')


def swap(text, reverse=False):
    """inc -> ex (or ex -> inc), via placeholders so one token's output can't be re-matched."""
    pairs = [(b, a) for a, b in TOK] if reverse else list(TOK)
    for i, (a, _) in enumerate(pairs):
        text = text.replace(a, "\x00%d\x00" % i)
    for i, (_, b) in enumerate(pairs):
        text = text.replace("\x00%d\x00" % i, b)
    return text


def main():
    pairs = collections.OrderedDict()
    texts = {name: io.open(ROOT + name, encoding="utf-8").read() for name in FILES}
    source = "zero" if any(CALL_ZERO in t for t in texts.values()) else "pre"
    print("reading the pages as the %r state" % source)
    for name in FILES:
        text = texts[name]
        lines = text.split("\n")
        for line in lines:
            if source == "pre":
                if not (HINT_RE.search(line) or any(a in line for a, _ in TOK)):
                    continue
                if lines.count(line) != 1:
                    raise SystemExit("ambiguous line in %s: %r" % (name, line[:80]))
                pre = line
                zero = swap(HINT_RE.sub("", line))
                post = HINT_RE.sub("", line)
                if VAT_PRE in line:                   # the table note carries its own wording
                    zero = swap(line).replace(swap(VAT_PRE), VAT_ZERO)
                    post = line.replace(VAT_PRE, VAT_POST)
            else:
                if not (VAT_ZERO in line or any(b in line for _, b in TOK)):
                    continue
                if lines.count(line) != 1:
                    raise SystemExit("ambiguous line in %s: %r" % (name, line[:80]))
                zero = line
                inc = swap(line, reverse=True)
                pre = inc.replace(VAT_ZERO, VAT_PRE)
                post = inc.replace(VAT_ZERO, VAT_POST)
            if zero == line and post == line and pre == line:
                continue
            pairs.setdefault(name, []).append({"pre": pre, "zero": zero, "post": post})

        if source == "pre":
            call = re.search(r'      <p><strong>Heads up.*?</p>', text, re.S)   # the VAT callout
            if call:
                pairs.setdefault(name, []).append(
                    {"pre": call.group(0), "zero": CALL_ZERO, "post": CALL_POST})
        elif CALL_ZERO in text:
            pairs.setdefault(name, []).append({"pre": CALL_PRE, "zero": CALL_ZERO, "post": CALL_POST})
        print("%-46s %2d state-dependent blocks" % (name, len(pairs.get(name, []))))

    cfg = {
        "_comment": ("VAT state for UK domestic electricity. scripts/apply-vat.py picks the state from "
                     "today's date and rewrites each block to that state's variant. Regenerate with "
                     "scripts/gen-vat-config.py after changing any rate or range in the pages."),
        "states": {"pre": {"until": "2026-10-01"},
                   "zero": {"from": "2026-10-01", "until": "2027-04-01"},
                   "post": {"from": "2027-04-01"}},
        "timezone": "Europe/London",
        "replacements": pairs,
    }
    with io.open(ROOT + "vat.config.json", "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("total:", sum(len(v) for v in pairs.values()))


if __name__ == "__main__":
    main()
