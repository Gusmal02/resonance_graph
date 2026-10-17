# Guía técnica — Resonance Graph0.1.0

## Alcance y estructura

Biblioteca Python, con diseño híbrido: un mismo contenido de referencia puede consultarse con prioridades estáticas o adaptativas. No requiere servidor, encoder ni LLM en el núcleo. El proyecto anfitrión proporciona embeddings y conserva los textos correspondientes a cada ID.

```text
src/resonance_graph/
  model.py            Estados, revisiones, transacciones y relaciones tipadas
  semantic_graph.py   Índice coseno, construcción de aristas y búsqueda
  navigation.py       Recorrido con presupuesto
  operational.py      Navegación operativa, backbone y vistas de poda
  adaptation.py       Prioridades estáticas, escalares, z y fases q
  evidence.py         Inspección de relaciones y procedencia
  projection.py       Proyección experimental separada del contenido
  demonstrator.py     Integración de contratos del núcleo
tests/                Pruebas portadas de contratos, recuperación y adaptación
examples/             Ejemplo autónomo con vectores sintéticos
docs/                 Reproducción, evaluación y procedencia del código
```

El paquete importable es `resonance_graph`; el nombre de distribución es `resonance-graph`. Los módulos internos se portaron desde la implementación independiente evaluada sin cambiar su algoritmo. La distribución nueva no sustituye ni modifica los archivos de investigación originales.

## Datos y significado

`NodeState` contiene identidad, revisión, referencia fuente y vector de contenido `x`, además de campos de estado. `GraphStore` aplica transacciones con versión esperada. No permite modificar contenido o referencia de un nodo sin aumentar su revisión. Las aristas conservan revisiones de sus extremos: si una revisión cambia, el vínculo anterior deja de ser vigente hasta revalidarse.

`RelationKind` distingue `semantic`, `usage`, `transmission` y `routing`. Una arista de navegación no se convierte en evidencia conceptual por existir. Los candidatos creados por coseno llevan evidencia del cálculo de afinidad, no una demostración de relación causal o una cita textual explicativa.

`build_graph(ids, vectors, edge_budget=..., candidate_k=...)` normaliza para comparar, elige candidatos por coseno y protege vecinos de primer rango dentro del presupuesto. El presupuesto debe admitir los candidatos y su cobertura; una configuración incompatible falla explícitamente. Pesos negativos se truncan a cero para el recorrido; esto no convierte afinidad negativa en una contradicción documental. La construcción k-NN no garantiza por sí sola conectividad global. `routing_tree` y `pruned_view` permiten construir vistas operativas diferenciadas; no se añaden automáticamente al usar `build_graph`.

## Consulta, feedback e integración

`AdaptiveRouter(store, index, entries, mode, config, seed)` acepta `static`, `recency`, `scalar`, `unanchored`, `anchored`, `q_frozen` y `q_active`.

- `static`: referencia sin prior adaptativo.
- `recency`/`scalar`: prioridad basada en actividad normalizada.
- `anchored`/`unanchored`: vector operativo z; el anclado limita el desplazamiento respecto de x.
- `q_frozen`/`q_active`: fases de cuatro componentes, respectivamente fijas o actualizadas con feedback y acoplamiento vecinal.

La implementación ofrece esas políticas dentro del mismo motor; no mezcla q y z en una política conjunta. En `AdaptiveRouter`, los arrays adaptativos viven en el router, separados de los campos del `NodeState`. El feedback no modifica x ni publica nuevas relaciones semánticas.

`search(query_vector, k=..., budget=...)` devuelve `SearchResult`: `hits` con ID/score, nodos puntuados, nodos expandidos y agotamiento del recorrido. El presupuesto limita nodos puntuados, no tokens ni coste monetario. El prior influye en qué candidatos se exploran; el ranking final utiliza coseno contra x. Pueden devolverse menos de k resultados si el recorrido no alcanza más nodos. Los empates utilizan identidad y redondeo controlados.

`feedback(query_vector, clicked_ids)` registra uso explícito. Los IDs deben ser del índice; corresponde al proyecto anfitrión exigir que hayan sido entregados, autorizados o elegidos realmente por el usuario. No usar respuestas del evaluador como feedback. No equivale a certificar que la fuente sea verdadera.

Para un agente, una integración típica es: consulta→vector→búsqueda→resolver IDs a textos→interpretar pistas→verificar citas y límites→registrar selección útil. La biblioteca devuelve IDs y afinidades; no genera por sí misma explicaciones, citas literales, descubrimientos o respuestas en lenguaje natural. Esa capa pertenece al agente o aplicación.

## Actualizaciones, persistencia y operación

`GraphStore.to_dict()` y `GraphStore.from_dict(...)` permiten serializar el grafo. La aplicación elige dónde y cómo guardar el JSON. **No guardan los arrays aprendidos del `AdaptiveRouter`**: no presentar guardar el store como un checkpoint completo de sesión. Esta versión no expone aún un formato público estable de checkpoint q/z.

Tras cambiar el contenido, reconstruir índice y router con las revisiones nuevas; no reutilizar un router con snapshots x/z anteriores esperando que actualice el contenido automáticamente. El store protege transacciones con bloqueo; el router muta arrays y no ofrece garantía de uso concurrente: usar una instancia por sesión o sincronizar externamente.

Las entradas, vectores de documentos y consultas deben tener idéntica dimensión y proceder del mismo encoder/preprocesado. Guardar fuera del grafo: ID, texto, fuente, revisión, hash, localizadores y permisos. La elección del encoder y del chunking corresponde al anfitrión.

## Complejidad y dependencias

Python≥3.11, NumPy≥2,<3 y NetworkX≥3,<4. Las operaciones exactas por coseno y la generación de candidatos tienen coste cuadrático en el tamaño del corpus; `routing_tree` también construye comparaciones globales. No es un índice ANN para millones de elementos. La búsqueda tiene presupuesto de puntuación, pero los priors calculan sobre arrays globales; ese presupuesto no limita todo el trabajo a O(budget). El aprendizaje q recorre nodos y vecindades.

No se incluyen Transformers, Torch, modelos, PDFs, credenciales ni un servidor HTTP. El núcleo funciona localmente. Validación de permisos, aislamiento entre usuarios y autenticación son responsabilidades del anfitrión.

## Resultados y reproducción

Ver [evaluación](docs/evaluation.md) para los resultados completos resumidos, condiciones, discrepancias de revisión y separación entre contribución de z y q. Ver [reproducción](docs/reproducibility.md) para entorno, instalación, ejecución y salidas esperadas. La demo y los tests se pueden reproducir sin documentos privados; las misiones históricas completas requieren corpus y artefactos adicionales que no se publican aquí.

## Licencia y madurez

Versión alfa0.1.0: contrato de integración documentado, tests y ejemplo ejecutable. El código original de la biblioteca se distribuye bajo [Apache 2.0](LICENSE). Las dependencias y los contenidos de terceros conservan sus licencias y derechos respectivos. No se publica en PyPI con este trabajo.
