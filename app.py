import streamlit as st
from scoring import (
    load_data, score_dish, restaurant_score, badge,
    ALLERGENS, VIBE_TAGS
)
from feedback import add_feedback, votes_for
from integrations import get_place_details_serpapi, gemini_summarize_reviews, gemini_dish_blurb
from streamlit_folium import st_folium
import folium
import json

st.set_page_config(page_title="AllerNav — Dish-level Allergy Safety", page_icon="🥗", layout="wide")

# ----------------- CSS -----------------
st.markdown("""
<style>
.card { 
    border: 1px solid #2c2c2c; 
    border-radius: 14px; 
    padding: 12px; 
    background:#141414; 
    margin-bottom: 10px;
}
.chip { 
    display:inline-block; 
    padding:2px 8px; 
    border-radius:999px; 
    border:1px solid #2d2d2d; 
    margin-right:6px; 
    font-size:12px; 
}
</style>
""", unsafe_allow_html=True)

# ----------------- LOAD DATA -----------------
restaurants, dishes = load_data()
try:
    reviews_seed = json.load(open("data/reviews.json"))
except:
    reviews_seed = {}

# ----------------- SIDEBAR -----------------
st.sidebar.title("Your Allergy Profile")
user_allergies = st.sidebar.multiselect("Select your allergies", ALLERGENS, default=["peanut","dairy"])
cities = sorted({r["city"] for r in restaurants})
city = st.sidebar.selectbox("City", cities)
vibe_pick = st.sidebar.multiselect("Vibe filter (optional)", VIBE_TAGS)

profile = st.sidebar.selectbox(
    "Profile Type",
    ["Standard Diner", "Highly Sensitive", "Parent / Planning for Family"]
)

# Adjust scoring sensitivity
sensitivity_factor = {
    "Standard Diner": 1.0,
    "Highly Sensitive": 0.75,
    "Parent / Planning for Family": 0.85
}[profile]


# filter restaurants
rlist = [r for r in restaurants if r["city"] == city]
if vibe_pick:
    rlist = [r for r in rlist if any(v in (r.get("vibe_tags") or []) for v in vibe_pick)]
dlist = [d for d in dishes if d["rid"] in {r["id"] for r in rlist}]

# ----------------- HEADER -----------------
st.title("AllerNav — Dish-level Allergy Safety")
st.write(f"👤 Profile: **{profile}**")

def trust_level(rid):
    s, m, a, comments = votes_for(rid, None)  # we’ll treat None as restaurant-level aggregation
    total_votes = s + m + a

    # Verified score from dataset
    restaurant = next(x for x in restaurants if x["id"] == rid)
    base = float(restaurant.get("verified_score", 0) or 0)

    # User sentiment trust boost
    if total_votes > 0:
        sentiment = (s*1 + m*0.5) / max(total_votes,1)
    else:
        sentiment = 0.5  # neutral if no votes

    trust = (base * 0.6) + (sentiment * 0.4)
    return round(trust, 2), total_votes


# ----------------- MAP -----------------
st.subheader(f"{city} — Restaurant Safety Map")

lat_center = float(rlist[0]["lat"]) if rlist else 38.98
lon_center = float(rlist[0]["lon"]) if rlist else -76.94
m = folium.Map(location=[lat_center, lon_center], zoom_start=13, tiles="CartoDB dark_matter")

def marker_color(s):
    if s >= 0.75: return "green"
    if s >= 0.45: return "orange"
    return "red"

for r in rlist:
    rd = [d for d in dlist if d["rid"] == r["id"]]
    s = restaurant_score(r, rd, user_allergies)
    rs = restaurant_score(r, rd, user_allergies) * sensitivity_factor

    folium.CircleMarker(
        location=[float(r["lat"]), float(r["lon"])],
        radius=10,
        fill=True,
        color=marker_color(s),
        fill_color=marker_color(s),
        popup=r["id"],         # <-- use ID for reliable lookup
        tooltip=f"{r['name']} ({round(s,2)})"
    ).add_to(m)

map_data = st_folium(m, width=1000, height=450)
clicked_id = map_data.get("last_object_clicked_popup") if map_data else None

# ----------------- RESTAURANT LIST -----------------
st.subheader("Restaurants (sorted by safety)")

sorted_rest = sorted(
    [(r, restaurant_score(r, [d for d in dlist if d["rid"]==r["id"]], user_allergies)) for r in rlist],
    key=lambda x: -x[1]
)

selected_id = clicked_id  # map click priority

for r, rs in sorted_rest:
    if st.button(f"{r['name']} ({round(rs,2)})", key=f"btn_{r['id']}"):
        selected_id = r["id"]

