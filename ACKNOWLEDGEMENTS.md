# Acknowledgements and source references

The Python tool was developed against public protocol documentation, driver implementations and device databases. It is distributed under GNU GPL v3.0. The referenced Linux driver declares GPL-3.0; see its license below. External dependencies retain their own licenses.

## Protocol research and device data

[echtzeit-solutions/monsgeek-akko-linux](https://github.com/echtzeit-solutions/monsgeek-akko-linux), snapshot commit:

`79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b`

Relevant sources at that revision:

- [Driver license](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/iot_driver_linux/LICENSE)
- [Protocol overview](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/docs/PROTOCOL.md)
- [Driver protocol bundle](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/protocol/hid_protocol_core.js): `profile_exchange*`, `CommonKBRY5088._getFnKeyMatrix`, `_setFnKeyConfig` and individual-key write methods.
- [Rust command structures](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/iot_driver_linux/monsgeek-transport/src/command.rs): GET_FN and SET_FN fields.
- [Rust keyboard implementation](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/iot_driver_linux/monsgeek-keyboard/src/lib.rs): Fn table reads and per-key configuration.
- [Device metadata](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/data/devices.json)
- [Physical matrices](https://github.com/echtzeit-solutions/monsgeek-akko-linux/blob/79c45f11dcc0fdd24d6075a0f30f5dabbc748c9b/data/device_matrices.json): records `12625:20521:2600` and `12625:20527:2305`.

The driver bundle, firmware images and complete upstream databases are not redistributed in this repository. Implementation references are not claims that every supported variant has been tested by this project.

## Earlier FUN60 configuration approach

[Automata02/fun60-keymap](https://github.com/Automata02/fun60-keymap) documents modifying the vendor driver's configuration response and demonstrates the `profile_exchange*` configuration names. This CLI instead communicates through USB HID. No file from that repository is included.

## Runtime dependency

[hidapi Python package](https://pypi.org/project/hidapi/) provides the `hid` import and HID access. It is installed separately using `requirements.txt`; this repository does not vendor it.

## Hardware feedback

An end user supplied Windows readback and shortcut-switching results for VID 3151 / PID 5029 / internal ID 2600. Those reports informed the switch from individual-key writes to batch transfer. Personal backups, serials, local paths and raw diagnostic logs are omitted from the public package.
