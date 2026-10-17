from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resonance_graph.model import GraphStore
from resonance_graph.semantic_graph import CosineIndex, build_graph, navigate


class Retrieval(unittest.TestCase):
    ids = ("a", "b", "c", "d")
    vectors = np.array([[1., 0.], [.8, .2], [.6, .4], [.4, .6]])

    def test_exact_search_matches_geometry(self):
        index = CosineIndex(self.ids, self.vectors)
        self.assertEqual([h.node_id for h in index.search([1., 0.], 3)], ["a", "b", "c"])
        self.assertEqual([h.node_id for h in index.search([1., 0.], 1, "a")], ["b"])

    def test_reordering_and_blocks_preserve_hits(self):
        first = CosineIndex(self.ids, self.vectors, 1)
        perm = [3, 1, 0, 2]
        second = CosineIndex([self.ids[i] for i in perm], self.vectors[perm], 3)
        queries = [[1., 0.], [0., 1.], [1., 1.]]
        left, right = first.search_batch(queries, 3), second.search_batch(queries, 3)
        for a, b in zip(left, right):
            self.assertEqual([h.node_id for h in a], [h.node_id for h in b])
            np.testing.assert_allclose([h.score for h in a], [h.score for h in b], atol=1e-12, rtol=0)

    def test_index_has_no_input_alias(self):
        vectors = self.vectors.copy()
        index = CosineIndex(self.ids, vectors)
        before = index.search([1., 0.], 4)
        vectors[:] = 100.
        self.assertEqual(before, index.search([1., 0.], 4))

    def test_invalid_queries_and_ids(self):
        index = CosineIndex(self.ids, self.vectors)
        for query in ([0., 0.], [float("nan"), 1.], [1., 2., 3.]):
            with self.assertRaises(ValueError):
                index.search(query)
        with self.assertRaises(ValueError):
            CosineIndex(["a", "a"], self.vectors[:2])

    def test_builder_preserves_x_and_budget(self):
        store, index = build_graph(self.ids, self.vectors, edge_budget=4, candidate_k=3)
        self.assertEqual(len(store.edges), 4)
        self.assertEqual(len(store.arc_view().arcs), 8)
        for node_id, row in zip(self.ids, self.vectors):
            self.assertEqual(store.nodes[node_id].x, tuple(row))
            self.assertTrue(store.neighbors(node_id))

    def test_builder_reordering_preserves_graph(self):
        first, _ = build_graph(self.ids, self.vectors, edge_budget=4, candidate_k=3)
        perm = [3, 1, 0, 2]
        second, _ = build_graph([self.ids[i] for i in perm], self.vectors[perm], edge_budget=4, candidate_k=3)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_projection_does_not_replace_source_content(self):
        projected = self.vectors[:, :1]
        store, index = build_graph(self.ids, projected, content_vectors=self.vectors,
                                   edge_budget=4, candidate_k=3, score_space="test_projection")
        self.assertEqual(index.dimensions, 1)
        self.assertEqual(store.nodes["b"].x, tuple(self.vectors[1]))
        self.assertTrue(all(edge.method.startswith("test_projection/") for edge in store.edges.values()))

    def test_navigation_budget_and_full_recall_small_connected_case(self):
        store, index = build_graph(self.ids, self.vectors, edge_budget=6, candidate_k=3)
        result = navigate(store, index, [1., 0.], k=3, budget=4, entry_points=["d"])
        self.assertEqual(result.hits, index.search([1., 0.], 3))
        small = navigate(store, index, [1., 0.], k=3, budget=2, entry_points=["d"])
        self.assertLessEqual(small.scored_nodes, 2)

    def test_phase_change_does_not_invalidate_content_index(self):
        store, index = build_graph(self.ids, self.vectors, edge_budget=6, candidate_k=3)
        store.advance_phase(.1)
        self.assertEqual(navigate(store, index, [1., 0.], budget=4, entry_points=["a"]).hits, index.search([1., 0.]))

    def test_revision_change_invalidates_derived_index(self):
        store, index = build_graph(self.ids, self.vectors, edge_budget=6, candidate_k=3)
        store.commit(nodes=[replace(store.nodes["a"], source_revision=1, x=(0., 1.))], expected_version=store.version)
        with self.assertRaises(ValueError):
            navigate(store, index, [1., 0.], budget=4, entry_points=["a"])

    def test_restart_rebuilds_equivalent_index(self):
        store, index = build_graph(self.ids, self.vectors, edge_budget=6, candidate_k=3)
        restored = GraphStore.from_dict(json.loads(json.dumps(store.to_dict())))
        rebuilt = CosineIndex.from_store(restored)
        self.assertEqual(navigate(store, index, [1., 0.], budget=4, entry_points=["a"]),
                         navigate(restored, rebuilt, [1., 0.], budget=4, entry_points=["a"]))


if __name__ == "__main__":
    unittest.main()
