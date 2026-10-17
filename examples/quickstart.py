"""Deterministic integration demo; synthetic vectors, no encoder or network."""
import json
from resonance_graph import AdaptiveRouter, DEFAULT_CONFIG, GraphStore, build_graph


def main():
    texts = {
        "alcance": "Una conclusión depende del alcance de sus premisas.",
        "revision": "Conservar versiones permite reconstruir qué evidencia se usó.",
        "ruta": "Una ruta ayuda a explorar; la prueba requiere comprobar sus pasos.",
        "archivo": "Priorizar revisión ahorra recursos, pero exige conservar procedencia.",
    }
    # Coordinates are hand-authored fixtures, not a semantic understanding model.
    vectors = [[1., 0., 0.], [.9, .1, 0.], [.2, .8, .1], [0., .9, .1]]
    store, index = build_graph(list(texts), vectors, edge_budget=4, candidate_k=3)
    restored = GraphStore.from_dict(store.to_dict())
    assert restored.to_dict() == store.to_dict()
    explorer = AdaptiveRouter(store, index, ["alcance"], "anchored", dict(DEFAULT_CONFIG), seed=710)
    query = [1., .2, 0.]
    before = explorer.search(query, k=2, budget=4)
    explorer.feedback(query, [before.hits[0].node_id])
    after = explorer.search(query, k=2, budget=4)
    assert len(after.hits) == 2 and after.scored_nodes <= 4
    assert explorer.diagnostics()["max_z_drift"] <= DEFAULT_CONFIG["drift_cap"] + 1e-12
    print(json.dumps({
        "nodes": len(store.nodes), "edges": len(store.edges), "mode": explorer.mode,
        "hits": [{"id": h.node_id, "text": texts[h.node_id]} for h in after.hits],
        "feedback_updates": explorer.updates, "roundtrip_graph": True,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
