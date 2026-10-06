import copy
import unittest
from unittest.mock import patch
import fun60_layer_tool as t

class Fake:
    def __init__(self, fail=False):
        self.tables = {p: bytearray(bytes(range(256))*2) for p in range(4)}
        self.fail = fail
        self.writes = []
    def write_key(self,p,i,c):
        self.writes.append((p,i,bytes(c)))
        self.tables[p][i*4:i*4+4] = c
        if self.fail:
            self.fail = False
            raise OSError('Simulated disconnect after write')
    def stable_table(self,p):
        return bytes(self.tables[p])

class Tests(unittest.TestCase):
    def test_model_pairs(self):
        for pid,device_id in [(0x5029,2600),(0x502F,2305),(0x5029,2305),(0x5029,9999)]:
            k=t.Keyboard(None,{'product_id':pid})
            response=bytes([0x8F])+device_id.to_bytes(4,'little')+bytes(59)
            with patch.object(k,'query',return_value=response):
                self.assertEqual(k.identify(False)['id'],device_id)
                if (pid,device_id) in t.SUPPORTED:
                    self.assertTrue(k.identify()['supported'])
                else:
                    with self.assertRaises(RuntimeError):k.identify()
    def test_backup_model_pairs(self):
        tables={str(p):bytes(512).hex() for p in range(4)}
        for pid,device_id in [(0x5029,2600),(0x502F,2305),(0x5029,2305)]:
            b={'schema':t.SCHEMA,'os':'windows','device':{'vid':t.VID,'pid':pid,'id':device_id},'tables':tables,'sha256':t.digest(tables)}
            if (pid,device_id) in t.SUPPORTED:
                self.assertEqual(len(t.validate_backup(b)),4)
            else:
                with self.assertRaises(ValueError):t.validate_backup(b)
    def test_readback_mismatch_evidence_and_rollback(self):
        class RejectH(Fake):
            def write_key(self,p,i,c):
                if i==39 and bytes(c)==bytes((8,0,4,1)):
                    return
                super().write_key(p,i,c)
        k=RejectH();old={p:bytes(v) for p,v in k.tables.items()};events=[]
        with self.assertRaisesRegex(RuntimeError,r'Fn\+H'):
            t.apply_changes(k,old,t.plan(old),events.append)
        bad=[e for e in events if e.get('diff')]
        self.assertEqual(bad[0]['diff'][0]['index'],39)
        self.assertEqual(bad[0]['diff'][0]['actual'],old[0][156:160].hex(' '))
        self.assertTrue(events[-1]['rollback_verified'])
        self.assertEqual({p:bytes(v) for p,v in k.tables.items()},old)
    def test_log_failure_still_rolls_back(self):
        k=Fake();old={p:bytes(v) for p,v in k.tables.items()}
        def broken(e):
            if e['stage'].startswith('after'):
                raise OSError('Log storage failure')
        with self.assertRaises(OSError):t.apply_changes(k,old,t.plan(old),broken)
        self.assertEqual({p:bytes(v) for p,v in k.tables.items()},old)
    def test_batch_packets(self):
        table=bytes(range(252))*2+bytes(8)
        ps=t.fn_table_packets(2,table)
        self.assertEqual(len(ps),10)
        self.assertEqual(b''.join(p[9:65] for p in ps[:9]),table[:504])
        for i,p in enumerate(ps):
            self.assertEqual(len(p),65)
            self.assertEqual(p[1:6],bytes((16,0,2,255,i)))
            self.assertEqual(sum(p[1:9])&255,255)
        self.assertEqual(ps[-1][6:8],bytes((0,1)))
        self.assertEqual(ps[-1][9:],bytes(56))
        with self.assertRaises(ValueError):t.fn_table_packets(0,bytes([1])*512)
        with self.assertRaises(ValueError):t.fn_table_packets(4,bytes(512))
    def test_batch_install_restore(self):
        class Batch:
            def __init__(self):self.tables={p:bytes(range(252))*2+bytes(8) for p in range(4)}
            def write_table(self,p,data):self.tables[p]=bytes(data)
            def stable_table(self,p):return self.tables[p]
        k=Batch();old=dict(k.tables);events=[]
        t.apply_table_changes(k,old,t.plan(old),events.append)
        self.assertEqual(t.plan(k.tables),[])
        for p in range(4):
            self.assertTrue(all(d['key']!='other' for d in t.table_diff(old[p],k.tables[p])))
        now=dict(k.tables)
        t.apply_table_changes(k,now,t.plan(now,old),events.append)
        self.assertEqual(k.tables,old)
    def test_batch_corruption_rollback(self):
        class Batch:
            def __init__(self):self.tables={p:bytes(512) for p in range(4)};self.bad=True
            def write_table(self,p,data):
                b=bytearray(data)
                if self.bad:
                    self.bad=False;b[132:136]=bytes(4)
                self.tables[p]=bytes(b)
            def stable_table(self,p):return self.tables[p]
        k=Batch();old=dict(k.tables);events=[]
        with self.assertRaisesRegex(RuntimeError,'Batch readback mismatch'):
            t.apply_table_changes(k,old,t.plan(old),events.append)
        self.assertEqual(k.tables,old)
        self.assertTrue(events[-1]['rollback_verified'])
    def test_wire(self):
        b=t.packet(0x10,(0,3,51,0,0,0),bytes((8,0,4,3)))
        self.assertEqual(len(b),65)
        self.assertEqual(b[1:8], bytes((16,0,3,51,0,0,0)))
        self.assertEqual(sum(b[1:9])&255,255)
        self.assertEqual(b[9:13],bytes((8,0,4,3)))
    def test_install_and_restore(self):
        k=Fake(); old={p:bytes(v) for p,v in k.tables.items()}
        t.apply_changes(k,old,t.plan(old))
        for p in range(4):
            for n,key in enumerate('GHJK'):
                i=t.POSITIONS[key]*4
                self.assertEqual(k.tables[p][i:i+4],bytes((8,0,4,n)))
            untouched=set(range(512))-{i*4+j for i in t.POSITIONS.values() for j in range(4)}
            self.assertTrue(all(k.tables[p][i]==old[p][i] for i in untouched))
        now={p:bytes(v) for p,v in k.tables.items()}
        self.assertEqual(t.plan(now),[])
        t.apply_changes(k,now,t.plan(now,old))
        self.assertEqual({p:bytes(v) for p,v in k.tables.items()},old)
    def test_rollback(self):
        k=Fake(True);old={p:bytes(v) for p,v in k.tables.items()}
        with self.assertRaises(OSError):t.apply_changes(k,old,t.plan(old))
        self.assertEqual({p:bytes(v) for p,v in k.tables.items()},old)
    def test_reject_outside_keys(self):
        k=t.Keyboard(None,{})
        for p,i,c in [(4,33,b'1234'),(0,34,b'1234'),(0,33,b'123')]:
            with self.assertRaises(ValueError):k.write_key(p,i,c)
    def test_corrupt_backup(self):
        tables={str(p):(bytes(512)).hex() for p in range(4)}
        b={'schema':t.SCHEMA,'os':'windows','device':{'vid':t.VID,'pid':t.PID,'id':t.DEVICE_ID},'tables':tables,'sha256':t.digest(tables)}
        self.assertEqual(len(t.validate_backup(b)),4)
        b['tables']['0']='01'+b['tables']['0'][2:]
        with self.assertRaises(ValueError):t.validate_backup(b)
    def test_framing_and_echo(self):
        class D:
            def send_feature_report(self,b):return len(b)
            def get_feature_report(self,*a):return bytes(64)
        with patch('fun60_layer_tool.time.sleep'):
            with self.assertRaises(RuntimeError):t.Keyboard(D(),{}).query(0x8F)
    def test_stale_pages(self):
        k=t.Keyboard(None,{})
        with patch.object(k,'table',side_effect=[bytes(512),bytes([1])*512]):
            with self.assertRaises(RuntimeError):k.stable_table(0)

if __name__=='__main__':unittest.main()
