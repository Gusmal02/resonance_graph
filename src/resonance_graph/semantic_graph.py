"""Búsqueda exacta por bloques, grafo semántico y navegación con presupuesto."""
from dataclasses import dataclass
import heapq
import math
from types import MappingProxyType
import numpy as np
from .model import GraphStore, NodeState, EdgeKey, EdgeState, EvidenceItem


def normalize_rows(vectors):
    matrix = np.array(vectors, dtype=np.float64, copy=True)
    if matrix.ndim != 2 or not len(matrix) or not np.isfinite(matrix).all():
        raise ValueError("Matriz de embeddings inválida")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms <= 1e-12):
        raise ValueError("Embedding de norma cero")
    return matrix / norms


@dataclass(frozen=True)
class Hit:
    node_id: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    hits: tuple
    scored_nodes: int
    expanded_nodes: int
    exhausted: bool


class CosineIndex:
    def __init__(self, node_ids, vectors, block_size=64):
        ids = tuple(node_ids)
        if not ids or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
            raise ValueError("Identidades inválidas o duplicadas")
        if not isinstance(block_size, int) or isinstance(block_size, bool) or block_size <= 0:
            raise ValueError("block_size inválido")
        matrix = normalize_rows(vectors)
        if len(ids) != len(matrix):
            raise ValueError("Identidades y embeddings desalineados")
        order = sorted(range(len(ids)), key=ids.__getitem__)
        self.ids = tuple(ids[i] for i in order)
        self._matrix = matrix[order].copy()
        self._matrix.flags.writeable = False
        self.position = MappingProxyType({node_id: i for i, node_id in enumerate(self.ids)})
        self.block_size = block_size
        self._store = None
        self._revisions = {}

    @classmethod
    def from_store(cls, store, block_size=64):
        ids = sorted(store.nodes)
        index = cls(ids, [store.nodes[n].x for n in ids], block_size)
        index._store = store
        index._revisions = {n: store.nodes[n].source_revision for n in ids}
        return index

    @property
    def dimensions(self):
        return self._matrix.shape[1]

    def search_batch(self, queries, k=10, exclude_ids=None):
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k inválido")
        q = normalize_rows(queries)
        if q.shape[1] != self.dimensions:
            raise ValueError("Dimensión de consulta incompatible")
        excluded = [None] * len(q) if exclude_ids is None else list(exclude_ids)
        if len(excluded) != len(q):
            raise ValueError("Exclusiones desalineadas")
        out = []
        for offset in range(0, len(q), self.block_size):
            scores = np.clip(q[offset:offset+self.block_size] @ self._matrix.T, -1., 1.)
            for local, row in enumerate(scores):
                skip = excluded[offset + local]
                if skip in self.position:
                    row[self.position[skip]] = -np.inf
                # Cuantización solo para desempates numéricos de ranking; el
                # score almacenado conserva precisión completa.
                order = np.lexsort((np.array(self.ids), -np.round(row, 12)))
                hits = tuple(Hit(self.ids[i], float(row[i])) for i in order[:min(k, len(self.ids)-(skip in self.position))])
                out.append(hits)
        return tuple(out)

    def search(self, query, k=10, exclude_id=None):
        return self.search_batch([query], k, [exclude_id])[0]

    def score(self, query, node_id):
        q = normalize_rows([query])[0]
        if len(q) != self.dimensions:
            raise ValueError("Dimensión de consulta incompatible")
        return float(np.clip(q @ self._matrix[self.position[node_id]], -1., 1.))

    def candidates(self, k=12):
        return self.search_batch(self._matrix, k, self.ids)


def build_graph(node_ids, vectors, *, edge_budget, candidate_k=12, power=1, pairs=None,
                content_vectors=None, score_space="content"):
    node_ids = tuple(node_ids)
    if not isinstance(edge_budget, int) or isinstance(edge_budget, bool) or edge_budget < 0:
        raise ValueError("Presupuesto inválido")
    if not math.isfinite(power) or power <= 0:
        raise ValueError("Potencia inválida")
    index = CosineIndex(node_ids, vectors)
    pool, protected = {}, set()
    if pairs is None:
        neighbors = index.candidates(candidate_k)
        for node_id, hits in zip(index.ids, neighbors):
            for rank, hit in enumerate(hits):
                key = tuple(sorted((node_id, hit.node_id)))
                pool[key] = hit.score
                if rank == 0:
                    protected.add(key)
        if len(protected) > edge_budget or len(pool) < edge_budget:
            raise ValueError("El presupuesto no admite cobertura y candidatos")
        remaining = sorted((key for key in pool if key not in protected), key=lambda key: (-round(pool[key], 12), key))
        chosen = sorted(protected) + remaining[:edge_budget-len(protected)]
    else:
        chosen = sorted({tuple(sorted(pair)) for pair in pairs})
        if len(chosen) != edge_budget:
            raise ValueError("Aristas de control fuera de presupuesto")
        for a, b in chosen:
            if a == b or a not in index.position or b not in index.position:
                raise ValueError("Pareja de control inválida")
            pool[(a, b)] = index.score(index._matrix[index.position[a]], b)
    store = GraphStore()
    content = vectors if content_vectors is None else content_vectors
    if len(content) != len(node_ids):
        raise ValueError("Contenido y representaciones desalineados")
    raw = {node_id: row for node_id, row in zip(node_ids, content)}
    nodes = [NodeState(node_id, 0, raw[node_id], f"embedding:{node_id}") for node_id in index.ids]
    edges = []
    for a, b in chosen:
        affinity = max(-1., min(1., float(pool[(a, b)])))
        evidence = EvidenceItem(f"embedding_pair:{a}:{b}", f"cosine_in_{score_space}", 0.)
        edges.append(EdgeState(EdgeKey(a, b), (0, 0), affinity, max(affinity, 0.) ** power,
                               f"{score_space}/positive_cosine_power_{power}", (evidence,)))
    store.commit(nodes=nodes, edges=edges, expected_version=0)
    index._store = store
    index._revisions = {n: 0 for n in index.ids}
    return store, index


def navigate(store, index, query, *, k=10, budget=90, entry_points=()):
    from .navigation import GraphNavigator
    return GraphNavigator(store, index, entry_points).search(query, k=k, budget=budget)
