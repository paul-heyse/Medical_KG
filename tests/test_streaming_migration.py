from __future__ import annotations

from scripts.check_streaming_migration import main as check_streaming_migration


def test_streaming_migration_script_runs() -> None:
    assert check_streaming_migration() == 0
