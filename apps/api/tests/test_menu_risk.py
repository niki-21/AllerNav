from __future__ import annotations

from allernav_api.menu_risk import classify_menu_item, classify_place_menu, is_non_food_category
from allernav_api.models import AllergyTag, MenuItem, MenuSection, PlaceMenu


def test_sesame_naan_is_avoid_for_sesame() -> None:
    result = classify_menu_item(
        MenuItem(name="Sesame Naan", description="Baked flatbread topped with sesame seeds."),
        [AllergyTag.SESAME],
    )
    assert result.risk_label == "avoid"
    assert result.matched_allergens == [AllergyTag.SESAME]
    assert result.confidence is not None and result.confidence >= 0.78


def test_tandoori_salmon_is_avoid_for_fish() -> None:
    result = classify_menu_item(
        MenuItem(name="Tandoori Salmon", description="Salmon roasted with spices."),
        [AllergyTag.FISH],
    )
    assert result.risk_label == "avoid"
    assert result.matched_allergens == [AllergyTag.FISH]


def test_ihop_style_fish_platter_is_avoid_for_fish() -> None:
    result = classify_menu_item(
        MenuItem(name="Crispy Fish & Fries Platter", description="Crispy battered fish served with fries."),
        [AllergyTag.FISH],
    )
    assert result.risk_label == "avoid"
    assert result.matched_allergens == [AllergyTag.FISH]


def test_basmati_rice_with_context_is_possible_lower_risk() -> None:
    result = classify_menu_item(
        MenuItem(name="Basmati Rice", description="Steamed long-grain basmati rice with herbs."),
        [AllergyTag.PEANUT, AllergyTag.SESAME, AllergyTag.FISH],
    )
    assert result.risk_label == "possible_lower_risk"
    assert result.matched_allergens == []
    assert result.confidence is not None and result.confidence > 0.6


def test_vague_item_is_insufficient_info() -> None:
    result = classify_menu_item(MenuItem(name="House Special"), [AllergyTag.PEANUT])
    assert result.risk_label == "insufficient_info"
    assert result.confidence is not None and result.confidence < 0.5


def test_unknown_curry_requires_staff_check() -> None:
    result = classify_menu_item(MenuItem(name="House Curry"), [AllergyTag.PEANUT])
    assert result.risk_label == "needs_check"


def test_seafood_salad_needs_check_for_fish() -> None:
    result = classify_menu_item(MenuItem(name="Seafood Salad"), [AllergyTag.FISH])
    assert result.risk_label == "needs_check"
    assert result.matched_allergens == []


def test_pasta_with_tomato_sauce_is_not_insufficient_info() -> None:
    result = classify_menu_item(
        MenuItem(name="Pasta with Tomato Sauce"),
        [AllergyTag.PEANUT, AllergyTag.SESAME, AllergyTag.FISH],
    )
    assert result.risk_label == "needs_check"


def test_simple_named_dish_is_possible_lower_risk() -> None:
    result = classify_menu_item(MenuItem(name="Plain Basmati Rice"), [AllergyTag.PEANUT, AllergyTag.FISH])
    assert result.risk_label == "possible_lower_risk"


def test_no_allergy_mode_does_not_add_risk_labels() -> None:
    result = classify_menu_item(MenuItem(name="Seafood Salad"), [])
    assert result.risk_label is None
    assert result.matched_allergens == []


def test_arabic_ocr_evidence_maps_to_english_allergen_summary() -> None:
    result = classify_menu_item(
        MenuItem(name="سلطة الطحينة", description="طحينة، سمسم، خيار"),
        [AllergyTag.SESAME],
        source_confidence=0.9,
    )

    assert result.risk_label == "avoid"
    assert result.matched_allergens == [AllergyTag.SESAME]
    assert "sesame" in result.risk_reasons[0].lower()
    assert "سمسم" in f"{result.name} {result.description}"


def test_menu_headers_are_non_food_categories_and_removed() -> None:
    dine_in = MenuItem(name="Dine-In Menu")
    toppings = MenuItem(name="Recommended Toppings Set")

    assert is_non_food_category(dine_in)
    assert is_non_food_category(toppings)

    menu = classify_place_menu(
        PlaceMenu(
            sections=[
                MenuSection(
                    title="Menu",
                    items=[dine_in, toppings, MenuItem(name="Soft Boiled Egg")],
                )
            ]
        ),
        [AllergyTag.FISH],
    )
    assert [item.name for item in menu.sections[0].items] == ["Soft Boiled Egg"]


def test_all_known_category_rows_are_excluded() -> None:
    category_names = (
        "Dine-In Menu",
        "Recommended Toppings Set",
        "Kids Menu",
        "Extracted Menu",
        "Menu",
        "Add-ons",
        "Toppings",
        "Dinner Section",
        "Lunch Category",
    )

    assert all(is_non_food_category(MenuItem(name=name)) for name in category_names)


def test_kids_ramen_needs_check_for_fish_broth_context() -> None:
    result = classify_menu_item(MenuItem(name="Kids Ramen"), [AllergyTag.FISH])
    assert result.risk_label == "needs_check"
    assert "broth" in result.risk_reasons[0].lower()


def test_simple_sides_and_desserts_are_possible_lower_risk_for_fish() -> None:
    for name in ("Soft Boiled Egg", "Matcha Pudding"):
        result = classify_menu_item(MenuItem(name=name), [AllergyTag.FISH])
        assert result.risk_label == "possible_lower_risk"


def test_bonito_broth_is_avoid_for_fish() -> None:
    result = classify_menu_item(MenuItem(name="Bonito Broth"), [AllergyTag.FISH])
    assert result.risk_label == "avoid"
    assert result.matched_allergens == [AllergyTag.FISH]


def test_dessert_sauce_is_not_automatically_a_fish_check() -> None:
    result = classify_menu_item(
        MenuItem(name="Matcha Pudding", description="Served with a sweet caramel sauce"),
        [AllergyTag.FISH],
    )
    assert result.risk_label == "possible_lower_risk"


def test_ramen_broth_is_check_but_dashi_broth_is_avoid_for_fish() -> None:
    ramen = classify_menu_item(MenuItem(name="Ramen Broth"), [AllergyTag.FISH])
    dashi = classify_menu_item(MenuItem(name="Dashi Ramen Broth"), [AllergyTag.FISH])

    assert ramen.risk_label == "needs_check"
    assert dashi.risk_label == "avoid"


def test_oyster_is_check_for_fish_but_avoid_for_shellfish() -> None:
    fish_result = classify_menu_item(MenuItem(name="Fresh Oyster"), [AllergyTag.FISH])
    shellfish_result = classify_menu_item(MenuItem(name="Fresh Oyster"), [AllergyTag.SHELLFISH])

    assert fish_result.risk_label == "needs_check"
    assert fish_result.matched_allergens == []
    assert shellfish_result.risk_label == "avoid"
    assert shellfish_result.matched_allergens == [AllergyTag.SHELLFISH]


def test_inferred_fish_without_direct_menu_text_needs_check() -> None:
    result = classify_menu_item(
        MenuItem(name="House Ramen", inferred_risks=[AllergyTag.FISH]),
        [AllergyTag.FISH],
    )

    assert result.risk_label == "needs_check"
    assert result.matched_allergens == []
    assert "direct menu evidence is missing" in result.risk_reasons[0].lower()
