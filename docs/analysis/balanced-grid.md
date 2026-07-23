# `balanced-grid`

Replay DEMO de 900 ticks. Es el caso pequeño y casi simétrico; sirve como
control para detectar si una estrategia introduce sesgo o cambios excesivos.

## Topología

Cuadrícula 2×2, cuatro cruces:

| Cruce | Coordenada `(x, y)` |
| --- | --- |
| A1 | (0,27; 0,27) |
| A2 | (0,72; 0,24) |
| B1 | (0,25; 0,74) |
| B2 | (0,75; 0,70) |

Hay cuatro polilíneas de carretera:

- EW: `west-0 → east-0`, `west-1 → east-1`
- NS: `north-0 → south-0`, `north-1 → south-1`

Las filas y columnas no son perfectamente rectas, pero el desplazamiento
dominante permite clasificar dos ejes EW y dos NS sin ambigüedad.

## Demanda, flujo y congestión

| Métrica final | Valor |
| --- | ---: |
| Spawned | 963 |
| Completed | 955 (99,17 %) |
| Unfinished | 8 |
| waitTicks | 13.623 |
| Coste DEMO | 16.023 |
| Espera / spawned | 14,15 ticks |
| Penalización por unfinished | 2.400 (15,0 % del coste) |

`13.623 + 300 × 8 = 16.023`, por lo que la fórmula de coste queda confirmada.

`waiting` es espera acumulada, no cola instantánea:

| Tick | Vehículos visibles | waiting acumulado | completed |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |
| 150 | 20 | 2.466 | 163 |
| 300 | 29 | 4.624 | 320 |
| 450 | 24 | 6.833 | 477 |
| 600 | 27 | 9.012 | 633 |
| 750 | 23 | 11.631 | 808 |
| 899 | 17 | 13.623 | 955 |

El pico observado es **43 vehículos vivos en el tick 686**. La población
normal suele quedar en la franja 20–30 y no crece de forma sostenida. El peor
incremento de espera entre muestras fue ticks 600–750 (+2.619), pese a que
también fue el intervalo con más completados (+175).

## Señales del DEMO

Los cuatro cruces tienen exactamente la misma fase en los 900 frames: el DEMO
es globalmente sincronizado, no reactivo por cruce.

| Fase por cruce | Ticks | % del replay | Longitud de racha |
| --- | ---: | ---: | --- |
| NS_GREEN | 345 | 38,3 % | típicamente 9; primera racha 12 |
| EW_GREEN | 333 | 37,0 % | siempre 9 |
| NS_YELLOW | 74 | 8,2 % | siempre 2 |
| EW_YELLOW | 74 | 8,2 % | siempre 2 |
| ALL_RED | 74 | 8,2 % | siempre 1 |

Sobre tiempo verde efectivo, NS recibe 50,9 % y EW 49,1 %. La secuencia típica
es un verde de 9 ticks, amarillo de 2 y `ALL_RED` de 1 antes del otro eje. Es
evidencia del comportamiento de este replay, no garantía del mínimo del motor.

## Patrón espacial

La primera dirección observada de cada ID está prácticamente equilibrada:

| Eje | Vehículos |
| --- | ---: |
| EW (E 255 + W 225) | 480 |
| NS (S 256 + N 227) | 483 |

Con radio normalizado 0,12, la concentración media por cruce va de 3,32
vehículos (A1) a 3,74 (B2); los picos locales son 9–10. No aparece un hotspot
dominante. Las pequeñas diferencias son demasiado débiles para justificar
pesos específicos por ID.

## Implicaciones para `control(state)`

- Un score de presión debe dar resultados casi simétricos aquí; un sesgo
  persistente NS/EW indicaría un error o una constante demasiado fuerte.
- No cambiar solo porque la presión contraria supera por poco a la actual:
  cada transición observada consume 3 ticks sin verde.
- Mantener un verde mínimo/histéresis y cambiar cuando la ventaja sea material
  debería mejorar sobre el ciclo fijo durante picos locales.
- Añadir edad máxima o espera máxima evita inanición cuando una cola pequeña
  compite con otra sostenida.
- No codificar A1–B2: calcular por cruce permite trasladar la misma regla a
  topologías privadas.
