"""
Entry point for running all market opportunity alerts.
"""

from __future__ import annotations

from logic import run_alerts


def main() -> None:
    run_alerts()


if __name__ == "__main__":
    main()

