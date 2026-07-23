# `northbound-morning`

Replay DEMO de 900 ticks. Es el caso público con demanda claramente sesgada
hacia el eje norte-sur, aunque los headings observados no muestran un sesgo
literal fuerte entre norte y sur.

## Topología

Cuadrícula 3×2, seis cruces:

| Fila | Cruces y coordenadas `(x, y)` |
| --- | --- |
| A | A1 (0,31; 0,17), A2 (0,58; 0,14) |
| B | B1 (0,36; 0,48), B2 (0,64; 0,50) |
| C | C1 (0,31; 0,82), C2 (0,70; 0,84) |

Cinco polilíneas atraviesan la red:

- EW: `west-0 → east-0`, `west-1 → east-1`, `west-2 → east-2`
- NS: `north-0 → south-0`, `north-1 → south-1`

Las dos columnas serpentean más que en `balanced-grid`, especialmente la
segunda (x=0,58→0,64→0,70), pero siguen siendo geométricamente NS.

## Demanda, flujo y congestión

| Métrica final | Valor |
| --- | ---: |
| Spawned | 1.250 |
| Completed | 1.220 (97,60 %) |
| Unfinished | 30 |
| waitTicks | 20.557 |
| Coste DEMO | 29.557 |
| Espera / spawned | 16,45 ticks |
| Penalización por unfinished | 9.000 (30,4 % del coste) |

`20.557 + 300 × 30 = 29.557`. En este mapa reducir el remanente final tiene
mucho valor: casi un tercio del coste DEMO es la penalización terminal.

| Tick | Vehículos visibles | waiting acumulado | completed |
| ---: | ---: | ---: | ---: |
| 0 | 2 | 2 | 0 |
| 150 | 44 | 3.474 | 199 |
| 300 | 51 | 7.401 | 425 |
| 450 | 66 | 11.512 | 661 |
| 600 | 31 | 15.006 | 884 |
| 750 | 33 | 17.766 | 1.051 |
| 899 | 46 | 20.557 | 1.220 |

El máximo es **66 vehículos vivos en el tick 450**. La acumulación de espera
se acelera hasta ese punto (+4.111 entre ticks 300–450) y luego se modera. La
caída de 66 a 31 vehículos entre 450 y 600 muestra un cambio de régimen que un
controller adaptativo debería aprovechar, en vez de conservar splits fijos.

## Señales del DEMO

Los seis cruces están perfectamente sincronizados durante los 900 frames.

| Fase por cruce | Ticks | % del replay | Longitud de racha |
| --- | ---: | ---: | --- |
| NS_GREEN | 480 | 53,3 % | 17 típica; extremos 20/1 por bordes |
| EW_GREEN | 252 | 28,0 % | siempre 9 |
| NS_YELLOW | 56 | 6,2 % | siempre 2 |
| EW_YELLOW | 56 | 6,2 % | siempre 2 |
| ALL_RED | 56 | 6,2 % | siempre 1 |

NS recibe **65,6 % del verde efectivo**, frente a 34,4 % EW. El DEMO codifica
la asimetría mediante verdes NS de ~17 ticks y EW de 9. La racha NS de 1 tick
es el final truncado del replay, no evidencia de un verde válido de un tick.

## Patrón espacial y direccional

La primera dirección observada de los 1.250 IDs es:

| Dirección | Vehículos |
| --- | ---: |
| Norte | 386 |
| Sur | 396 |
| Este | 250 |
| Oeste | 218 |

El eje NS suma **782 (62,6 %)** frente a 468 EW. Norte y sur son casi iguales,
por lo que los datos respaldan un **sesgo de corredor NS**, no una prioridad
hard-coded exclusivamente northbound.

La concentración media cerca de cruces (radio 0,12) es mayor en A1 (4,77) y C2
(4,61), y menor en B2 (3,78); los picos locales son 10–12. Los extremos de los
corredores reciben más acumulación que el centro, consistente con entradas y
salidas de borde, pero esta medida incluye coches en movimiento.

## Implicaciones para `control(state)`

- Inferir el sesgo desde colas/espera actuales; no reconocer el mapa por sus
  IDs ni fijar 65,6 % NS.
- Usar presión por eje y, si el estado lo permite, restar ocupación aguas abajo
  para no empujar una ola NS a un tramo saturado.
- Alargar el verde dominante cuando sigue descargando cola, pero conservar
  máximo de verde o bonus creciente de espera para proteger EW.
- La caída posterior al tick 450 favorece duraciones dependientes de densidad:
  ciclos más largos bajo carga alta y decisiones más ágiles bajo carga baja.
- Una memoria corta de tendencia (cola creciendo/disminuyendo) puede distinguir
  presión sostenida de un pico transitorio sin asumir una hora del día.
