# Changelog

## 0.4 — 2026-09-29

- Use full Fn-table batch transfer plus a final commit packet instead of individual key writes.
- Preserve all existing entries other than the four requested assignments.
- Verify all four profiles after each profile write; restore pre-operation tables on failure.
- Refuse unknown nonzero trailing bytes outside the 126-key matrix.
- Hardware report on PID 5029 / ID 2600: all four profile tables verified, shortcut switching confirmed, later readback matched.
- Power-cycle persistence and official-driver interactions remain unconfirmed.

## 0.3 — 2026-09-29

- Add diagnostic JSONL logs with expected/actual tables and packets.
- Increase individual-write delay.
- Hardware observation: writing Fn+H caused the preceding Fn+G assignment to read back as zero; rollback verified. Do not use this individual-write path for installation.

## 0.2 — 2026-09-29

- Add PID 5029 / ID 2600 identity pair and read-only diagnosis.
- Keep PID and internal-ID pairing checks on writes and backup restore.

## 0.1 — 2026-09-29

- Initial experimental tool with preview, backup, write and restore commands.
- Initial allowlist: PID 502F / ID 2305.

## Publication preparation — 2026-10-01 (Japan)

- Add English/Japanese READMEs, protocol/source notes, contribution guidance, issue template, CI configuration, GNU GPL v3.0 license and publishing instructions.
- Preserve v0.4 Python source, dependency requirements and its 14 tests unchanged.
