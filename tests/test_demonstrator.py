import unittest
from resonance_graph.demonstrator import Demonstrator


class IntegrationContracts(unittest.TestCase):
    def make(self):
        demo = Demonstrator()
        demo.ingest_batch([("a", [1., 0.], "document:a:revision:0"),
                           ("b", [0., 1.], "document:b:revision:0")])
        return demo

    def test_ingest_retrieve_update_inspect_restart(self):
        demo = self.make()
        self.assertEqual(demo.retrieve([1., 0.], 1)[0].node_id, "a")
        demo.update("a", [-1., 0.], "document:a:revision:1", expected_revision=0)
        self.assertEqual(demo.retrieve([1., 0.], 1)[0].node_id, "b")
        self.assertEqual(demo.store.nodes["a"].source_revision, 1)
        self.assertEqual(demo.inspect_relation("a", "b")["state"], "similaridad_observada")
        self.assertIsNone(demo.inspect_relation("a", "b")["calibrated_probability"])
        restored = Demonstrator.restore(demo.snapshot())
        self.assertEqual(restored.retrieve([1., 0.]), demo.retrieve([1., 0.]))

    def test_invalid_update_and_duplicate_ingest_atomic(self):
        demo = self.make()
        before = demo.snapshot()
        for action in (lambda: demo.update("a", [0., 0.], "invalid", expected_revision=0),
                       lambda: demo.update("a", [1., 0.], "invalid", expected_revision=9),
                       lambda: demo.ingest("a", [1., 0.], "duplicate"),
                       lambda: demo.ingest("c", [1., 0., 0.], "wrong_dimension")):
            with self.assertRaises(ValueError):
                action()
            self.assertEqual(before, demo.snapshot())
