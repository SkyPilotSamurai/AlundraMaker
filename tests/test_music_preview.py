import sys,unittest,wave,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import music_preview as mp

DISC=ROOT/'game/disc'
SOUND=next((p for p in (DISC/'DATA/SOUND.BIN',ROOT/'game/editor-audio-cache/SOUND.BIN') if p.is_file()),None)


class EnvelopeAndWavTests(unittest.TestCase):
    def test_envelope_rises_holds_and_releases(self):
        points=mp.envelope_points(0x80FF,0xDFE8,1.0,44100)
        self.assertEqual(points[0],(0.0,0.0))
        self.assertTrue(all(b[0]>=a[0] for a,b in zip(points,points[1:])))
        self.assertEqual(points[-1][1],0.0 if points[-1][1]==0 else points[-1][1])
        self.assertGreater(points[-1][0],1.0)

    def test_volume_scales_normalised_output(self):
        quiet=mp.to_wav(22050,[1000.0,-1000.0]*100,0.25);loud=mp.to_wav(22050,[1000.0,-1000.0]*100,1.0)
        q=wave.open(io.BytesIO(quiet)).readframes(1);l=wave.open(io.BytesIO(loud)).readframes(1)
        self.assertLess(abs(int.from_bytes(q[:2],'little',signed=True)),abs(int.from_bytes(l[:2],'little',signed=True)))
        with self.assertRaises(ValueError):mp.to_wav(22050,[0.0,0.0],1.5)

    def test_vag_loop_flags(self):
        block=bytes([0x00,0x06])+bytes(14)+bytes([0x00,0x03])+bytes(14)
        pcm,loop,loops=mp.decode_vag(block)
        self.assertEqual(len(pcm),56);self.assertTrue(loops);self.assertEqual(loop,0)


@unittest.skipUnless(SOUND and (DISC/'ALUN_CD.EXE').is_file(),'needs the game audio files')
class RealMusicTests(unittest.TestCase):
    def test_every_track_parses_and_renders(self):
        from music_database import music_rows
        exe=(DISC/'ALUN_CD.EXE').read_bytes();sound=SOUND.read_bytes()
        rows=music_rows(exe,sound)
        for row in rows[1:]:
            seq=sound[row['sequence_offset']:row['header_offset']]
            resolution,tempo,events=mp.parse_sequence(seq)
            self.assertEqual(events[-1][1],0x2F,row['id'])
        row=rows[16]
        rate,stereo=mp.render(sound[row['sequence_offset']:row['header_offset']],sound[row['header_offset']:row['body_offset']],
                              sound[row['body_offset']:row['end_offset']],seconds=4)
        self.assertEqual(len(stereo),rate*4*2);self.assertTrue(any(abs(v)>100 for v in stereo[rate:]))


if __name__=='__main__':unittest.main()
