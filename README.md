# vs-mod-tools

A Python toolkit for working with **Vintage Story** mod item definition files.

`vs-mod-tools` processes the relaxed JSON files used by Vintage Story mods, exposing utilities for variant generation, pattern validation, and interactive filtering — all from the command line or as an importable library.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [CLI Reference](#cli-reference)
    - [vs-show-variants](#vs-show-variants)
    - [Examples](#examples)
- [Package API](#package-api)
    - [core.loader](#coreloader)
    - [core.variants](#corevariants)
    - [core.validation](#corevalidation)
- [Development Setup](#development-setup)
- [Running the Tests](#running-the-tests)
- [Linting and Formatting](#linting-and-formatting)
- [Project Structure](#project-structure)

---

## Features

- **Relaxed JSON parsing** — Loads VS item files directly, including unquoted keys, trailing commas, inline comments (`//`), and block comments (`/* */`). Handles UTF-8 BOM transparently.
- **Variant generation** — Computes the effective variant list by applying `skipVariants` (subtractive) and `allowedVariants` (filtering) in the correct order.
- **Interactive filtering** — One CLI flag is generated per `variantgroup`. Flags can be repeated for OR logic within a group; multiple groups are ANDed.
- **Pattern validation** — Walks all known variant-pattern fields (type maps, `handbook.groupBy`, `baseByType`, etc.) and reports any pattern or template expansion that matches no active variant.
- **Importable library** — All core functions are available as a stable Python API.

---

## Requirements

- Python **3.11+**
- [`json5`](https://pypi.org/project/json5/) ≥ 0.9 (installed automatically)

---

## Installation

### From source (recommended during early development)

```bash
git clone https://github.com/DarkMatterProductions/vs-mod-tools.git
cd vs-mod-tools
pip install -e .
```

### From PyPI *(once published)*

```bash
pip install vs-mod-tools
```

---

## CLI Reference

### vs-show-variants

```
vs-show-variants -f <JSON_FILE> [--validate] [--<group> <state>] ...
```

| Flag | Description |
|------|-------------|
| `-f / --file JSON_FILE` | **(required)** Path to the VS item definition JSON. |
| `--validate` | Check every pattern field in the JSON against the processed variant list. Reports patterns that match nothing. |
| `--<group> <state>` | Filter variants by group state. One flag is generated per `variantgroup` in the file. May be repeated for OR logic; multiple groups are ANDed. |
| `-h / --help` | Show help. When combined with `-f`, the full dynamic flag list is shown. |

> **Tip:** Run `vs-show-variants -f <file> --help` to see the exact flags and valid choices for a specific item definition.

### Examples

```bash
# Show all effective variants
vs-show-variants -f armor.json

# Filter to leg and head variants only (OR within group)
vs-show-variants -f armor.json --bodypart legs --bodypart head

# Filter across groups — AND logic (head jerkin variants only)
vs-show-variants -f armor.json --bodypart head --construction jerkin

# Validate all pattern fields with no user filter
vs-show-variants -f armor.json --validate

# Validate with a filter active
vs-show-variants -f armor.json --bodypart legs --validate
```

#### Sample output

```
────────────────────────────────────────────────────────────────
  Variants  (4 total)
  Filters: --bodypart ['head', 'legs']
────────────────────────────────────────────────────────────────
  armor-head-leather
  armor-head-iron
  armor-legs-leather
  armor-legs-iron
────────────────────────────────────────────────────────────────
```

---

## Package API

All public functions are re-exported from `vs_mod_tools.core`.

```python
from vs_mod_tools.core import (
    load_vs_json,
    raw_cartesian,
    generate_variants,
    expand_vs_template,
    extract_patterns,
    find_invalid_patterns,
)
```

### core.loader

#### `load_vs_json(path: Path) -> dict`

Load a VS item definition JSON file. Supports the full VS relaxed JSON superset (unquoted keys, trailing commas, `//` and `/* */` comments) via `json5`. Strips a UTF-8 BOM if present.

```python
from pathlib import Path
from vs_mod_tools.core import load_vs_json

data = load_vs_json(Path("items/armor-head.json"))
```

---

### core.variants

#### `raw_cartesian(data: dict) -> list[str]`

Returns the full cartesian product of all `variantgroup` states with no filtering applied. Useful as a structural baseline or for diffing against the processed output.

```python
from vs_mod_tools.core import raw_cartesian

all_combos = raw_cartesian(data)
# ["armor-head-leather", "armor-head-iron", "armor-body-leather", ...]
```

#### `generate_variants(data: dict, user_filters: dict[str, list[str]]) -> list[str]`

Builds the effective variant list by:

1. Applying optional per-group `user_filters` (OR within a group, AND across groups).
2. Removing `skipVariants` matches (subtractive pass).
3. Retaining only `allowedVariants` matches (filtering pass).

```python
from vs_mod_tools.core import generate_variants

# No user filters — full processed list
variants = generate_variants(data, {})

# Filter to head variants in leather only
variants = generate_variants(data, {"bodypart": ["head"], "material": ["leather"]})
```

---

### core.validation

#### `expand_vs_template(pattern: str, data: dict) -> list[str]`

Expands a VS template pattern (one containing `{groupcode}` tokens) into every concrete `fnmatch` glob it represents. Unknown tokens are replaced with `*`. Returns `[pattern]` unchanged if no tokens are present.

```python
from vs_mod_tools.core import expand_vs_template

globs = expand_vs_template("armor-{bodypart}-*", data)
# ["armor-head-*", "armor-body-*", "armor-legs-*"]
```

#### `extract_patterns(data: dict) -> list[tuple[str, str]]`

Walks all known variant-pattern fields in an item definition and returns `(json_path, pattern)` pairs. Covers:

| Source | Field(s) |
|--------|----------|
| Top-level lists | `skipVariants`, `allowedVariants` |
| Top-level type maps | `shapeByType`, `texturesByType`, `durabilityByType`, `tpHandTransformByType`, `guiTransformByType`, `groundTransformByType` |
| `attributes` | `handbook.groupBy`, `clothesCategoryByType`, `attachableToEntity.{categoryCodeByType,disableElementsByType,keepElementsByType}`, `footStepSoundByType`, `protectionModifiersByType` |
| Recursive | `baseByType` (anywhere in the tree) |

```python
from vs_mod_tools.core import extract_patterns

patterns = extract_patterns(data)
# [("skipVariants", "armor-head-iron"), ("shapeByType", "armor-*"), ...]
```

#### `find_invalid_patterns(patterns, all_variants, data) -> list[tuple[str, str, str]]`

Validates each pattern against `all_variants`. Template patterns are expanded first via `expand_vs_template`; each expansion is checked independently. Returns `(json_path, original_pattern, expanded_pattern)` triples for every expansion that matches no variant.

```python
from vs_mod_tools.core import generate_variants, extract_patterns, find_invalid_patterns

all_variants = generate_variants(data, {})
patterns     = extract_patterns(data)
invalid      = find_invalid_patterns(patterns, all_variants, data)

for path, original, expanded in invalid:
    print(f"{path}: {original!r} → {expanded!r} matches nothing")
```

---

## Development Setup

### Prerequisites

- Python **3.11+**
- [pip](https://pip.pypa.io/) 24+ (for PEP 735 `--group` support) *or* [uv](https://github.com/astral-sh/uv)

### Clone and install

```bash
git clone https://github.com/DarkMatterProductions/vs-mod-tools.git
cd vs-mod-tools

# Install the package in editable mode
pip install -e .

# Install development dependencies (PEP 735)
pip install --group dev
```

### Verify your setup

```bash
# Run the full test suite
pytest tests/

# Check linting
flake8 src/
black --check src/
isort --check-only src/
mypy src/
```

---

## Running the Tests

The test suite uses **pytest** with `pytest-mock`, `pytest-cov`, and `pytest-benchmark`. All tests are in `tests/`, one file per source module.

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=vs_mod_tools --cov-report=term-missing

# Run a specific test file
pytest tests/test_variants.py -v

# Run a specific test class
pytest tests/test_variants.py::TestGenerateVariants -v

# Run benchmarks only
pytest tests/ -k benchmark --benchmark-only
```

### Test structure

| File | Classes | Tests |
|------|---------|-------|
| `tests/test_loader.py` | `TestLoadVsJson` | 10 |
| `tests/test_variants.py` | `TestRawCartesian`, `TestGenerateVariants` | 20 |
| `tests/test_validation.py` | `TestExpandVsTemplate`, `TestExtractPatterns`, `TestFindInvalidPatterns` | 41 |
| `tests/test_show_variants.py` | `TestAddStaticArgs`, `TestBuildParser`, `TestMain` | 33 |
| **Total** | | **104** |

Each class uses `setup_method()` for per-test data initialisation. External I/O is mocked via `pytest-mock`. Every class contains positive tests, negative/edge-case tests, and one benchmark.

### Coverage target

The project targets **≥ 100% line and branch coverage**. Check locally before submitting:

```bash
pytest tests/ --cov=vs_mod_tools --cov-report=term-missing
```

---

## Linting and Formatting

All tools are configured in `pyproject.toml`. CI enforces zero errors on all four checks before merging.

| Tool | Purpose | Run |
|------|---------|-----|
| `black` | Opinionated formatter (line length 88) | `black src/` |
| `isort` | Import ordering (`profile = "black"`) | `isort src/` |
| `flake8` | Style and error checking | `flake8 src/` |
| `mypy` | Static type checking (strict mode) | `mypy src/` |

```bash
# Check only (non-destructive)
black --check src/ && isort --check-only src/ && flake8 src/ && mypy src/

# Auto-fix formatting
black src/
isort src/
```

---

## Project Structure

```
vs-mod-tools/
├── pyproject.toml                  ← build, metadata, and all tool configuration
├── README.md
├── CONTRIBUTING.md
│
├── src/
│   └── vs_mod_tools/
│       ├── __init__.py             ← package version
│       ├── core/
│       │   ├── __init__.py         ← re-exports all public core functions
│       │   ├── loader.py           ← load_vs_json()
│       │   ├── variants.py         ← raw_cartesian(), generate_variants()
│       │   └── validation.py       ← expand_vs_template(), extract_patterns(),
│       │                               find_invalid_patterns()
│       └── cli/
│           ├── __init__.py
│           └── show_variants.py    ← main() → vs-show-variants entrypoint
│
└── tests/
    ├── conftest.py                 ← shared fixtures
    ├── test_loader.py
    ├── test_variants.py
    ├── test_validation.py
    └── test_show_variants.py
```

---

## Vintage Story JSON format

VS item definitions use a relaxed JSON superset. Key differences from standard JSON:

```jsonc
{
    // Single-line comments are allowed
    /* Block comments too */
    code: "armor-head",           // Unquoted keys are valid
    variantgroups: [
        { code: "material", states: ["leather", "iron",] },  // Trailing commas OK
    ],
    skipVariants: ["armor-head-iron"],
    allowedVariants: ["armor-*-leather"],
}
```

`vs-mod-tools` uses the [`json5`](https://pypi.org/project/json5/) library to parse these files, and opens them with `utf-8-sig` encoding to transparently strip any UTF-8 BOM written by Windows editors.
