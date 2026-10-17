# Reproducción sin contexto previo

Esta guía permite instalar y verificar la biblioteca desde una máquina nueva. No requiere conocer las conversaciones ni tener rutas del equipo del autor.

## 1. Requisitos

Python3.11 o posterior, Git y acceso al índice de paquetes para la primera instalación. La demo no llama a una IA ni usa red. La instalación sí necesita descargar dependencias si no están disponibles localmente. No utiliza una GPU.

## 2. Descargar y aislar

Una vez publicado el contenido en la rama `main`:

```bash
git clone https://github.com/Gusmal02/resonance_graph.git
cd resonance_graph
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\python.exe examples/quickstart.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS:

```bash
.venv/bin/python -m pip install .
.venv/bin/python examples/quickstart.py
.venv/bin/python -m unittest discover -s tests -v
```

La instalación no es necesaria solo para leer el código, pero sí se usa en este procedimiento para comprobar los imports del paquete real. Para desarrollar se puede sustituir `pip install .` por `pip install -e .`.

## 3. Qué debe ocurrir

El ejemplo imprime un objeto JSON con `nodes=4`, `edges=4`, `mode=anchored`, dos resultados, `feedback_updates=1` y `roundtrip_graph=true`. Los resultados deben ser `revision` y `alcance`, en ese orden. Sus textos son fixtures escritos a mano; no prueban calidad semántica de un encoder. El ejemplo comprueba además presupuesto y límite de desplazamiento z.

Los tests deben terminar con `OK`, sin descargas de modelos ni archivos privados. Cubren estado/revisiones, transacciones, recuperación, navegación, poda, proyección e invariantes de adaptación. Ejecutar `python scripts/verify_release.py` con el Python del entorno comprueba también dos ejecuciones idénticas de la demo y las huellas del núcleo, y registra el resultado en `docs/build_verification.json`.

Para repetir las dependencias verificadas con Python 3.12, instalar con `python -m pip install -c requirements-reproduce.txt .`. Ese archivo fija NumPy y NetworkX del entorno de preparación; no es una afirmación de que se hayan probado todas las plataformas. La matriz de CI está configurada para Windows/Linux y Python 3.11–3.13; solo una ejecución real de CI confirmará sus combinaciones.

Para comparar la demo exactamente, ejecutar dos veces en el mismo entorno y contrastar el JSON completo. La semilla es710. Para reproducir números de coma flotante entre plataformas, registrar también versiones de Python, NumPy, NetworkX y plataforma; no asumir igualdad bit a bit entre cualquier versión.

## 4. Usar un corpus propio

1. Crear fragmentos con IDs únicos y guardar texto, fuente, revisión y localizadores.
2. Generar vectores de igual dimensión con un encoder y preprocesado fijos.
3. Construir el grafo con presupuesto que admita los candidatos y cobertura. Empezar con un corpus pequeño y revisar conectividad.
4. Elegir entradas y modo; transformar cada consulta con el mismo encoder.
5. Resolver resultados a textos. Un agente puede interpretar y justificar las relaciones usando esos pasajes.
6. Dar feedback únicamente sobre selecciones reales y conservar un registro externo de consulta, IDs, revisión, configuración y semilla.

No mezclar vectores de modelos distintos, no usar el score como probabilidad de verdad y no ejecutar código procedente del corpus. La actualización de contenido requiere reconstruir índice/router, como explica `technical.md`.

## 5. Qué es reproducible aquí y qué requiere material adicional

La construcción y navegación del núcleo, sus contratos y la demo son reproducibles desde este repositorio. Los resúmenes y evidencias numéricas de la investigación histórica se incluyen en `docs/results/`.

La repetición de las ocho investigaciones completas no está incluida como un comando autónomo: requiere el corpus canónico, vectores, encoder local, instrucciones, motor, agentes y trazas descritos en `docs/evaluation.md`. Esos materiales no se publican indiscriminadamente porque contienen documentos de terceros y rutas de trabajo personales. El repositorio no finge reconstruir las misiones con datos sintéticos.

## 6. Problemas habituales

- `ModuleNotFoundError`: utilizar el mismo Python para instalar y ejecutar; no confundir el entorno global con `.venv`.
- Error de presupuesto/candidatos: reducir aristas solicitadas o ampliar candidatos; consultar el error antes de ajustar a ciegas.
- Dimensión incompatible: consulta y documentos deben usar el mismo encoder.
- Menos resultados de los esperados: revisar presupuesto, entradas y componentes alcanzables; no es un barrido automático de todo el corpus.
