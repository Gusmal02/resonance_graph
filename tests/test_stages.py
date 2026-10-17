import unittest
import numpy as np
from resonance_graph.model import EdgeKey, RelationKind
from resonance_graph.semantic_graph import build_graph, CosineIndex
from resonance_graph.operational import PruningPolicy, pruned_view, routing_tree, OperationalNavigator, coverage
from resonance_graph.adaptation import AdaptiveRouter
from resonance_graph.evidence import inspect_relation

CFG = {"learning_rate": .15, "anchor": .08, "drift_cap": .25, "decay": .9,
       "routing_prior": .1, "phase_coupling": .1, "phase_dt": .1}


class StageContracts(unittest.TestCase):
    def make(self):
        vectors = np.array([[1., 0., 0.], [.9, .1, 0.], [0., 1., 0.], [0., .9, .1]])
        store, index = build_graph(list("abcd"), vectors, edge_budget=4, candidate_k=3)
        return store, index

    def test_hysteresis_requires_persistent_weakness(self):
        policy = PruningPolicy(["edge"], weak_ticks=3)
        policy.observe({"edge": .49})
        policy.observe({"edge": .49})
        self.assertIn("edge", policy.active)
        policy.observe({"edge": .49})
        self.assertNotIn("edge", policy.active)
        policy.observe({"edge": .53})
        self.assertNotIn("edge", policy.active)
        policy.observe({"edge": .56})
        self.assertIn("edge", policy.active)

    def test_pruning_validation_is_atomic(self):
        policy = PruningPolicy(["a", "b"])
        with self.assertRaises(ValueError):
            policy.observe({"a": 0., "b": float("nan")})
        self.assertEqual(policy.active, {"a", "b"})

    def test_routing_connects_without_semantic_evidence_or_source_mutation(self):
        store, index = self.make()
        original = store.to_dict()
        view = pruned_view(store, (), backbone=routing_tree(index), edge_budget=4)
        self.assertEqual(store.to_dict(), original)
        self.assertEqual(coverage(view, ("a",))["unreachable_from_entries"], 0)
        self.assertFalse(view.arc_view().arcs)
        for edge in view.edges.values():
            self.assertEqual(inspect_relation(view, edge.key.a, edge.key.b, RelationKind.ROUTING)["state"], "evidencia_insuficiente")

    def test_operational_repeat_and_restart(self):
        store, index = self.make()
        view = pruned_view(store, (), backbone=routing_tree(index), edge_budget=4)
        navigator = OperationalNavigator(view, CosineIndex.from_store(view), ("a",))
        first = navigator.search([1., 0., 0.], budget=4, k=4)
        self.assertEqual(first, navigator.search([1., 0., 0.], budget=4, k=4))
        self.assertEqual(first.scored_nodes, 4)

    def test_prior_modes_preserve_source_and_phase_contracts(self):
        store, index = self.make()
        before = store.to_dict()
        for mode in AdaptiveRouter.MODES:
            router = AdaptiveRouter(store, index, ("a",), mode, CFG, 42)
            for _ in range(30):
                router.feedback([0., 1., 0.], ["a"])
            self.assertEqual(store.to_dict(), before)
            self.assertLess(router.diagnostics()["max_q_norm_error"], 1e-12)
            if mode == "anchored":
                self.assertLessEqual(router.diagnostics()["max_z_drift"], .25+1e-12)
            if mode == "q_frozen":
                self.assertFalse(router.diagnostics()["q_changed"])
            if mode == "q_active":
                self.assertTrue(router.diagnostics()["q_changed"])

    def test_collective_feedback_abstains_without_fabricating_edges(self):
        store, index = self.make()
        router = AdaptiveRouter(store, index, ("a",), "q_active", CFG, 42)
        q, z = router.q.copy(), router.z.copy()
        router.feedback([1., 0., 0.], list("abcd"), collective=True)
        np.testing.assert_array_equal(router.q, q)
        np.testing.assert_array_equal(router.z, z)
        self.assertEqual(router.updates, 0)
        self.assertEqual(router.collective_abstentions, 1)

    def test_static_is_original_navigation_with_zero_prior(self):
        store, index = self.make()
        router = AdaptiveRouter(store, index, ("a",), "static", CFG, 42)
        self.assertEqual(router.search([1., 0., 0.], budget=3, k=2),
                         router.navigator.search([1., 0., 0.], budget=3, k=2))

    def test_budget_cannot_remove_semantic_member_of_backbone(self):
        store, index = self.make()
        tree = routing_tree(index)
        # Tight budget: exactly n-1 edges, including semantic tree members.
        view = pruned_view(store, store.edges, backbone=tree, edge_budget=3)
        self.assertEqual(len(view.edges), 3)
        self.assertEqual(coverage(view, ("a",))["components"], 1)

    def test_operational_adjacency_is_cached_until_store_changes(self):
        store, index = self.make()
        nav = OperationalNavigator(store, index, ("a",))
        cached = nav._adjacency
        nav.search([1., 0., 0.], k=2, budget=3)
        self.assertIs(nav._adjacency, cached)
        from dataclasses import replace
        edge = next(iter(store.edges.values()))
        store.commit(edges=[replace(edge, weight=0.)], expected_version=store.version)
        nav.search([1., 0., 0.], k=2, budget=3)
        self.assertIsNot(nav._adjacency, cached)
