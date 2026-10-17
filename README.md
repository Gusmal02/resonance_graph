# Grafo Resonante

**Un mapa de conexiones para mirar tus documentos desde otros ángulos.**

Una idea útil no siempre está en el documento que esperabas. Puede aparecer en otra disciplina, en una condición que nadie había revisado o en una explicación que contradice la primera impresión.

Grafo Resonante ayuda a explorar esos caminos. Organiza contenidos como una red de relaciones para que una persona, una aplicación o un agente de inteligencia artificial pueda encontrar pistas, seguir conexiones y volver a sus fuentes.

## Más que encontrar una respuesta

Imagina una biblioteca donde, además de encontrar un libro, puedes descubrir qué otros libros te ayudan a entenderlo, ponerlo a prueba o aplicarlo de otra manera.

Eso es lo que propone este proyecto: **convertir una colección de contenidos en un espacio de exploración**. La cercanía entre piezas abre una pregunta; su procedencia permite investigarla.

Puede servir para:

- Explorar documentos de temas distintos y detectar conexiones que merecen una segunda mirada.
- Dar a un agente de IA pistas y contexto que pueda contrastar, en lugar de limitarse a una respuesta aislada.
- Organizar conocimiento con referencias, revisiones y relaciones diferenciadas.
- Reutilizar una red de contenidos en proyectos propios sin depender de una plataforma cerrada.

## Una red estable que también puede adaptarse

La biblioteca reúne navegación estable y adaptación dentro del mismo núcleo. Puedes explorar una estructura de referencia o hacer que la experiencia de uso influya en las prioridades del recorrido, conservando separado el contenido original.

Tú eliges el corpus, las representaciones y cómo se integra con tu aplicación. No exige un proveedor de IA, una clave de API ni un servicio remoto para ejecutar el núcleo.

## Lo más destacado de las pruebas

En una prueba de investigación de tres rondas, ocho investigadores asistidos trabajaron sobre342 unidades de21 fuentes. Produjeron propuestas, revisaron sus decisiones ante nuevas condiciones y entregaron prototipos verificables.

Entre las conexiones exploradas estuvieron las condiciones de validez de ecuaciones y la revisión de afirmaciones; la comprobación de componentes en física y la auditoría de premisas; y los límites de mantener conocimiento extenso en disciplinas distintas.

La adaptación de una de las modalidades cambió dos búsquedas y aportó dos fuentes nuevas que el investigador incorporó a su trabajo final. **El resultado valioso fue una pista encontrada, interpretada y vinculada a evidencia**, no solo una lista más larga de coincidencias.

Los resultados y su alcance están descritos en [technical.md](technical.md) y [el informe de evaluación](docs/evaluation.md).

## Pruébalo en tu proyecto

Necesitas Python3.11 o posterior. Desde la carpeta descargada del repositorio:

```bash
python -m pip install .
python examples/quickstart.py
```

El ejemplo es pequeño, determinista y no descarga modelos. Muestra cómo construir la red, consultarla y registrar retroalimentación. Para documentos reales, tu aplicación aporta los textos y sus representaciones numéricas con un mismo modelo.

Para integrarlo desde Python:

```python
from resonance_graph import AdaptiveRouter, DEFAULT_CONFIG, build_graph

store, index = build_graph(
    ["idea-a", "idea-b", "idea-c"],
    [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    edge_budget=3,
    candidate_k=2,
)
explorer = AdaptiveRouter(store, index, ["idea-a"], "anchored", dict(DEFAULT_CONFIG), seed=710)
result = explorer.search([1.0, 0.2], k=2, budget=3)
print([hit.node_id for hit in result.hits])
```

## Documentación

- [Guía técnica e integración](technical.md).
- [Reproducción paso a paso, sin contexto previo](docs/reproducibility.md).
- [Resultados y trazabilidad de la evaluación](docs/evaluation.md).
- [Historial de esta distribución](CHANGELOG.md).

Primera versión de biblioteca: **0.1.0**, bajo licencia [Apache 2.0](LICENSE). El código del núcleo se distribuye separado de los corpus personales y de los entornos de investigación. Las dependencias y los materiales de terceros conservan sus propias licencias y derechos.
