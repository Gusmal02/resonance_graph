"""Estado inmutable, actualizaciones atómicas y fase cuaterniónica pasiva."""
from dataclasses import dataclass, replace
from enum import Enum
import math
from types import MappingProxyType
from threading import RLock


def vector(values, length=None, nonzero=False):
    result = tuple(float(v) for v in values)
    if not result or (length is not None and len(result) != length):
        raise ValueError("Dimensión inválida")
    if not all(math.isfinite(v) for v in result):
        raise ValueError("Estado no finito")
    if nonzero and math.hypot(*result) <= 1e-12:
        raise ValueError("Vector de norma cero")
    return result


def integer(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("Entero inválido")
    return value


def identity(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Identidad vacía")
    return value


def hamilton(a, b):
    aw, ax, ay, az = vector(a, 4)
    bw, bx, by, bz = vector(b, 4)
    return (aw*bw-ax*bx-ay*by-az*bz, aw*bx+ax*bw+ay*bz-az*by,
            aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw)


def mean_phase(phases):
    phases = tuple(vector(q, 4) for q in phases)
    if not phases:
        return None
    average = tuple(math.fsum(q[d] for q in phases) / len(phases) for d in range(4))
    norm = math.hypot(*average)
    # Fases antipodales canceladas no definen una dirección colectiva.
    return None if norm <= 1e-12 else tuple(v / norm for v in average)


class RelationKind(str, Enum):
    SEMANTIC = "semantic"
    USAGE = "usage"
    TRANSMISSION = "transmission"
    ROUTING = "routing"


@dataclass(frozen=True)
class Activity:
    timestamp: float
    context: str

    def __post_init__(self):
        if not math.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("Timestamp inválido")
        identity(self.context)


@dataclass(frozen=True)
class NodeState:
    node_id: str
    source_revision: int
    x: tuple
    source_ref: str
    z: tuple | None = None
    q: tuple = (1., 0., 0., 0.)
    omega: tuple = (0., 0., 0.)
    activity: tuple = ()

    def __post_init__(self):
        identity(self.node_id)
        identity(self.source_ref)
        integer(self.source_revision)
        x = vector(self.x, nonzero=True)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "z", x if self.z is None else vector(self.z, len(x)))
        q = vector(self.q, 4, nonzero=True)
        if abs(math.hypot(*q) - 1.) > 1e-9:
            raise ValueError("q debe pertenecer a S³")
        object.__setattr__(self, "q", q)
        object.__setattr__(self, "omega", vector(self.omega, 3))
        activity = tuple(self.activity)
        if not all(isinstance(event, Activity) for event in activity):
            raise ValueError("Actividad no tipada")
        object.__setattr__(self, "activity", activity)


@dataclass(frozen=True)
class EdgeKey:
    a: str
    b: str
    kind: RelationKind = RelationKind.SEMANTIC
    directed: bool = False

    def __post_init__(self):
        identity(self.a)
        identity(self.b)
        if self.a == self.b:
            raise ValueError("Autoarista no permitida")
        object.__setattr__(self, "kind", RelationKind(self.kind))
        if not isinstance(self.directed, bool):
            raise ValueError("Dirección no booleana")
        if self.kind == RelationKind.SEMANTIC and self.directed:
            raise ValueError("Afinidad semántica simétrica")
        if not self.directed and self.a > self.b:
            a, b = self.b, self.a
            object.__setattr__(self, "a", a)
            object.__setattr__(self, "b", b)


@dataclass(frozen=True)
class EvidenceItem:
    record_id: str
    source_ref: str
    timestamp: float
    observations: int = 1
    collective: bool = False

    def __post_init__(self):
        identity(self.record_id)
        identity(self.source_ref)
        integer(self.observations, 1)
        if not math.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("Timestamp inválido")
        if not isinstance(self.collective, bool):
            raise ValueError("Contexto colectivo inválido")


@dataclass(frozen=True)
class EdgeState:
    key: EdgeKey
    source_revisions: tuple
    affinity: float
    weight: float
    method: str
    evidence: tuple = ()

    def __post_init__(self):
        if not isinstance(self.key, EdgeKey):
            raise ValueError("Clave de arista inválida")
        revisions = tuple(self.source_revisions)
        if len(revisions) != 2:
            raise ValueError("Revisiones inválidas")
        for revision in revisions:
            integer(revision)
        object.__setattr__(self, "source_revisions", revisions)
        if not math.isfinite(self.affinity) or not -1 <= self.affinity <= 1:
            raise ValueError("Afinidad inválida")
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ValueError("Peso inválido")
        identity(self.method)
        evidence = tuple(self.evidence)
        if not all(isinstance(item, EvidenceItem) for item in evidence):
            raise ValueError("Evidencia no tipada")
        if len({item.record_id for item in evidence}) != len(evidence):
            raise ValueError("Evidencia duplicada")
        object.__setattr__(self, "evidence", evidence)


@dataclass(frozen=True)
class ArcView:
    version: int
    kind: RelationKind
    arcs: tuple


@dataclass(frozen=True)
class Receipt:
    version_before: int
    version_after: int
    node_ids: tuple
    edge_keys: tuple


class GraphStore:
    def __init__(self):
        self._nodes, self._edges = {}, {}
        self._version = 0
        self._lock = RLock()

    @property
    def version(self):
        return self._version

    @property
    def nodes(self):
        return MappingProxyType(self._nodes)

    @property
    def edges(self):
        return MappingProxyType(self._edges)

    def commit(self, *, nodes=(), edges=(), expected_version):
        with self._lock:
            return self._commit(nodes=nodes, edges=edges, expected_version=expected_version)

    def _commit(self, *, nodes=(), edges=(), expected_version):
        integer(expected_version)
        if expected_version != self.version:
            raise ValueError("Versión de escritura obsoleta")
        nodes, edges = tuple(nodes), tuple(edges)
        if not all(isinstance(n, NodeState) for n in nodes) or not all(isinstance(e, EdgeState) for e in edges):
            raise ValueError("Actualización no tipada")
        if len({n.node_id for n in nodes}) != len(nodes) or len({e.key for e in edges}) != len(edges):
            raise ValueError("Identidad duplicada en la transacción")
        new_nodes, new_edges = dict(self._nodes), dict(self._edges)
        for node in nodes:
            old = new_nodes.get(node.node_id)
            if old:
                if node.source_revision < old.source_revision:
                    raise ValueError("Revisión retrocedida")
                if node.source_revision == old.source_revision and (node.x != old.x or node.source_ref != old.source_ref):
                    raise ValueError("Contenido cambiado sin revisión nueva")
            new_nodes[node.node_id] = node
        if len({len(n.x) for n in new_nodes.values()}) > 1:
            raise ValueError("Dimensiones semánticas incompatibles")
        for edge in edges:
            if edge.key.a not in new_nodes or edge.key.b not in new_nodes:
                raise ValueError("Extremo de arista ausente")
            revisions = (new_nodes[edge.key.a].source_revision, new_nodes[edge.key.b].source_revision)
            if revisions != edge.source_revisions:
                raise ValueError("Evidencia de arista obsoleta")
            new_edges[edge.key] = edge
        before = self.version
        if nodes or edges:
            self._nodes, self._edges = new_nodes, new_edges
            self._version += 1
        return Receipt(before, self.version, tuple(sorted(n.node_id for n in nodes)), tuple(e.key for e in edges))

    def current(self, edge):
        with self._lock:
            return edge.source_revisions == (self._nodes[edge.key.a].source_revision,
                                              self._nodes[edge.key.b].source_revision)

    def arc_view(self, kind=RelationKind.SEMANTIC):
        with self._lock:
            return self._arc_view(kind)

    def _arc_view(self, kind):
        kind = RelationKind(kind)
        arcs = []
        for key, edge in self._edges.items():
            if key.kind != kind or not self.current(edge):
                continue
            arcs.append((key.a, key.b, edge.weight))
            if not key.directed:
                arcs.append((key.b, key.a, edge.weight))
        return ArcView(self.version, kind, tuple(sorted(arcs)))

    def neighbors(self, node_id, kind=RelationKind.SEMANTIC):
        if node_id not in self._nodes:
            raise KeyError(node_id)
        view = self.arc_view(kind)
        return tuple(sorted(((dst, weight) for src, dst, weight in view.arcs if src == node_id and weight > 0),
                            key=lambda item: (-item[1], item[0])))

    def advance_phase(self, dt):
        with self._lock:
            return self._advance_phase(dt)

    def _advance_phase(self, dt):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("dt inválido")
        if dt == 0:
            return Receipt(self.version, self.version, (), ())
        updated = []
        for node in self._nodes.values():
            speed = math.hypot(*node.omega)
            angle = .5 * speed * dt
            rotation = (1., 0., 0., 0.) if speed <= 1e-12 else (
                math.cos(angle), *(math.sin(angle) * v / speed for v in node.omega))
            q = hamilton(rotation, node.q)
            norm = math.hypot(*q)
            updated.append(replace(node, q=tuple(v / norm for v in q)))
        return self.commit(nodes=updated, expected_version=self.version)

    def to_dict(self):
        with self._lock:
            return self._to_dict()

    def _to_dict(self):
        nodes = [{"node_id": n.node_id, "source_revision": n.source_revision, "source_ref": n.source_ref,
                  "x": list(n.x), "z": list(n.z), "q": list(n.q), "omega": list(n.omega),
                  "activity": [vars(event) for event in n.activity]} for _, n in sorted(self._nodes.items())]
        edges = [{"a": e.key.a, "b": e.key.b, "kind": e.key.kind.value, "directed": e.key.directed,
                  "source_revisions": list(e.source_revisions), "affinity": e.affinity,
                  "weight": e.weight, "method": e.method, "evidence": [vars(item) for item in e.evidence]}
                 for _, e in sorted(self._edges.items(), key=lambda item: (item[0].kind.value, item[0].a, item[0].b, item[0].directed))]
        return {"schema": 1, "version": self.version, "nodes": nodes, "edges": edges}

    @classmethod
    def from_dict(cls, snapshot):
        if snapshot.get("schema") != 1:
            raise ValueError("Esquema incompatible")
        integer(snapshot["version"])
        store = cls()
        nodes = [NodeState(**{**n, "activity": tuple(Activity(**ev) for ev in n["activity"])}) for n in snapshot["nodes"]]
        store.commit(nodes=nodes, expected_version=0)
        edges = {}
        for raw in snapshot["edges"]:
            key = EdgeKey(raw["a"], raw["b"], raw["kind"], raw["directed"])
            edge = EdgeState(key, raw["source_revisions"], raw["affinity"], raw["weight"], raw["method"],
                             tuple(EvidenceItem(**ev) for ev in raw["evidence"]))
            if key in edges or key.a not in store.nodes or key.b not in store.nodes:
                raise ValueError("Arista duplicada o extremos ausentes")
            if any(r > store.nodes[n].source_revision for r, n in zip(edge.source_revisions, (key.a, key.b))):
                raise ValueError("Revisión futura de arista")
            edges[key] = edge
        store._edges = edges
        store._version = snapshot["version"]
        return store
