# `city-rush`

Replay DEMO de 900 ticks. Es la red pública más grande y cargada; expone el
coste de usar una única fase sincronizada para nueve cruces con condiciones
locales distintas.

## Topología

Cuadrícula 3×3, nueve cruces:

| Fila | Cruces y coordenadas `(x, y)` |
| --- | --- |
| A | A1 (0,17; 0,20), A2 (0,49; 0,14), A3 (0,82; 0,23) |
| B | B1 (0,13; 0,51), B2 (0,52; 0,47), B3 (0,87; 0,54) |
| C | C1 (0,22; 0,82), C2 (0,57; 0,86), C3 (0,80; 0,79) |

Seis polilíneas recorren toda la malla:

- EW: `west-0 → east-0`, `west-1 → east-1`, `west-2 → east-2`
- NS: `north-0 → south-0`, `north-1 → south-1`, `north-2 → south-2`

Las carreteras son curvas y los cruces no están equiespaciados. La etiqueta de
fase debe venir del estado/API, no de comparar headings con ángulos ideales.

## Demanda, flujo y congestión

| Métrica final | Valor |
| --- | ---: |
| Spawned | 2.297 |
| Completed | 2.246 (97,78 %) |
| Unfinished | 51 |
| waitTicks | 52.991 |
| Coste DEMO | 68.291 |
| Espera / spawned | 23,07 ticks |
| Penalización por unfinished | 15.300 (22,4 % del coste) |

`52.991 + 300 × 51 = 68.291`. Aunque el porcentaje completado se parece al de
`northbound-morning`, cada vehículo acumula bastante más espera.

| Tick | Vehículos visibles | waiting acumulado | completed |
| ---: | ---: | ---: | ---: |
| 0 | 5 | 5 | 0 |
| 150 | 89 | 8.964 | 336 |
| 300 | 101 | 18.703 | 752 |
| 450 | 118 | 26.736 | 1.103 |
| 600 | 139 | 35.652 | 1.495 |
| 750 | 101 | 44.659 | 1.857 |
| 899 | 82 | 52.991 | 2.246 |

El pico absoluto es **145 vehículos vivos en el tick 269**. La población sigue
alta hasta después del tick 600 y la espera crece entre 8.033 y 9.739 ticks
por intervalo de 150: no hay una recuperación limpia temprana. Este es el
mapa donde bloquear salidas o desperdiciar transiciones resulta más caro.

## Señales del DEMO

Los nueve cruces comparten exactamente la misma fase en todos los frames.

| Fase por cruce | Ticks | % del replay | Longitud de racha |
| --- | ---: | ---: | --- |
| NS_GREEN | 452 | 50,2 % | 27 típica; inicio 30, final 17 |
| EW_GREEN | 352 | 39,1 % | siempre 22 |
| NS_YELLOW | 32 | 3,6 % | siempre 2 |
| EW_YELLOW | 32 | 3,6 % | siempre 2 |
| ALL_RED | 32 | 3,6 % | siempre 1 |

NS recibe 56,2 % del verde efectivo y EW 43,8 %. Los verdes largos (27/22)
reducen la fracción de transición a 10,7 %, pero la sincronización global no
responde a focos locales y puede lanzar pelotones hacia cruces ya ocupados.

## Patrón espacial

La primera dirección de cada vehículo es casi equilibrada por eje:

| Eje | Vehículos |
| --- | ---: |
| EW (E 581 + W 589) | 1.170 (50,9 %) |
| NS (S 553 + N 574) | 1.127 (49,1 %) |

No hay base para una prioridad NS fija por demanda de entrada. Sin embargo, la
concentración alrededor de cruces es heterogénea:

| Zona | Media de vehículos a radio ≤ 0,12 |
| --- | ---: |
| C3 / B3 / A3 | 7,33 / 7,28 / 7,19 |
| A1 / C1 / B1 | 6,71 / 6,60 / 6,46 |
| C2 / A2 / B2 | 5,79 / 5,63 / 4,64 |

Los picos locales llegan a 11–14. La columna central, en especial B2, aparece
menos poblada que los bordes; puede deberse a longitudes geométricas y flujos
de frontera, por lo que esta proximidad no debe interpretarse como cola pura.

## Implicaciones para `control(state)`

- Decidir por cruce, no con un reloj global. La presión local debería romper la
  sincronía cuando los bordes y el centro están en estados distintos.
- Incorporar ocupación de salida a Max-Pressure: bajo 100–145 coches vivos, una
  fase con mucha entrada puede ser mala si descarga hacia un enlace saturado.
- Amortizar los 3 ticks de transición con mínimo verde e histéresis; en alta
  densidad convienen verdes más largos que en una red vacía.
- Evitar máximos excesivos: la heterogeneidad espacial exige rescatar pronto
  una aproximación minoritaria cuya espera siga creciendo.
- Dar más peso relativo a espera/edad cuando dos presiones son parecidas. Eso
  mejora equidad sin fijar prioridades por columna o por ID.
