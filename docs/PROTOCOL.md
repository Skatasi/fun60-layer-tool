# Protocol and implementation notes

These notes describe **v0.4's implemented path**, not a universal specification for every MonsGeek device. See [pinned references](../ACKNOWLEDGEMENTS.md).

## Identity and transport

The tool enumerates VID `0x3151`, candidate PIDs `0x5029` / `0x502F`, Usage Page `0xFFFF`, Usage `2`. `GET_USB_VERSION` (`0x8F`) returns an echoed command followed by a four-byte little-endian internal device ID. Only PID/ID pairs `5029/2600` and `502F/2305` pass strict checks.

Feature reports use report ID zero plus 64 bytes of vendor data: 65 bytes through this tool's hidapi calls. Responses with another length or prefix are rejected, rather than heuristically shifted. A checksum in vendor byte 7 is `255 - (sum(bytes[0:7]) & 255)`; the leading report ID is excluded.

## Positions and values

HID usages are not physical matrix indices.

| Key | HID usage | Physical index | Requested config `[type,b1,b2,b3]` |
| --- | --- | --- | --- |
| G | 10 | 33 | `08 00 04 00` |
| H | 11 | 39 | `08 00 04 01` |
| J | 13 | 45 | `08 00 04 02` |
| K | 14 | 51 | `08 00 04 03` |

These configs correspond to the vendor names `profile_exchange`, `profile_exchange2`, `profile_exchange3`, `profile_exchange4`. They select profiles; they are not QMK `TO()` codes.

## Read

GET_FN vendor bytes begin `[0x90, 0, profile, 0xFF, page, 0, 0, checksum]`, where OS selector 0 is Windows and page is 0–7. Each page contributes 64 raw payload bytes, producing a 512-byte table.

Raw pages have no command echo. The tool reads pages once in ascending order and again in descending order, reconstructing both tables in ascending order. They must match. This detects some stale/unstable responses but cannot prove that a consistently wrong response is correct.

Before installation, profile 0's base matrix is queried with GET_KEYMATRIX (`0x8A`). G/H/J/K must match the expected single-key base configs. This intentionally rejects some customized layouts instead of guessing their mapping.

## Batch write

For each affected profile, construct a complete desired Fn table from the pre-write snapshot. Replace only G/H/J/K. Refuse a nonzero value in bytes 504–511, which are outside the expected 126-entry matrix.

The vendor payload layout for SET_FN (`0x10`) is:

| Vendor byte | Value |
| --- | --- |
| 0 | `0x10` |
| 1 | OS selector `0` |
| 2 | Profile `0..3` |
| 3 | `0xFF` for table transfer |
| 4 | Chunk index `0..9` |
| 5 | Payload length: 56 for chunks 0–8, 0 for chunk 9 |
| 6 | Final flag: 0 for chunks 0–8, 1 for chunk 9 |
| 7 | Header checksum |
| 8–63 | Payload, zero padded |

Nine data packets carry 504 bytes. The tenth packet commits the transfer with zero payload length. The tool inserts 100 ms between packets and waits another second after the sequence. No GET command is interleaved with the batch.

After each profile transfer, all four profiles are read twice and compared with the evolving expected state. Cross-profile changes also count as failure. On failure, attempted profiles are restored from the snapshot; remaining mismatches are also restored, then all four profiles are checked again. Recovery is best effort, not an atomic transaction, and depends on a working USB connection.

Manual `restore` differs: it copies only four target assignments from an older backup into each current table. It does not restore the entire historical device state.

## Why individual-key writes are no longer used by the CLI

In v0.3's device report, Fn+G initially read back correctly. After writing Fn+H, H matched but G became zero. Increasing the delay did not change that observation. The exact internal firmware cause has not been established.

v0.4 follows the vendor driver's table transfer/commit sequence. The user confirmed all four profile table verifications and actual shortcut switching. Do not describe the earlier observation as a proven universal firmware defect.

The source retains earlier individual-key helpers and offline regression tests for historical coverage; the install/restore CLI calls `apply_table_changes`, not `apply_changes`.

## Backup and logs

Schema `fun60-fn-backup-v1` contains identity, OS selector, timestamp, four hex-encoded 512-byte tables and a SHA-256 digest of their concatenated bytes. The digest detects accidental corruption; it is not an authenticity signature and does not cover the metadata.

Device IDs and available serials are checked for restore. Units with empty serials cannot be uniquely distinguished. JSONL diagnostic logs record commands, expected/actual tables, differences and rollback results; they are local artifacts, not automatic telemetry.

## Verification boundaries

- Offline tests check software behavior with mock tables, not firmware behavior.
- Full readback validates stored tables at that moment.
- Reported keypress tests validate shortcut switching on the reported unit.
- Power-cycle persistence and official-driver coexistence require separate testing and remain unconfirmed in the supplied report.
