"""VS JSON file loader supporting relaxed JSON5 syntax."""

from pathlib import Path
from typing import Any, Dict, List, Union

try:
    import json5
except ImportError:
    raise SystemExit(
        "error: the 'json5' library is required to parse VS JSON files.\n" "       Install it with:  pip install json5"
    )


def load_vs_json(path: Path) -> Dict[str, Any]:
    """
    Load a Vintage Story JSON file.

    VS JSON is a relaxed superset of standard JSON that allows: unquoted object keys (e.g. `code: "armor"`), trailing commas in objects and arrays, single-line comments (`// ...`), and multi-line comments (`/* ... */`). Files may also carry a UTF-8 BOM (common from Windows editors), which is stripped transparently via the `utf-8-sig` encoding.

    :param path: (Path) Path to the `.json` file to load.

    :return: (dict) The parsed item definition.
    """
    payload = {}
    with path.open(encoding="utf-8-sig") as fh:
        payload = json5.load(fh)
    return payload  # type: ignore[no-any-return]
