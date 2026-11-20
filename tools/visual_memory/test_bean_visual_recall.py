"""Synthetic offline checks for real photo indexing, recall and tamper detection."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from bean_visual_recall import build,search,similar,verify

class VisualRecallTests(unittest.TestCase):
    def test_import_recall_integrity_rebuild(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for directory in ['frames_320','frames_full']:(p/directory).mkdir()
            for i,color in enumerate(('red','green')):
                for directory in ['frames_320','frames_full']:
                    Image.new('RGB',(64,64),color).save(p/directory/f'frame_{i:03d}s.jpg')
            d={'capture_id':'synthetic','source':{'filename':'synthetic.mp4','sha256':'a'*64,'duration_seconds':2},
               'scenes':[{'id':'room','name':'Synthetic room','start':0,'end':1,'confidence':'high','description':'A synthetic sofa room'}],
               'frames':{'items':[{'t_seconds':i,'room_id':'room','caption':cap,
               'full_frame':f'frames_full/frame_{i:03d}s.jpg','thumbnail':f'frames_320/frame_{i:03d}s.jpg'}
               for i,cap in enumerate(('red sofa','green table'))]}}
            m=p/'visual_memory.json';m.write_text(json.dumps(d))
            db=p/'index.sqlite3'
            self.assertEqual(build(m,db)['indexed_frames'],2)
            self.assertEqual(len(search(db,'sofa')),2) # both mention sofa in their scene context
            self.assertEqual(similar(db,p/'frames_full/frame_000s.jpg')[0]['t_seconds'],0)
            self.assertTrue(verify(db)['ok'])
            self.assertEqual(build(m,db)['indexed_frames'],2) # idempotent import
            (p/'frames_full/frame_001s.jpg').write_bytes(b'tampered')
            self.assertFalse(verify(db)['ok'])
    def test_reject_relative_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'frames_320').mkdir()
            m=p/'visual_memory.json'
            m.write_text(json.dumps({'capture_id':'bad','source':{'filename':'x.mp4','sha256':'x','duration_seconds':1},
               'scenes':[{'id':'x','name':'x','start':0,'end':1,'description':'x','confidence':'low'}],
               'frames':{'items':[{'t_seconds':0,'room_id':'x','caption':'x','full_frame':'../../etc/passwd','thumbnail':'frames_320/no.jpg'}]}}))
            with self.assertRaises(ValueError): build(m,p/'index.sqlite3')

if __name__=='__main__':unittest.main()