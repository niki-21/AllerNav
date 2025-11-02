import google.generativeai as genai
import pandas as pd

genai.configure(api_key="AIzaSyBuQCcJkGRBFI6dJbuy_3bcOwhZDLFIKxs")

# --- INPUT: restaurant names for your city ---
restaurants_list = [
    "Poke Bowl College Park",
    "Mama Roma Pasta College Park",
    "Sushi On College Park",
    "Taqueria Habanero College Park",
    "Bagel Place College Park",
    "Halal Bros College Park"
]

def get_restaurant_info(name, city="College Park, MD"):
    prompt = f"""
You are extracting structured data for an allergy-safe dining dataset.

Restaurant: {name}
City: {city}

Output JSON with fields:
- name
- cuisine (comma separated tags)
- dishes: list of dish objects, each:
    - name
    - ingredients (if unknown infer typical)
    - inferred_allergens (from ingredients + cuisine)
    - cross_contact_risk (0-1)
    - confidence (0-1)
    - reason
- venue_risk_flags (shared fryer, bakery, etc inferred from cuisine)

Focus on *accuracy and safety over creativity*.
Return ONLY JSON.
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    r = model.generate_content(prompt)

    return r.candidates[0].content.parts[0].text



rows = []
dish_rows = []

for rname in restaurants_list:
    try:
        data = eval(get_restaurant_info(rname))
        rid = rname[:10].lower().replace(" ","_")
        
        rows.append({
            "id": rid,
            "name": data["name"],
            "city": "College Park, MD",
            "cuisine": "|".join(data["cuisine"]),
            "cross_contact": "|".join(data["venue_risk_flags"]),
            "verified_score": 0.55   # seed initial score
        })

        for d in data["dishes"]:
            dish_rows.append({
                "rid": rid,
                "dish_id": rid + "_" + d["name"].replace(" ", "_")[:10],
                "name": d["name"],
                "desc": ", ".join(d["ingredients"]),
                "inferred_allergens": "|".join(d["inferred_allergens"]),
                "confidence": d["confidence"],
                "inference_reason": d["reason"]
            })
    except Exception as e:
        print("Error:", e)

pd.DataFrame(rows).to_csv("data/restaurants.csv", index=False)
pd.DataFrame(dish_rows).to_csv("data/dishes.csv", index=False)

print("Dataset Generated!")
