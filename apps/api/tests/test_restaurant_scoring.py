from allernav_api.models import AllergyTag, MenuItem, MenuSection, MenuSource, SourceType
from allernav_api.restaurant_scoring import has_confirmed_allergen_risk_review, score_restaurant_menu


def menu_source(items: list[MenuItem]) -> MenuSource:
    return MenuSource(
        source_type=SourceType.RESTAURANT_WEBSITE,
        reliability=0.85,
        sections=[MenuSection(title="Menu", items=items)],
    )


def test_restaurant_score_penalizes_selected_allergen_matches() -> None:
    lower_risk = score_restaurant_menu(
        menu_source([MenuItem(name="Basmati Rice", description="Steamed rice with herbs and lemon")]),
        [AllergyTag.SESAME, AllergyTag.FISH],
    )
    concern = score_restaurant_menu(
        menu_source([MenuItem(name="Sesame Naan", description="Naan topped with sesame seeds")]),
        [AllergyTag.SESAME, AllergyTag.FISH],
    )

    assert lower_risk.possible_lower_risk_count == 1
    assert concern.avoid_count == 1
    assert concern.score < lower_risk.score
    assert lower_risk.label == "Strong candidate, still verify"
    assert concern.label == "High concern"


def test_restaurant_score_rewards_possible_lower_risk_ratio() -> None:
    mostly_possible = score_restaurant_menu(
        menu_source(
            [
                MenuItem(name="Herb Rice", description="Steamed rice with herbs and lemon"),
                MenuItem(name="Roasted Vegetables", description="Seasonal vegetables roasted with olive oil"),
            ]
        ),
        [AllergyTag.FISH],
    )
    mostly_checks = score_restaurant_menu(
        menu_source([MenuItem(name="Kids Ramen"), MenuItem(name="House Broth")]),
        [AllergyTag.FISH],
    )

    assert mostly_possible.possible_lower_risk_count == 2
    assert mostly_possible.score > mostly_checks.score


def test_some_avoid_items_do_not_sink_a_menu_with_many_possible_options() -> None:
    items = [
        MenuItem(name=f"Rice Plate {index}", description="Steamed rice with vegetables and fresh herbs")
        for index in range(8)
    ] + [
        MenuItem(name="Fish Fry", description="Crispy battered fish with fries"),
        MenuItem(name="Grilled Salmon", description="Salmon with seasonal vegetables"),
    ]
    score = score_restaurant_menu(menu_source(items), [AllergyTag.FISH])

    assert score.avoid_count == 2
    assert score.possible_lower_risk_count == 8
    assert score.score >= 75
    assert score.label == "Strong candidate, still verify"


def test_restaurant_score_does_not_reward_menu_size_alone() -> None:
    concise = score_restaurant_menu(
        menu_source([MenuItem(name="Herb Rice", description="Steamed rice with herbs and lemon")]),
        [AllergyTag.PEANUT],
    )
    vague = score_restaurant_menu(
        menu_source([MenuItem(name=f"Dish {index}") for index in range(20)]),
        [AllergyTag.PEANUT],
    )

    assert concise.score > vague.score
    assert vague.insufficient_info_count == 20


def test_scan_needed_score_is_capped_and_not_recommended() -> None:
    score = score_restaurant_menu(None, [AllergyTag.PEANUT])
    assert score.score <= 20
    assert score.label == "Scan needed"


def test_short_but_specific_dishes_are_not_over_penalized() -> None:
    score = score_restaurant_menu(
        menu_source([MenuItem(name="Plain Rice"), MenuItem(name="Roasted Vegetables"), MenuItem(name="Garden Salad")]),
        [AllergyTag.PEANUT, AllergyTag.SESAME, AllergyTag.FISH],
    )
    assert score.possible_lower_risk_count == 3
    assert score.insufficient_info_count == 0
    assert score.score >= 70


def test_restaurant_score_excludes_non_food_category_rows() -> None:
    score = score_restaurant_menu(
        menu_source(
            [
                MenuItem(name="Dine-In Menu"),
                MenuItem(name="Recommended Toppings Set"),
                MenuItem(name="Soft Boiled Egg"),
                MenuItem(name="Kids Ramen"),
            ]
        ),
        [AllergyTag.FISH],
    )

    assert score.menu_item_count == 2
    assert score.possible_lower_risk_count == 1
    assert score.needs_check_count == 1
    assert score.avoid_count == 0
    assert score.score >= 60
    assert "no menu items directly mention fish" in score.reason.lower()


def test_ichiran_style_menu_scores_as_better_candidate_for_fish() -> None:
    items = [
        MenuItem(name="Soft Boiled Egg"),
        MenuItem(name="White Rice"),
        MenuItem(name="Matcha Pudding"),
        MenuItem(name="Green Tea Pudding"),
        MenuItem(name="Sliced Pork"),
        MenuItem(name="Seasonal Vegetables"),
        MenuItem(name="Classic Ramen"),
        MenuItem(name="Kids Ramen"),
        MenuItem(name="House Broth"),
    ]

    score = score_restaurant_menu(menu_source(items), [AllergyTag.FISH])

    assert score.possible_lower_risk_count == 6
    assert score.needs_check_count == 3
    assert score.avoid_count == 0
    assert 70 <= score.score <= 85
    assert score.label == "Strong candidate, still verify"


def test_several_possible_items_and_one_avoid_do_not_score_extremely_low() -> None:
    items = [
        MenuItem(name=f"Vegetable Plate {index}", description="Vegetables, rice, and herbs")
        for index in range(4)
    ] + [MenuItem(name="Grilled Salmon")]

    score = score_restaurant_menu(menu_source(items), [AllergyTag.FISH])

    assert score.possible_lower_risk_count == 4
    assert score.avoid_count == 1
    assert score.score >= 75


def test_buffet_or_shared_prep_signal_lowers_restaurant_score() -> None:
    source = menu_source(
        [
            MenuItem(name="Steamed Rice"),
            MenuItem(name="Roasted Vegetables"),
            MenuItem(name="Garden Salad"),
        ]
    ).model_copy(update={"raw_text": "All-you-can-eat buffet with a shared grill."})

    regular = score_restaurant_menu(menu_source(source.sections[0].items), [AllergyTag.FISH])
    buffet = score_restaurant_menu(source, [AllergyTag.FISH])

    assert buffet.buffet_or_shared_prep_signal is True
    assert buffet.score == regular.score - 20


def test_confirmed_allergen_review_lowers_restaurant_score() -> None:
    source = menu_source(
        [
            MenuItem(name="Steamed Rice"),
            MenuItem(name="Roasted Vegetables"),
            MenuItem(name="Garden Salad"),
        ]
    )

    regular = score_restaurant_menu(source, [AllergyTag.FISH])
    with_review = score_restaurant_menu(source, [AllergyTag.FISH], confirmed_allergen_review=True)

    assert with_review.confirmed_allergen_review is True
    assert with_review.score == regular.score - 20


def test_confirmed_allergen_review_requires_risk_phrase_and_selected_allergen() -> None:
    assert has_confirmed_allergen_risk_review(
        ["I had an allergic reaction after being served salmon."],
        [AllergyTag.FISH],
    )
    assert not has_confirmed_allergen_risk_review(
        ["The salmon was delicious and service was slow."],
        [AllergyTag.FISH],
    )
