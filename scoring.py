import csv
from pathlib import Path
from typing import List, Dict, Tuple
from feedback import votes_for

ALLERGENS = ["peanut","tree_nut","dairy","egg","gluten","soy","fish","shellfish","sesame","mustard"]
VIBE_TAGS = ["date night","casual","study spot","family","halal-friendly","vegan-friendly","late-night"]

HIDDEN_MAP = {
  "pesto": ["tree_nut","dairy"], "aioli": ["egg"], "mayo": ["egg"],
  "butter": ["dairy"], "ghee": ["dairy"], "paneer": ["dairy"],
  "whey": ["dairy"], "tahini": ["sesame"], "satay": ["peanut"],
  "tempura": ["gluten","egg"], "ponzu": ["soy","fish"], "katsu": ["gluten","egg"],
  "teriyaki": ["soy"], "pad_thai": ["peanut","egg","soy"], "green_curry": ["fish","shellfish"]
}

CUISINE_PRIORS = {
  "thai": ["peanut","fish","shellfish","soy"],
  "indian": ["dairy","tree_nut","mustard","gluten"],
  "japanese": ["soy","fish","sesame","gluten"],
  "italian": ["gluten","dairy","egg","tree_nut"],
  "mexican": ["dairy","gluten"],
  "mediterranean": ["sesame","tree_nut","dairy"]
}

CROSS_CONTACT_RISKS = {
  "shared_fryer": 0.25, "bakery": 0.35, "ice_cream_shop": 0.30,
  "buffet": 0.40, "open_kitchen_nuts": 0.40, "tempura_station": 0.25,
  "tahini_bar": 0.20, "cheese_station": 0.20, "soy_station": 0.15
}

def load_data(data_dir=Path("data")):
    # restaurants
    restaurants = []
    with open(data_dir/"restaurants.csv", newline='', encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Safe parsing for lists
            cuisine = row.get("cuisine", "")
            cross = row.get("cross_contact", "")

            row["cuisine"] = cuisine.split("|") if cuisine else []
            row["cross_contact"] = cross.split("|") if cross else []

            # Safe verified score
            try:
                row["verified_score"] = float(row.get("verified_score", 0) or 0)
            except:
                row["verified_score"] = 0.0

            # Safe lat/lon
            try:
                row["lat"] = float(row["lat"])
                row["lon"] = float(row["lon"])
            except:
                row["lat"], row["lon"] = 0, 0  # default if missing

            restaurants.append(row)

    # dishes
    dishes = []
    with open(data_dir/"dishes.csv", newline='', encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["confidence"] = float(row.get("confidence", 0) or 0)
            except:
                row["confidence"] = 0.0

            inferred = row.get("inferred_allergens", "")
            row["inferred_allergens"] = inferred.split("|") if inferred else []
            dishes.append(row)

    return restaurants, dishes


def cross_penalty(r: Dict) -> float:
    total = 0.0
    for flag in r.get("cross_contact", []):
        total += CROSS_CONTACT_RISKS.get(flag, 0.0)
    return min(total, 0.6)

def cuisine_penalty(r: Dict, user_allergies: List[str]) -> float:
    priors = set()
    for c in r.get("cuisine", []):
        priors.update(CUISINE_PRIORS.get(c, []))
    return 0.15 if (set(priors) & set(user_allergies)) else 0.0

def score_dish(r: Dict, d: Dict, user_allergies: List[str]) -> float:
    """
    Option B: Gemini + user reports + rule penalties.
    """
    # base: ingredients vs allergies
    intersects = bool(set(d.get("inferred_allergens", [])) & set(user_allergies))
    ingredient_safety = 0.0 if intersects else 1.0

    # community votes (email-gated)
    s, mild, a, _ = votes_for(r["id"], d["dish_id"])
    denom = s + a + 1
    community = max(-0.3, min(0.3, (s - a) / denom))  # bounded

    # description confidence (from dataset or LLM extraction)
    desc_conf = float(d.get("confidence", 0)) * 0.2

    # risk penalties
    penalty_cross = cross_penalty(r)
    penalty_cuisine = cuisine_penalty(r, user_allergies)

    # combine
    score = ingredient_safety - penalty_cross - penalty_cuisine + desc_conf + community
    return max(0.0, min(1.0, round(score, 2)))

def restaurant_score(r: Dict, dishes_for_r: List[Dict], user_allergies: List[str]) -> float:
    if not dishes_for_r:
        return float(r.get("verified_score", 0) or 0)
    vals = [score_dish(r, d, user_allergies) for d in dishes_for_r]
    vals.sort(reverse=True)
    k = min(3, len(vals))  # top-K average: optimistic but realistic
    base = sum(vals[:k]) / k
    # blend seed verified_score (from our dataset / known safe brands)
    return round(0.8*base + 0.2*float(r.get("verified_score",0)), 2)

def badge(score: float) -> str:
    if score >= 0.75: return "Safe"
    if score >= 0.45: return "⚠️ Ask staff"
    return "Avoid"
