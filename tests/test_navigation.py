from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resonance_graph.model import EdgeKey
from resonance_graph.semantic_graph import build_graph
from resonance_graph.navigation import GraphNavigator


class Navigation(unittest.TestCase):
    def fixture(self):
        return build_graph(["a", "b", "c", "d"], [[1., 0.], [.8, .2], [.6, .4], [.4, .6]], edge_budget=6, candidate_k=3)

    def test_budget_and_full_ranking(self):
        store, index = self.fixture()
        navigator = GraphNavigator(store, index, ["d"])
        result = navigator.search([1., 0.], k=3, budget=4)
        self.assertEqual([h.node_id for h in result.hits], [h.node_id for h in index.search([1., 0.], 3)])
        self.assertEqual(navigator.search([1., 0.], budget=2).scored_nodes, 2)

    def test_cache_observes_edge_update(self):
        store, index = self.fixture()
        navigator = GraphNavigator(store, index, ["d"])
        old_version = navigator._version
        edges = [replace(edge, weight=0.) for edge in store.edges.values()]
        store.commit(edges=edges, expected_version=store.version)
        result = navigator.search([1., 0.], budget=4)
        self.assertEqual(result.scored_nodes, 1)
        self.assertGreater(navigator._version, old_version)

    def test_revision_change_rejects_cached_index(self):
        store, index = self.fixture()
        navigator = GraphNavigator(store, index, ["d"])
        store.commit(nodes=[replace(store.nodes["a"], x=(0., 1.), source_revision=1)], expected_version=store.version)
        with self.assertRaises(ValueError):
            navigator.search([1., 0.])


if __name__ == "__main__":
    unittest.main()
