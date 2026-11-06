from app.data.it_catalog import (
    get_it_families,
    get_it_levels,
    get_it_role,
    get_it_roles,
    is_valid_it_family,
    is_valid_it_level,
    is_valid_it_role,
)


def test_it_catalog_counts():
    assert len(get_it_roles()) == 179
    assert len(get_it_families()) == 23
    assert len(get_it_levels()) == 8


def test_it_role_slugs_are_unique():
    slugs = [role["slug"] for role in get_it_roles()]
    assert len(slugs) == len(set(slugs))


def test_it_roles_reference_valid_family_and_levels():
    family_ids = {family["id"] for family in get_it_families()}
    level_codes = {level["code"] for level in get_it_levels()}

    for role in get_it_roles():
        assert role["family"] in family_ids
        assert role["level_min"] in level_codes
        assert role["level_max"] in level_codes


def test_lookup_helpers():
    assert is_valid_it_role("backend-developer")
    assert not is_valid_it_role("marketing-manager")
    assert get_it_role("backend-developer")["family"] == "backend"
    assert is_valid_it_family("security")
    assert not is_valid_it_family("finance")
    assert is_valid_it_level("senior")
    assert not is_valid_it_level("principal-engineer")
