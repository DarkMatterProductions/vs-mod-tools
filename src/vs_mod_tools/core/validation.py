"""Pattern validation logic for VS item definitions."""

import fnmatch
import re
from itertools import product

_VS_TEMPLATE_RE = re.compile(r"\{([^}]+)\}")


def expand_vs_template(pattern: str, data: dict) -> list[str]:  # type: ignore[type-arg]
    """
    Expand a VS template pattern into every concrete fnmatch glob it describes.

    VS uses ``{groupcode}`` as a substitution variable. Each token is replaced
    by each of that group's actual state values, and the cartesian product of
    all referenced groups is taken so that every unique combination becomes its
    own concrete pattern.

    Any ``{variable}`` not found in the item's variantgroups is left as a ``*``
    wildcard so unknown substitutions degrade gracefully.

    Parameters
    ----------
    pattern:
        A raw VS pattern string, e.g. ``"item-{bodypart}-{construction}-*"``.
    data:
        Parsed VS item definition dict (used to look up group states).

    Returns
    -------
    list[str]
        One concrete fnmatch glob per state combination.
        Returns ``[pattern]`` unchanged when no template variables are present.

    Examples
    --------
    >>> expand_vs_template("item-{part}-*", data)
    ["item-head-*", "item-body-*", "item-legs-*"]
    """
    tokens: list[str] = _VS_TEMPLATE_RE.findall(pattern)
    if not tokens:
        return [pattern]

    group_states: dict[str, list[str]] = {
        g["code"]: g["states"] for g in data["variantgroups"]
    }

    # Preserve insertion order; de-duplicate in case a token appears twice.
    seen: set[str] = set()
    ordered_tokens: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            ordered_tokens.append(t)

    known = [t for t in ordered_tokens if t in group_states]
    unknown = [t for t in ordered_tokens if t not in group_states]

    if not known:
        # All tokens are unrecognised — collapse every {var} to *.
        return [_VS_TEMPLATE_RE.sub("*", pattern)]

    expanded: list[str] = []
    for combo in product(*(group_states[t] for t in known)):
        concrete = pattern
        for token, value in zip(known, combo):
            concrete = concrete.replace(f"{{{token}}}", value)
        for token in unknown:
            concrete = concrete.replace(f"{{{token}}}", "*")
        expanded.append(concrete)

    return expanded


def extract_patterns(data: dict) -> list[tuple[str, str]]:  # type: ignore[type-arg]
    """
    Walk all known variant-pattern fields and return ``(json_path, pattern)`` pairs.

    Handles both top-level fields and deeply nested locations.

    Covered fields
    --------------
    Top-level:
        ``skipVariants``, ``allowedVariants``, ``shapeByType``,
        ``texturesByType``, ``durabilityByType``, ``tpHandTransformByType``,
        ``guiTransformByType``, ``groundTransformByType``

    Under ``attributes``:
        ``handbook.groupBy``, ``clothesCategoryByType``,
        ``attachableToEntity.{categoryCodeByType, disableElementsByType,
        keepElementsByType}``, ``footStepSoundByType``,
        ``protectionModifiersByType``

    Recursive (anywhere in the tree):
        ``baseByType``

    Parameters
    ----------
    data:
        Parsed VS item definition dict.

    Returns
    -------
    list[tuple[str, str]]
        ``(dot-separated JSON path, pattern string)`` pairs.
    """
    results: list[tuple[str, str]] = []

    def from_list(path: str, lst: list) -> None:  # type: ignore[type-arg]
        for item in lst:
            if isinstance(item, str):
                results.append((path, item))

    def from_dict_keys(path: str, dct: dict) -> None:  # type: ignore[type-arg]
        for key in dct:
            results.append((path, str(key)))

    def recurse_for_key(path: str, node: object, target: str) -> None:
        """Recursively find every dict keyed by *target* and harvest its keys."""
        if isinstance(node, dict):
            for k, v in node.items():
                child = f"{path}.{k}"
                if k == target:
                    from_dict_keys(child, v)
                else:
                    recurse_for_key(child, v, target)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                recurse_for_key(f"{path}[{i}]", item, target)

    # ── Top-level list fields ─────────────────────────────────────────────────
    from_list("skipVariants", data.get("skipVariants") or [])
    from_list("allowedVariants", data.get("allowedVariants") or [])

    # ── Top-level *ByType dict fields ─────────────────────────────────────────
    for field in (
        "shapeByType",
        "texturesByType",
        "durabilityByType",
        "tpHandTransformByType",
        "guiTransformByType",
        "groundTransformByType",
    ):
        from_dict_keys(field, data.get(field) or {})

    # ── attributes sub-fields ─────────────────────────────────────────────────
    attrs: dict = data.get("attributes") or {}  # type: ignore[type-arg]

    from_list(
        "attributes.handbook.groupBy",
        (attrs.get("handbook") or {}).get("groupBy") or [],
    )
    from_dict_keys(
        "attributes.clothesCategoryByType",
        attrs.get("clothesCategoryByType") or {},
    )

    attachable: dict = attrs.get("attachableToEntity") or {}  # type: ignore[type-arg]
    for sub in ("categoryCodeByType", "disableElementsByType", "keepElementsByType"):
        from_dict_keys(
            f"attributes.attachableToEntity.{sub}",
            attachable.get(sub) or {},
        )

    from_dict_keys(
        "attributes.footStepSoundByType",
        attrs.get("footStepSoundByType") or {},
    )
    from_dict_keys(
        "attributes.protectionModifiersByType",
        attrs.get("protectionModifiersByType") or {},
    )

    # ── Recursive search for baseByType anywhere in the tree ─────────────────
    recurse_for_key("root", data, "baseByType")

    return results


def find_invalid_patterns(
    patterns: list[tuple[str, str]],
    all_variants: list[str],
    data: dict,  # type: ignore[type-arg]
) -> list[tuple[str, str, str]]:
    """
    Return ``(path, original_pattern, expanded_pattern)`` triples where the
    expanded concrete pattern matches no entry in *all_variants*.

    Template variables (``{groupcode}``) are first expanded into every
    concrete combination via :func:`expand_vs_template`. Each expansion is
    checked independently — a template that produces one empty group is
    reported even if other expansions of the same template are valid.

    Parameters
    ----------
    patterns:
        Output of :func:`extract_patterns`.
    all_variants:
        The processed variant list (after skip/allow filtering) to validate
        against.
    data:
        Parsed VS item definition dict (passed to :func:`expand_vs_template`).

    Returns
    -------
    list[tuple[str, str, str]]
        ``(json_path, original_pattern, expanded_pattern)`` for every
        expansion that matches no valid variant.
    """
    invalid: list[tuple[str, str, str]] = []
    for path, pattern in patterns:
        for expanded in expand_vs_template(pattern, data):
            if not any(fnmatch.fnmatch(v, expanded) for v in all_variants):
                invalid.append((path, pattern, expanded))
    return invalid
