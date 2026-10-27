import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cd_sector
import mod_export as me
SOURCE=ROOT/'Alundra (USA) (Rev 1).bin'

@unittest.skipUnless(SOURCE.exists(),'Local lawful game image required')
class FastRebuildTests(unittest.TestCase):
 def test_sector_codes_match_the_original_disc(self):
  with SOURCE.open('rb') as f:
   for lba in (16,1000,100000):
    f.seek(lba*2352);raw=f.read(2352);s=bytearray(raw);s[2072:]=bytes(280)
    self.assertEqual(bytes(cd_sector.mode2_form1(s)),raw)
 def test_only_changed_sectors_are_rewritten_and_removed_edits_go_back(self):
  with tempfile.TemporaryDirectory() as folder:
   dst=Path(folder)/'game.bin';cue=dst.with_suffix('.cue');shutil.copyfile(SOURCE,dst);cue.write_text('FILE "game.bin" BINARY\n')
   datas=bytearray(me.read_datas(SOURCE));me._write_build_manifest(SOURCE,dst,{'DATA/DATAS.BIN':bytes(datas)})
   datas[123456]^=0xFF;lines=[]
   self.assertIsNotNone(me._patch_previous_build(SOURCE,dst,cue,{'DATA/DATAS.BIN':bytes(datas)},lines.append))
   self.assertIn('Updating 1 changed sector',lines[0]);self.assertEqual(me.read_datas(dst),bytes(datas))
   # a file the last build wrote but this one does not is put back
   self.assertIsNotNone(me._patch_previous_build(SOURCE,dst,cue,{},lambda t:None))
   self.assertEqual(me.read_datas(dst),me.read_datas(SOURCE))
   # a size change needs a full rebuild; no manifest, no patch either
   self.assertIsNone(me._patch_previous_build(SOURCE,dst,cue,{'DATA/DATAS.BIN':bytes(datas)+b'x'},lambda t:None))
   os.utime(dst,ns=(1,1))
   self.assertIsNone(me._patch_previous_build(SOURCE,dst,cue,{'DATA/DATAS.BIN':bytes(datas)},lambda t:None))

if __name__=='__main__':unittest.main()
