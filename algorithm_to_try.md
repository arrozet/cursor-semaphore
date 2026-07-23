Para este problema, conviene modelar la ciudad como un **grafo dirigido**:

* Cada **intersección** es un nodo.
* Cada **carretera o carril** es una arista dirigida.
* La dirección de la arista representa el sentido del tráfico.
* Cada arista almacena longitud, velocidad máxima, capacidad, número de coches y semáforo asociado.
* Cada semáforo controla grupos de movimientos compatibles: recto, giro a la izquierda y giro a la derecha.

La solución más robusta no suele ser un único algoritmo estático, sino un controlador adaptativo que evalúa periódicamente el estado del tráfico.

## 1. Algoritmo basado en presión de tráfico: Max-Pressure

Es una de las mejores opciones para un proyecto de este tipo porque se adapta al número de coches sin necesitar predecir todo el tráfico futuro.

Para cada posible fase del semáforo se calcula una presión:

[
P(fase)=\sum_{movimientos} \left(cochesEntrada-cochesSalida\right)\cdot capacidadMovimiento
]

El semáforo selecciona la fase con mayor presión.

Ejemplo:

* Carril norte: 30 coches.
* Carril sur: 20 coches.
* Carril este: 8 coches.
* Carril oeste: 5 coches.

La fase norte-sur tendrá más prioridad que la fase este-oeste.

### Ventajas

* Es adaptativo.
* Es relativamente sencillo.
* Funciona bien en redes grandes.
* Tiene en cuenta la congestión aguas abajo.
* Evita enviar coches hacia una carretera que ya está llena.

### Inconvenientes

* Puede cambiar demasiado frecuentemente si no se añaden límites.
* Necesita conocer las colas de entrada y salida.

Debes incluir:

* Tiempo verde mínimo.
* Tiempo verde máximo.
* Tiempo amarillo.
* Tiempo de seguridad entre fases.
* Tiempo máximo de espera por carril.

Pseudocódigo:

```text
cada intervalo de control:
    para cada interseccion:
        mejor_fase = ninguna
        mayor_presion = -infinito

        para cada fase posible:
            presion = 0

            para cada movimiento permitido en la fase:
                entrada = coches_en_carril_origen
                salida = coches_en_carril_destino
                capacidad = capacidad_del_movimiento

                presion += (entrada - salida) * capacidad

            si presion > mayor_presion:
                mayor_presion = presion
                mejor_fase = fase

        si se cumple el tiempo_verde_minimo:
            activar mejor_fase
```

Esta sería mi recomendación principal para una primera implementación funcional.

---

## 2. Algoritmo de tiempo verde proporcional

Es más simple. Asigna el tiempo verde en proporción a la cantidad de coches que esperan.

[
TiempoVerde_i =
TiempoCiclo \cdot
\frac{Coches_i}{\sum Coches}
]

Ejemplo:

* Norte-sur: 60 coches.
* Este-oeste: 40 coches.
* Ciclo disponible: 80 segundos.

Entonces:

[
T_{NS}=80\cdot\frac{60}{100}=48
]

[
T_{EO}=80\cdot\frac{40}{100}=32
]

Pseudocódigo:

```text
coches_totales = sumar_coches_de_todas_las_fases()

para cada fase:
    proporcion = coches_fase / coches_totales
    tiempo_verde = tiempo_disponible * proporcion

    tiempo_verde = limitar(
        tiempo_verde,
        tiempo_verde_minimo,
        tiempo_verde_maximo
    )
```

### Ventajas

* Muy fácil de implementar.
* Reacciona a cambios de tráfico.
* Es interpretable y fácil de depurar.

### Inconvenientes

* No considera si la carretera de salida está congestionada.
* Puede generar bloqueos en cadena.
* Tiene menos capacidad de coordinación entre intersecciones.

Es apropiado como algoritmo inicial o referencia de comparación.

---

## 3. Algoritmo basado en puntuación de prioridad

Puedes crear una puntuación para cada fase combinando varios factores:

[
Score =
w_1 \cdot cochesEsperando +
w_2 \cdot tiempoEspera +
w_3 \cdot densidad +
w_4 \cdot velocidadBaja -
w_5 \cdot ocupacionSalida
]

Por ejemplo:

```text
puntuacion =
    2.0 * numero_coches +
    1.5 * tiempo_medio_espera +
    3.0 * densidad_carril -
    2.5 * ocupacion_carril_salida
```

Después se selecciona la fase con mayor puntuación.

Pseudocódigo:

```text
para cada fase:
    puntuacion = 0

    para cada carril controlado por la fase:
        puntuacion += peso_coches * carril.numero_coches
        puntuacion += peso_espera * carril.tiempo_medio_espera
        puntuacion += peso_densidad * carril.densidad
        puntuacion -= peso_salida * carril.destino.ocupacion

seleccionar fase con mayor puntuacion
```

