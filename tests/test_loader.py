"""Tests for vs_mod_tools.core.loader."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vs_mod_tools.core.loader import load_vs_json


class TestLoadVsJson:
    """Tests for :func:`load_vs_json`."""

    def setup_method(self) -> None:
        """Initialise reusable test state before each test."""
        self.expected_data: dict = {
            "code": "test-item",
            "variantgroups": [
                {"code": "part", "states": ["head", "body"]},
            ],
        }
        # Pre-built mock Path; individual tests may override attributes.
        self.mock_path: MagicMock = MagicMock(spec=Path)
        self.mock_file: MagicMock = MagicMock()
        self.mock_path.open.return_value.__enter__.return_value = self.mock_file

    # ── Positive tests ────────────────────────────────────────────────────────

    def test_returns_parsed_dict(self, mocker: MagicMock) -> None:
        """load_vs_json returns whatever json5.load produces."""
        mock_load = mocker.patch(
            "vs_mod_tools.core.loader.json5.load",
            return_value=self.expected_data,
        )

        result = load_vs_json(self.mock_path)

        assert result == self.expected_data
        mock_load.assert_called_once_with(self.mock_file)

    def test_opens_with_utf8_sig_encoding(self, mocker: MagicMock) -> None:
        """File is always opened with utf-8-sig to strip a UTF-8 BOM if present."""
        mocker.patch(
            "vs_mod_tools.core.loader.json5.load",
            return_value=self.expected_data,
        )

        load_vs_json(self.mock_path)

        self.mock_path.open.assert_called_once_with(encoding="utf-8-sig")

    def test_passes_file_handle_to_json5(self, mocker: MagicMock) -> None:
        """json5.load receives the file handle returned by Path.open."""
        mock_load = mocker.patch(
            "vs_mod_tools.core.loader.json5.load",
            return_value=self.expected_data,
        )

        load_vs_json(self.mock_path)

        mock_load.assert_called_once_with(self.mock_file)

    def test_parses_relaxed_vs_json_file(self, tmp_path: Path) -> None:
        """Unquoted keys, trailing commas, and // comments are accepted."""
        vs_file = tmp_path / "test.json"
        vs_file.write_text(
            "{\n"
            '    code: "armor",\n'
            "    variantgroups: [\n"
            '        { code: "part", states: ["head", "body",] },\n'
            "    ],\n"
            "    // inline comment\n"
            "    skipVariants: [],\n"
            "}\n",
            encoding="utf-8",
        )

        result = load_vs_json(vs_file)

        assert result["code"] == "armor"
        assert result["variantgroups"][0]["states"] == ["head", "body"]

    def test_parses_standard_quoted_key_json(self, tmp_path: Path) -> None:
        """Standard JSON (all keys quoted, no trailing commas) is also valid."""
        json_file = tmp_path / "standard.json"
        json_file.write_text(
            '{"code": "armor", "variantgroups": []}',
            encoding="utf-8",
        )

        result = load_vs_json(json_file)

        assert result["code"] == "armor"

    def test_strips_utf8_bom(self, tmp_path: Path) -> None:
        """A leading UTF-8 BOM (0xEF 0xBB 0xBF) does not cause a parse error."""
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(
            b"\xef\xbb\xbf"  # UTF-8 BOM
            + b'{"code": "armor", "variantgroups": []}'
        )

        result = load_vs_json(bom_file)

        assert result["code"] == "armor"

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_propagates_json_parse_error(self, mocker: MagicMock) -> None:
        """A malformed JSON file surfaces the underlying parse exception."""
        mocker.patch(
            "vs_mod_tools.core.loader.json5.load",
            side_effect=ValueError("unexpected token"),
        )

        with pytest.raises(ValueError, match="unexpected token"):
            load_vs_json(self.mock_path)

    def test_missing_file_raises_os_error(self, tmp_path: Path) -> None:
        """Attempting to open a non-existent file raises FileNotFoundError."""
        missing = tmp_path / "does_not_exist.json"

        with pytest.raises((FileNotFoundError, OSError)):
            load_vs_json(missing)

    def test_io_error_propagates(self, mocker: MagicMock) -> None:
        """An IOError from Path.open bubbles up unchanged."""
        self.mock_path.open.side_effect = IOError("disk read failed")

        with pytest.raises(IOError, match="disk read failed"):
            load_vs_json(self.mock_path)

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def test_benchmark_load_real_file(self, benchmark, tmp_path: Path) -> None:
        """Benchmark load_vs_json against a file with VS relaxed syntax."""
        vs_file = tmp_path / "bench.json"
        vs_file.write_text(
            "{\n"
            '    code: "bench",\n'
            "    variantgroups: [\n"
            '        { code: "part", states: ["head", "body", "legs"] },\n'
            '        { code: "mat",  states: ["leather", "iron", "steel"] },\n'
            "    ],\n"
            "    skipVariants: [],\n"
            "    allowedVariants: [],\n"
            "}\n",
            encoding="utf-8",
        )
        benchmark(load_vs_json, vs_file)
