import json
import unittest
from resonance_graph import AdaptiveRouter, DEFAULT_CONFIG, GraphStore, build_graph, __version__


class PublicAPI(unittest.TestCase):
    def test_library_integration_and_roundtrip(self):
        store, index = build_graph(['a', 'b', 'c'], [[1., 0.], [.9, .1], [0., 1.]],
                                   edge_budget=3, candidate_k=2)
        router = AdaptiveRouter(store, index, ['a'], 'anchored', dict(DEFAULT_CONFIG), seed=710)
        result = router.search([1., .2], k=2, budget=3)
        self.assertEqual(len(result.hits), 2)
        router.feedback([1., .2], [result.hits[0].node_id])
        self.assertEqual(router.updates, 1)
        raw = json.loads(json.dumps(store.to_dict()))
        self.assertEqual(GraphStore.from_dict(raw).to_dict(), store.to_dict())
        self.assertEqual(__version__, '0.1.0')

    def test_defaults_are_not_globally_mutable(self):
        with self.assertRaises(TypeError):
            DEFAULT_CONFIG['drift_cap'] = 9.
