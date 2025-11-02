# integrations.py — Offline Demo Version (No APIs)

from typing import Dict, Any, List

# ----------------------------
# Manual fallback data
# ----------------------------
DEMO_PLACE_DATA = {
    "CAVA College Park": {
        "address": "7317 Baltimore Ave, College Park, MD",
        "phone": "(301) 560-1401",
        "website": "https://cava.com",
        "hours": "10:45 AM – 10:00 PM",
        "photo": "https://images.unsplash.com/photo-1617196034515-8c1df7d0f5be",
        "review_snippets": [
            "They handled my dairy allergy well.",
            "Avoid pita chips — shared fryer.",
        ]
    },
    "Taqueria Habanero": {
        "address": "8147 Baltimore Ave, College Park, MD",
        "phone": "(240) 965-5500",
        "website": "https://taqueriahabanero.com",
        "hours": "11:00 AM – 9:00 PM",
        "photo": "https://images.unsplash.com/photo-1600891964599-f61ba0e24092",
        "review_snippets": [
            "They warned me about cheese in sauces.",
            "Corn tortillas safe for gluten-free.",
        ]
    },
    "Pho Thom": {
        "address": "7323 Baltimore Ave, College Park, MD",
        "phone": "(301) 277-6999",
        "website": "https://phothom.com",
        "hours": "11:00 AM – 9:30 PM",
        "photo": "https://images.unsplash.com/photo-1604908177522-050d94642a3f",
        "review_snippets": [
            "Good understanding of peanut allergy.",
            "Pho broth is dairy-free."
        ]
    },
    "The Hall CP": {
        "address": "4656 Hotel Dr, College Park, MD",
        "phone": "(240) 582-4980",
        "website": "https://thehallcp.com",
        "hours": "8:00 AM – 10:00 PM",
        "photo": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c",
        "review_snippets": [
            "Staff helpful but shared fryer warning.",
            "Gluten-free buns available."
        ]
    },
    "Bagels n Grinds": {
        "address": "8900 Baltimore Ave, College Park, MD",
        "phone": "(301) 779-3900",
        "website": "https://bagelsngrinds.com",
        "hours": "6:30 AM – 4:00 PM",
        "photo": "https://images.unsplash.com/photo-1542831371-d531d36971e6",
        "review_snippets": [
            "Bagel wheat cross-contact risk.",
            "They offered lettuce wrap alternative."
        ]
    }
}

# ----------------------------
# Offline dummy functions
# ----------------------------
def get_place_details_serpapi(name: str, city: str) -> Dict[str, Any]:
    """Return local demo data instead of calling SerpAPI."""
    return DEMO_PLACE_DATA.get(name, {})


def gemini_summarize_reviews(reviews: List[str]) -> str:
    """Fake 'AI summary' to replace Gemini output."""
    if not reviews:
        return ""
    return (
        "• Staff awareness varies, ask questions\n"
        "• Some cross-contact possible, avoid shared fryers\n"
        "• Sauces and dressings have most allergens\n"
        "• Good options for simple bowls and proteins\n"
        "• Customizable items safest"
    )


def gemini_dish_blurb(name: str, desc: str, allergies: List[str]) -> str:
    """Short flavor blurb placeholder."""
    return f"Tasty pick if avoiding {', '.join(allergies)} — ask about sauces."
