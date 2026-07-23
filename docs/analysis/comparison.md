# Comparación e implicaciones para el controller

## Escala, demanda y resultado DEMO

| Mapa | Malla | Cruces | Spawned | % completado | Pico vivos | wait/spawn | Coste/spawn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced-grid | 2×2 | 4 | 963 | 99,17 % | 43 | 14,15 | 16,64 |
| northbound-morning | 3×2 | 6 | 1.250 | 97,60 % | 66 | 16,45 | 23,65 |
| city-rush | 3×3 | 9 | 2.297 | 97,78 % | 145 | 23,07 | 29,73 |

La carga no escala solo con el número de cruces. `city-rush` tiene 2,25 veces
los cruces de `balanced-grid`, pero 3,89 veces sus `waitTicks`. El coste por
vehículo también crece un 79 %. Un controller debe detectar densidad y
congestión, no elegir el ciclo por tamaño de la matriz.

| Mapa | waitTicks | Penalización terminal | Coste | Parte terminal |
| --- | ---: | ---: | ---: | ---: |
| balanced-grid | 13.623 | 2.400 | 16.023 | 15,0 % |
| northbound-morning | 20.557 | 9.000 | 29.557 | 30,4 % |
| city-rush | 52.991 | 15.300 | 68.291 | 22,4 % |

En los tres:

```text
cost = waitTicks + 300 × unfinished
```

Cada coche sin terminar equivale a 300 ticks de espera. Cerca del fin del
episodio, sostener throughput y vaciar la red puede valer más que una mejora
pequeña de equidad. Esto no justifica codificar un horizonte de 900 hasta
confirmar el estado/API real.

## Demanda por eje

Clasificación según el heading de la primera aparición de cada ID:

| Mapa | EW | NS | Lectura |
| --- | ---: | ---: | --- |
| balanced-grid | 480 (49,8 %) | 483 (50,2 %) | equilibrado |
| northbound-morning | 468 (37,4 %) | 782 (62,6 %) | corredor NS dominante |
| city-rush | 1.170 (50,9 %) | 1.127 (49,1 %) | equilibrado en entrada |

En `northbound-morning`, norte (386) y sur (396) son casi iguales. El replay
demuestra sesgo del **eje** NS, no una regla fiable «siempre dar norte». La
acción disponible, además, selecciona el eje completo.

## Qué hace realmente el DEMO

Todos los cruces de cada mapa están en la misma fase en los 900 frames. El
DEMO usa planes fijos globalmente sincronizados:

| Mapa | Verde NS típico | Verde EW típico | NS del verde | Transición por cambio |
| --- | ---: | ---: | ---: | ---: |
| balanced-grid | 9 | 9 | 50,9 % | amarillo 2 + rojo 1 |
| northbound-morning | 17 | 9 | 65,6 % | amarillo 2 + rojo 1 |
| city-rush | 27 | 22 | 56,2 % | amarillo 2 + rojo 1 |

Los extremos de algunas primeras/últimas rachas se deben al recorte del replay.
Los 2 ticks amarillos y 1 `ALL_RED` son observaciones consistentes, pero el
challenge solo garantiza que el **motor** maneja seguridad y mínimos. El
controller no debe devolver esas fases.

Dos conclusiones:

1. Una duración fija universal no generaliza: el propio DEMO cambia tanto el
   split como la longitud según el escenario.
2. Cada cambio tiene coste de capacidad. Pedir el eje ganador en cada tick sin
   histéresis puede oscilar y perder 3 ticks repetidamente.

## Patrones de congestión

- `balanced-grid`: población estable alrededor de 20–30, pico tardío de 43 y
  concentración espacial homogénea.
- `northbound-morning`: sube a 66 en tick 450 y cae a 31 en tick 600; es un
  ejemplo claro de régimen variable y demanda por corredor.
- `city-rush`: pico 145 en tick 269 y carga alta prolongada; los cruces de
  borde tienen ~6,5–7,3 vehículos próximos de media frente a 4,64 en B2.

La proximidad geométrica incluye vehículos en marcha y no sustituye a las
colas del `state`. Su utilidad es demostrar heterogeneidad local: incluso con
demanda global equilibrada, los cruces no necesitan la misma fase a la vez.

## Diseño recomendado al kickoff

### 1. Adaptador de estado antes que constantes

Inspeccionar primero las claves y unidades reales de `state`: colas de entrada,
espera, fase/edad y ocupación de enlaces. El replay no revela cómo se asocian
carriles, movimientos y salidas en la API. Construir por cruce dos agregados,
NS y EW, sin depender de IDs concretos.

### 2. Núcleo tipo Max-Pressure

Si el estado permite enlazar entradas y salidas:

```text
pressure(axis) =
    queue_in(axis)
  - downstream_occupancy(axis)
  + wait_weight × waiting(axis)
```

Elegir el eje con mayor presión, con estas protecciones:

- **Verde mínimo / histéresis:** mantener fase si la ventaja contraria es
  pequeña; el motor aplica el mínimo legal, pero la política debe evitar
  solicitudes alternantes.
- **Starvation:** sumar un bonus creciente por espera/tiempo sin servicio y
  forzar rescate al superar una edad máxima.
- **Verde máximo adaptable:** impedir monopolio del eje dominante sin cortar
  una descarga productiva demasiado pronto.
- **Bloqueo aguas abajo:** no premiar solo la cola entrante; penalizar una
  salida llena para evitar trasladar el atasco al siguiente cruce.

Si no existe mapeo fiable de salidas, empezar con cola + espera es más seguro
que inventar conectividad a partir de nombres.

### 3. Regímenes de densidad

- **Baja:** si la fase actual tiene demanda o ambas están casi vacías,
  mantenerla y evitar transiciones inútiles.
- **Media:** decidir por diferencia de presión, con verde mínimo e histéresis.
- **Alta:** aumentar persistencia de verdes que descargan, dar más peso a
  ocupación aguas abajo y vigilar crecimiento de la cola opuesta.

Los umbrales deberían normalizarse por capacidad/ocupación disponible o por la
demanda total del cruce, no por cifras absolutas tomadas de estos tres mapas.

### 4. Memoria corta por cruce

Guardar dentro del mapa:

- eje servido y tick de la última petición de cambio;
- espera/edad acumulada por eje;
- tendencia suavizada de cola o presión;
- último score para aplicar histéresis.

Cada mapa arranca un proceso nuevo, así que esta memoria no debe contener
suposiciones aprendidas de mapas anteriores.

### 5. Orden de experimentación

1. Baseline seguro: mantener fase con mínimo verde y elegir mayor
   `queue + λ·wait`.
2. Añadir histéresis y protección anti-starvation.
3. Añadir penalización aguas abajo (Max-Pressure completo).
4. Adaptar persistencia a densidad/tendencia.
5. Solo después probar coordinación de corredores; nunca reemplazar la
   respuesta local con sincronización global rígida.

Medir cada cambio con `python run.py`: coste total, `waitTicks`, unfinished y
resultado por mapa. Una mejora media que empeore mucho una familia es
arriesgada porque privados/finales dominan la puntuación.

## Límites de esta comparación

Los costes aquí son del controlador DEMO, **no baseline/gold oficiales**. Los 6
mapas privados de validación y los 12 finales sellados no están disponibles.
El 80 % de la clasificación depende de privados y el resultado final toma el
peor score de cada pareja familiar. Por tanto, las cifras públicas sirven para
formular y probar invariantes (presión, estabilidad, equidad, bloqueo), no
para reconocer escenarios ni fijar planes por mapa.
