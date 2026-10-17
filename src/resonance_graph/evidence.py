"""Inspección de observaciones; scores y soporte no son probabilidades."""
from .model import EdgeKey, RelationKind, integer


def inspect_relation(store, a, b, kind=RelationKind.SEMANTIC, minimum_support=3, directed=False):
    integer(minimum_support, 1)
    kind = RelationKind(kind)
    if a not in store.nodes or b not in store.nodes:
        raise KeyError("Entidad no declarada")
    edge = store.edges.get(EdgeKey(a, b, kind, directed))
    result = {"kind": kind.value, "state": "evidencia_insuficiente", "affinity": None,
              "support": 0, "collective_support": 0, "sources": [], "next_observation": None}
    if edge is None:
        result["next_observation"] = "Medir contenido o actividad de la pareja con procedencia verificable."
        return result
    result.update(affinity=edge.affinity, sources=[item.source_ref for item in edge.evidence])
    if not store.current(edge):
        result.update(state="obsoleta_por_revision", next_observation="Reevaluar la relación con las revisiones actuales.")
        return result
    support = sum(item.observations for item in edge.evidence if not item.collective)
    collective = sum(item.observations for item in edge.evidence if item.collective)
    result.update(support=support, collective_support=collective)
    if kind == RelationKind.SEMANTIC and support:
        result["state"] = "similaridad_observada"
    elif kind == RelationKind.USAGE and support >= minimum_support:
        result["state"] = "uso_observado"
    else:
        result["next_observation"] = ("Una ruta o peso de transmisión no demuestra relación semántica."
                                      if kind in (RelationKind.ROUTING, RelationKind.TRANSMISSION)
                                      else f"Registrar al menos {max(0, minimum_support-support)} observaciones fuera de eventos colectivos.")
    return result
