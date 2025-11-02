import csv
from pathlib import Path
from typing import List, Dict

DATA = Path("data")
DATA.mkdir(exist_ok=True)
FEEDBACK = DATA / "feedback.csv"

def init_feedback():
    if not FEEDBACK.exists():
        with open(FEEDBACK, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["rid","dish_id","email","choice","comment"])

def add_feedback(rid: str, dish_id: str, email: str, choice: str, comment: str):
    init_feedback()
    with open(FEEDBACK, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([rid, dish_id, (email or "").strip(), choice, (comment or "").strip()])

def load_feedback() -> List[Dict]:
    init_feedback()
    rows = []
    with open(FEEDBACK, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def votes_for(rid: str, dish_id: str):
    fb = load_feedback()
    safe = sum(1 for r in fb if r["rid"]==rid and r["dish_id"]==dish_id and r["choice"]=="safe")
    mild = sum(1 for r in fb if r["rid"]==rid and r["dish_id"]==dish_id and r["choice"]=="mild")
    avoid = sum(1 for r in fb if r["rid"]==rid and r["dish_id"]==dish_id and r["choice"]=="avoid")
    comments = [r["comment"] for r in fb if r["rid"]==rid and r["dish_id"]==dish_id and r["comment"].strip()]
    return safe, mild, avoid, comments
