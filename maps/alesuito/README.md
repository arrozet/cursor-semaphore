# maps/alesuito — suite de estrés (Alesuito)

Carpeta **propia** (no tocar `maps/basic/` ni la carpeta de mapas de la compañera).

Replay JSON con la **misma estructura** que `maps/basic/` (`version`, `scenario`, `map`, `frames`, `metrics`), generados con el `fixed_time_controller` del motor.

Cada mapa incluye además un sidecar `*.scenario.json` para que `run.py` lo descubra automáticamente (cualquier subcarpeta bajo `maps/`).

## Usar con run.py

Desde `source/`:

```bash
python run.py --list
python run.py --scenario single-cell --no-browser
python run.py --scenario windows-flip-axis
python run.py --all
```

`--list` muestra públicos + todos los `maps/**/*.scenario.json`.  
`--all` corre todos una vez y reporta media geométrica.

La compañera solo necesita dejar `nombre.scenario.json` en su carpeta bajo `maps/` (mismo esquema) para que aparezcan igual.

## Regenerar

```bash
python3 maps/alesuito/generate.py --sidecars-only   # solo definiciones para run.py
python3 maps/alesuito/generate.py                   # sidecars + replays pesados
```

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

Ver detalle y costes DEMO en `catalog.json`.