### Ventajas

* Muy flexible.
* Puedes incorporar ambulancias, autobuses o vehículos prioritarios.
* Permite experimentar con diferentes criterios.

### Inconvenientes

* Los pesos deben ajustarse.
* Una combinación incorrecta puede producir decisiones inestables.
* No garantiza una solución global óptima.

Para un trabajo académico, este enfoque permite explicar claramente cómo influyen las variables.

---

## 4. Algoritmo de onda verde

Sirve para coordinar varios semáforos consecutivos en una avenida.

La idea es calcular un desplazamiento temporal entre semáforos:

[
Offset = \frac{distancia}{velocidadMedia}
]

Ejemplo:

* Dos intersecciones separadas por 500 metros.
* Velocidad media: 50 km/h.

[
50\ km/h = 13.89\ m/s
]

[
Offset = \frac{500}{13.89} \approx 36\ segundos
]

El segundo semáforo debería ponerse en verde aproximadamente 36 segundos después del primero.

Pseudocódigo:

```text
para cada corredor principal:
    para cada par de intersecciones consecutivas:
        tiempo_viaje = distancia / velocidad_media
        semaforo_siguiente.offset = semaforo_actual.offset + tiempo_viaje
```

### Ventajas

* Reduce paradas en avenidas principales.
* Mejora la velocidad media.
* Reduce la formación de colas.

### Inconvenientes

* Funciona peor cuando el tráfico es muy irregular.
* Puede perjudicar calles secundarias.
* Debe recalcularse si cambia significativamente la velocidad media.

Puede combinarse con Max-Pressure: onda verde en condiciones normales y control adaptativo cuando aparecen congestiones.

---

## 5. Algoritmo predictivo: Model Predictive Control

El control predictivo intenta estimar cómo evolucionará el tráfico durante los siguientes segundos o minutos.

En cada ciclo:

1. Lee el estado actual.
2. Simula diferentes configuraciones de semáforos.
3. Calcula el coste de cada configuración.
4. Aplica solo la primera decisión.
5. Repite el proceso con nuevos datos.

Una función de coste podría ser:

[
Coste =
a \cdot tiempoTotalEspera +
b \cdot longitudColas +
c \cdot numeroParadas +
d \cdot riesgoBloqueo
]

El objetivo es minimizar:

[
\min Coste
]

Pseudocódigo simplificado:

```text
mejor_plan = ninguno
menor_coste = infinito

para cada plan_de_fases_posible:
    estado_simulado = copiar_estado_actual()

    simular(plan_de_fases, estado_simulado, horizonte=60 segundos)

    coste = calcular_coste(estado_simulado)

    si coste < menor_coste:
        menor_coste = coste
        mejor_plan = plan_de_fases

aplicar primera fase de mejor_plan
```

### Ventajas

* Considera consecuencias futuras.
* Puede coordinar varias intersecciones.
* Permite optimizar múltiples objetivos.

### Inconvenientes

* Requiere bastante capacidad computacional.
* La cantidad de combinaciones puede crecer rápidamente.
* Necesita un modelo razonablemente preciso.

Es una solución potente, pero más compleja para implementar en un único archivo.

---

## 6. Algoritmos genéticos

Un individuo puede representar un plan completo de semáforos:

```text
[30, 20, 40, 15, 25, 35]
```

Cada número puede representar la duración de una fase o el desplazamiento temporal de un semáforo.

El algoritmo:

1. Genera diferentes planes.
2. Simula el tráfico con cada uno.
3. Evalúa su calidad.
4. Selecciona los mejores.
5. Aplica cruces y mutaciones.
6. Repite el proceso.

Función de aptitud:

[
Fitness =
-\left(
tiempoEspera +
colas +
paradas +
congestion
\right)
]

### Ventajas

* Puede resolver problemas con muchas variables.
* No necesita una fórmula exacta para obtener el óptimo.
* Es útil para encontrar configuraciones globales.

### Inconvenientes

* No suele ser adecuado para decidir cada segundo.
* Puede tardar bastante en converger.
* No garantiza el óptimo real.
* Depende mucho del simulador.

Resulta más apropiado para optimizar planes base fuera de línea que para controlar los semáforos en tiempo real.

---

## 7. Aprendizaje por refuerzo

Cada intersección puede considerarse un agente.

### Estado

```text
- número de coches por carril
- velocidad media
- longitud de cola
- fase actual
- tiempo desde el último cambio
- ocupación de carriles de salida
```

### Acciones

```text
- mantener fase
- activar norte-sur
- activar este-oeste
- activar giros
```

### Recompensa

```text
recompensa =
    - tiempo_total_espera
    - longitud_total_colas
    - numero_de_paradas
    - penalizacion_por_bloqueo
```

El agente aprende qué acción produce mejores resultados.

### Ventajas

