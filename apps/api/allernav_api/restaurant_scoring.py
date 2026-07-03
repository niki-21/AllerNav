from __future__ import annotations

from dataclasses import dataclass

from .menu_risk import classify_menu_item, is_non_food_category
from .models import AllergyTag, MenuSource
from .risk_engine import ALLERGEN_TERMS, term_matches


@dataclass(frozen=True)
class RestaurantFitScore:
    score: int
    label: str
    menu_item_count: int
    avoid_count: int
    needs_check_count: int
    possible_lower_risk_count: int
    insufficient_info_count: int
    evidence_quality: float
    reason: str
    next_action: str
    possible_item_names: tuple[str, ...]
    avoid_item_names: tuple[str, ...]
    buffet_or_shared_prep_signal: bool = False
    confirmed_allergen_review: bool = False


BUFFET_SHARED_PREP_TERMS = (
    "buffet",
    "all-you-can-eat",
    "all you can eat",
    "shared fryer",
    "shared grill",
    "shared preparation",
    "communal grill",
    "communal pot",
)

CONFIRMED_REVIEW_RISK_TERMS = (
    "allergic reaction",
    "had a reaction",
    "cross contamination",
    "cross-contamination",
    "cross contact",
    "cross-contact",
    "served me",
    "got sick",
    "anaphylaxis",
    "hospital",
)


def has_confirmed_allergen_risk_review(
    review_texts: list[str],
    selected_allergens: list[AllergyTag],
) -> bool:
    for review_text in review_texts:
        normalized = review_text.lower()
        has_risk = any(term in normalized for term in CONFIRMED_REVIEW_RISK_TERMS)
        has_allergen = any(
            term_matches(normalized, term)
            for allergen in selected_allergens
            for term in ALLERGEN_TERMS[allergen]
        )
        if has_risk and has_allergen:
            return True
    return False


