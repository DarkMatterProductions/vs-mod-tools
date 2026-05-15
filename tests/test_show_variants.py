"""Tests for vs_mod_tools.cli.show_variants."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vs_mod_tools.cli.show_variants import (
    _DESCRIPTION,
    _add_static_args,
    _build_parser,
    main,
)


class TestAddStaticArgs:
    """Tests for :func:`_add_static_args`."""

    def setup_method(self) -> None:
        """Fresh ArgumentParser for each test."""
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser()

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_adds_file_short_flag(self) -> None:
        """-f is accepted and stored as args.file."""
        _add_static_args(self.parser)
        args = self.parser.parse_args(["-f", "test.json"])
        assert args.file == "test.json"

    def test_adds_file_long_flag(self) -> None:
        """--file is accepted as an alias for -f."""
        _add_static_args(self.parser)
        args = self.parser.parse_args(["--file", "test.json"])
        assert args.file == "test.json"

    def test_adds_validate_flag(self) -> None:
        """--validate is present and stores True when supplied."""
        _add_static_args(self.parser)
        args = self.parser.parse_args(["-f", "x.json", "--validate"])
        assert args.validate is True

    def test_validate_defaults_false(self) -> None:
        """--validate defaults to False when omitted."""
        _add_static_args(self.parser)
        args = self.parser.parse_args(["-f", "x.json"])
        assert args.validate is False

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_file_is_required(self) -> None:
        """Omitting -f causes argparse to exit with a non-zero code."""
        _add_static_args(self.parser)
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args([])
        assert exc_info.value.code != 0

    def test_unknown_flag_causes_error(self) -> None:
        """An unrecognised flag causes argparse to exit."""
        _add_static_args(self.parser)
        with pytest.raises(SystemExit):
            self.parser.parse_args(["-f", "x.json", "--nonexistent"])


class TestBuildParser:
    """Tests for :func:`_build_parser`."""

    def setup_method(self) -> None:
        """Two-group item data used to build the dynamic parser."""
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
        }

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_returns_argument_parser_instance(self) -> None:
        """_build_parser returns an ArgumentParser."""
        parser = _build_parser(self.data)
        assert isinstance(parser, argparse.ArgumentParser)

    def test_description_matches_module_constant(self) -> None:
        """The parser's description is taken from the _DESCRIPTION constant."""
        parser = _build_parser(self.data)
        assert parser.description == _DESCRIPTION

    def test_dynamic_group_flags_registered(self) -> None:
        """One flag per variantgroup is accepted by the parser."""
        parser = _build_parser(self.data)
        args = parser.parse_args(["-f", "x.json", "--part", "head", "--mat", "iron"])
        assert args.part == ["head"]
        assert args.mat == ["iron"]

    def test_dynamic_flags_are_repeatable(self) -> None:
        """The same group flag may be repeated to express OR logic."""
        parser = _build_parser(self.data)
        args = parser.parse_args(["-f", "x.json", "--part", "head", "--part", "body"])
        assert args.part == ["head", "body"]

    def test_dynamic_args_placed_in_named_group(self) -> None:
        """Dynamic group flags appear under 'variant group filter arguments'."""
        parser = _build_parser(self.data)
        group_titles = [g.title for g in parser._action_groups]
        assert "variant group filter arguments" in group_titles

    def test_hyphenated_group_code_dest_uses_underscore(self) -> None:
        """A group code containing hyphens is stored with underscores as dest."""
        data = {
            "code": "item",
            "variantgroups": [
                {"code": "body-part", "states": ["upper", "lower"]},
            ],
        }
        parser = _build_parser(data)
        args = parser.parse_args(["-f", "x.json", "--body-part", "upper"])
        assert args.body_part == ["upper"]

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_invalid_state_value_rejected(self) -> None:
        """A value not in a group's states causes argparse to exit."""
        parser = _build_parser(self.data)
        with pytest.raises(SystemExit):
            parser.parse_args(["-f", "x.json", "--part", "invalid_state"])

    def test_no_variant_groups_produces_no_dynamic_flags(self) -> None:
        """With an empty variantgroups list no dynamic flags are registered."""
        data = {"code": "item", "variantgroups": []}
        parser = _build_parser(data)
        all_opts = [opt for a in parser._actions for opt in a.option_strings]
        assert "--part" not in all_opts
        assert "--mat" not in all_opts


