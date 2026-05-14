"""Variant generation logic for VS item definitions."""

import fnmatch
from itertools import product


def raw_cartesian(data: dict) -> list[str]:  # type: ignore[type-arg]
    """
    Generate the full cartesian product of all variant group states.

    No ``skipVariants`` or ``allowedVariants`` filtering is applied.
    This is the structural baseline used for validation.

    Parameters
    ----------
    data:
        Parsed VS item definition dict.

    Returns
    -------
    list[str]
        Every possible variant code, e.g. ``["item-head-leather", ...]``.
    """
    prefix: str = data["code"]
    group_states: list[list[str]] = [
        group["states"] for group in data["variantgroups"]
    ]
    if not group_states:
        return [prefix]
    return [
        f"{prefix}-" + "-".join(combo) for combo in product(*group_states)
    ]


def generate_variants(
    data: dict,  # type: ignore[type-arg]
    user_filters: dict[str, list[str]],
) -> list[str]:
    """
    Build the effective variant list.

    Processing order
    ----------------
    1. Cartesian product of (optionally pre-filtered) group states.
    2. Remove any ``skipVariants`` matches.   *(subtractive)*
    3. Keep only ``allowedVariants`` matches.  *(filtering)*

    Parameters
    ----------
    data:
        Parsed VS item definition dict.
    user_filters:
        Maps group code → list of allowed state values.
        An empty list means *no filter* for that group.
        OR logic is applied within a group; AND logic across groups.

    Returns
    -------
    list[str]
        The effective variant codes after all filtering.
    """
    prefix: str = data["code"]

    # Reduce each group's state space per user filters (OR within, AND across).
    filtered_states: list[list[str]] = []
    for group in data["variantgroups"]:
        states: list[str] = group["states"]
        allowed = user_filters.get(group["code"])
        if allowed:
            states = [s for s in states if s in allowed]
        filtered_states.append(states)

    variants: list[str] = [
        f"{prefix}-" + "-".join(combo) for combo in product(*filtered_states)
    ]

    # Subtractive pass — skipVariants
    skip_patterns: list[str] = data.get("skipVariants") or []
    if skip_patterns:
        variants = [
            v
            for v in variants
            if not any(fnmatch.fnmatch(v, p) for p in skip_patterns)
        ]

    # Filtering pass — allowedVariants
    allowed_patterns: list[str] = data.get("allowedVariants") or []
    if allowed_patterns:
        variants = [
            v
            for v in variants
            if any(fnmatch.fnmatch(v, p) for p in allowed_patterns)
        ]

    return variants
