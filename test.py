"""
Manual test runner for alert logic.
DO NOT USE IN PRODUCTION.
"""

from logic import run_alerts

TEST_DRAWDOWNS = [-5, -10, -15, -20]

for dd in TEST_DRAWDOWNS:
    print(f"\n=== Testing drawdown {dd}% ===")

    run_alerts(
        test_mode=True,
        forced_drawdown=dd,
        force_confirm=True,        # bypass confirmation logic
        state_file="state_test.json",
    )
