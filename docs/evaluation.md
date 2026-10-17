# Evaluación: exploración acumulativa y utilidad de las pistas

## Diseño y resultado destacado

Se ejecutaron ocho investigaciones independientes de tres rondas sobre dos misiones: diseñar una memoria investigadora y separar navegación de prueba documental. Cada entrega debía conectar al menos cuatro familias de fuentes, conservar hipótesis rivales, incorporar nuevas condiciones, responder a un desafío adversarial y entregar un prototipo ejecutable.

El hallazgo positivo más concreto fue que la adaptación z cambió dos búsquedas y entregó dos fuentes nuevas que el investigador utilizó después: un pasaje de ecuaciones sobre condiciones de existencia/unicidad y otro que permitía auditar una afirmación categórica basada en patrones. El agente explicó el puente y sus límites. La relación entre el primer pasaje y la gestión de evidencia se utilizó como analogía de diseño, no como transferencia automática de un teorema.

El núcleo no redactó esas interpretaciones: las hizo el agente investigador sobre los resultados recibidos.

## Condiciones iguales

- 342 unidades canónicas, 21 fuentes, embeddings originales de768 dimensiones y1955 aristas.
- Mismo grafo, corpus, entradas, configuración inicial y modelo económico de investigador para cada modalidad.
- Hasta60 nodos puntuados por búsqueda, seis fragmentos de160 palabras; hasta18 acciones y20.000 palabras serializadas por misión.
- Mínimo dos consultas por ronda, con libertad para elegir consultas y pistas; sin búsqueda léxica alternativa que evitara el router.
- Notas acumulativas disponibles por igual; feedback basado en selección y citas reales, no en respuestas del evaluador.
- Semilla710. Configuración igual a `DEFAULT_CONFIG` de esta distribución.

Los investigadores tuvieron contextos separados. Dos revisores frescos evaluaron paquetes anónimos, sin correspondencia de métodos. La adjudicación final contrastó desacuerdos con texto y ejecución. El investigador podía ver diagnósticos del motor, por lo que no se afirma cegamiento perfecto de esa etapa.

## Resultados del producto completo

Una misión aprobaba con al menos14/16, sin bloqueadores graves y las nueve comprobaciones ejecutables correctas. La rúbrica incluía soporte, diversidad funcional, límites, rivales, operación, tiempo/topología, costes y revisión adversarial. La regla se fijó antes de consultar resultados.

| Modalidad | Misiones aprobadas | Casos ejecutables correctos |
|---|---:|---:|
| Estática |1 de2 |17 de18 |
| q aprendida |0 de2 |16 de18 |
| Misma q inicial congelada |2 de2 |18 de18 |
| z anclada |1 de2 |17 de18 |

Los cuatro fallos ejecutables fueron defectos de contabilidad de presupuesto en los prototipos escritos por los investigadores: declaraban gasto positivo ante presupuesto cero. Todos rechazaron universalidad sin prueba, premisa ausente, evidencia obsoleta y fuente incierta, preservaron historial y admitieron un caso positivo válido. La prueba de orden alternativo de ruta conservó estatus.

En la propuesta de una misión q congelada apareció una disyunción ambigua en la definición de apoyo. El código y otras reglas explícitas exigían tanto prueba como premisas, y las ejecuciones pasaron. Se penalizó claridad, sin considerarlo una aprobación efectiva indebida. Con la lectura documental más estricta de uno de los revisores, esa modalidad bajaría a1 de2 misiones. Estático frente a z seguiría1 frente a1.

Los errores de programación no se atribuyen causalmente al mecanismo del grafo. Una ejecución distinta del agente puede producir código distinto aun recibiendo las mismas pistas.

## Intervención sobre la dinámica utilizada

Después del cierre se reprodujeron exactamente las27 búsquedas de las cuatro sesiones con aprendizaje. Para cada consulta real se comparó el resultado con el mismo grafo y presupuesto al retirar el aprendizaje: q activa frente a su q inicial congelada; z anclada frente a estático.

- q:0 cambios de resultados entregados en14 búsquedas, aunque sus estados evolucionaron.
- z:2 cambios de resultados entregados en13 búsquedas. Ambos ocurrieron en la misión de memoria.

La búsqueda5 de `MI-01_4` entregó por primera vez el pasaje `u:6f9cf8c942a818f70221e7df4a7c966e` sobre condiciones de aplicabilidad de ecuaciones. La búsqueda9 entregó por primera vez `u:1d3efce015a20e5d02eb3b60da349307`, útil para auditar el salto desde patrones a afirmación universal. Ambos quedaron citados en la nota final y la propuesta. El control estático no devolvía esos pasajes en esas consultas respectivas.

Esto identifica pistas efectivamente incorporadas, no solo diferencias de ranking. No representa el historial completo de preguntas que otro agente habría formulado en un mundo alternativo.

## Lectura para integradores

La estructura sirve como soporte operativo de exploración: entrega candidatos que un agente interpreta, cruza y limita. La modalidad z mostró una contribución localizada; q no cambió las pistas recibidas en estas misiones. El resultado global estático/z fue empate. La prueba comparó variantes del grafo, no un agente sin grafo ni todos los sistemas RAG.

El corpus histórico es un subconjunto de las extracciones, no la totalidad de los PDF. Contiene diferencias de calidad, afirmaciones que requieren auditoría y fórmulas extraídas con degradación tipográfica. Las citas estructuradas se comprobaron contra rangos entregados: eso acredita procedencia textual, no corrección científica. Los resultados no separan el efecto de cambiar chunking porque este se mantuvo igual entre métodos.

## Evidencias incluidas y repetición

`results/` incluye copias de los resúmenes estructurados originales: `adjudication.json`, `dynamics_audit.json`, `operational_results.json`, `fixture_results.json` y ambas revisiones independientes. Se conservan los desacuerdos originales; no deben confundirse con la adjudicación. Una revisión automática propuso bloqueadores que no estaban respaldados por las ejecuciones; se rechazaron con justificación en `adjudication.json`.

No se distribuyen aquí las páginas extraídas ni el encoder original. Para repetir las misiones históricas desde cero harían falta el pool canónico y grafo congelados, el modelo y preprocesado originales, misiones/rúbrica previas, motor de sesiones, agentes aislados, estados, citas, propuestas y protocolo de revisión. La demo pública no pretende sustituir esa repetición. Los tests del repositorio sí verifican los contratos del núcleo sin ese material.

El código adaptativo portado puede contrastarse con la huella registrada en `code_provenance.json`. Los costes textuales históricos son palabras serializadas, no tokens facturados ni precios; los tiempos de herramienta no incluyen todo el trabajo del agente.
