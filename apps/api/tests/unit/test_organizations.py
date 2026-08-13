from insightforge.services.organizations import slugify


def test_slugify_is_stable_url_safe_and_english_code_only() -> None:
    assert slugify("North Star Analytics") == "north-star-analytics"
    assert slugify("  Growth & Revenue  ") == "growth-revenue"
