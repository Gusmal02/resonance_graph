"""Resonance Graph: reusable graph exploration primitives."""
from types import MappingProxyType
from .model import Activity, NodeState, EdgeKey, EdgeState, EvidenceItem, GraphStore, RelationKind
from .semantic_graph import CosineIndex, Hit, SearchResult, build_graph, navigate
from .navigation import GraphNavigator
from .operational import OperationalNavigator
from .adaptation import AdaptiveRouter
from .evidence import inspect_relation

__version__ = "0.1.0"
DEFAULT_CONFIG = MappingProxyType({
    "learning_rate": .15, "anchor": .08, "drift_cap": .25,
    "decay": .9, "routing_prior": .1, "phase_coupling": .1, "phase_dt": .1,
})
__all__ = [
    "Activity", "NodeState", "EdgeKey", "EdgeState", "EvidenceItem", "GraphStore", "RelationKind",
    "CosineIndex", "Hit", "SearchResult", "build_graph", "navigate", "GraphNavigator",
    "OperationalNavigator", "AdaptiveRouter", "inspect_relation", "DEFAULT_CONFIG",
]
