# Archived Ledger Migration Tooling

The legacy `migrate_ledger_to_state_machine.py` script was retained here for
historical reference after the ingestion ledger completed its transition to the
strict `LedgerState` enum during the May 2024 rollout. Production ledgers were
compacted and verified at that time, so the script is no longer part of the
supported tooling surface.

If you need to review the one-off migration logic, inspect
`scripts/archive/migrate_ledger_to_state_machine.py`. New migrations should rely
on enum-native ledger entries and do **not** require this script.
