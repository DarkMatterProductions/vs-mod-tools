"""Tests for vs_mod_tools.core.validation."""

import pytest

from vs_mod_tools.core.validation import (
    expand_vs_template,
    extract_patterns,
    find_invalid_patterns,
)


class TestExpandVsTemplate:
    """Tests for :func:`expand_vs_template`."""

    def setup_method(self) -> None:
        """Data with two groups used across all expansion tests."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body", "legs"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
        }

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_no_template_vars_returned_unchanged(self) -> None:
        """A plain wildcard pattern with no {variables} is returned as a single-item list."""
        result = expand_vs_template("item-*-leather", self.data)

        assert result == ["item-*-leather"]

    def test_single_known_var_expands_to_states(self) -> None:
        """One {var} produces one concrete pattern per state in that group."""
        result = expand_vs_template("item-{part}-leather", self.data)

        assert len(result) == 3
        assert "item-head-leather" in result
        assert "item-body-leather" in result
        assert "item-legs-leather" in result

    def test_two_known_vars_produce_cartesian_product(self) -> None:
        """Two {variables} produce N×M concrete patterns."""
        result = expand_vs_template("item-{part}-{mat}", self.data)

        assert len(result) == 6  # 3 parts × 2 mats
        assert "item-head-leather" in result
        assert "item-head-iron" in result
        assert "item-legs-iron" in result

    def test_unknown_var_replaced_with_wildcard(self) -> None:
        """An unrecognised {variable} is replaced with * rather than raising."""
        result = expand_vs_template("item-{unknown}-leather", self.data)

        assert result == ["item-*-leather"]

    def test_mixed_known_and_unknown_vars(self) -> None:
        """Known vars expand normally; unknown vars become * in each expansion."""
        result = expand_vs_template("item-{part}-{unknown}", self.data)

        assert len(result) == 3
        assert "item-head-*" in result
        assert "item-body-*" in result
        assert "item-legs-*" in result

    def test_duplicate_var_not_doubled(self) -> None:
        """The same {var} appearing twice is de-duplicated; the dimension is not doubled."""
        result = expand_vs_template("{part}-and-{part}", self.data)

        # 3 states × 1 (deduplicated) = 3 expansions
        assert len(result) == 3

    def test_wildcard_suffix_preserved_in_expansions(self) -> None:
        """A trailing * in the pattern is preserved verbatim in every expansion."""
        result = expand_vs_template("item-{part}-*", self.data)

        assert all(v.endswith("-*") for v in result)

    def test_var_at_start_of_pattern(self) -> None:
        """{variable} at the beginning of the pattern expands correctly."""
        result = expand_vs_template("{part}-suffix", self.data)

        assert "head-suffix" in result
        assert "body-suffix" in result

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_all_unknown_vars_collapse_to_single_wildcard_pattern(self) -> None:
        """When every variable is unknown, one pattern with all * is returned."""
        result = expand_vs_template("{foo}-{bar}", self.data)

        assert result == ["*-*"]

    def test_empty_string_returned_in_list(self) -> None:
        """An empty pattern string is returned as ['']."""
        result = expand_vs_template("", self.data)

        assert result == [""]

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_expand_two_vars(self, benchmark) -> None:
        """Benchmark expand_vs_template with a two-variable pattern."""
        benchmark(expand_vs_template, "item-{part}-{mat}", self.data)


class TestExtractPatterns:
    """Tests for :func:`extract_patterns`."""

    def setup_method(self) -> None:
        """Fully-populated data covering every supported field path."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
            "skipVariants": ["item-head-iron"],
            "allowedVariants": ["item-*-leather"],
            "shapeByType": {"item-*": {"base": "entity/{part}"}},
            "texturesByType": {
                "*": {
                    "material": {
                        "baseByType": {"*": "entity/{mat}"},
                    }
                }
            },
            "durabilityByType": {"item-*-leather": 250},
            "tpHandTransformByType": {"item-head-*": {"scale": 0.64}},
            "guiTransformByType": {"item-head-*": {"scale": 2.0}},
            "groundTransformByType": {"item-head-*": {"scale": 3.1}},
            "attributes": {
                "handbook": {"groupBy": ["item-{part}-*"]},
                "clothesCategoryByType": {"item-head-*": "armorhead"},
                "attachableToEntity": {
                    "categoryCodeByType": {"item-*": "armor"},
                    "disableElementsByType": {"item-head-*": ["hair"]},
                    "keepElementsByType": {"item-head-*": ["covered"]},
                },
                "footStepSoundByType": {"item-body-*": "leather*"},
                "protectionModifiersByType": {
                    "item-*-leather": {"relativeProtection": 0.4}
                },
            },
        }

    def _paths(self, patterns: list[tuple[str, str]]) -> list[str]:
        return [p for p, _ in patterns]

    def _values(self, patterns: list[tuple[str, str]]) -> list[str]:
        return [v for _, v in patterns]

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_extracts_skip_variants(self) -> None:
        result = extract_patterns(self.data)
        assert ("skipVariants", "item-head-iron") in result

    def test_extracts_allowed_variants(self) -> None:
        result = extract_patterns(self.data)
        assert ("allowedVariants", "item-*-leather") in result

    def test_extracts_shape_by_type_keys(self) -> None:
        result = extract_patterns(self.data)
        assert ("shapeByType", "item-*") in result

    def test_extracts_durability_by_type_keys(self) -> None:
        result = extract_patterns(self.data)
        assert ("durabilityByType", "item-*-leather") in result

    def test_extracts_tp_hand_transform_by_type_keys(self) -> None:
        result = extract_patterns(self.data)
        assert ("tpHandTransformByType", "item-head-*") in result

    def test_extracts_gui_transform_by_type_keys(self) -> None:
        result = extract_patterns(self.data)
        assert ("guiTransformByType", "item-head-*") in result

    def test_extracts_ground_transform_by_type_keys(self) -> None:
        result = extract_patterns(self.data)
        assert ("groundTransformByType", "item-head-*") in result

    def test_extracts_handbook_group_by(self) -> None:
        result = extract_patterns(self.data)
        assert ("attributes.handbook.groupBy", "item-{part}-*") in result

    def test_extracts_clothes_category_by_type(self) -> None:
        result = extract_patterns(self.data)
        assert ("attributes.clothesCategoryByType", "item-head-*") in result

    def test_extracts_attachable_category_code(self) -> None:
        result = extract_patterns(self.data)
        assert ("attributes.attachableToEntity.categoryCodeByType", "item-*") in result

    def test_extracts_disable_elements_by_type(self) -> None:
        result = extract_patterns(self.data)
        assert (
            "attributes.attachableToEntity.disableElementsByType",
            "item-head-*",
        ) in result

    def test_extracts_keep_elements_by_type(self) -> None:
        result = extract_patterns(self.data)
        assert (
            "attributes.attachableToEntity.keepElementsByType",
            "item-head-*",
        ) in result

    def test_extracts_foot_step_sound_by_type(self) -> None:
        result = extract_patterns(self.data)
        assert ("attributes.footStepSoundByType", "item-body-*") in result

    def test_extracts_protection_modifiers_by_type(self) -> None:
        result = extract_patterns(self.data)
        assert ("attributes.protectionModifiersByType", "item-*-leather") in result

    def test_extracts_nested_base_by_type_recursively(self) -> None:
        """baseByType keys are found regardless of nesting depth."""
        result = extract_patterns(self.data)
        base_by_type_paths = [p for p in self._paths(result) if "baseByType" in p]
        assert len(base_by_type_paths) >= 1

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_missing_all_optional_fields_returns_empty(self) -> None:
        """Data with no pattern-bearing fields returns an empty list without error."""
        bare = {"code": "item", "variantgroups": []}

        result = extract_patterns(bare)

        assert result == []

    def test_empty_skip_and_allow_contribute_nothing(self) -> None:
        """Empty skipVariants / allowedVariants lists add no entries."""
        data = {
            "code": "item",
            "variantgroups": [],
            "skipVariants": [],
            "allowedVariants": [],
        }

        result = extract_patterns(data)

        paths = self._paths(result)
        assert "skipVariants" not in paths
        assert "allowedVariants" not in paths

    def test_none_valued_attributes_section_skipped(self) -> None:
        """A missing 'attributes' key does not raise."""
        data = {"code": "item", "variantgroups": [], "durabilityByType": {"item-*": 100}}

        result = extract_patterns(data)

        assert ("durabilityByType", "item-*") in result

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_extract_patterns(self, benchmark) -> None:
        """Benchmark extract_patterns against the fully-populated fixture."""
        benchmark(extract_patterns, self.data)