def score_restaurant_menu(
    source: MenuSource | None,
    selected_allergens: list[AllergyTag],
    *,
    confirmed_allergen_review: bool = False,
    restaurant_context: str = "",
) -> RestaurantFitScore:
    if not selected_allergens:
        return RestaurantFitScore(
            score=0,
            label="Scan needed",
            menu_item_count=sum(len(section.items) for section in source.sections) if source else 0,
            avoid_count=0,
            needs_check_count=0,
            possible_lower_risk_count=0,
            insufficient_info_count=0,
            evidence_quality=source.reliability if source else 0,
            reason="No allergies were selected, so allergy-fit scoring was not applied.",
            next_action="Browse the menu and restaurant details.",
            possible_item_names=(),
            avoid_item_names=(),
        )
    if source is None:
        return RestaurantFitScore(
            score=20,
            label="Scan needed",
            menu_item_count=0,
            avoid_count=0,
            needs_check_count=0,
            possible_lower_risk_count=0,
            insufficient_info_count=0,
            evidence_quality=0,
            reason="No scanned menu evidence is available yet.",
            next_action="Scan this menu before comparing allergy fit.",
            possible_item_names=(),
            avoid_item_names=(),
        )

    source_confidence = source.extraction_confidence
    if source_confidence is None:
        source_confidence = source.reliability
    classified = [
        classify_menu_item(
            item,
            selected_allergens,
            source_confidence=source_confidence,
            section_title=section.title,
        )
        for section in source.sections
        for item in section.items
        if not is_non_food_category(item)
    ]
    item_count = len(classified)
    if item_count == 0:
        return RestaurantFitScore(
            score=20,
            label="Scan needed",
            menu_item_count=0,
            avoid_count=0,
            needs_check_count=0,
            possible_lower_risk_count=0,
            insufficient_info_count=0,
            evidence_quality=0,
            reason="The scan did not produce reliable dish-level evidence.",
            next_action="Run another menu scan or inspect the official menu source.",
            possible_item_names=(),
            avoid_item_names=(),
        )

    counts = {
        "avoid": sum(item.risk_label == "avoid" for item in classified),
        "needs_check": sum(item.risk_label == "needs_check" for item in classified),
        "possible_lower_risk": sum(item.risk_label == "possible_lower_risk" for item in classified),
        "insufficient_info": sum(item.risk_label == "insufficient_info" for item in classified),
    }
    grounded_ratio = sum(item.risk_label != "insufficient_info" for item in classified) / item_count
    evidence_quality = min(1.0, max(0.0, source_confidence * 0.75 + grounded_ratio * 0.25))
    avoid_ratio = counts["avoid"] / item_count
    needs_check_ratio = counts["needs_check"] / item_count
    insufficient_ratio = counts["insufficient_info"] / item_count
    possible_ratio = counts["possible_lower_risk"] / item_count
    source_text = " ".join(
        [
            restaurant_context,
            source.raw_text or "",
            *(section.title for section in source.sections),
        ]
    ).lower()
    buffet_or_shared_prep_signal = any(term in source_text for term in BUFFET_SHARED_PREP_TERMS)
    score = round(
        60
        + 25 * possible_ratio
        + (10 if counts["possible_lower_risk"] >= 3 else 0)
        - 35 * avoid_ratio
        - (15 if counts["avoid"] > 0 and counts["avoid"] >= counts["possible_lower_risk"] else 0)
        - (20 if buffet_or_shared_prep_signal else 0)
        - (20 if confirmed_allergen_review else 0)
        - 8 * needs_check_ratio
        - 8 * insufficient_ratio
    )
    score = max(0, min(100, score))

    if score >= 80:
        label = "Strong candidate, still verify"
    elif score >= 65:
        label = "Better candidate, still verify"
    elif score >= 45:
        label = "Some options, needs verification"
    elif score >= 25:
        label = "Limited options"
    else:
        label = "High concern"

    if (
        set(selected_allergens) == {AllergyTag.FISH}
        and not counts["avoid"]
        and counts["needs_check"]
    ):
        reason = (
            "High score because no menu items directly mention fish, but ramen broth and sauces need staff verification."
            if score >= 65
            else "No menu items directly mention fish, but ramen broth and sauces need staff verification."
        )
    elif counts["avoid"]:
        reason = (
            f"{counts['avoid']} item{'s' if counts['avoid'] != 1 else ''} match selected allergens; "
            f"{counts['possible_lower_risk']} possible lower-risk item"
            f"{'s' if counts['possible_lower_risk'] != 1 else ''} remain to verify."
        )
    elif counts["possible_lower_risk"]:
        reason = (
            f"{counts['possible_lower_risk']} possible lower-risk item"
            f"{'s' if counts['possible_lower_risk'] != 1 else ''} have source-backed descriptions."
        )
    else:
        reason = "The menu is scanned, but its items still need ingredient or preparation checks."

    if buffet_or_shared_prep_signal:
        reason += " Buffet or shared-preparation evidence lowers the score."
    if confirmed_allergen_review:
        reason += " A confirmed allergen-risk review lowers the score."

    return RestaurantFitScore(
        score=score,
        label=label,
        menu_item_count=item_count,
        avoid_count=counts["avoid"],
        needs_check_count=counts["needs_check"],
        possible_lower_risk_count=counts["possible_lower_risk"],
        insufficient_info_count=counts["insufficient_info"],
        evidence_quality=round(evidence_quality, 2),
        reason=reason,
        next_action="Ask staff about sauces, broths, and shared prep before ordering.",
        possible_item_names=tuple(item.name for item in classified if item.risk_label == "possible_lower_risk")[:3],
        avoid_item_names=tuple(item.name for item in classified if item.risk_label == "avoid")[:3],
        buffet_or_shared_prep_signal=buffet_or_shared_prep_signal,
        confirmed_allergen_review=confirmed_allergen_review,
    )
