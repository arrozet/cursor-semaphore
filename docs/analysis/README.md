# Análisis previo de los mapas públicos

Este directorio resume lo observable en los replays JSON públicos de 900
ticks. Su objetivo es orientar el diseño inicial de `control(state)`, no
deducir detalles internos del simulador.

## Documentos

- [Cuadrícula equilibrada](balanced-grid.md)
- [Mañana hacia el norte](northbound-morning.md)
- [Hora punta](city-rush.md)
- [Comparación e implicaciones](comparison.md)
- [`analyze_maps.py`](analyze_maps.py): reproduce las estadísticas principales
  con Python estándar.

## Fuente y método

Fuentes analizadas:

- `maps/basic/balanced-grid.json`
- `maps/basic/northbound-morning.json`
- `maps/basic/city-rush.json`

Cada frame aporta `tick`, vehículos `[id, x, y, heading]`, señales,
`completed` y `waiting`. En estos ficheros, `waiting` es acumulado: su valor
final coincide con `metrics.waitTicks`; no es el número instantáneo de coches
parados. La ocupación espacial se aproxima contando vehículos a distancia
normalizada ≤ 0,12 de cada cruce. Es un indicador de concentración, no una
cola exacta.

Para regenerar el resumen estructurado:

```bash
python3 docs/analysis/analyze_maps.py
```

## Caveats importantes

1. Estos JSON son **replays públicos del controlador DEMO**. Sus costes no son
   los costes oficiales de baseline/gold.
2. El formato replay **no es la API del motor**. Al comenzar habrá que
   inspeccionar el `state` real antes de implementar heurísticas.
3. Los 6 mapas privados de validación y los 12 mapas finales sellados no están
   disponibles. El 80 % del resultado depende de mapas privados: hay que
   optimizar para generalizar.
4. El motor gestiona amarillos, tiempos mínimos y seguridad. El controller
   solo elige `NS_GREEN` o `EW_GREEN`; no debe intentar emitir `YELLOW` ni
   `ALL_RED`.
5. Las coordenadas están normalizadas y algo deformadas respecto a una
   cuadrícula perfecta. Aquí «NS» y «EW» describen el eje geométrico dominante.

## Lectura rápida

| Mapa | Cruces | Spawned | Completados | Sin terminar | Pico vivos | waitTicks | Coste DEMO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced-grid | 4 | 963 | 955 | 8 | 43 | 13.623 | 16.023 |
| northbound-morning | 6 | 1.250 | 1.220 | 30 | 66 | 20.557 | 29.557 |
| city-rush | 9 | 2.297 | 2.246 | 51 | 145 | 52.991 | 68.291 |

En los tres casos se verifica exactamente:

```text
cost = waitTicks + 300 × unfinished
spawned = completed + unfinished
```

El valor de `vehicles` del frame 899 no coincide necesariamente con
`unfinished`: el frame y el resumen final pertenecen a momentos distintos del
cierre del tick. Para penalización y balance de demanda se usan las métricas
finales.
