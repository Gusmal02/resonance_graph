"""Adaptación experimental de routing; el ranking final siempre usa x vigente."""
import heapq
import math
import numpy as np
from .model import hamilton
from .semantic_graph import normalize_rows, Hit, SearchResult
from .operational import OperationalNavigator


class AdaptiveRouter:
    MODES = ("static", "recency", "unanchored", "anchored", "q_frozen", "q_active", "scalar")

    def __init__(self, store, index, entries, mode, config, seed):
        if mode not in self.MODES:
            raise ValueError("Modo desconocido")
        self.navigator = OperationalNavigator(store, index, entries)
        self.index, self.mode, self.config = index, mode, config
        self.x = index._matrix.copy()
        self.z = self.x.copy()
        self.activity = np.zeros(len(index.ids))
        rng = np.random.default_rng(seed+9010)
        self.projection = rng.normal(size=(index.dimensions, 4))/math.sqrt(index.dimensions)
        self.q = normalize_rows(rng.normal(size=(len(index.ids), 4)))
        self.initial_q = self.q.copy()
        self.updates = 0
        self.collective_abstentions = 0

    def prior(self, query):
        if self.mode in ("recency", "scalar"):
            maximum = max(float(self.activity.max()), 1e-12)
            return self.activity/maximum
        if self.mode in ("unanchored", "anchored"):
            return normalize_rows(self.z) @ query
        if self.mode in ("q_active", "q_frozen"):
            phase = query @ self.projection
            norm = np.linalg.norm(phase)
            return np.zeros(len(self.q)) if norm <= 1e-12 else self.q @ (phase/norm)
        return np.zeros(len(self.x))

    def search(self, query, *, k=10, budget=90):
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in (k, budget)):
            raise ValueError("Presupuesto inválido")
        nav = self.navigator
        nav._refresh()
        if len(nav.entries) > budget:
            raise ValueError("Entradas fuera del presupuesto")
        query = normalize_rows([query])[0]
        if query.shape != (self.index.dimensions,):
            raise ValueError("Dimensión incompatible")
        prior = self.prior(query)
        scores, queue, expanded = {}, [], set()
        factor = self.config["routing_prior"]
        def evaluate(nodes):
            if not nodes:
                return
            positions = [self.index.position[n] for n in nodes]
            values = np.clip(self.x[positions] @ query, -1., 1.)
            for n, p, score in zip(nodes, positions, values):
                scores[n] = float(score)
                heapq.heappush(queue, (-round(float(score)+factor*float(prior[p]), 12), n))
        evaluate(nav.entries)
        limit = min(budget, len(self.index.ids))
        while queue and len(scores) < limit:
            _, n = heapq.heappop(queue)
            expanded.add(n)
            evaluate([dst for dst in nav._adjacency[n] if dst not in scores][:limit-len(scores)])
        order = sorted(scores, key=lambda n: (-round(scores[n], 12), n))[:k]
        return SearchResult(tuple(Hit(n, scores[n]) for n in order), len(scores), len(expanded), not queue)

    def feedback(self, query, clicked_ids, *, collective=False):
        # La abstención depende de metadatos observables del evento, nunca de su etiqueta evaluadora.
        if not isinstance(collective, bool):
            raise ValueError("Contexto colectivo inválido")
        positions = [self.index.position[n] for n in clicked_ids]
        query = normalize_rows([query])[0]
        if query.shape != (self.index.dimensions,):
            raise ValueError("Dimensión incompatible")
        if collective:
            self.collective_abstentions += 1
            return
        cfg = self.config
        self.activity *= cfg["decay"]
        self.activity[positions] += 1
        if self.mode in ("unanchored", "anchored"):
            self.z[positions] += cfg["learning_rate"]*(query-self.z[positions])
            if self.mode == "anchored":
                self.z += cfg["anchor"]*(self.x-self.z)
                displacement = self.z-self.x
                norm = np.linalg.norm(displacement, axis=1)
                scale = np.minimum(1., cfg["drift_cap"]/np.maximum(norm, 1e-12))
                self.z = self.x + displacement*scale[:, None]
        if self.mode == "q_active":
            target = query @ self.projection
            if np.linalg.norm(target) > 1e-12:
                target /= np.linalg.norm(target)
                old = self.q.copy()
                updated = old.copy()
                # Hamilton exact rotation + coupling projected onto tangent space of S3.
                for i, n in enumerate(self.index.ids):
                    activation = min(float(self.activity[i]), 1.)
                    omega = target[1:]*activation
                    speed = float(np.linalg.norm(omega))
                    angle = .5*speed*cfg["phase_dt"]
                    rotation = (1., 0., 0., 0.) if speed <= 1e-12 else (math.cos(angle), *(math.sin(angle)*omega/speed))
                    rotated = np.array(hamilton(rotation, old[i]))
                    neighbors = self.navigator._adjacency[n]
                    mean = np.mean(old[[self.index.position[d] for d in neighbors]], axis=0) if neighbors else old[i]
                    drive = cfg["phase_coupling"]*mean + activation*target
                    tangent = drive-rotated*float(rotated @ drive)
                    updated[i] = rotated+cfg["phase_dt"]*tangent
                self.q = normalize_rows(updated)
        self.updates += 1

    def diagnostics(self):
        return {"max_z_drift": float(np.linalg.norm(self.z-self.x, axis=1).max()),
                "max_q_norm_error": float(np.max(np.abs(np.linalg.norm(self.q, axis=1)-1))),
                "mean_phase_coherence": float(np.linalg.norm(self.q.mean(axis=0))),
                "q_changed": bool(not np.array_equal(self.initial_q, self.q)),
                "feedback_updates": self.updates, "collective_abstentions": self.collective_abstentions,
                "semantic_edges_created_by_feedback": 0}
