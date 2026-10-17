"""Poda como vista inmutable; backbone operativo, nunca evidencia semántica."""
from dataclasses import replace
import math
import networkx as nx
import numpy as np
from .model import GraphStore, RelationKind, EdgeKey, EdgeState
from .navigation import GraphNavigator


class PruningPolicy:
    def __init__(self, keys, *, low=.50, high=.55, weak_ticks=3, hysteresis=True):
        if not (math.isfinite(low) and math.isfinite(high) and low < high):
            raise ValueError("Umbrales inválidos")
        if isinstance(weak_ticks, bool) or not isinstance(weak_ticks, int) or weak_ticks < 1:
            raise ValueError("Persistencia inválida")
        self.low, self.high, self.ticks, self.hysteresis = low, high, weak_ticks, hysteresis
        self.active = set(keys)
        self.weak = {key: 0 for key in keys}

    def observe(self, scores):
        if set(scores) != set(self.weak) or not all(math.isfinite(v) and -1 <= v <= 1 for v in scores.values()):
            raise ValueError("Observaciones incompatibles")
        before = set(self.active)
        for key, score in scores.items():
            if not self.hysteresis:
                if score >= (self.low+self.high)/2:
                    self.active.add(key)
                else:
                    self.active.discard(key)
            elif key in self.active:
                self.weak[key] = self.weak[key]+1 if score < self.low else 0
                if self.weak[key] >= self.ticks:
                    self.active.remove(key)
            elif score >= self.high:
                self.active.add(key)
                self.weak[key] = 0
        return len(before ^ self.active)


def routing_tree(index):
    # Todos los scores se calculan una vez para TODOS los brazos, no solo protegido.
    scores = np.clip(index._matrix @ index._matrix.T, -1., 1.)
    graph = nx.Graph()
    graph.add_nodes_from(index.ids)
    for i, a in enumerate(index.ids):
        for j in range(i+1, len(index.ids)):
            graph.add_edge(a, index.ids[j], weight=float(scores[i, j]))
    return tuple((a, b, float(data["weight"])) for a, b, data in
                 nx.maximum_spanning_tree(graph).edges(data=True))


def pruned_view(source, retained, *, backbone=(), edge_budget=1044):
    """Devuelve nuevo store: no elimina ni muta el original; x/revisiones idénticos."""
    if not set(retained).issubset(source.edges):
        raise ValueError("Arista desconocida")
    snapshot = source.to_dict()
    snapshot["edges"] = []
    snapshot["version"] += 1
    store = GraphStore.from_dict(snapshot)
    edges = [source.edges[key] for key in retained if source.current(source.edges[key])]
    semantic_pairs = {(e.key.a, e.key.b) for e in edges}
    routes = []
    protected_keys = set()
    for a, b, affinity in backbone:
        key = EdgeKey(a, b, RelationKind.ROUTING)
        if (key.a, key.b) in semantic_pairs:
            protected_keys.add(EdgeKey(key.a, key.b))
            continue
        routes.append(EdgeState(key, (store.nodes[key.a].source_revision, store.nodes[key.b].source_revision),
                                affinity, max(affinity, 1e-6), "operational_maximum_spanning_tree", ()))
    # Las rutas cuentan en el mismo presupuesto total que las aristas semánticas.
    if len(routes)+len(protected_keys) > edge_budget:
        raise ValueError("Backbone supera presupuesto")
    # Primero TODOS los miembros del árbol, incluso los que ya son semánticos.
    edges.sort(key=lambda e: (e.key not in protected_keys, -e.weight, e.key.a, e.key.b))
    edges = edges[:max(0, edge_budget-len(routes))] + routes
    store.commit(edges=edges, expected_version=store.version)
    return store


class OperationalNavigator(GraphNavigator):
    def _refresh(self):
        previous_version = self._version
        super()._refresh()
        if previous_version == self._version:
            return
        # Unión tipada; ninguna ruta se copia al conjunto semántico.
        merged = {n: {} for n in self.index.ids}
        for a, b, weight in self.store.arc_view(RelationKind.SEMANTIC).arcs:
            if weight > 0:
                merged[a][b] = weight
        for a, b, weight in self.store.arc_view(RelationKind.ROUTING).arcs:
            if weight > 0:
                merged[a][b] = max(merged[a].get(b, 0), weight)
        self._adjacency = {n: tuple(dst for dst, w in sorted(items.items(), key=lambda item: (-round(item[1], 12), item[0])))
                           for n, items in merged.items()}


def coverage(store, entries):
    graph = nx.Graph()
    graph.add_nodes_from(store.nodes)
    for kind in (RelationKind.SEMANTIC, RelationKind.ROUTING):
        for a, b, weight in store.arc_view(kind).arcs:
            if weight > 0:
                graph.add_edge(a, b)
    reachable = set().union(*(nx.node_connected_component(graph, n) for n in entries))
    return {"components": nx.number_connected_components(graph), "unreachable_from_entries": len(graph)-len(reachable),
            "largest_component": max(map(len, nx.connected_components(graph)), default=0)}
