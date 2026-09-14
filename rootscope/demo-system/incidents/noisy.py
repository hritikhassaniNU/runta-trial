"""Generate the noisy-log incident: thousands of heartbeats, one real error."""

from pathlib import Path
from typing import List

NOISE_LINE = "INFO heartbeat service=orders sku=ABC available=10"
ERROR_LINE = "ERROR order confirmation failed sku=ABC KeyError: 'available'"
DEFAULT_LINE_COUNT = 4000
DEFAULT_ERROR_INDEX = 1847


def generate_log(
    path: Path,
    line_count: int = DEFAULT_LINE_COUNT,
    error_index: int = DEFAULT_ERROR_INDEX,
) -> Path:
    if not 0 <= error_index < line_count:
        raise ValueError("error_index must fall inside the log")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(line_count):
        if i == error_index:
            lines.append(ERROR_LINE)
        else:
            lines.append(f"{NOISE_LINE} seq={i}")
    path.write_text("\n".join(lines) + "\n")
    return path


def error_lines(path: Path) -> List[str]:
    return [line for line in path.read_text().splitlines() if line.startswith("ERROR ")]
