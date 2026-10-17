import copy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resonance_graph.model import Activity, NodeState, EdgeKey, EdgeState, EvidenceItem, GraphStore, RelationKind, hamilton, mean_phase
from resonance_graph.evidence import inspect_relation


class Contracts(unittest.TestCase):
    def fixture(self, kind=RelationKind.SEMANTIC, collective=False):
        store = GraphStore()
        nodes = [NodeState("a", 0, [1., 0.], "doc-a", omega=(0., 0., 1.)),
                 NodeState("b", 0, [0., 1.], "doc-b")]
        evidence = EvidenceItem("obs-1", "source", 1., observations=3, collective=collective)
        edge = EdgeState(EdgeKey("b", "a", kind), (0, 0), .5, .25, "measured", (evidence,))
        store.commit(nodes=nodes, edges=[edge], expected_version=0)
        return store, edge

    def test_input_alias_cannot_change_x(self):
        values = [1., 2.]
        node = NodeState("a", 0, values, "doc")
        values[0] = 999.
        self.assertEqual(node.x, (1., 2.))
        with self.assertRaises(FrozenInstanceError):
            node.x = (2., 1.)

    def test_zero_and_nonfinite_vectors_rejected(self):
        for values in ([0., 0.], [float("nan"), 1.], [float("inf"), 1.]):
            with self.assertRaises(ValueError):
                NodeState("a", 0, values, "doc")

    def test_quaternion_contract(self):
        for q in ((0., 0., 0., 0.), (2., 0., 0., 0.)):
            with self.assertRaises(ValueError):
                NodeState("a", 0, [1.], "doc", q=q)
        i, j = (0., 1., 0., 0.), (0., 0., 1., 0.)
        self.assertEqual(hamilton(i, j), (0., 0., 0., 1.))
        self.assertEqual(hamilton(j, i), (0., 0., 0., -1.))

    def test_cancelled_phase_has_no_direction(self):
        self.assertIsNone(mean_phase([(1., 0., 0., 0.), (-1., 0., 0., 0.)]))
        self.assertIsNone(mean_phase([]))

    def test_phase_steps_preserve_content_and_norm(self):
        store, _ = self.fixture()
        before = {n: state.x for n, state in store.nodes.items()}
        for _ in range(20):
            store.advance_phase(.1)
        self.assertEqual(before, {n: state.x for n, state in store.nodes.items()})
        self.assertNotEqual(store.nodes["a"].q, (1., 0., 0., 0.))
        for node in store.nodes.values():
            self.assertAlmostEqual(sum(v*v for v in node.q), 1., places=12)

    def test_invalid_step_is_atomic(self):
        store, _ = self.fixture()
        before = store.to_dict()
        with self.assertRaises(ValueError):
            store.advance_phase(float("nan"))
        self.assertEqual(before, store.to_dict())

    def test_symmetric_relation_stored_once(self):
        store, edge = self.fixture()
        self.assertEqual(EdgeKey("a", "b"), EdgeKey("b", "a"))
        self.assertEqual(len(store.edges), 1)
        self.assertEqual(store.arc_view().arcs, (("a", "b", .25), ("b", "a", .25)))
        with self.assertRaises(ValueError):
            store.commit(edges=[edge, edge], expected_version=store.version)

    def test_weight_update_has_one_owner(self):
        store, edge = self.fixture()
        old_view = store.arc_view()
        store.commit(edges=[replace(edge, weight=.9)], expected_version=store.version)
        self.assertEqual(store.neighbors("a"), (("b", .9),))
        self.assertNotEqual(old_view.version, store.arc_view().version)
        self.assertEqual(old_view.arcs[0][2], .25)

    def test_missing_endpoint_keeps_full_snapshot(self):
        store, _ = self.fixture()
        before = store.to_dict()
        extra = NodeState("c", 0, (1., 1.), "doc-c")
        bad = EdgeState(EdgeKey("c", "d"), (0, 0), .1, .1, "measured")
        with self.assertRaises(ValueError):
            store.commit(nodes=[extra], edges=[bad], expected_version=store.version)
        self.assertEqual(before, store.to_dict())

    def test_incompatible_dimensions_atomic(self):
        store, _ = self.fixture()
        before = store.to_dict()
        with self.assertRaises(ValueError):
            store.commit(nodes=[NodeState("c", 0, [1., 1., 1.], "doc")], expected_version=store.version)
        self.assertEqual(before, store.to_dict())

    def test_content_requires_new_revision(self):
        store, _ = self.fixture()
        before = store.to_dict()
        with self.assertRaises(ValueError):
            store.commit(nodes=[replace(store.nodes["a"], x=(2., 1.))], expected_version=store.version)
        self.assertEqual(before, store.to_dict())

    def test_new_revision_invalidates_old_relationship(self):
        store, _ = self.fixture()
        store.commit(nodes=[replace(store.nodes["a"], source_revision=1, x=(2., 1.))], expected_version=store.version)
        self.assertEqual(inspect_relation(store, "a", "b")["state"], "obsoleta_por_revision")
        self.assertEqual(store.arc_view().arcs, ())

    def test_stale_write_rejected(self):
        store, edge = self.fixture()
        before = store.to_dict()
        with self.assertRaises(ValueError):
            store.commit(edges=[replace(edge, weight=.5)], expected_version=0)
        self.assertEqual(before, store.to_dict())

    def test_two_writers_cannot_commit_same_expected_version(self):
        store, edge = self.fixture()
        expected = store.version
        barrier = Barrier(2)
        def writer(weight):
            barrier.wait(timeout=5)
            try:
                store.commit(edges=[replace(edge, weight=weight)], expected_version=expected)
                return "committed"
            except ValueError:
                return "stale"
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(writer, weight) for weight in (.3, .7)]
            results = [future.result(timeout=5) for future in futures]
        self.assertEqual(sorted(results), ["committed", "stale"])
        self.assertEqual(store.version, expected+1)

    def test_snapshot_round_trip_and_reordering(self):
        store, _ = self.fixture()
        state = json.loads(json.dumps(store.to_dict(), allow_nan=False))
        state["nodes"].reverse()
        restored = GraphStore.from_dict(state)
        self.assertEqual(store.to_dict(), restored.to_dict())
        store.advance_phase(.3)
        restored.advance_phase(.3)
        self.assertEqual(store.to_dict(), restored.to_dict())

    def test_snapshot_rejects_duplicate_edges(self):
        store, _ = self.fixture()
        state = store.to_dict()
        state["edges"].append(copy.deepcopy(state["edges"][0]))
        with self.assertRaises(ValueError):
            GraphStore.from_dict(state)

    def test_insufficient_support_is_not_refutation(self):
        store, _ = self.fixture(RelationKind.USAGE, collective=True)
        result = inspect_relation(store, "a", "b", RelationKind.USAGE)
        self.assertEqual(result["state"], "evidencia_insuficiente")
        self.assertEqual(result["collective_support"], 3)
        self.assertNotIn("confidence", result)

    def test_routing_is_not_semantic_evidence(self):
        store, _ = self.fixture(RelationKind.ROUTING)
        self.assertEqual(inspect_relation(store, "a", "b", RelationKind.ROUTING)["state"], "evidencia_insuficiente")
        self.assertEqual(inspect_relation(store, "a", "b")["state"], "evidencia_insuficiente")

    def test_directed_relation_has_one_arc(self):
        store, _ = self.fixture()
        edge = EdgeState(EdgeKey("b", "a", RelationKind.USAGE, True), (0, 0), .1, .2, "ordered_use", (EvidenceItem("ordered", "trace", 1., 3),))
        store.commit(edges=[edge], expected_version=store.version)
        self.assertEqual(store.arc_view(RelationKind.USAGE).arcs, (("b", "a", .2),))
        self.assertEqual(inspect_relation(store, "b", "a", RelationKind.USAGE, directed=True)["state"], "uso_observado")
        self.assertEqual(inspect_relation(store, "a", "b", RelationKind.USAGE, directed=True)["state"], "evidencia_insuficiente")


if __name__ == "__main__":
    unittest.main()
