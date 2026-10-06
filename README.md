# FUN60 Layer Tool

[日本語](README_ja.md) · [Protocol notes](docs/PROTOCOL.md) · [Changelog](CHANGELOG.md)

An unofficial Python CLI that assigns **Fn+G / H / J / K to onboard profiles 0 / 1 / 2 / 3** on selected MonsGeek FUN60 PRO keyboards.

The settings live on the keyboard; this tool does not need to run while typing. This switches complete device profiles, **not QMK layers**. The project does not install QMK or replace firmware, and is not affiliated with MonsGeek or Akko.

| Shortcut | Internal profile | If the driver labels profiles from 1 |
| --- | --- | --- |
| Fn+G | 0 | 1 |
| Fn+H | 1 | 2 |
| Fn+J | 2 | 3 |
| Fn+K | 3 | 4 |

The same assignments are installed in all four Windows Fn tables, so switching profiles does not remove access to these shortcuts.

## Compatibility and verification

| VID | PID | Internal device ID | Status |
| --- | --- | --- | --- |
| `3151` | `5029` | `2600` | v0.4 write, full Fn-table readback, actual shortcut switching and later matching readback confirmed by one user on Windows |
| `3151` | `502F` | `2305` | Included based on public protocol/device data; not hardware-tested here |

Both USB identifiers and the internal device ID must match. The product name alone is not sufficient. Other combinations are rejected.

- Python **3.10+**, `hidapi>=0.14,<0.16`.
- **USB wired mode** and the **Windows Fn table** only. No Bluetooth, dongle, Mac Fn table, ISO or Ultra support is claimed.
- The reported setup used Python 3.11 and hidapi 0.15.0 on Windows. Other Python versions are covered by a supplied CI configuration, not by claimed hardware validation.
- Persistence across a power cycle and behavior after opening/saving in the official driver have **not been explicitly confirmed** in the report.
- This is experimental configuration software. A successful readback is not proof of shortcut behavior or power-cycle persistence. Interrupted USB writes can prevent automatic recovery.

## Quick start — Windows PowerShell

Download/extract the repository or clone it, then open a terminal in the directory containing `fun60_layer_tool.py` and `requirements.txt`.

Connect the keyboard in wired mode. Close the official driver, its web tabs, and other keyboard configuration/RGB utilities. Do not press keys or disconnect USB during an apply operation.

```powershell
python -m pip install -r requirements.txt
python fun60_layer_tool.py --version
python fun60_layer_tool.py list
python fun60_layer_tool.py diagnose
python fun60_layer_tool.py backup backup.json
python fun60_layer_tool.py install-ghjk
```

The last command previews changes; it does not change settings. `diagnose` reads the internal ID. These read operations still send HID query requests to the keyboard.

If the preview is correct:

```powershell
python fun60_layer_tool.py install-ghjk --apply
```

This saves a fresh pre-write Fn backup, sends modified Fn tables in batches, and reads all four profiles back after each profile write. It takes tens of seconds. On a mismatch or error, it attempts to restore the pre-write tables and checks the result.

Successful output ends with:

```text
Profile 0: batch write verified (all four profiles checked).
Profile 1: batch write verified (all four profiles checked).
Profile 2: batch write verified (all four profiles checked).
Profile 3: batch write verified (all four profiles checked).
Write and full Fn-table readback verified. Test Fn+G/H/J/K and reconnect persistence.
```

Test each shortcut, reconnect USB, and test again. To check the stored assignments without writing:

```powershell
python fun60_layer_tool.py install-ghjk
```

`Already matches. No writes.` means the current Fn assignments match the requested values. Keep your **original `backup.json`**.

## Commands

| Command | Effect |
| --- | --- |
| `list` | Enumerate candidate USB configuration interfaces; no settings writes |
| `diagnose` | Read device identity; no settings writes |
| `backup FILE` | Save all four Windows Fn tables; refuses to overwrite an existing file |
| `install-ghjk` | Preview the four assignments in all profiles |
| `install-ghjk --apply` | Back up, write and verify |
| `restore FILE` | Preview restoring only Fn+G/H/J/K from a backup |
| `restore FILE --apply` | Restore those assignments, preserving other current entries |

Use `--serial SERIAL` with device commands except `list` if multiple supported devices have distinct serial numbers. If their serials are empty, connect only one. `--backup-dir DIRECTORY` changes the automatic backup/log destination for install and restore. Default: `backups/`.

## Restore

```powershell
python fun60_layer_tool.py restore backup.json
python fun60_layer_tool.py restore backup.json --apply
```

Manual restore takes **only Fn+G/H/J/K** from the specified backup, retaining other current Fn entries. It still transmits whole tables. Failure recovery restores the entire pre-operation Fn tables instead.

A backup contains Fn tables, **not** lighting, magnetic-switch parameters, macros or a full device image. Do not interpret `restore` as full-device recovery. If two units have no serial, the tool cannot distinguish them; use a backup from the same physical keyboard.

## Troubleshooting

| Message / symptom | Next step |
| --- | --- |
| `requirements.txt` missing | Change into the extracted directory containing that file; ZIP extraction may create an extra folder |
| `list` prints `[]` | Check wired mode/cable and close other device utilities; do not edit the allowlist blindly |
| Unsupported PID / device ID | Provide `list` and redacted `diagnose` output in an issue |
| `base mapping differs` | Profile 0 G/H/J/K must match the expected base mappings; custom remaps or another layout can fail this check |
| `Unexpected HID framing` / unstable reads | Close competing software, reconnect and retry read-only commands |
| Nonzero trailing bytes | Batch writes are refused because bytes outside the expected 126-key matrix are not understood |
| `Readback mismatch` / batch mismatch | Check the diagnostic log and rollback result; avoid repeated writes without investigating |
| `Rollback verified.` | All four Fn tables read back as they were before the attempt |
| `Rollback FAILED` | Stop installation attempts. Reconnect, retain backups/logs and investigate; manual restore only repairs the four target keys |

The official driver may overwrite the assignments when applying its own configuration. Concurrent access is not supported. If assignments disappear, close it and preview/reapply with this tool.

## Tests and contributing

```powershell
python -m unittest -v
```

14 offline tests cover packets, allowlists, backup validation, changed-entry limits, readback mismatch detection and rollback. They do not require hardware or `hidapi` to be installed. The included GitHub Actions workflow runs these tests on Windows and Linux; no hosted runner writes to hardware.

See [CONTRIBUTING.md](CONTRIBUTING.md). Diagnostics contain mappings, device metadata and potentially paths/serials. Redact them before posting; do not commit personal backups.

## References and license

Based on protocol research and device data in [echtzeit-solutions/monsgeek-akko-linux](https://github.com/echtzeit-solutions/monsgeek-akko-linux), and the earlier configuration approach documented by [Automata02/fun60-keymap](https://github.com/Automata02/fun60-keymap).

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for pinned source references. No upstream driver bundle, firmware or personal diagnostic capture is included.

This repository's original files are provided under the [GNU GPL v3.0](LICENSE). Referenced projects and dependencies retain their respective licenses.
