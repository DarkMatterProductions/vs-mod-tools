"""Shared pytest fixtures available to all test modules."""

import pytest


@pytest.fixture
def minimal_data() -> dict:
    """Minimal VS item data — two groups, two states each, no skip/allow."""
    return {
        "code": "item",
        "variantgroups": [
            {"code": "part", "states": ["head", "body"]},
            {"code": "mat", "states": ["leather", "iron"]},
        ],
        "skipVariants": [],
        "allowedVariants": [],
    }


@pytest.fixture
def data_with_skip() -> dict:
    """VS item data with a single exact skipVariants entry."""
    return {
        "code": "item",
        "variantgroups": [
            {"code": "part", "states": ["head", "body"]},
            {"code": "mat", "states": ["leather", "iron"]},
        ],
        "skipVariants": ["item-head-iron"],
        "allowedVariants": [],
    }


@pytest.fixture
def data_with_allow() -> dict:
    """VS item data where allowedVariants restricts to leather + body-iron."""
    return {
        "code": "item",
        "variantgroups": [
            {"code": "part", "states": ["head", "body"]},
            {"code": "mat", "states": ["leather", "iron"]},
        ],
        "skipVariants": [],
        "allowedVariants": ["item-*-leather", "item-body-iron"],
    }


@pytest.fixture
def full_data() -> dict:
    """
    Full VS item data with all major fields populated.

    Raw cartesian  : head-leather, head-iron, body-leather, body-iron,
                     legs-leather, legs-iron  (6 variants)
    After skip     : removes head-iron                                  (5)
    After allow    : keeps *-leather + body-iron                        (4)
    Final variants : head-leather, body-leather, body-iron, legs-leather
    """
    return {
        "code": "item",
        "variantgroups": [
            {"code": "part", "states": ["head", "body", "legs"]},
            {"code": "mat", "states": ["leather", "iron"]},
        ],
        "skipVariants": ["item-head-iron"],
        "allowedVariants": ["item-*-leather", "item-body-iron"],
        "shapeByType": {
            "item-*": {"base": "entity/{part}"},
        },
        "texturesByType": {
            "*": {
                "material": {
                    "baseByType": {"*": "entity/{mat}"},
                }
            }
        },
        "durabilityByType": {
            "item-*-leather": 250,
            "item-*-iron": 500,
        },
        "tpHandTransformByType": {"item-head-*": {"scale": 0.64}},
        "guiTransformByType": {"item-head-*": {"scale": 2.0}},
        "groundTransformByType": {"item-head-*": {"scale": 3.1}},
        "attributes": {
            "handbook": {"groupBy": ["item-{part}-*"]},
            "clothesCategoryByType": {
                "item-head-*": "armorhead",
                "item-body-*": "armorbody",
            },
            "attachableToEntity": {
                "categoryCodeByType": {"item-*": "armor"},
                "disableElementsByType": {"item-head-*": ["hair"]},
                "keepElementsByType": {"item-head-*": ["hair-covered"]},
            },
            "footStepSoundByType": {"item-body-*": "leather*"},
            "protectionModifiersByType": {
                "item-*-leather": {"relativeProtection": 0.4},
            },
        },
    }
