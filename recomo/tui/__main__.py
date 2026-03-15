"""Run the ReCoMo TUI: python -m recomo.tui [path/to/trace.json]"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from recomo.tui.app import run_tui


def main() -> None:
    load_dotenv()
    trace_path = sys.argv[1] if len(sys.argv) > 1 else None
    if trace_path:
        trace_path = Path(trace_path)
    run_tui(trace_path=trace_path)


if __name__ == "__main__":
    main()
