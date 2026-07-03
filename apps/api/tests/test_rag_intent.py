from __future__ import annotations

import asyncio
from unittest.mock import patch

from allernav_api.models import (
    AllergyTag,
    HybridSearchResponse,
    LatLng,
    MenuItem,
    MenuSection,
    MenuSource,
    NearbySuggestionRequest,
    PlaceListItem,
    SourceType,
)
from allernav_api.rag_service import suggest_nearby_places_service


def test_specific_cuisine_intent_ranks_matching_candidate_first() -> None:
    candidates = [
        PlaceListItem(
            id="random",
            name="Random Grill",
            primary_type="restaurant",
            location=LatLng(lat=40.0, lng=-73.0),
        ),
        PlaceListItem(
            id="french",
            name="Maison Paris",
            primary_type="french_restaurant",
            location=LatLng(lat=40.01, lng=-73.01),
        ),
    ]
    source = MenuSource(
        source_type=SourceType.RESTAURANT_WEBSITE,
        reliability=0.9,
        sections=[
            MenuSection(
                title="Mains",
                items=[MenuItem(name="Steamed Rice"), MenuItem(name="Roasted Vegetables")],
            )
        ],
    )
    payload = NearbySuggestionRequest(
        question="I want a French restaurant",
        query="French restaurants",
        allergens=[AllergyTag.FISH],
        candidate_places=candidates,
    )

    with patch("allernav_api.rag_service.load_menu_source", return_value=source), patch(
        "allernav_api.rag_service.load_cached_reviews", return_value=[]
    ), patch(
        "allernav_api.rag_service.hybrid_search_menu",
        return_value=HybridSearchResponse(query="French restaurants", results=[]),
    ):
        response = asyncio.run(suggest_nearby_places_service(payload))

    assert response.places[0].place.id == "french"
    assert response.places[0].intent_match is True
    assert response.places[1].intent_match is False


def test_specific_cuisine_intent_reports_when_candidates_do_not_match() -> None:
    payload = NearbySuggestionRequest(
        question="I want a French restaurant",
        query="French restaurants",
        allergens=[AllergyTag.FISH],
        candidate_places=[
            PlaceListItem(
                id="random",
                name="Random Grill",
                primary_type="restaurant",
                location=LatLng(lat=40.0, lng=-73.0),
            )
        ],
    )

    with patch("allernav_api.rag_service.load_menu_source", return_value=None):
        response = asyncio.run(suggest_nearby_places_service(payload))

    assert "do not strongly match french" in response.answer.lower()
    assert response.places[0].intent_match is False
