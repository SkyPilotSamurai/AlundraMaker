import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import native_werewolf_donor as source


class WerewolfDonorTests(unittest.TestCase):
    def guards(self, record=None, callbacks=None, program=b'\x1a\x00\xff'):
        records=[bytes(20)]*source.ENTITY+[bytes.fromhex(source.RECORD) if record is None else record]
        return (
            patch.object(source,'record_cluster',return_value={'entities':records}),
            patch.object(source,'sprite_callbacks',return_value=source.CALLBACKS if callbacks is None else callbacks),
            patch.object(source,'EditSession',return_value=SimpleNamespace(data=program)),
            patch.object(source,'reachable_instructions',return_value=[(0,0x1a,len(program))]),
            patch.object(source,'PROGRAM_SIGNATURES',{'A 1':(3,hashlib.sha256(source.INITIALIZER).hexdigest())}),
        )

    def verify(self, **kw):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for guard in self.guards(**kw):stack.enter_context(guard)
            return source.donor(b'')

    def test_initializer_preserves_native_ai_and_excludes_only_new_story_hooks(self):
        result=self.verify()
        self.assertEqual(result['native_callbacks'],[('A',0),('C',37),('D',11),('E',1),('F',0)])
        self.assertEqual(result['reproduced_initializer_hex'],'1a00ff')
        self.assertFalse(result['existing_stock_actors_changed'])
        self.assertFalse(result['gameplay_verified'])

    def test_record_and_callback_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'record differs'):self.verify(record=bytes(20))
        with self.assertRaisesRegex(ValueError,'callback'):self.verify(callbacks=[('C',0)])

    def test_cinematic_or_initializer_byte_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'program differs'):self.verify(program=b'\x1a\x01\xff')
        with self.assertRaisesRegex(ValueError,'program differs'):self.verify(program=b'\x1a\x00')


if __name__=='__main__':unittest.main()
