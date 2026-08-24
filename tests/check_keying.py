#!/usr/bin/env python3
"""Consistency check: items.md and hand-scoring.md must match score.py.
Also hand-scores the two synthetic answer files using only the hand table and
compares bands/archetype with score.py. Run: python3 tests/check_keying.py"""
import os, re, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills", "profile")
spec = importlib.util.spec_from_file_location("score", os.path.join(SK, "scripts", "score.py"))
score = importlib.util.module_from_spec(spec); spec.loader.exec_module(score)

def read(p): return open(os.path.join(SK, "references", p), encoding="utf-8").read()

# 1. items.md rows == score.ITEMS
rows = re.findall(r"^\| (\d+) \| (\w+) \| ([+-]) \| (.+?) \|$", read("items.md"), re.M)
assert len(rows) == 40, len(rows)
for (n, f, k, t), it in zip(rows, score.ITEMS):
    assert (int(n), f, k, t) == (it["n"], it["facet"], it["key"], it["text"]), (n, it)
facets = [f[0] for f in score.FACETS]
assert all(it["facet"] == facets[(it["n"]-1) % 8] for it in score.ITEMS)
for code in facets:
    keys = [it["key"] for it in score.ITEMS if it["facet"] == code]
    assert sorted(keys) == ["+", "+", "+", "-", "-"], (code, keys)

# 2. hand-scoring.md direct/reversed item lists == score.ITEMS
hand = {}
for code, d, r in re.findall(r"^\| (\w{3}) [^|]+\| ([\d, ]+) \| ([\d, ]+) \|$", read("hand-scoring.md"), re.M):
    hand[code] = ({int(x) for x in d.split(",")}, {int(x) for x in r.split(",")})
assert set(hand) == set(facets), hand.keys()
for code in facets:
    d = {it["n"] for it in score.ITEMS if it["facet"] == code and it["key"] == "+"}
    r = {it["n"] for it in score.ITEMS if it["facet"] == code and it["key"] == "-"}
    assert hand[code] == (d, r), code

# 3. band cutoffs stated in hand-scoring.md and interpretation text
txt = read("hand-scoring.md")
assert "low 5–12 · mid 13–17 · high 18–25" in txt
assert score.BANDS == [(5, 12, "low"), (13, 17, "mid"), (18, 25, "high")]

# 4. hand-score the synthetic files using ONLY the parsed hand table
def hand_band(s): return "low" if s <= 12 else "mid" if s <= 17 else "high"
def hand_arch(b):  # transcribed from the table in hand-scoring.md
    o, s = b["ORD"], b["SDI"]
    if o == "high" and s == "high": return "Архитектор"
    if o == "high": return "Хранитель"
    if s == "high": return "Партизан"
    if s == "low": return "Охотник"
    return "Исследователь" if b["VAR"] == "high" else "Ремесленник"
for name in ("answers-hunter.txt", "answers-architect.txt"):
    vals = score.parse_answers(os.path.join(ROOT, "tests", name))
    hb = {}
    for code in facets:
        d, r = hand[code]
        hb[code] = hand_band(sum(vals[i-1] for i in d) + sum(6 - vals[i-1] for i in r))
    res = score.score(vals)
    sb = {f["code"]: f["band"] for f in res["facets"]}
    assert hb == sb, (name, hb, sb)
    assert hand_arch(hb) == res["archetype"], name
    print(f"{name}: hand table == score.py -> {hb} / {res['archetype']}")

# 5. archetype rule covers all 9 ORD×SDI cells (×3 VAR)
names = {score.archetype({"ORD": o, "SDI": s, "VAR": v}) for o in ("low","mid","high") for s in ("low","mid","high") for v in ("low","mid","high")}
assert names == {"Архитектор","Хранитель","Партизан","Охотник","Исследователь","Ремесленник"}, names
print("OK: keying, hand table, bands and archetype rules are consistent")
