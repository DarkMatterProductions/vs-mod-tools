"""VS JSON file loader supporting relaxed JSON5 syntax."""

from pathlib import Path

try:
    import json5
except ImportError:
    raise SystemExit(
        "error: the 'json5' library is required to parse VS JSON files.\n"
        "       Install it with:  pip install json5"
    )


def load_vs_json(path: Path) -> dict:  # type: ignore[type-arg]
    """
    Load a Vintage Story JSON file.

    VS JSON is a relaxed superset of standard JSON that allows:
      - Unquoted object keys  (e.g. ``code: "armor"``)
      - Trailing commas in objects and arrays
      - Single-line comments  (``// ...``)
      - Multi-line comments   (``/* ... */``)

    Files may also carry a UTF-8 BOM (common from Windows editors), which is
    stripped transparently via the ``utf-8-sig`` encoding.

    Parameters
    ----------
    path:
        Path to the ``.json`` file to load.

    Returns
    -------
    dict
        The parsed item definition.
    """
    with path.open(encoding="utf-8-sig") as fh:
        return json5.load(fh)  # type: ignore[no-any-return]
