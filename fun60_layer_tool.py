#!/usr/bin/env python3
"""Experimental FUN60 PRO tool v0.4 (502f/2305, 5029/2600), Windows Fn."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import time

VID, PID, DEVICE_ID = 0x3151, 0x502F, 2305
SUPPORTED = {(0x502F, 2305), (0x5029, 2600)}
VERSION = '0.4'
POSITIONS = dict(zip('GHJK', (33, 39, 45, 51)))
SCHEMA = 'fun60-fn-backup-v1'


def packet(cmd, args=(), config=None):
    if cmd not in (0x8F, 0x90, 0x8A, 0x10):
        raise ValueError('Command not allowed')
    b = bytearray(64)
    b[0] = cmd
    if len(args) > 6:
        raise ValueError('Too many arguments')
    b[1:1+len(args)] = bytes(args)
    b[7] = 255 - (sum(b[:7]) & 255)
    if config is not None:
        if cmd != 0x10 or len(config) != 4:
            raise ValueError('Invalid config')
        b[8:12] = bytes(config)
    return bytes([0]) + b


def fn_table_packets(profile, table):
    # Mirrors CommonKBRY5088._setFnKeyConfig: 9 data packets + final commit.
    if profile not in range(4) or len(table) != 512:
        raise ValueError('Invalid profile/table size')
    if any(table[504:]):
        raise ValueError('Nonzero trailing bytes beyond the 126-key matrix; refusing batch write')
    out = []
    for page in range(10):
        size, final = (56, 0) if page < 9 else (0, 1)
        b = bytearray(packet(0x10, (0, profile, 255, page, size, final)))
        payload = table[page*56:page*56+size]
        b[9:9+len(payload)] = payload
        out.append(bytes(b))
    return out


def digest(tables):
    return hashlib.sha256(b''.join(bytes.fromhex(tables[str(p)]) for p in range(4))).hexdigest()


def validate_backup(obj):
    if obj.get('schema') != SCHEMA or obj.get('os') != 'windows':
        raise ValueError('Unsupported backup format/OS')
    ident = obj.get('device', {})
    if ident.get('vid') != VID or (ident.get('pid'), ident.get('id')) not in SUPPORTED:
        raise ValueError('Backup is for another model')
    tables = obj.get('tables', {})
    if set(tables) != {'0','1','2','3'}:
        raise ValueError('Backup must contain all four profiles')
    if any(len(bytes.fromhex(v)) != 512 for v in tables.values()):
        raise ValueError('Invalid table length')
    if obj.get('sha256') != digest(tables):
        raise ValueError('Backup checksum mismatch')
    return {int(p): bytes.fromhex(v) for p,v in tables.items()}


def save_new(path, obj):
    # Exclusive creation: never destroy an earlier backup.
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')
        f.flush()
        import os
        os.fsync(f.fileno())


class Keyboard:
    def __init__(self, dev, info):
        self.dev, self.info = dev, info

    def send(self, cmd, args=(), config=None):
        data = packet(cmd, args, config)
        n = self.dev.send_feature_report(data)
        if n != len(data):
            raise RuntimeError(f'Short HID write: {n}/{len(data)}')
        time.sleep(0.50 if cmd == 0x10 else 0.10)

    def query(self, cmd, args=(), raw=False):
        self.send(cmd, args)
        r = bytes(self.dev.get_feature_report(0, 65))
        # Do not guess report-ID placement: this backend requires 65 bytes.
        if len(r) != 65 or r[0] != 0:
            raise RuntimeError(f'Unexpected HID framing ({len(r)} bytes). No write performed by query.')
        r = r[1:]
        if not raw and r[0] != cmd:
            raise RuntimeError('Unexpected command echo; close other keyboard apps')
        return r

    def identify(self, strict=True):
        r = self.query(0x8F)
        device_id = int.from_bytes(r[1:5], 'little')
        pid = self.info['product_id']
        supported = (pid, device_id) in SUPPORTED
        if strict and not supported:
            raise RuntimeError(f'Unsupported PID {pid:#06x} / device ID {device_id}. Stopping.')
        return {'vid': VID, 'pid': pid, 'id': device_id, 'supported': supported,
                'serial': self.info.get('serial_number') or '',
                'product': self.info.get('product_string') or '', 'version_response': r.hex()}

    def table(self, profile, base=False, reverse=False):
        if profile not in range(4):
            raise ValueError('Invalid profile')
        pages = {}
        for page in (reversed(range(8)) if reverse else range(8)):
            args = (profile, 255, page, 0) if base else (0, profile, 255, page)
            pages[page] = self.query(0x8A if base else 0x90, args, raw=True)
        return b''.join(pages[p] for p in range(8))

    def stable_table(self, profile, base=False):
        a = self.table(profile, base)
        b = self.table(profile, base, reverse=True)
        if a != b:
            raise RuntimeError(f'Unstable table read for profile {profile}; stopping')
        return a

    def snapshot(self):
        ident = self.identify()
        tables = {str(p): self.stable_table(p).hex() for p in range(4)}
        return {'schema': SCHEMA, 'os': 'windows', 'device': ident,
                'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'tables': tables, 'sha256': digest(tables)}

    def check_positions(self):
        # Published matrix uses physical indices, not HID usage numbers.
        base = self.stable_table(0, base=True)
        for key, usage in zip('GHJK', (10,11,13,14)):
            i = POSITIONS[key]*4
            if base[i:i+4] != bytes((0,0,usage,0)):
                raise RuntimeError(f'{key} base mapping differs from expected factory mapping. '
                                   'No writes. Share the diagnostic backup for inspection.')

    def write_key(self, profile, index, config):
        if profile not in range(4) or index not in POSITIONS.values() or len(config) != 4:
            raise ValueError('Write outside the four authorized Fn keys')
        self.send(0x10, (0,profile,index,0,0,0), config)

    def write_table(self, profile, table):
        reports = fn_table_packets(profile, table)
        # Do not interleave GET requests with shared staging-buffer writes.
        for report in reports:
            n = self.dev.send_feature_report(report)
            if n != len(report):
                raise RuntimeError(f'Short HID batch write: {n}/{len(report)}')
            time.sleep(0.10)
        time.sleep(1.0)


def plan(tables, restored=None):
    changes = []
    for p in range(4):
        for target,key in enumerate('GHJK'):
            i = POSITIONS[key]*4
            before = tables[p][i:i+4]
            after = restored[p][i:i+4] if restored is not None else bytes((8,0,4,target))
            if before != after:
                changes.append((p,key,before,after))
    return changes


def table_diff(expected, actual):
    if len(expected) != 512 or len(actual) != 512:
        raise ValueError('Expected 512-byte tables')
    names = {v:k for k,v in POSITIONS.items()}
    return [{'index': i, 'key': names.get(i, 'other'),
             'expected': expected[i*4:i*4+4].hex(' '),
             'actual': actual[i*4:i*4+4].hex(' ')}
            for i in range(128) if expected[i*4:i*4+4] != actual[i*4:i*4+4]]


def apply_changes(kb, original, changes, record=None):
    expected = {p: bytearray(v) for p,v in original.items()}
    attempted = []

    def verify(p, want, stage):
        actual = kb.stable_table(p)
        diffs = table_diff(want, actual)
        if record:
            record({'stage': stage, 'profile': p, 'diff': diffs,
                    'expected_table': bytes(want).hex(), 'actual_table': actual.hex()})
        if diffs:
            print(f'{stage}: profile {p}, {len(diffs)} differing entries', flush=True)
            for d in diffs[:12]:
                print(f"  index={d['index']} key={d['key']} expected={d['expected']} actual={d['actual']}", flush=True)
        return not diffs

    try:
        for p,key,before,after in changes:
            attempted.append((p,key,before))
            if record:
                record({'stage':'write_attempt','profile':p,'key':key,
                        'packet':packet(0x10,(0,p,POSITIONS[key],0,0,0),after).hex()})
            kb.write_key(p, POSITIONS[key], after)
            i = POSITIONS[key]*4
            expected[p][i:i+4] = after
            if not verify(p, expected[p], 'after Fn+'+key):
                raise RuntimeError(f'Readback mismatch: profile {p}, Fn+{key}')
        for p in range(4):
            if not verify(p, expected[p], 'final'):
                raise RuntimeError(f'Final verification failed: profile {p}')
    except BaseException as failure:
        errors = []
        # Diagnostic file problems must never skip rollback.
        for p,key,before in reversed(attempted):
            try:
                kb.write_key(p, POSITIONS[key], before)
            except BaseException as e:
                errors.append(str(e))
        try:
            for p in range(4):
                if kb.stable_table(p) != original[p]:
                    errors.append(f'Profile {p}: rollback mismatch')
        except BaseException as e:
            errors.append(str(e))
        print('Rollback FAILED: '+ '; '.join(errors) if errors else 'Rollback verified.', file=sys.stderr)
        if record:
            try:
                record({'stage':'failure','error':str(failure),'rollback_errors':errors,
                        'rollback_verified':not errors})
            except Exception as e:
                print(f'Diagnostic logging failed: {e}', file=sys.stderr)
        raise


def apply_table_changes(kb, original, changes, record):
    wanted = {p: bytearray(original[p]) for p in range(4)}
    affected = []
    seen = set()
    # Validate the entire plan before sending any settings command.
    for p,key,before,after in changes:
        if p not in range(4) or key not in POSITIONS or (p,key) in seen:
            raise ValueError('Invalid/duplicate change')
        seen.add((p,key))
        i = POSITIONS[key]*4
        if len(after) != 4 or original[p][i:i+4] != before:
            raise ValueError('Change does not match snapshot')
        wanted[p][i:i+4] = after
        if p not in affected:
            affected.append(p)
    for p in affected:
        fn_table_packets(p, original[p])
        fn_table_packets(p, wanted[p])
    expected = {p:bytes(v) for p,v in original.items()}
    attempted = []
    try:
        for p in affected:
            reports = fn_table_packets(p, wanted[p])
            record({'stage':'batch_attempt','profile':p,'packets':[b.hex() for b in reports]})
            attempted.append(p)
            kb.write_table(p, wanted[p])
            expected[p] = bytes(wanted[p])
            # Check other profiles too: shared/aliased tables must fail closed.
            mismatch = False
            for q in range(4):
                actual = kb.stable_table(q)
                diffs = table_diff(expected[q], actual)
                record({'stage':'after_batch','written_profile':p,'profile':q,
                        'diff':diffs,'expected_table':expected[q].hex(),'actual_table':actual.hex()})
                if diffs:
                    mismatch = True
                    print(f'After profile {p} batch: profile {q}, {len(diffs)} differences',flush=True)
                    for d in diffs[:12]:
                        print(f"  index={d['index']} key={d['key']} expected={d['expected']} actual={d['actual']}",flush=True)
            if mismatch:
                raise RuntimeError(f'Batch readback mismatch after profile {p}')
            print(f'Profile {p}: batch write verified (all four profiles checked).',flush=True)
    except BaseException as failure:
        errors = []
        for p in reversed(attempted):
            try:
                kb.write_table(p, original[p])
            except BaseException as e:
                errors.append(f'Profile {p}: {e}')
        # A cross-profile side effect may require restoring a profile we did not target.
        for p in range(4):
            try:
                if kb.stable_table(p) != original[p]:
                    kb.write_table(p, original[p])
            except BaseException as e:
                errors.append(f'Profile {p}: {e}')
        for p in range(4):
            try:
                if kb.stable_table(p) != original[p]:
                    errors.append(f'Profile {p}: rollback mismatch')
            except BaseException as e:
                errors.append(f'Profile {p}: {e}')
        print('Rollback FAILED: '+'; '.join(errors) if errors else 'Rollback verified.',file=sys.stderr)
        try:
            record({'stage':'failure','error':str(failure),'rollback_verified':not errors,
                    'rollback_errors':errors})
        except Exception as e:
            print(f'Diagnostic logging failed: {e}',file=sys.stderr)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    ap.add_argument('--version', action='version', version=VERSION)
    sub.add_parser('list')
    diag = sub.add_parser('diagnose')
    diag.add_argument('--serial')
    for name in ('backup','install-ghjk','restore'):
        s = sub.add_parser(name)
        s.add_argument('--serial', help='Select a specific device serial')
        if name == 'backup':
            s.add_argument('output')
        else:
            s.add_argument('--apply', action='store_true', help='Actually write (default: preview)')
            s.add_argument('--backup-dir', default='backups')
        if name == 'restore':
            s.add_argument('input', help='Restore ONLY Fn+G/H/J/K from this backup')
    a = ap.parse_args()
    try:
        import hid
    except ImportError:
        raise RuntimeError('Install dependency: py -m pip install hidapi')
    candidates = [d for d in hid.enumerate(VID, 0)
                  if d.get('product_id') in {p for p,_ in SUPPORTED}
                  and d.get('usage_page') == 0xFFFF and d.get('usage') == 2]
    if a.command == 'list':
        print(json.dumps([{k:d.get(k) for k in ('vendor_id','product_id','product_string',
              'serial_number','interface_number','usage_page','usage')} for d in candidates],indent=2))
        return
    if a.serial:
        candidates = [d for d in candidates if d.get('serial_number') == a.serial]
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one supported USB device, found {len(candidates)}. '
                           'Use wired mode; unplug other units or select --serial.')
    restored = None
    if a.command == 'restore':
        obj = json.loads(Path(a.input).read_text(encoding='utf-8'))
        restored = validate_backup(obj)
        if obj['device']['serial'] != (candidates[0].get('serial_number') or ''):
            raise RuntimeError('Backup/device serial mismatch')
    dev = hid.device()
    try:
        dev.open_path(candidates[0]['path'])
        kb = Keyboard(dev, candidates[0])
        if a.command == 'diagnose':
            print(json.dumps(kb.identify(strict=False), indent=2))
            return
        ident = kb.identify()
        if restored is not None and any(obj['device'].get(k) != ident.get(k) for k in ('vid','pid','id','serial')):
            raise RuntimeError('Backup/device identity mismatch')
        snap = kb.snapshot()
        if a.command == 'backup':
            save_new(a.output, snap)
            print(f'Fn tables backed up: {a.output}')
            return
        current = validate_backup(snap)
        if a.command == 'install-ghjk':
            kb.check_positions()
        changes = plan(current, restored)
        for p,key,before,after in changes:
            print(f'Profile {p}: Fn+{key}: {before.hex(" ")} -> {after.hex(" ")}')
        if not changes:
            print('Already matches. No writes.')
            return
        if not a.apply:
            print('PREVIEW ONLY. Re-run with --apply to write. Hardware support is experimental.')
            return
        for p in range(4):
            fn_table_packets(p, current[p])
        directory = Path(a.backup_dir)
        directory.mkdir(parents=True, exist_ok=True)
        filename = directory / (dt.datetime.now(dt.timezone.utc).strftime('fn-%Y%m%dT%H%M%S-%fZ.json'))
        save_new(filename, snap)
        print(f'Pre-write backup: {filename}', flush=True)
        logpath = filename.with_suffix('.diagnostic.jsonl')
        # Open the diagnostic log before any settings write; exclusive creation.
        with logpath.open('x', encoding='utf-8') as log:
            def record(event):
                event = dict(event, tool_version=VERSION,
                             time_utc=dt.datetime.now(dt.timezone.utc).isoformat())
                log.write(json.dumps(event, ensure_ascii=False)+'\n')
                log.flush()
            record({'stage':'start', 'device':snap['device'], 'backup':str(filename)})
            print(f'Diagnostic log: {logpath}', flush=True)
            apply_table_changes(kb, current, changes, record)
            record({'stage':'success'})
        print('Write and full Fn-table readback verified. Test Fn+G/H/J/K and reconnect persistence.')
    finally:
        dev.close()


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)
