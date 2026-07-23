# maps/alesuito — suite de estrés (Alesuito)

Carpeta **propia** (no tocar `maps/basic/` ni la carpeta de mapas de la compañera).

Replay JSON con la **misma estructura** que `maps/basic/` (`version`, `scenario`, `map`, `frames`, `metrics`), generados con el `fixed_time_controller` del motor (sin modificar código del reto).

## Para qué sirven

La clasificación usa **media geométrica**: un solo mapa oculto malo hunde el score. Esta suite cubre extremos y excepciones para comprobar que el controller es **map-agnóstico** (mallas raras, demanda asimétrica, bursts, ventanas, capacidades pequeñas, endgame flood, etc.).

No son los mapas privados oficiales; son proxies de estrés.

## Regenerar

Desde la raíz del repo:

```bash
python3 maps/alesuito/generate.py
```

Escribe un `.json` por escenario + `catalog.json` (índice con métricas baseline).

## Familias cubiertas

| Familia | Ejemplos de id |
|---|---|
| Degenerados / corredores | `single-cell`, `corridor-1x4`, `corridor-5x1` |
| Balance vs tormenta de eje | `grid-2x2-balanced`, `grid-2x2-ns-storm`, `grid-2x2-ew-storm` |
| Sparse / saturado | `grid-2x2-sparse`, `grid-2x2-saturated`, `dead-quiet-2x2` |
| Rectángulos / grandes | `grid-5x3-wide`, `grid-4x4-heavy`, `combo-5x5-mild` |
| Capacidad / travel extremos | `tiny-links-2x2`, `fat-links-3x3`, `slow-travel-3x3` |
| Un solo eje casi vacío | `ns-only-3x3`, `ew-only-3x3` |
| `demand_windows` (régimen) | `windows-flip-axis`, `windows-oscillate`, `windows-endgame-flood` |
| Sesgo por carril | `windows-lane-skew-rows`, `combo-corner-bias-3x3` |
| Combos raros | `combo-1x3-burst-tiny-links`, `combo-2x2-flip-tiny-cap` |

Ver detalle y costes DEMO en `catalog.json` tras generar.