* Puede descubrir estrategias avanzadas.
* Se adapta a escenarios complejos.
* Permite coordinación entre intersecciones.

### Inconvenientes

* Requiere entrenamiento.
* Necesita muchas simulaciones.
* Puede tomar decisiones difíciles de explicar.
* No es recomendable entrenarlo directamente sobre tráfico real.
* Puede comportarse mal ante situaciones no vistas.

Lo usaría como ampliación avanzada, no como primera solución.

---

# Estructura de datos recomendada

Aunque todo deba estar en un único archivo, separa la lógica mediante clases o estructuras.

```python
class Lane:
    def __init__(
        self,
        lane_id,
        origin,
        destination,
        length,
        speed_limit,
        capacity
    ):
        self.id = lane_id
        self.origin = origin
        self.destination = destination
        self.length = length
        self.speed_limit = speed_limit
        self.capacity = capacity

        self.vehicle_count = 0
        self.queue_length = 0
        self.average_speed = 0.0
        self.waiting_time = 0.0


class Phase:
    def __init__(self, phase_id, allowed_movements):
        self.id = phase_id
        self.allowed_movements = allowed_movements


class TrafficLight:
    def __init__(
        self,
        light_id,
        phases,
        minimum_green,
        maximum_green,
        yellow_time
    ):
        self.id = light_id
        self.phases = phases
        self.current_phase = 0
        self.minimum_green = minimum_green
        self.maximum_green = maximum_green
        self.yellow_time = yellow_time
        self.elapsed_time = 0.0


class Intersection:
    def __init__(self, intersection_id):
        self.id = intersection_id
        self.incoming_lanes = []
        self.outgoing_lanes = []
        self.traffic_light = None
```

Un movimiento debería identificar un carril de entrada y otro de salida:

```python
class Movement:
    def __init__(self, incoming_lane, outgoing_lane, flow_rate):
        self.incoming_lane = incoming_lane
        self.outgoing_lane = outgoing_lane
        self.flow_rate = flow_rate
```

---

# Solución híbrida recomendada

La mejor arquitectura para tu caso sería:

1. **Max-Pressure** como algoritmo principal.
2. Tiempo máximo de espera para evitar que un carril quede olvidado.
3. Onda verde para las avenidas principales.
4. Prioridad especial para emergencias o transporte público.
5. Un modo de emergencia basado en reglas cuando una carretera esté bloqueada.
6. Un simulador por pasos para evaluar la calidad de las decisiones.

Una puntuación híbrida podría ser:

[
Score(fase) =
Presion(fase)
+
\alpha \cdot EsperaMaxima(fase)
+
\beta \cdot PrioridadEmergencia(fase)
+
\gamma \cdot CoordinacionCorredor(fase)
]

Pseudocódigo:

```text
cada segundo:
    actualizar posiciones y velocidades
    actualizar colas de cada carril
    actualizar ocupacion de carreteras

    para cada interseccion:
        si existe vehiculo de emergencia:
            seleccionar fase de emergencia

        si no:
            para cada fase:
                score = calcular_presion(fase)
                score += peso_espera * espera_maxima(fase)
                score += peso_corredor * beneficio_onda_verde(fase)
                score -= peso_bloqueo * riesgo_de_bloqueo(fase)

            fase_objetivo = fase con mayor score

        si puede_cambiar_fase():
            cambiar hacia fase_objetivo
```

## Restricciones imprescindibles

El algoritmo debe respetar siempre:

```text
tiempo_verde >= tiempo_verde_minimo
tiempo_verde <= tiempo_verde_maximo
tiempo_amarillo obligatorio
fases incompatibles nunca activas simultaneamente
ningun carril supera el tiempo_maximo_de_espera
no permitir entrada si el carril de salida esta lleno
```

La última condición evita el **bloqueo de caja**, cuando los vehículos entran en una intersección pero no pueden salir.

## Métricas para comparar algoritmos

No evalúes la calidad usando únicamente el número de coches procesados. Registra al menos:

[
TiempoMedioEspera =
\frac{\sum tiempoEsperaVehiculos}{numeroVehiculos}
]

[
VelocidadMedia =
\frac{\sum velocidadVehiculos}{numeroVehiculos}
]

[
LongitudMediaCola =
\frac{\sum longitudColas}{numeroCarriles}
]

También conviene medir:

* Tiempo máximo de espera.
* Número de vehículos que llegan a su destino.
* Número de paradas por vehículo.
* Ocupación media de los carriles.
* Cantidad de intersecciones bloqueadas.
* Equidad entre carreteras principales y secundarias.

Mi recomendación es implementar primero el **algoritmo proporcional** como línea base y después implementar **Max-Pressure con penalización por saturación del carril de salida**. Esa combinación ofrece una buena relación entre rendimiento, flexibilidad, complejidad y facilidad de justificación académica.
