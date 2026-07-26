<p align="center">
  <img src="docs/assets/hero-traffic-arena.jpg" alt="Traffic Lights Arena — city grid with synchronized signals" width="100%" />
</p>

<h1 align="center">Traffic Lights Arena</h1>

<p align="center">
  <strong>Cursor Build Night · Málaga · 23 julio 2026</strong><br/>
  Control adaptativo de semáforos con <em>agentic AI</em> — exploración multiagente + explotación del mejor controlador
</p>

<p align="center">
  <img alt="Resultado" src="https://img.shields.io/badge/resultado-4%C2%BA%20de%2017-f97316?style=for-the-badge" />
  <img alt="Score final" src="https://img.shields.io/badge/score_final-18.108-111827?style=for-the-badge" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img alt="Tiempo" src="https://img.shields.io/badge/hackathon-105%20min-0f172a?style=for-the-badge" />
</p>

<p align="center">
  <a href="https://www.cursorspain.com/mlg/es">Evento</a> ·
  <a href="https://github.com/arrozet/cursor-semaphore/tree/strategy-b-optimization">Controller ganador (`strategy-b-optimization`)</a> ·
  <a href="challenge.md">Reglas del reto</a>
</p>

---

## Resultado

**4º de 17 equipos** en la clasificación final (20% mapas públicos + 80% suite sellada).

Equipo: **JORGE MAREA NO VA A GANAR** · score final **18.108**

<p align="center">
  <img src="docs/assets/leaderboard-final.png" alt="Clasificación final — 4º puesto" width="720" />
</p>

<p align="center">
  <img src="docs/assets/replay-balanced-grid.png" alt="Replay del envío en balanced-grid" width="720" />
</p>

---

## El problema

En **105 minutos**, un único archivo: `controller.py`.

El motor simula una ciudad a ticks discretos. Tú solo decides, en cada cruce, si el verde va a `NS_GREEN` o `EW_GREEN`. El resto (amarillo, all-red, mínimos) lo hace el simulador.

Lo difícil no era “mover coches”: era **generalizar**. Solo había **3 mapas públicos**; la puntuación real venía de **mapas privados desconocidos**. Un controlador overfiteado a los públicos moría en la final.

Coste por escenario (confirmado en el motor):

```text
cost = wait_ticks + 300 × unfinished
```

Cada coche que **no llega** al final del episodio suma **+300**. La agregación entre mapas es una **media geométrica**, así que un escenario malo hunde el total mucho más que uno bueno lo sube.

---

## Enfoque: exploración → explotación

El Build Night estaba pensado para **agentic AI**: problemas abstractos, APIs nuevas, poco tiempo. Nuestra estrategia no fue “una IA que resuelve el tráfico”, sino **orquestar agentes** con un loop claro.

### 1. Entender el juego

- Leer motor, scoring y restricciones
- Benchmarkear heurísticas (fixed-time, max-pressure local, sync global…)
- Descubrir que **desincronizar cruces colapsa** redes grandes → fases **sincronizadas** a nivel de red

### 2. Exploración (varios agentes en paralelo)

Una vez claro el espacio de soluciones, lanzamos agentes en **worktrees/ramas distintas**, cada uno con una tesis:

| Estrategia | Idea |
|---|---|
| A · Completion-aware | Drenaje de endgame |
| **B · Sync max-pressure** | Corredor sincronizado + histéresis / gap-out |
| C · Demand-ratio | Split por EMA de demanda |
| D · Travel / floor | Inferir travel y subir el suelo |

Los evaluábamos en:

1. los **3 mapas públicos**, y  
2. una suite propia de estrés (`maps/alesuito`, ~41 escenarios) para forzar generalización antes de pelear con los privados.

### 3. Explotación (optimizar al líder)

Cuando **B** ganó en geom pública + alesuito, la rama
[`strategy-b-optimization`](https://github.com/arrozet/cursor-semaphore/tree/strategy-b-optimization)
pasó a modo explotación:

- subir **mínimos** (la geom castiga el peor mapa)
- reducir **unfinished** (`+300` por coche)
- soft-hold / freeze tardío y **spike-gated drain** (variante U9) sin romper el suelo público

Ese controlador es el que enviamos y el que representa el resultado del equipo.

```text
PUBLIC geom  ≈ 22.983   (igual que B base)
ALL geom     ≈ 20.996   (públicos + alesuito; +527 vs B)
```

---

## Por qué importa la media geométrica

Con media aritmética puedes “compensar” un mapa malo con otro excelente.  
Con media geométrica, **el suelo manda**.

Por eso la explotación no buscaba picos en un solo escenario, sino:

- elevar `combo-4x4-sparse-slow`, `fast-travel-*`, saturados, endgame floods…
- evitar switches inútiles al final del episodio
- no dejar platoones colgados (cada unfinished duele ×300)

---

## Estructura del repo

```text
source/controller.py          # punto de entrada del reto
source/traffic_arena/         # motor + scoring
maps/alesuito/                # suite de estrés propia (generalización)
variants/                     # ablations (E, U, …)
strategy-b-optimization       # rama del controller enviado (U9 sobre B)
docs/assets/                  # capturas e imágenes del README
```

> El controller “de producción” del equipo está en la rama
> [`strategy-b-optimization`](https://github.com/arrozet/cursor-semaphore/tree/strategy-b-optimization)
> (`source/controller.py` allí = U9 spike-drain sobre Strategy B).

---

## Quick start

```bash
cd source
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --scenario balanced-grid
```

Para evaluar una batería local (públicos + sidecars bajo `maps/`):

```bash
python eval_all.py controller.py
```

---

## Stack & constraints

- Python (stdlib + NumPy)
- Un solo archivo editable en competición: el controlador
- Memoria **dentro** de un mapa; proceso limpio entre mapas
- Scoring: curva baseline→gold al cuadrado; agregación geométrica; final por familias (min de cada par)

---

## Créditos

- Evento: [Cursor Build Night Málaga](https://www.cursorspain.com/mlg/es) — *Traffic Lights Arena*
- Starter / motor: Cursor Málaga (MIT, ver `source/LICENSE`)
- Assets del viewer: Kenney (ver `source/viewer/assets/KENNEY-LICENSE.txt`)

---

<p align="center">
  <sub>Hackathon de agentic AI: agentes que exploran hipótesis distintas, humanos que eligen qué explotar, y una métrica que castiga no generalizar.</sub>
</p>
