"""Navegación con caché derivada e invalidación por versión."""
import heapq
import numpy as np
from .semantic_graph import normalize_rows, Hit, SearchResult


class GraphNavigator:
    def __init__(self, store, index, entry_points):
        self.store, self.index = store, index
        self.entries = tuple(dict.fromkeys(entry_points))
        self._version = -1
        self._adjacency = {}
        self._refresh()

    def _refresh(self):
        if self.index._store is not self.store or set(self.store.nodes) != set(self.index.ids):
            raise ValueError("Grafo e índice desalineados")
        if any(self.store.nodes[n].source_revision != self.index._revisions[n] for n in self.index.ids):
            raise ValueError("Índice de contenido obsoleto")
        if any(n not in self.store.nodes for n in self.entries) or not self.entries:
            raise ValueError("Entradas inválidas")
        if self._version != self.store.version:
            adjacency = {node_id: [] for node_id in self.index.ids}
            for src, dst, weight in self.store.arc_view().arcs:
                if weight > 0:
                    adjacency[src].append((dst, weight))
            self._adjacency = {n: tuple(dst for dst, w in sorted(neighbors, key=lambda item: (-round(item[1], 12), item[0])))
                               for n, neighbors in adjacency.items()}
            self._version = self.store.version

    def search(self, query, *, k=10, budget=90):
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in (k, budget)):
            raise ValueError("k/presupuesto inválido")
        self._refresh()
        if len(self.entries) > budget:
            raise ValueError("Entradas fuera de presupuesto")
        q = normalize_rows([query])[0]
        if len(q) != self.index.dimensions:
            raise ValueError("Dimensión incompatible")
        scores, queue, expanded = {}, [], set()
        def evaluate(nodes):
            if not nodes:
                return
            positions = [self.index.position[n] for n in nodes]
            values = np.clip(self.index._matrix[positions] @ q, -1., 1.)
            for node_id, score in zip(nodes, values):
                scores[node_id] = float(score)
                heapq.heappush(queue, (-round(float(score), 12), node_id))
        evaluate(self.entries)
        limit = min(budget, len(self.index.ids))
        while queue and len(scores) < limit:
            _, node_id = heapq.heappop(queue)
            expanded.add(node_id)
            remaining = limit - len(scores)
            evaluate([n for n in self._adjacency[node_id] if n not in scores][:remaining])
        order = sorted(scores, key=lambda n: (-round(scores[n], 12), n))[:k]
        return SearchResult(tuple(Hit(n, scores[n]) for n in order), len(scores), len(expanded), not queue)
