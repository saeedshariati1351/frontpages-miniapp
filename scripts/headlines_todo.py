#!/usr/bin/env python3
"""List papers that have a cover for DATE but no headlines yet.

Usage: python3 scripts/headlines_todo.py YYYY-MM-DD
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
date = sys.argv[1]
covers = json.load(open(os.path.join(ROOT, "data", f"{date}.covers.json")))
hp = os.path.join(ROOT, "headlines", f"{date}.json")
heads = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
todo = [s for s in covers if s not in heads]
print(" ".join(todo))