# ----------------- RESTAURANT DETAILS -----------------
if selected_id:
    r = next(rr for rr in rlist if rr["id"] == selected_id)
    rd = [d for d in dlist if d["rid"] == r["id"]]

    # Try live lookup
    info = get_place_details_serpapi(r["name"], city) or {}

    # ---- Manual Demo Data ----
    demo_places = {
        "CAVA College Park": {
            "address": "7317 Baltimore Ave, College Park, MD",
            "phone": "(301) 560-1401",
            "website": "https://cava.com",
            "hours": "10:45 AM – 10:00 PM",
            "photo": "https://images.unsplash.com/photo-1617196034515-8c1df7d0f5be"
        },
        "Taqueria Habanero": {
            "address": "8147 Baltimore Ave, College Park, MD",
            "phone": "(240) 965-5500",
            "website": "https://taqueriahabanero.com",
            "hours": "11:00 AM – 9:00 PM",
            "photo": "https://images.unsplash.com/photo-1600891964599-f61ba0e24092"
        },
        "Pho Thom": {
            "address": "7323 Baltimore Ave, College Park, MD",
            "phone": "(301) 277-6999",
            "website": "https://phothom.com",
            "hours": "11:00 AM – 9:30 PM",
            "photo": "https://images.unsplash.com/photo-1604908177522-050d94642a3f"
        },
        "The Hall CP": {
            "address": "4656 Hotel Dr, College Park, MD",
            "phone": "(240) 582-4980",
            "website": "https://thehallcp.com",
            "hours": "8:00 AM – 10:00 PM",
            "photo": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c"
        },
        "Bagels n Grinds": {
            "address": "8900 Baltimore Ave, College Park, MD",
            "phone": "(301) 779-3900",
            "website": "https://bagelsngrinds.com",
            "hours": "6:30 AM – 4:00 PM",
            "photo": "https://images.unsplash.com/photo-1542831371-d531d36971e6"
        }
    }

    # apply demo info if missing
    if r["name"] in demo_places:
        for k, v in demo_places[r["name"]].items():
            info.setdefault(k, v)

    raw_score = restaurant_score(r, rd, user_allergies)
    score = raw_score * sensitivity_factor


    st.markdown(f"## {r['name']}")

    st.write(f"📍 {info.get('address','')}")
    st.write(f"📞 {info.get('phone','')}")
    st.write(f"🌐 {info.get('website','')}")
    st.write(f"🕒 {info.get('hours','')}")
    st.write(f"🍽️ Cuisine: {', '.join(r['cuisine'])}")
    st.write(f"⚠️ Cross contact: {', '.join(r.get('cross_contact', [])) or 'None'}")
    st.write(f"🛡️ Safety Score: **{round(score,2)}**")

    trust, tv = trust_level(r["id"])

    trust_bar = "█" * int(trust*10) + "░" * (10-int(trust*10))

    st.write(f"🤝 Trust Level: **{trust}**  ({tv} votes)")
    st.write(f"`{trust_bar}`")


    vibes = r.get("vibe_tags", [])
    if isinstance(vibes, str):
        vibes = vibes.split("|")
    st.write("✨ Vibe: " + ", ".join(vibes))

    rest_reviews = info.get("review_snippets", []) or reviews_seed.get(r["name"], [])
    if rest_reviews:
        st.write("### AI Allergy Summary from Reviews")
        st.write(gemini_summarize_reviews(rest_reviews))

    st.write("### Menu — Click a dish")

    for d in rd:
        dish_score = score_dish(r, d, user_allergies)
        pct = int(dish_score*100)

        with st.expander(f"{d['name']} — {badge(dish_score)} {pct}%"):
            st.markdown(f"**Ingredients:** {d.get('desc','')}")
            st.markdown(f"**Why:** {d.get('inference_reason','')}")

            s, m, a, comments = votes_for(r["id"], d["dish_id"])
            st.write(f"Votes: ✅ {s} ⚠️ {m} ❌ {a}")

            # ✅ hide form after voting
            if st.session_state.get(f"voted_{r['id']}_{d['dish_id']}", False):
                st.success("✅ Thanks! Refresh to vote again later.")
            else:
                with st.form(key=f"vote_{r['id']}_{d['dish_id']}"):
                    email = st.text_input("Email (trust weight)")
                    choice = st.radio("Rate:", ["👍 safe","⚠️ mild","❌ avoid"], horizontal=True)
                    comment = st.text_area("Comment (optional)")
                    if st.form_submit_button("Submit"):
                        mapped = {"👍 safe":"safe","⚠️ mild":"mild","❌ avoid":"avoid"}[choice]
                        add_feedback(r["id"], d["dish_id"], email, mapped, comment)
                        st.session_state[f"voted_{r['id']}_{d['dish_id']}"] = True
                        st.rerun()
