#!/usr/bin/env python3
"""instill scheduler — FSRS-5 topic-level scheduling.

Usage:
  python tools/instill_sched.py today [--topic TOPIC] [--limit 8] [--new-limit 3]
  python tools/instill_sched.py review --topic TOPIC --grade {again,hard,good,easy}
  python tools/instill_sched.py enroll --topic TOPIC [--importance high|med|low] [--anchor PATH]
  python tools/instill_sched.py skip --topic TOPIC
  python tools/instill_sched.py stats

Deck state lives in instill/_deck.json. Schema:
  {
    "request_retention": 0.9,
    "topics": {
       "<topic-tag>": {
         "importance": "high|med|low",
         "anchor": str | null,            # wiki page path hint (e.g. "concepts/picd.md")
         "stability": float, "difficulty": float,
         "due": "YYYY-MM-DD", "last_review": "YYYY-MM-DD" | null,
         "reps": int, "lapses": int, "last_grade": str | null,
         "state": "new|learning|review|skipped"
       }, ...
    }
  }

Topic = a durable concept (kebab-case tag). Questions are composed fresh from
the wiki page each session — see CLAUDE.md §4.4 (encoding variability).

Implements FSRS-5 with the published default 19 weights. Short-term review
within a single day (W[17], W[18]) is not modeled — instill sessions assume
one review per topic per day. For higher fidelity, swap to `pip install fsrs`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

DECK_PATH = Path(__file__).resolve().parent.parent / "instill" / "_deck.json"

# FSRS-5 default weights (19 parameters)
W = [
    0.4072, 1.1829, 3.1262, 15.4722,
    7.2102, 0.5316, 1.0651, 0.0234,
    1.616, 0.1544, 1.0824, 1.9813,
    0.0953, 0.2975, 2.2042, 0.2407,
    2.9466, 0.5034, 0.6567,
]
DECAY = -0.5
FACTOR = 19 / 81  # ensures retrievability = 0.9 when elapsed = stability

GRADE = {"again": 1, "hard": 2, "good": 3, "easy": 4}


# ---------- FSRS-5 core ----------

def init_stability(rating: int) -> float:
    return max(W[rating - 1], 0.1)

def init_difficulty(rating: int) -> float:
    return _clip(W[4] - math.exp(W[5] * (rating - 1)) + 1, 1, 10)

def retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * elapsed_days / stability) ** DECAY

def next_difficulty(d: float, rating: int) -> float:
    delta = -W[6] * (rating - 3)
    d_after = d + delta * ((10 - d) / 9)
    d_new = W[7] * init_difficulty(4) + (1 - W[7]) * d_after
    return _clip(d_new, 1, 10)

def next_stability(d: float, s: float, r: float, rating: int) -> float:
    if rating == 1:
        return W[11] * (d ** -W[12]) * ((s + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r))
    hard_penalty = W[15] if rating == 2 else 1.0
    easy_bonus = W[16] if rating == 4 else 1.0
    return s * (1 + math.exp(W[8]) * (11 - d) * (s ** -W[9])
                * (math.exp(W[10] * (1 - r)) - 1) * hard_penalty * easy_bonus)

def next_interval(stability: float, request_retention: float) -> int:
    days = (stability / FACTOR) * (request_retention ** (1 / DECAY) - 1)
    return max(1, min(int(round(days)), 365))

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------- deck I/O ----------

def load_deck() -> dict:
    if not DECK_PATH.exists():
        return {"request_retention": 0.9, "topics": {}}
    with DECK_PATH.open(encoding="utf-8") as f:
        deck = json.load(f)
    deck.setdefault("topics", {})
    return deck

def save_deck(deck: dict) -> None:
    DECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECK_PATH.open("w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2, sort_keys=False)


# ---------- commands ----------

def cmd_today(args) -> None:
    deck = load_deck()
    today = date.today()
    due, new = [], []
    for topic, t in deck["topics"].items():
        if t["state"] == "skipped":
            continue
        if args.topic and topic != args.topic:
            continue
        if t["state"] == "new":
            new.append((topic, t))
        else:
            due_date = date.fromisoformat(t["due"])
            if due_date <= today:
                due.append((topic, t, (today - due_date).days))

    imp_rank = {"high": 0, "med": 1, "low": 2}
    due.sort(key=lambda x: (-x[1]["lapses"], -x[2], imp_rank.get(x[1].get("importance", "med"), 1)))
    due = due[: args.limit]
    new.sort(key=lambda x: imp_rank.get(x[1].get("importance", "med"), 1))
    new = new[: args.new_limit]

    out = {
        "today": today.isoformat(),
        "due": [{"topic": tp, **t, "overdue_days": od} for tp, t, od in due],
        "new_candidates": [{"topic": tp, **t} for tp, t in new],
        "totals": {
            "active": sum(1 for t in deck["topics"].values() if t["state"] != "skipped"),
            "due_total": sum(
                1 for t in deck["topics"].values()
                if t["state"] not in ("new", "skipped")
                and date.fromisoformat(t["due"]) <= today
            ),
            "new_total": sum(1 for t in deck["topics"].values() if t["state"] == "new"),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_review(args) -> None:
    deck = load_deck()
    if args.topic not in deck["topics"]:
        sys.exit(f"unknown topic: {args.topic}")
    t = deck["topics"][args.topic]
    if t["state"] == "skipped":
        sys.exit(f"topic is skipped: {args.topic}")
    rating = GRADE[args.grade]
    today = date.today()
    rr = deck.get("request_retention", 0.9)

    if t["state"] == "new":
        t["stability"] = init_stability(rating)
        t["difficulty"] = init_difficulty(rating)
        t["state"] = "learning" if rating < 3 else "review"
    else:
        last = date.fromisoformat(t["last_review"]) if t.get("last_review") else today
        elapsed = max(0, (today - last).days)
        r = retrievability(elapsed, t["stability"])
        t["difficulty"] = next_difficulty(t["difficulty"], rating)
        t["stability"] = next_stability(t["difficulty"], t["stability"], r, rating)
        if rating == 1:
            t["lapses"] += 1
            t["state"] = "learning"
        else:
            t["state"] = "review"

    interval = next_interval(t["stability"], rr)
    t["due"] = (today + timedelta(days=interval)).isoformat()
    t["last_review"] = today.isoformat()
    t["reps"] += 1
    t["last_grade"] = args.grade
    save_deck(deck)
    print(json.dumps({"topic": args.topic, "due": t["due"], "interval_days": interval,
                      "stability": round(t["stability"], 2),
                      "difficulty": round(t["difficulty"], 2),
                      "state": t["state"], "lapses": t["lapses"]},
                     ensure_ascii=False, indent=2))


def cmd_enroll(args) -> None:
    deck = load_deck()
    if args.topic in deck["topics"]:
        sys.exit(f"already enrolled: {args.topic}")
    deck["topics"][args.topic] = {
        "importance": args.importance,
        "anchor": args.anchor,
        "stability": 0.0, "difficulty": 0.0,
        "due": date.today().isoformat(),
        "last_review": None,
        "reps": 0, "lapses": 0, "last_grade": None,
        "state": "new",
    }
    save_deck(deck)
    print(json.dumps({"enrolled": args.topic, "anchor": args.anchor}, ensure_ascii=False))


def cmd_skip(args) -> None:
    deck = load_deck()
    if args.topic not in deck["topics"]:
        sys.exit(f"unknown topic: {args.topic}")
    deck["topics"][args.topic]["state"] = "skipped"
    save_deck(deck)
    print(json.dumps({"skipped": args.topic}, ensure_ascii=False))


def cmd_stats(args) -> None:
    deck = load_deck()
    today = date.today()
    total = len(deck["topics"])
    by_state: dict = {}
    due = 0
    for t in deck["topics"].values():
        by_state[t["state"]] = by_state.get(t["state"], 0) + 1
        if t["state"] not in ("new", "skipped") and date.fromisoformat(t["due"]) <= today:
            due += 1
    stabilities = [t["stability"] for t in deck["topics"].values() if t["stability"] > 0]
    avg_s = sum(stabilities) / len(stabilities) if stabilities else 0
    print(json.dumps({"total_topics": total, "by_state": by_state, "due_today": due,
                      "avg_stability_days": round(avg_s, 2),
                      "request_retention": deck.get("request_retention", 0.9)},
                     ensure_ascii=False, indent=2))


# ---------- CLI ----------

def main() -> None:
    p = argparse.ArgumentParser(prog="instill_sched")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("today")
    t.add_argument("--topic", default=None)
    t.add_argument("--limit", type=int, default=8)
    t.add_argument("--new-limit", type=int, default=3)
    t.set_defaults(func=cmd_today)

    r = sub.add_parser("review")
    r.add_argument("--topic", required=True)
    r.add_argument("--grade", required=True, choices=GRADE.keys())
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("enroll")
    e.add_argument("--topic", required=True)
    e.add_argument("--importance", default="med", choices=["high", "med", "low"])
    e.add_argument("--anchor", default=None, help="wiki page path hint, e.g. concepts/picd.md")
    e.set_defaults(func=cmd_enroll)

    s = sub.add_parser("skip")
    s.add_argument("--topic", required=True)
    s.set_defaults(func=cmd_skip)

    st = sub.add_parser("stats")
    st.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
