import unittest,tempfile,json,sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from editor_session import EditSession
from mod_export import save_mod,load_mod,build_game

class ModTests(unittest.TestCase):
 def test_qol_is_emitted_to_verified_disc_copy(self):
  import mod_export
  s=EditSession(bytes(64),verify=False)
  s.content_database={'format':'alundra-content-database-v1','definitions':[], 'mod_options':{'instant_text':True,'open_world':True}}
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);tool_dir=root/'Randomizer/tools';tool_dir.mkdir(parents=True)
   for tool in ('dumpsxiso.exe','mkpsxiso.exe'):(tool_dir/tool).touch()
   source=root/'source.bin';source.write_bytes(b'original disc')
   def read(path,name='DATA/DATAS.BIN'):
    if name=='DATA/DATAS.BIN':return s.original if Path(path)==source else b'X'+s.original[1:]
    return b'original exe' if Path(path)==source else b'patched exe'
   def patch_qol(exported,exe):
    self.assertTrue(exported.content_database['mod_options']['open_world'])
    exported.replace(0,b'X','Test intro data patch')
    return b'patched exe',{'options':{'open_world':True}}
   def run(args,**kwargs):
    if Path(args[0]).name=='dumpsxiso.exe':
     dump=Path(args[args.index('-x')+1]);(dump/'DATA').mkdir()
     (dump/'DATA/DATAS.BIN').write_bytes(s.original);(dump/'ALUN_CD.EXE').write_bytes(b'original exe')
    else:
     work=Path(kwargs['cwd']);self.assertEqual((work/'dump/ALUN_CD.EXE').read_bytes(),b'patched exe')
     written=(work/'dump/DATA/DATAS.BIN').read_bytes();self.assertEqual(written[:len(s.original)],b'X'+s.original[1:]);self.assertFalse(any(written[len(s.original):]))   # reserved room after the data
     Path(args[args.index('-o')+1]).write_bytes(b'built disc')
     Path(args[args.index('-c')+1]).write_text('FILE "result.bin" BINARY\nTRACK 01 MODE2/2352\n')
    return SimpleNamespace(returncode=0,stderr='',stdout='')
   with patch.object(mod_export,'ROOT',root),patch.object(mod_export,'read_datas',side_effect=read),patch('editor_qol.apply_qol',side_effect=patch_qol) as qol,patch('mod_export.subprocess.run',side_effect=run):
    result=build_game(mod_export.build_snapshot(s),source,root/'edited.bin')
   self.assertEqual(result[0].read_bytes(),b'built disc');self.assertIn('edited.bin',result[1].read_text())
   qol.assert_called_once();self.assertEqual(source.read_bytes(),b'original disc')
   self.assertFalse(hasattr(s,'extra_files'))
   self.assertEqual(s.data,s.original);self.assertEqual(s.undo_stack,[])

 def test_game_options_round_trip_and_snapshot_isolation(self):
  from mod_export import build_snapshot
  from content_database import ContentDatabase
  s=EditSession(bytes(64),verify=False)
  database=ContentDatabase();database.document['mod_options']={'skip_intro':True,'lr_swaps':True,'instant_text':True,'open_world':True,'starting_equipment':[1,20,36],'start_point':{'map_id':242,'x':38,'y':12,'z':2}}
  s.content_database=database.to_json()
  snapshot=build_snapshot(s)
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'options.alundramod';save_mod(s,path,'Options',244)
   with patch('editor_session.verify_datas'):
    restored,_=load_mod(s.original,path)
   self.assertEqual(restored.content_database['mod_options'],s.content_database['mod_options'])
  s.content_database['mod_options']['instant_text']=False
  self.assertTrue(snapshot.content_database['mod_options']['instant_text'])

 def test_project_round_trip_and_tamper_rejection(self):
  s=EditSession(bytes(64),verify=False);s.replace(12,b"abc","test")
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/"test.alundramod";save_mod(s,path,"Test",244)
   with patch("editor_session.verify_datas"):
    loaded,m=load_mod(s.original,path)
    self.assertEqual(loaded.data,s.data);self.assertEqual(m,244)
    d=json.loads(path.read_text());d["patch"]["changes"][0]["after"]="000000";path.write_text(json.dumps(d))
    with self.assertRaises(ValueError):load_mod(s.original,path)
   with self.assertRaises(FileExistsError):save_mod(s,path,"Test",244)
 def test_mod_overwrite_is_atomic_and_default_remains_safe(self):
  s=EditSession(bytes(64),verify=False);s.replace(2,b'new','new')
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'same.alundramod';path.write_text('previous')
   with self.assertRaises(FileExistsError):save_mod(s,path,'Same',244)
   save_mod(s,path,'Same',244,overwrite=True)
   self.assertEqual(json.loads(path.read_text())['name'],'Same')
   self.assertFalse(list(Path(folder).glob('*.tmp')))
 def test_build_protects_existing_output_and_checks_base(self):
  s=EditSession(bytes(64),verify=False)
  with tempfile.TemporaryDirectory() as folder:
   dest=Path(folder)/"test.bin";dest.write_bytes(b"keep")
   with self.assertRaises(ValueError):build_game(s,"unused.bin",dest)
   self.assertEqual(dest.read_bytes(),b"keep")
   with patch("mod_export.read_datas",return_value=b"wrong"):
    with self.assertRaises(ValueError):build_game(s,"unused.bin",Path(folder)/"new.bin")
   self.assertFalse((Path(folder)/"new.bin").exists())
 def test_build_pair_overwrites_as_a_pair_and_preserves_input(self):
  import mod_export
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);built=root/'fresh.bin';built.write_bytes(b'new game')
   destination=root/'game.bin';cue=destination.with_suffix('.cue')
   destination.write_bytes(b'old game');cue.write_text('old cue')
   mod_export._commit_build_pair(built,'FILE "game.bin" BINARY\n',destination,cue,True)
   self.assertEqual(destination.read_bytes(),b'new game')
   self.assertEqual(cue.read_text(),'FILE "game.bin" BINARY\n')
   self.assertEqual(built.read_bytes(),b'new game')
   self.assertEqual(sorted(p.name for p in root.iterdir()),['fresh.bin','game.bin','game.cue'])
 def test_build_pair_rolls_back_both_files_if_second_replace_fails(self):
  import mod_export,os
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);built=root/'fresh.bin';built.write_bytes(b'new game')
   destination=root/'game.bin';cue=root/'game.cue';destination.write_bytes(b'old game');cue.write_text('old cue')
   real=os.replace;failed=[False]
   def replace(source,target):
    if Path(target)==cue and Path(source).suffix=='.tmp' and not failed[0]:
     failed[0]=True;raise OSError('simulated cue install failure')
    return real(source,target)
   with patch('mod_export.os.replace',side_effect=replace),self.assertRaisesRegex(OSError,'simulated'):
    mod_export._commit_build_pair(built,'new cue',destination,cue,True)
   self.assertEqual(destination.read_bytes(),b'old game');self.assertEqual(cue.read_text(),'old cue')
   self.assertEqual(sorted(p.name for p in root.iterdir()),['fresh.bin','game.bin','game.cue'])
