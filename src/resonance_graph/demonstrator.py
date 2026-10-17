"""Integrador local conservador: contenido revisado y consulta exacta por defecto."""
from dataclasses import replace
import json
from .model import GraphStore, NodeState
from .semantic_graph import build_graph, CosineIndex
from .evidence import inspect_relation


class Demonstrator:
    def __init__(self):
        self.store = GraphStore()
        self.index = None

    def _rebuild(self, nodes):
        ids = sorted(nodes)
        if len(ids) < 2:
            store = GraphStore()
            store.commit(nodes=nodes.values(), expected_version=0)
        else:
            budget = min(1044, len(ids)*(len(ids)-1)//2)
            # Demostrador pequeño: pool completo evita un presupuesto imposible.
            store, _ = build_graph(ids, [nodes[n].x for n in ids], edge_budget=budget,
                                   candidate_k=len(ids)-1)
            edges = [replace(e, source_revisions=(nodes[e.key.a].source_revision, nodes[e.key.b].source_revision))
                     for e in store.edges.values()]
            store = GraphStore()
            store.commit(nodes=nodes.values(), edges=edges, expected_version=0)
        index = CosineIndex.from_store(store)
        self.store, self.index = store, index

    def ingest(self, node_id, vector, source_ref):
        if node_id in self.store.nodes:
            raise ValueError("Identidad ya existe; usar update")
        nodes = dict(self.store.nodes)
        nodes[node_id] = NodeState(node_id, 0, tuple(vector), source_ref)
        self._rebuild(nodes)

    def ingest_batch(self, records):
        nodes = dict(self.store.nodes)
        for node_id, vector, source_ref in records:
            if node_id in nodes:
                raise ValueError("Identidad duplicada")
            nodes[node_id] = NodeState(node_id, 0, tuple(vector), source_ref)
        if not nodes:
            raise ValueError("Carga vacía")
        self._rebuild(nodes)

    def retrieve(self, query, k=10):
        if self.index is None:
            raise ValueError("Sin contenido")
        return self.index.search(query, k)

    def update(self, node_id, vector, source_ref, *, expected_revision):
        old = self.store.nodes[node_id]
        if old.source_revision != expected_revision:
            raise ValueError("Revisión obsoleta")
        nodes = dict(self.store.nodes)
        nodes[node_id] = NodeState(node_id, old.source_revision+1, tuple(vector), source_ref)
        self._rebuild(nodes)

    def inspect_relation(self, a, b, **kwargs):
        result = inspect_relation(self.store, a, b, **kwargs)
        result["qualification"] = "Coseno observado no demuestra causalidad, relevancia humana ni puente semántico."
        result["calibrated_probability"] = None
        return result

    def snapshot(self):
        return self.store.to_dict()

    @classmethod
    def restore(cls, snapshot):
        demo = cls()
        demo.store = GraphStore.from_dict(snapshot)
        demo.index = CosineIndex.from_store(demo.store)
        return demo
