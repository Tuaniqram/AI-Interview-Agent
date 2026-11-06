from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("it_catalog.json")


@lru_cache(maxsize=1)
def load_it_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_it_families() -> list[dict[str, Any]]:
    return load_it_catalog()["families"]


def get_it_levels() -> list[dict[str, Any]]:
    return load_it_catalog()["levels"]


def get_it_roles() -> list[dict[str, Any]]:
    return load_it_catalog()["roles"]


@lru_cache(maxsize=1)
def _role_by_slug() -> dict[str, dict[str, Any]]:
    return {role["slug"]: role for role in get_it_roles()}


@lru_cache(maxsize=1)
def it_family_ids() -> frozenset[str]:
    return frozenset(family["id"] for family in get_it_families())


@lru_cache(maxsize=1)
def it_level_codes() -> frozenset[str]:
    return frozenset(level["code"] for level in get_it_levels())


def get_it_role(slug: str) -> dict[str, Any] | None:
    return _role_by_slug().get(slug)


def is_valid_it_role(slug: str) -> bool:
    return slug in _role_by_slug()


def is_valid_it_family(family: str) -> bool:
    return family in it_family_ids()


def is_valid_it_level(level: str) -> bool:
    return level in it_level_codes()
