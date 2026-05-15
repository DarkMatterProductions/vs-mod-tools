"""Tests for vs_mod_tools.core.variants."""

import pytest

from vs_mod_tools.core.variants import generate_variants, raw_cartesian


class TestRawCartesian:
    """Tests for :func:`raw_cartesian`."""

    def setup_method(self) -> None:
        """Base two-group, two-state data used across most tests."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
        }

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_generates_full_product(self) -> None:
        """Two groups of two states produce exactly four variants."""
        result = raw_cartesian(self.data)

        assert len(result) == 4
        assert "item-head-leather" in result
        assert "item-head-iron" in result
        assert "item-body-leather" in result
        assert "item-body-iron" in result

    def test_code_prefix_prepended(self) -> None:
        """Every variant starts with the item's code followed by a hyphen."""
        result = raw_cartesian(self.data)

        assert all(v.startswith("item-") for v in result)

    def test_single_group(self) -> None:
        """One group returns one variant per state in order."""
        data = {
            "code": "item",
            "variantgroups": [{"code": "mat", "states": ["leather", "iron", "steel"]}],
        }

        result = raw_cartesian(data)

        assert result == ["item-leather", "item-iron", "item-steel"]

    def test_three_groups_cartesian_count(self) -> None:
        """Three groups of two states each produce 2³ = 8 variants."""
        data = {
            "code": "item",
            "variantgroups": [
                {"code": "a", "states": ["x", "y"]},
                {"code": "b", "states": ["1", "2"]},
                {"code": "c", "states": ["p", "q"]},
            ],
        }

        result = raw_cartesian(data)

        assert len(result) == 8

    def test_no_variant_groups_returns_bare_code(self) -> None:
        """With no groups the product of an empty sequence yields one item: the prefix."""
        data = {"code": "item", "variantgroups": []}

        result = raw_cartesian(data)

        assert result == ["item"]

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_group_with_empty_states_yields_empty(self) -> None:
        """A group with zero states short-circuits the cartesian product to []."""
        data = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head"]},
                {"code": "mat", "states": []},
            ],
        }

        result = raw_cartesian(data)

        assert result == []

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_raw_cartesian(self, benchmark) -> None:
        """Benchmark raw_cartesian with a two-group, two-state dataset."""
        benchmark(raw_cartesian, self.data)


class TestGenerateVariants:
    """Tests for :func:`generate_variants`."""

    def setup_method(self) -> None:
        """Three-part, two-material base data with no skip/allow."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body", "legs"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
            "skipVariants": [],
            "allowedVariants": [],
        }
        self.all_variants: list[str] = [
            "item-head-leather",
            "item-head-iron",
            "item-body-leather",
            "item-body-iron",
            "item-legs-leather",
            "item-legs-iron",
        ]

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_no_filters_returns_all_variants(self) -> None:
        """Empty filters + no skip/allow → full cartesian product."""
        result = generate_variants(self.data, {})

        assert sorted(result) == sorted(self.all_variants)

    def test_single_group_filter_or_logic(self) -> None:
        """Two values for the same group apply OR logic."""
        result = generate_variants(self.data, {"part": ["head", "legs"]})

        assert "item-head-leather" in result
        assert "item-head-iron" in result
        assert "item-legs-leather" in result
        assert "item-legs-iron" in result
        assert "item-body-leather" not in result
        assert "item-body-iron" not in result

    def test_cross_group_filters_and_logic(self) -> None:
        """Filters across different groups are ANDed — only the intersection survives."""
        result = generate_variants(self.data, {"part": ["head"], "mat": ["leather"]})

        assert result == ["item-head-leather"]

    def test_skip_variants_exact_match_removed(self) -> None:
        """An exact skipVariants entry removes precisely that variant."""
        data = {**self.data, "skipVariants": ["item-head-iron"]}

        result = generate_variants(data, {})

        assert "item-head-iron" not in result
        assert "item-head-leather" in result
        assert len(result) == 5

    def test_skip_variants_wildcard_removes_all_matches(self) -> None:
        """A wildcard skipVariants entry removes every matching variant."""
        data = {**self.data, "skipVariants": ["item-*-iron"]}

        result = generate_variants(data, {})

        assert not any("iron" in v for v in result)
        assert len(result) == 3

    def test_allowed_variants_restricts_to_matches(self) -> None:
        """allowedVariants keeps only variants matching at least one pattern."""
        data = {**self.data, "allowedVariants": ["item-*-leather"]}

        result = generate_variants(data, {})

        assert all("leather" in v for v in result)
        assert len(result) == 3

    def test_allowed_variants_multiple_patterns_are_ored(self) -> None:
        """Multiple allowedVariants entries act as OR: a variant passes if any matches."""
        data = {
            **self.data,
            "allowedVariants": ["item-head-leather", "item-body-iron"],
        }

        result = generate_variants(data, {})

        assert sorted(result) == ["item-body-iron", "item-head-leather"]

    def test_skip_applied_before_allow(self) -> None:
        """skipVariants is processed first, so a skipped variant cannot be re-admitted by allowedVariants."""
        data = {
            **self.data,
            "skipVariants": ["item-head-iron"],
            "allowedVariants": ["item-*-iron"],
        }

        result = generate_variants(data, {})

        # head-iron removed by skip; allow then keeps remaining iron variants
        assert "item-head-iron" not in result
        assert "item-body-iron" in result
        assert "item-legs-iron" in result

    def test_user_filter_combined_with_skip_and_allow(self) -> None:
        """User filters, skip, and allow all stack independently."""
        data = {
            **self.data,
            "skipVariants": ["item-head-iron"],
            "allowedVariants": ["item-*-leather", "item-body-iron"],
        }

        result = generate_variants(data, {"part": ["head", "body"]})

        assert "item-head-leather" in result
        assert "item-body-leather" in result
        assert "item-body-iron" in result
        assert "item-head-iron" not in result  # removed by skip
        assert "item-legs-leather" not in result  # removed by user filter

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_filter_for_nonexistent_state_returns_empty(self) -> None:
        """A filter value that matches no state produces an empty variant list."""
        result = generate_variants(self.data, {"part": ["nonexistent"]})

        assert result == []

    def test_allow_list_with_no_matches_returns_empty(self) -> None:
        """An allowedVariants list that matches nothing results in no variants."""
        data = {**self.data, "allowedVariants": ["item-*-steel"]}

        result = generate_variants(data, {})

        assert result == []

    def test_skip_all_variants_returns_empty(self) -> None:
        """Skipping every variant produces an empty list."""
        data = {**self.data, "skipVariants": ["item-*"]}

        result = generate_variants(data, {})

        assert result == []

    def test_missing_skip_and_allow_treated_as_empty(self) -> None:
        """Data without skipVariants/allowedVariants keys behaves like empty lists."""
        data = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
            ],
        }

        result = generate_variants(data, {})

        assert sorted(result) == ["item-body", "item-head"]

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_generate_variants(self, benchmark) -> None:
        """Benchmark generate_variants with typical three-part, two-material data."""
        benchmark(generate_variants, self.data, {})