class TestMain:
    """End-to-end tests for :func:`main`."""

    def setup_method(self) -> None:
        """
        Common test data and a pre-configured mock Path.

        Individual tests patch ``Path`` and ``load_vs_json`` via ``mocker``
        so that no real filesystem access occurs.
        """
        self.data: dict = {
            "code": "item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
                {"code": "mat", "states": ["leather", "iron"]},
            ],
            "skipVariants": [],
            "allowedVariants": [],
        }
        # Expected full variant set (no skip/allow, no user filters)
        self.all_variants: list[str] = [
            "item-head-leather",
            "item-head-iron",
            "item-body-leather",
            "item-body-iron",
        ]
        self.mock_path: MagicMock = MagicMock(spec=Path)
        self.mock_path.is_file.return_value = True

    def _patch_io(self, mocker: MagicMock) -> None:
        """Patch Path construction and load_vs_json for a typical successful run."""
        mock_cls = mocker.patch("vs_mod_tools.cli.show_variants.Path")
        mock_cls.return_value = self.mock_path
        mocker.patch(
            "vs_mod_tools.cli.show_variants.load_vs_json",
            return_value=self.data,
        )

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_help_without_file_exits_zero(self) -> None:
        """--help without -f prints static help and exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_short_help_without_file_exits_zero(self) -> None:
        """-h without -f also exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["-h"])
        assert exc_info.value.code == 0

    def test_help_with_file_exits_zero(self, mocker: MagicMock) -> None:
        """--help with -f (full dynamic parser) exits with code 0."""
        self._patch_io(mocker)
        with pytest.raises(SystemExit) as exc_info:
            main(["-f", "fake.json", "--help"])
        assert exc_info.value.code == 0

    def test_outputs_all_variants(self, mocker: MagicMock, capsys) -> None:
        """main() prints every variant in the effective list."""
        self._patch_io(mocker)

        main(["-f", "fake.json"])

        out = capsys.readouterr().out
        for v in self.all_variants:
            assert v in out

    def test_outputs_variant_count_header(self, mocker: MagicMock, capsys) -> None:
        """The header line contains the total variant count."""
        self._patch_io(mocker)

        main(["-f", "fake.json"])

        assert "4 total" in capsys.readouterr().out

    def test_filter_reduces_output(self, mocker: MagicMock, capsys) -> None:
        """Supplying a group filter excludes non-matching variants."""
        self._patch_io(mocker)

        main(["-f", "fake.json", "--part", "head"])

        out = capsys.readouterr().out
        assert "item-head-leather" in out
        assert "item-head-iron" in out
        assert "item-body-leather" not in out
        assert "item-body-iron" not in out

    def test_repeated_filter_flag_or_logic(self, mocker: MagicMock, capsys) -> None:
        """Two --part flags produce OR logic: both head and body variants appear."""
        self._patch_io(mocker)

        main(["-f", "fake.json", "--part", "head", "--part", "body"])

        out = capsys.readouterr().out
        assert "item-head-leather" in out
        assert "item-body-leather" in out

    def test_filter_note_shown_when_active(self, mocker: MagicMock, capsys) -> None:
        """A 'Filters:' line is printed when at least one group filter is active."""
        self._patch_io(mocker)

        main(["-f", "fake.json", "--part", "head"])

        assert "Filters:" in capsys.readouterr().out

    def test_no_filter_note_when_no_filters(self, mocker: MagicMock, capsys) -> None:
        """No 'Filters:' line appears when no group filters are specified."""
        self._patch_io(mocker)

        main(["-f", "fake.json"])

        assert "Filters:" not in capsys.readouterr().out

    def test_validate_flag_shows_validation_block(self, mocker: MagicMock, capsys) -> None:
        """--validate causes a validation section to appear in the output."""
        self._patch_io(mocker)
        mocker.patch("vs_mod_tools.cli.show_variants.extract_patterns", return_value=[])
        mocker.patch("vs_mod_tools.cli.show_variants.find_invalid_patterns", return_value=[])

        main(["-f", "fake.json", "--validate"])

        assert "Validation" in capsys.readouterr().out

    def test_validate_all_valid_shows_success_message(self, mocker: MagicMock, capsys) -> None:
        """When no invalid patterns exist, the success message is shown."""
        self._patch_io(mocker)
        mocker.patch("vs_mod_tools.cli.show_variants.extract_patterns", return_value=[])
        mocker.patch("vs_mod_tools.cli.show_variants.find_invalid_patterns", return_value=[])

        main(["-f", "fake.json", "--validate"])

        assert "all patterns match" in capsys.readouterr().out

    def test_validate_shows_invalid_plain_pattern(self, mocker: MagicMock, capsys) -> None:
        """Invalid non-template patterns are printed with their field path."""
        self._patch_io(mocker)
        mocker.patch(
            "vs_mod_tools.cli.show_variants.extract_patterns",
            return_value=[("durabilityByType", "item-*-steel")],
        )
        mocker.patch(
            "vs_mod_tools.cli.show_variants.find_invalid_patterns",
            return_value=[("durabilityByType", "item-*-steel", "item-*-steel")],
        )

        main(["-f", "fake.json", "--validate"])

        out = capsys.readouterr().out
        assert "item-*-steel" in out
        assert "1 unmatched" in out

    def test_validate_shows_template_and_expanded_form(self, mocker: MagicMock, capsys) -> None:
        """When the original and expanded patterns differ, both are shown."""
        self._patch_io(mocker)
        mocker.patch(
            "vs_mod_tools.cli.show_variants.extract_patterns",
            return_value=[("groupBy", "item-{part}-*")],
        )
        mocker.patch(
            "vs_mod_tools.cli.show_variants.find_invalid_patterns",
            return_value=[("groupBy", "item-{part}-*", "item-body-*")],
        )

        main(["-f", "fake.json", "--validate"])

        out = capsys.readouterr().out
        assert "template" in out
        assert "expanded" in out

    def test_validate_count_reflects_number_of_invalids(self, mocker: MagicMock, capsys) -> None:
        """The 'N unmatched expansion(s)' line counts correctly."""
        self._patch_io(mocker)
        mocker.patch("vs_mod_tools.cli.show_variants.extract_patterns", return_value=[])
        mocker.patch(
            "vs_mod_tools.cli.show_variants.find_invalid_patterns",
            return_value=[
                ("fieldA", "item-*-steel", "item-*-steel"),
                ("fieldB", "item-*-gold", "item-*-gold"),
            ],
        )

        main(["-f", "fake.json", "--validate"])

        assert "2 unmatched" in capsys.readouterr().out

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_missing_file_exits_with_error_message(self, mocker: MagicMock) -> None:
        """main() raises SystemExit with an error string when the file is absent."""
        mock_cls = mocker.patch("vs_mod_tools.cli.show_variants.Path")
        mock_cls.return_value.is_file.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            main(["-f", "nonexistent.json"])

        assert "error" in str(exc_info.value.code).lower()

    def test_invalid_filter_value_exits(self, mocker: MagicMock) -> None:
        """Passing a state value not in the group's choices triggers a parse error."""
        self._patch_io(mocker)

        with pytest.raises(SystemExit):
            main(["-f", "fake.json", "--part", "totally_wrong"])

    def test_no_args_exits_with_error(self) -> None:
        """Calling main() with an empty argv causes argparse to exit (missing -f)."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0
