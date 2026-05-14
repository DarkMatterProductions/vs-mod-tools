# Contributing to vs-mod-tools

Thank you for your interest in contributing to **vs-mod-tools**! This document outlines the standards and processes that all contributors are expected to follow. Taking the time to read it before submitting changes will make the review process faster and smoother for everyone.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Branching Strategy](#branching-strategy)
- [Making Changes](#making-changes)
- [Commit Message Standards](#commit-message-standards)
- [Unit Testing Requirements](#unit-testing-requirements)
- [Linting and Code Style](#linting-and-code-style)
- [Architecture Decision Records (ADRs)](#architecture-decision-records-adrs)
- [Pull Request Guidelines](#pull-request-guidelines)
- [PR Template](#pr-template)
- [Review Process](#review-process)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

All contributors are expected to behave professionally and respectfully. Harassment, discrimination, or abusive behavior of any kind will not be tolerated. By participating in this project you agree to uphold these expectations in all interactions — issues, pull requests, code reviews, and discussions alike.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/vs-mod-tools.git
   cd vs-mod-tools
   ```
3. **Add the upstream remote** so you can stay in sync:
   ```bash
   git remote add upstream https://github.com/DarkMatterProductions/vs-mod-tools.git
   ```

---

## Development Environment Setup

### Prerequisites

- **Python 3.11+**
- [pip](https://pip.pypa.io/) 24+ (for PEP 735 `--group` support) *or* [uv](https://github.com/astral-sh/uv)

### Install with Development Dependencies

```bash
pip install -e .
pip install --group dev
```

### Verify Your Setup

```bash
# Run the test suite
pytest tests/

# Check linting
flake8 src/
black --check src/
isort --check-only src/
mypy src/
```

---

## Branching Strategy

- **`main`** — stable, releasable code only. Direct pushes are not permitted.
- **Feature branches** — branch off `main` using a descriptive name:
    - `feature/<short-description>` — new functionality
    - `fix/<short-description>` — bug fixes
    - `docs/<short-description>` — documentation-only changes
    - `adr/<ADR-XXXXX-topic>` — ADR additions or updates
    - `chore/<short-description>` — maintenance tasks (dependency updates, CI, etc.)

Always keep your branch up to date with `main` before opening a PR:

```bash
git fetch upstream
git rebase upstream/main
```

---

## Making Changes

Before writing any code, consider whether your change:

- Affects more than one component or module
- Introduces a new integration or dependency
- Reverses or contradicts an existing architectural decision
- Has non-obvious trade-offs or could be misunderstood later

If any of these apply, an ADR may be required. See [Architecture Decision Records (ADRs)](#architecture-decision-records-adrs).

---

## Commit Message Standards

Every commit must include a **clear, detailed message** that explains both *what* changed and *why*. Vague messages like `"fix bug"` or `"update code"` will not be accepted.

### Format

```
<type>(<scope>)[!|*]: <short summary — imperative mood, max 72 chars>

<body — itemized list explaining the motivation, context, and any relevant detail>

<footer — optional: issue references, ADR references, breaking change notices>
```

### Best Practices

#### Subject Line (First Line)
- Use the **`<type>(<scope>)[!|*]:`** prefix from the types table below, with optional override flags `!` and `*`
- Override flags indicate:
    - `!` — this commit should be treated as a breaking change regardless of type
    - `*` — this commit should be treated as a minor version bump, even if the type would normally trigger a major or patch bump
- Write in **imperative mood** — *"add feature"* not *"added feature"*
- Keep it **≤ 72 characters**
- Be specific — avoid vague summaries like `"fix bug"` or `"update code"`

#### Body
- Separate from the subject line with a **blank line**
- Use an **itemized list** to explain:
    - **What** changed
    - **Why** it changed (motivation)
    - Any relevant **context or trade-offs**
- Do not simply restate the subject — explain the *reasoning*

#### Footer
- Reference closed issues: `Closes #42`
- Reference relevant ADRs: `ADR-00001`
- Note breaking changes if applicable

### Types

| Type        | When to use                                         |
|-------------|-----------------------------------------------------|
| `breaking`  | A backwards incompatible change to the API or CLI   |
| `rewrite`   | Complete rewrites / architectural overhauls         |
| `milestone` | Significant feature milestones / stable releases    |
| `deprecate` | Major deprecation cleanups                          |
| `eos`       | End of support for a runtime/platform               |
| `license`   | License changes                                     |
| `security`  | Security-mandated incompatible changes              |
| `feat`      | A new feature or capability                         |
| `fix`       | A bug fix                                           |
| `test`      | Adding or updating tests                            |
| `docs`      | Documentation changes only                          |
| `refactor`  | Code restructuring with no behaviour change         |
| `chore`     | Build system, tooling, or dependency changes        |
| `adr`       | Adding or updating an Architecture Decision Record  |

### No-Release Scopes

Certain scopes suppress version bumping **regardless of the commit type**. Even a `fix` or `feature` commit will not trigger a release if its scope is one of the following:

| Scope     | When to use                                                         |
|-----------|---------------------------------------------------------------------|
| `ci`      | Changes to CI/CD pipeline configuration or workflow files           |
| `tools`   | Changes to scripts or utilities under `.github/tools/`              |

These scopes are enforced by `build_and_publish.py` via the `NO_RELEASE_SCOPES` constant. When a commit matches a no-release scope, `determine_bump()` sets `has_none = True` and skips all further bump checks for that commit — meaning even a `fix(ci):` or `feature(tools):` commit will produce `bump=none` in `GITHUB_OUTPUT` and skip the PyPI publish step.

If a new no-release scope is needed, add it to the `NO_RELEASE_SCOPES` set in `build_and_publish.py` **and** document it in this table.

**Example:**
```
fix(ci): correct PyPI publish condition in build-and-publish.yml

- The publish step was not correctly gating on the bump output variable
- Updated the if-condition to reference the correct step id
```

### Examples

```
feat(variants): add raw_cartesian as a public API function

- raw_cartesian was previously an internal helper used only by
  generate_variants; it is useful on its own as a structural baseline
  for diffing and diagnostics
- Renamed from _raw_cartesian and added to core/__init__.py exports
- Added corresponding unit tests in TestRawCartesian

Closes #12
```

```
fix(validation): handle empty variantgroups in expand_vs_template

- When a data dict contained no variantgroups, product() of an empty
  sequence yielded one empty tuple, producing a trailing hyphen in the
  result (e.g. "item-" instead of "item")
- Added an early return guard for the empty-groups case
- No behaviour change for non-empty variantgroups

Closes #19
```

---

## Unit Testing Requirements

All code changes **must** be accompanied by unit tests. Pull requests that modify logic without corresponding test coverage will not be merged.

### Standards

- Tests live in `tests/` and follow the naming convention `test_<module_name>.py`.
- Each test file maps to one source module (e.g. `tests/test_variants.py` covers `core/variants.py`).
- Tests are organised into **pytest classes** (`class TestFunctionName`), using `setup_method()` to initialise per-test data.
- **All file I/O and external calls** must be mocked using `pytest-mock`. Unit tests must never touch the real filesystem beyond `tmp_path` fixtures.
- **New functions or CLI behaviours** require tests covering:
    - The happy path
    - Relevant error/edge cases (empty input, missing files, invalid arguments, etc.)

### Coverage Requirement

The project targets **≥ 100% line and branch coverage**. Ensure your changes do not reduce coverage below this threshold. Check coverage locally before submitting:

```bash
pytest --cov=vs_mod_tools --cov-report=term-missing tests/
```

### Running the Full Test Suite

```bash
# All tests
pytest tests/

# With coverage report
pytest tests/ --cov=vs_mod_tools --cov-report=term-missing

# A specific test file
pytest tests/test_validation.py -v

# A specific test class
pytest tests/test_show_variants.py::TestMain -v

# Benchmarks only
pytest tests/ -k benchmark --benchmark-only
```

---

## Linting and Code Style

All code must conform to the linting and formatting rules configured in `pyproject.toml`. CI will enforce these checks — fix all issues locally before pushing.

### Tools in Use

| Tool     | Purpose                    | Configuration                       |
|----------|----------------------------|-------------------------------------|
| `flake8` | Style and error checking   | `[tool.flake8]` in `pyproject.toml` |
| `black`  | Opinionated code formatter | `[tool.black]` in `pyproject.toml`  |
| `isort`  | Import ordering            | `[tool.isort]` in `pyproject.toml`  |
| `mypy`   | Static type checking       | `[tool.mypy]` in `pyproject.toml`   |

### Key Rules

- **Line length:** `black` and `flake8` are both configured to `88` characters.
- **Import ordering:** `isort` is configured with `profile = "black"`. Run `isort src/` before committing.
- **Type annotations:** All new public functions and methods must include type annotations. `mypy` is run in strict mode with `ignore_missing_imports = true` (to accommodate `json5`, which ships no stubs).
- **Docstrings:** Public modules, classes, and functions must have docstrings.

### Running the Linters

```bash
# Check formatting (non-destructive)
black --check src/
isort --check-only src/
flake8 src/
mypy src/

# Auto-fix formatting
black src/
isort src/
```

All four checks must pass with zero errors before a PR will be reviewed.

---

## Architecture Decision Records (ADRs)

This project uses **Architecture Decision Records** to document significant design decisions. All contributors must understand and honor the ADRs stored in `.context/decisions/`.

### When an ADR Is Required

Create a new ADR before — not after — implementing any change that:

- Affects more than one component or module
- Introduces or replaces a dependency
- Changes a behaviour that was the subject of a previous ADR
- Has non-obvious trade-offs or could be costly to reverse
- Reflects a constraint, policy, or design principle

If you are uncertain whether your change warrants an ADR, open an issue and ask. When in doubt, write the ADR.

### Honoring Existing ADRs

Before writing code, review the relevant ADRs in `.context/decisions/`. Contributions must not:

- Contradict or circumvent an `Accepted` or `Implemented` ADR without first superseding it through the formal ADR process.
- Re-litigate a settled decision in a PR without opening a new ADR.

If you believe an existing decision should be revisited, create a new `Proposed` ADR referencing the original and initiate the review process.

### ADR File Conventions

- **Location:** `.context/decisions/`
- **Naming:** `ADR-XXXXX-<kebab-case-topic>.md` (zero-padded 5-digit number)
- **Never delete** an ADR file, even if it is deprecated or superseded.

### Commit Convention for ADRs

```
adr(ADR-XXXXX): accept decision on <topic>
```

---

## Pull Request Guidelines

### Before Opening a PR

Ensure the following are true:

- [ ] All tests pass locally: `pytest tests/`
- [ ] Coverage has not dropped below 100%: `pytest --cov=vs_mod_tools --cov-report=term-missing tests/`
- [ ] All linters pass with zero errors: `black --check src/ && isort --check-only src/ && flake8 src/ && mypy src/`
- [ ] Any new or changed public APIs have type annotations and docstrings
- [ ] Any architectural change is covered by a new or updated ADR
- [ ] Your branch is up to date with `main`

### PR Title

Write the title in **imperative mood** as a plain summary of the change — ≤ 72 characters. Do **not** use a `<type>(<scope>):` prefix in the title. Type and scope information belongs in the **Change Types** table in the PR description (see below), because a single PR may span multiple commit types and a single-type prefix would lose that signal.

**Good:** `Add pattern validation with VS template expansion`  
**Bad:** `feat(validation): add pattern validation with VS template expansion`

### PR Description

Every PR **must** include a thorough description using the template at `.github/PULL_REQUEST_TEMPLATE.md`. The following sections are required:

#### Change Types
A table mapping each `type` and `scope` present in the PR's commits to a short description of what that group of changes covers. This replaces the single-type prefix that would appear in a commit subject line.

```markdown
## Change Types

| Type | Scope |
|------|-------|
| `feat` | `validation` |
| `test` | `validation` |
| `docs` | `readme` |
```

Every distinct `type(scope)` combination in the PR's commits must appear as a row. Use the type values defined in the [Commit Message Standards](#commit-message-standards) types table.

#### Summary
A clear explanation of what this PR does and why. Do not simply restate the title. Explain the motivation and the problem being solved.

#### Changes Made
A concise bullet-point list of the significant changes introduced. Include files or modules affected where helpful.

#### Testing
Describe what was tested and how. Include:
- Which test files were added or modified
- Any edge cases or error conditions covered
- How to reproduce the behaviour manually if relevant

#### ADRs Referenced
List any ADRs that informed, constrain, or are affected by this change. If a new ADR was created, link to it here.

#### Checklist
Include the pre-PR checklist above in your description and check off each item.

### PR Template

A GitHub PR template is provided at `.github/PULL_REQUEST_TEMPLATE.md`. It pre-populates the required sections when you open a new PR. Fill in every section — do not delete any headings.

---

## Review Process

1. **Automated checks** (linting, tests, coverage) run on every PR via CI. All checks must pass before a human review is requested.
2. **A maintainer** will review the code for correctness, test coverage, adherence to linting rules, and compliance with ADRs.
3. **Feedback** will be given via inline comments or a review summary. Address all comments before re-requesting review.
4. **Approval and merge** — once approved, a maintainer will merge the PR using squash-merge to keep the `main` history clean.

---

## Reporting Issues

If you have found a bug or have a feature request:

1. **Search existing issues** first — it may already be reported.
2. **Open a new issue** using the appropriate template (bug report or feature request).
3. Include as much context as possible: Python version, OS, the item definition JSON (or a minimal reproduction), steps to reproduce, and expected vs. actual behaviour.

For security vulnerabilities, **do not open a public issue**. Contact the maintainers directly at [pypi@darkmatter-productions.com](mailto:pypi@darkmatter-productions.com).

---

## Questions?

If you have questions about the contribution process or the project architecture, open a [GitHub Discussion](https://github.com/DarkMatterProductions/vs-mod-tools/discussions) or reach out via the Issues tracker.

---

<div align="center">

**Thank you for contributing to vs-mod-tools.**

</div>
