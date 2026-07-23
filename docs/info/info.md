# Traffic Lights Arena — info del reto

Fuente principal: [cursorspain.com/mlg/es](https://www.cursorspain.com/mlg/es) y [challenge](https://www.cursorspain.com/mlg/es/challenge) (también EN: `/mlg/en/...`).  
Recopilado el 23.07.2026 · evento aún en fase `upcoming` (starter bloqueado).

## Resumen

| Campo | Valor |
|-------|--------|
| Evento | Cursor Build Night Málaga |
| Challenge | **01 · Traffic Lights Arena** |
| Fecha | 23 julio 2026 · Málaga, España |
| Duración | **105 minutos** (`durationSeconds: 6300`) |
| Qué haces | Programar el controlador de semáforos de una ciudad simulada |
| Archivo a tocar | **Uno solo** (el controller) |
| Lenguaje | Python · stdlib + **NumPy** |
| Acciones | Por cruce: `"NS_GREEN"` o `"EW_GREEN"` |
| Login equipo | Código tipo `MLG-XXXX` (tarjeta de mesa) |

**Pitch (ES):** Programa los semáforos de una ciudad viva. Reduce esperas, evita atascos y encuentra una estrategia que funcione aunque cambie el tráfico.

**Pitch (EN):** Control every junction in a simulated city. Move more cars, reduce waiting, adapt to maps you have never seen.

## Sitio web (mapa de páginas)

| Ruta | Contenido |
|------|-----------|
| [`/mlg/es`](https://www.cursorspain.com/mlg/es) | Landing + demos de los 3 mapas públicos + clasificación en vivo |
| [`/mlg/es/challenge`](https://www.cursorspain.com/mlg/es/challenge) | Reglas del reto (objetivo, API, score, entrega) |
| [`/mlg/es/leaderboard`](https://www.cursorspain.com/mlg/es/leaderboard) | Clasificación provisional (orden, sin scores de equipos) |
| [`/mlg/es/team`](https://www.cursorspain.com/mlg/es/team) | Login con código de equipo; envíos y replays |
| `/mlg/en/...` | Mismas páginas en inglés |

Timer en home/leaderboard muestra **01:45:00** mientras el evento no ha empezado.

## Estado del evento (API en vivo)

`GET https://www.cursorspain.com/mlg/api/v1/leaderboard` (poll cada 3s en el front):

```json
{
  "entries": [],
  "event": {
    "phase": "upcoming",
    "startsAt": null,
    "endsAt": null,
    "pausedAt": null,
    "durationSeconds": 6300,
    "remainingSeconds": 6300,
    "finalistsSelectedAt": null,
    "scoreStage": "provisional",
    "showFinalLeaderboard": false,
    "serverNow": "…"
  }
}
```

Fases vistas en el front: `upcoming` · `live` · `paused` · `finalizing` · `finished`.

Starter pack (solo cuando `phase` ∈ live/paused/finalizing/finished):

- URL: `https://www.cursorspain.com/mlg/starter/traffic-lights-arena.zip`
- Ahora: **403 Forbidden** (“Disponible al comenzar” / “Available at kickoff”)

## Objetivo

En **105 minutos**, modificar **un único archivo**: el controlador.

El **motor** se encarga de:

- fases en amarillo
- tiempos mínimos
- seguridad / transiciones

Tú solo decides **qué eje recibe el verde** en cada cruce.

## API del controlador

```python
def control(state):
    return {
        "A1": "NS_GREEN",
        "A2": "EW_GREEN",
    }
```

### `state` (documentado en el challenge)

- colas
- tiempo de espera
- fase actual
- edad de fase
- ocupación de carreteras

### Restricciones

- Memoria **sí** entre ticks **dentro de un mapa**
- Memoria **no** entre mapas (cada mapa = proceso nuevo)
- Solo stdlib Python + NumPy
- No tocar el motor de simulación

### Acciones del controller vs fases del motor

El controller pide solo verde NS/EW. En los demos públicos el motor también usa:

| Fase | Quién la controla |
|------|-------------------|
| `NS_GREEN` / `EW_GREEN` | Tu `control()` |
| `NS_YELLOW` / `EW_YELLOW` | Motor (en demos: **2 ticks**) |
| `ALL_RED` | Motor (en demos: **1 tick**) |

En el demo de `balanced-grid`, el verde efectivo típico del ciclo fijo es **~9 ticks** (mínimo aparente del motor en ese replay).

## Mapas públicos (los 3 de la home)

Definidos en el front + demos en `/mlg/replays/<id>.json` (versión replay `2`, **900 ticks** cada uno).

| ID | ES | EN | Grid | Cruces |
|----|----|----|------|--------|
| `balanced-grid` | Cuadrícula equilibrada (Equilibrada) | Balanced grid | 2×2 | A1 A2 B1 B2 |
| `northbound-morning` | Mañana hacia el norte (Norte) | Northbound morning | 3×2 | A1 A2 B1 B2 C1 C2 |
| `city-rush` | Hora punta | City rush | 3×3 | A1–A3, B1–B3, C1–C3 |

Replays de demo (copias locales en [`maps/basic/`](../../maps/basic/)):

- [`balanced-grid.json`](../../maps/basic/balanced-grid.json) · https://www.cursorspain.com/mlg/replays/balanced-grid.json
- [`northbound-morning.json`](../../maps/basic/northbound-morning.json) · https://www.cursorspain.com/mlg/replays/northbound-morning.json
- [`city-rush.json`](../../maps/basic/city-rush.json) · https://www.cursorspain.com/mlg/replays/city-rush.json
- Snapshot API: [`leaderboard.json`](./leaderboard.json) · https://www.cursorspain.com/mlg/api/v1/leaderboard

### Métricas de los demos públicos (no son baseline/gold oficiales)

Estos JSON son **replays de demostración** (controlador fijo de muestra), no los umbrales de puntuación del reto.

| Mapa | spawned | completed | unfinished | waitTicks | cost |
|------|---------|-----------|------------|-----------|------|
| balanced-grid | 963 | 955 | 8 | 13623 | **16023** |
| northbound-morning | 1250 | 1220 | 30 | 20557 | **29557** |
| city-rush | 2297 | 2246 | 51 | 52991 | **68291** |

Fórmula observada en los tres demos:

```text
cost = waitTicks + 300 * unfinished
```

Formato de frame (útil para entender la simulación):

- `vehicles`: `[id, x, y, heading]`
- `signals`: mapa cruce → fase
- `completed`, `waiting` acumulados

## Puntuación

### Por mapa

| Hito | Puntos |
|------|--------|
| Floor | 1 |
| Igualar baseline | **10.000** |
| Alcanzar o superar gold | **25.000** |
| Máximo | 25.000 |

Curva (texto oficial):

- Coste **peor** que baseline → score baja **en proporción al coste**
- Entre baseline y gold → avance **al cuadrado** (acercarse al gold pesa mucho más que una mejora pequeña)

Los valores numéricos de coste baseline/gold **por mapa** no están publicados en la web (vienen con el starter / evaluación).

### Clasificación provisional (durante el evento)

| Componente | Peso |
|------------|------|
| Media geométrica de **3 mapas públicos** | **20%** |
| Media geométrica de **6 mapas privados de validación** | **80%** |

- Se ve el **orden** provisional, **no** las puntuaciones de otros equipos
- La proyección del evento muestra solo el **total combinado cada 20 minutos**
- Leaderboard: *“ORDEN PROVISIONAL · 20% PÚBLICO + 80% VALIDACIÓN · PUNTUACIONES SOLO EN LA PROYECCIÓN”*

### Clasificación final (al cerrar entregas)

1. Se elige el **mejor envío provisional** de cada equipo (no tiene por qué ser el último)
2. Se evalúa **una sola vez** en **12 mapas finales sellados** agrupados en **6 familias**
3. Cada familia aporta el **menor** de sus dos scores
4. Las 6 familias se combinan con **media geométrica**
5. Mismo reparto **20% público / 80% privado** para el ranking final

Implicación: **generalizar** > overfittear los 3 mapas públicos.

## Entrega / workflow

```bash
python run.py                    # prueba local
python submit.py login MLG-XXXX  # una vez
python submit.py                 # envía el controller actual
```

### Límites de envío

- Máx. **20 envíos aceptados** en los 105 minutos
- **1 minuto** de cooldown entre envíos
- Reenviar **exactamente el mismo** controller → reutiliza el envío existente (**no** gasta intento ni cooldown)
- **Errores del controller sí consumen** un intento aceptado → probar en local antes

### Equipo (página `/team`)

- Campo: código `MLG-XXXX`
- Tras login: estado de envíos + abrir replay para enseñar al final

## Implicaciones estratégicas (para el agente)

1. Cambios **solo** en el archivo del controller
2. El **80%** del score provisional/final viene de mapas **no públicos** → priorizar generalización
3. Apuntar **cerca del gold**: la curva al cuadrado premia acercarse al gold más que mejoras pequeñas sobre baseline
4. Envíos escasos (20); no gastar intentos en controllers rotos
5. Cada mapa es proceso limpio → ok estado/módulo global **por mapa**, no entre mapas
6. El motor ya impone amarillo / mínimo / ALL_RED → no reinventar seguridad; decidir **cuándo** cambiar de eje

## Enlaces rápidos

- Home ES: https://www.cursorspain.com/mlg/es
- Challenge ES: https://www.cursorspain.com/mlg/es/challenge
- Challenge EN: https://www.cursorspain.com/mlg/en/challenge
- Leaderboard: https://www.cursorspain.com/mlg/es/leaderboard
- Team: https://www.cursorspain.com/mlg/es/team
- API leaderboard: https://www.cursorspain.com/mlg/api/v1/leaderboard
- Starter (al kickoff): https://www.cursorspain.com/mlg/starter/traffic-lights-arena.zip

## Qué aún no está en la web pública

- Costes **baseline** y **gold** por mapa
- Contenido del zip starter (`run.py`, `submit.py`, shape exacto de `state`, etc.) — **403** hasta kickoff
- Mapas de validación / finales (sellados)
- Scores de equipos durante el live (solo orden + proyección cada 20 min)
