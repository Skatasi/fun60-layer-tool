# Contributing

Run `python -m unittest -v` from the repository root. Tests are offline and must not open HID devices. Runtime uses `hidapi`; tests use only Python's standard library.

For a bug report, include the tool version, OS, Python/hidapi versions, VID/PID/internal ID, connection mode, exact command, expected/actual behavior and rollback result. Use the issue template. Redact serial numbers and local paths; share only the relevant diagnostic excerpts initially. Do not attach your entire Fn backup by default.

For a new device, provide read-only identity output and published matrix/protocol evidence first. Do not broaden the allowlist based only on a marketing name, or ask users to disable identity/readback checks. State which behavior has been verified on real hardware and which is inferred.

Changes to write packets must have packet-level tests, preservation tests, failure/rollback tests and an explanation of the protocol evidence. Do not turn CI into a hardware-write test. Individual-key write helpers remain in the source for historical offline tests; the v0.4 CLI uses `apply_table_changes` and must keep the batch path.

Documentation fixes are welcome. Preserve the distinction between a preview, a successful readback, actual shortcut switching and power-cycle persistence. Keep hardware observations separate from mock test results.

This project uses the GNU GPL v3.0 license; submit only material you can contribute under its terms. Referenced driver bundles and firmware should not be copied into this repository.