class TestFindInvalidPatterns:
    """Tests for :func:`find_invalid_patterns`."""

    def setup_method(self) -> None:
        """Two-group data and a representative processed-variant list."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
        }
        # Simulates the processed variant list (after skip/allow)
        self.variants: list[str] = [
            "item-head-leather",
            "item-body-leather",
            "item-body-iron",
        ]

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_all_valid_returns_empty_list(self) -> None:
        """No invalid patterns → empty result."""
        patterns = [
            ("shapeByType", "item-*-leather"),
            ("durabilityByType", "item-body-*"),
        ]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert result == []

    def test_one_invalid_plain_pattern_reported(self) -> None:
        """A pattern matching no variant appears in the result."""
        patterns = [("durabilityByType", "item-*-steel")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert len(result) == 1
        path, original, expanded = result[0]
        assert path == "durabilityByType"
        assert original == "item-*-steel"
        assert expanded == "item-*-steel"

    def test_plain_pattern_original_and_expanded_are_equal(self) -> None:
        """For non-template patterns the original and expanded fields are identical."""
        patterns = [("field", "item-*-steel")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        _, original, expanded = result[0]
        assert original == expanded

    def test_template_all_expansions_valid_returns_empty(self) -> None:
        """
        item-{part}-* → item-head-* and item-body-*.
        item-head-leather matches item-head-*; item-body-leather and
        item-body-iron both match item-body-*, so all expansions are valid.
        """
        patterns = [("groupBy", "item-{part}-*")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert result == []

    def test_template_one_bad_expansion_reported(self) -> None:
        """
        item-{part}-{mat} expands to four combos; item-head-iron is not in
        self.variants, so that expansion is reported.
        """
        patterns = [("groupBy", "item-{part}-{mat}")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        expanded_values = [exp for _, _, exp in result]
        assert "item-head-iron" in expanded_values

    def test_multiple_invalid_patterns_all_reported(self) -> None:
        """Every invalid pattern is included, not just the first."""
        patterns = [
            ("fieldA", "item-*-steel"),
            ("fieldB", "item-*-gold"),
        ]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert len(result) == 2

    def test_result_contains_correct_field_path(self) -> None:
        """The json_path component of each result triple is the source field path."""
        patterns = [("attributes.durabilityByType", "item-*-steel")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert result[0][0] == "attributes.durabilityByType"

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_empty_patterns_always_returns_empty(self) -> None:
        """With no patterns to validate the result is always empty."""
        result = find_invalid_patterns([], self.variants, self.data)

        assert result == []

    def test_empty_variants_marks_every_pattern_invalid(self) -> None:
        """When the processed variant list is empty every pattern is unmatched."""
        patterns = [
            ("fieldA", "item-*"),
            ("fieldB", "item-head-*"),
        ]

        result = find_invalid_patterns(patterns, [], self.data)

        assert len(result) == 2

    def test_exact_match_pattern_valid(self) -> None:
        """An exact-match pattern that equals a variant exactly is considered valid."""
        patterns = [("field", "item-head-leather")]

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert result == []

    def test_exact_match_pattern_not_in_list_is_invalid(self) -> None:
        """An exact-match pattern for a non-existent variant is invalid."""
        patterns = [("field", "item-head-iron")]  # not in self.variants

        result = find_invalid_patterns(patterns, self.variants, self.data)

        assert len(result) == 1

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_find_invalid(self, benchmark) -> None:
        """Benchmark find_invalid_patterns with a mixed valid/template pattern set."""
        patterns = [
            ("skipVariants", "item-*-leather"),
            ("allowedVariants", "item-head-*"),
            ("groupBy", "item-{part}-*"),
            ("durabilityByType", "item-{part}-{mat}"),
        ]
        benchmark(find_invalid_patterns, patterns, self.variants, self.data)
