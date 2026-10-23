#!/usr/bin/env python3
"""Merge new headlines into headlines/DATE.json without touching existing papers.

Usage: python3 scripts/add_headlines.py YYYY-MM-DD new.json
new.json: {slug: [[original, persian], ...]}. Slugs already present are kept as they are.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
date, new = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
hp = os.path.join(ROOT, "headlines", f"{date}.json")
heads = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
added = [s for s in new if s not in heads]
for s in added:
    heads[s] = new[s]
json.dump(heads, open(hp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"added {len(added)} papers ({sum(len(new[s]) for s in added)} headlines); skipped existing: {[s for s in new if s not in added]}")
