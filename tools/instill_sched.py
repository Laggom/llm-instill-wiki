#!/usr/bin/env python3
"""instill scheduler — FSRS-5 card scheduling.

Usage:
  python tools/instill_sched.py today [--topic TOPIC] [--limit 8] [--new-limit 3]
  python tools/instill_sched.py review --id ID --grade {again,hard,good,easy}
  python tools/instill_sched.py enroll --id ID [--importance high|med|low] [--topic TOPIC]
  python tools/instill_sched.py skip --id ID
  python tools/instill_sched.py stats

Deck state lives in instill/_deck.json. Schema:
  {
    "request_retention": 0.9,
    "cards": {
       "<id>": {
         "topic": str, "importance": "high|med|low",
         "stability": float, "difficulty": float,
         "due": "YYYY-MM-DD", "last_review": "YYYY-MM-DD" | null,
         "reps": int, "lapses": int, "last_grade": str | null,
         "state": "new|learning|review|skipped"
       }, ...
    }
  }

Implements FSRS-5 with the published default 19 weights. Short-term review
within a single day (W[17], W[18]) is not modeled — instill sessions assume
one review per card per day, which matches the personal-scale use case.
For higher fidelity (e.g., training custom weights), swap to `pip install fsrs`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
    # FSRS-5: D₀(G) = W[4] - e^(W[5] * (G-1)) + 1
    return _clip(W[4] - math.exp(W[5] * (rating - 1)) + 1, 1, 10)

def retrievability(elapsed_days: float, stability: float) -> float:
    # FSRS-5: R(t, S) = (1 + FACTOR * t/S)^DECAY
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * elapsed_days / stability) ** DECAY

def next_difficulty(d: float, rating: int) -> float:
    # Linear damping + mean reversion toward init_difficulty(rating=4) baseline.
    delta = -W[6] * (rating - 3)
    d_after = d + delta * ((10 - d) / 9)
    d_new = W[7] * init_difficulty(4) + (1 - W[7]) * d_after
    return _clip(d_new, 1, 10)

def next_stability(d: float, s: float, r: float, rating: int) -> float:
    if rating == 1:  # Again — lapse
        return W[11] * (d ** -W[12]) * ((s + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r))
    hard_penalty = W[15] if rating == 2 else 1.0
    easy_bonus = W[16] if rating == 4 else 1.0
    return s * (1 + math.exp(W[8]) * (11 - d) * (s ** -W[9])
                * (math.exp(W[10] * (1 - r)) - 1) * hard_penalty * easy_bonus)

def next_interval(stability: float, request_retention: float) -> int:
    # FSRS-5: I(r, S) = (S/FACTOR) * (r^(1/DECAY) - 1)
    days = (stability / FACTOR) * (request_retention ** (1 / DECAY) - 1)
    return max(1, min(int(round(days)), 365))

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------- deck I/O ----------

def load_deck() -> dict:
    if not DECK_PATH.exists():
        return {"request_retention": 0.9, "cards": {}}
    with DECK_PATH.open(encoding="utf-8") as f:
        return json.load(f)

def save_deck(deck: dict) -> None:
    DECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECK_PATH.open("w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2, sort_keys=False)


# ---------- commands ----------

def cmd_today(args) -> None:
    deck = load_deck()
    today = date.today()
    due, new = [], []
    for cid, c in deck["cards"].items():
        if c["state"] == "skipped":
            continue
        if args.topic and c.get("topic") != args.topic:
            continue
        if c["state"] == "new":
            new.append((cid, c))
        else:
            due_date = date.fromisoformat(c["due"])
            if due_date <= today:
                due.append((cid, c, (today - due_date).days))

    # Priority: lapses > most overdue > importance
    imp_rank = {"high": 0, "med": 1, "low": 2}
    due.sort(key=lambda t: (-t[1]["lapses"], -t[2], imp_rank.get(t[1].get("importance", "med"), 1)))
    due = due[: args.limit]
    new.sort(key=lambda t: imp_rank.get(t[1].get("importance", "med"), 1))
    new = new[: args.new_limit]

    out = {
        "today": today.isoformat(),
        "due": [{"id": cid, **c, "overdue_days": od} for cid, c, od in due],
        "new_candidates": [{"id": cid, **c} for cid, c in new],
        "totals": {
            "active": sum(1 for c in deck["cards"].values() if c["state"] != "skipped"),
            "due_total": sum(
                1 for c in deck["cards"].values()
                if c["state"] not in ("new", "skipped")
                and date.fromisoformat(c["due"]) <= today
            ),
            "new_total": sum(1 for c in deck["cards"].values() if c["state"] == "new"),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_review(args) -> None:
    deck = load_deck()
    if args.id not in deck["cards"]:
        sys.exit(f"unknown card: {args.id}")
    c = deck["cards"][args.id]
    if c["state"] == "skipped":
        sys.exit(f"card is skipped: {args.id}")
    rating = GRADE[args.grade]
    today = date.today()
    rr = deck.get("request_retention", 0.9)

    if c["state"] == "new":
        c["stability"] = init_stability(rating)
        c["difficulty"] = init_difficulty(rating)
        c["state"] = "learning" if rating < 3 else "review"
    else:
        last = date.fromisoformat(c["last_review"]) if c.get("last_review") else today
        elapsed = max(0, (today - last).days)
        r = retrievability(elapsed, c["stability"])
        c["difficulty"] = next_difficulty(c["difficulty"], rating)
        c["stability"] = next_stability(c["difficulty"], c["stability"], r, rating)
        if rating == 1:
            c["lapses"] += 1
            c["state"] = "learning"
        else:
            c["state"] = "review"

    interval = next_interval(c["stability"], rr)
    c["due"] = (today + timedelta(days=interval)).isoformat()
    c["last_review"] = today.isoformat()
    c["reps"] += 1
    c["last_grade"] = args.grade
    save_deck(deck)
    print(json.dumps({"id": args.id, "due": c["due"], "interval_days": interval,
                      "stability": round(c["stability"], 2),
                      "difficulty": round(c["difficulty"], 2),
                      "state": c["state"], "lapses": c["lapses"]},
                     ensure_ascii=False, indent=2))


def cmd_enroll(args) -> None:
    deck = load_deck()
    if args.id in deck["cards"]:
        sys.exit(f"already enrolled: {args.id}")
    deck["cards"][args.id] = {
        "topic": args.topic or "",
        "importance": args.importance,
        "stability": 0.0, "difficulty": 0.0,
        "due": date.today().isoformat(),
        "last_review": None,
        "reps": 0, "lapses": 0, "last_grade": None,
        "state": "new",
    }
    save_deck(deck)
    print(json.dumps({"enrolled": args.id}, ensure_ascii=False))


def cmd_skip(args) -> None:
    deck = load_deck()
    if args.id not in deck["cards"]:
        sys.exit(f"unknown card: {args.id}")
    deck["cards"][args.id]["state"] = "skipped"
    save_deck(deck)
    print(json.dumps({"skipped": args.id}, ensure_ascii=False))


def cmd_stats(args) -> None:
    deck = load_deck()
    today = date.today()
    total = len(deck["cards"])
    by_state = {}
    due = 0
    for c in deck["cards"].values():
        by_state[c["state"]] = by_state.get(c["state"], 0) + 1
        if c["state"] not in ("new", "skipped") and date.fromisoformat(c["due"]) <= today:
            due += 1
    stabilities = [c["stability"] for c in deck["cards"].values() if c["stability"] > 0]
    avg_s = sum(stabilities) / len(stabilities) if stabilities else 0
    print(json.dumps({"total": total, "by_state": by_state, "due_today": due,
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
    r.add_argument("--id", required=True)
    r.add_argument("--grade", required=True, choices=GRADE.keys())
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("enroll")
    e.add_argument("--id", required=True)
    e.add_argument("--importance", default="med", choices=["high", "med", "low"])
    e.add_argument("--topic", default=None)
    e.set_defaults(func=cmd_enroll)

    s = sub.add_parser("skip")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_skip)

    st = sub.add_parser("stats")
    st.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
