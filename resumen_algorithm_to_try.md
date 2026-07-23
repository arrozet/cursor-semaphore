# 🚦 Resumen para empezar la implementación

## 🎯 Objetivo

Controlar los semáforos de forma **adaptativa**, dando más tiempo a las direcciones con más tráfico y evitando enviar coches hacia salidas congestionadas.

## 🗺️ Modelo de la ciudad

- 🔵 **Intersecciones** → nodos.
- 🛣️ **Carreteras y carriles** → conexiones dirigidas.
- 🚗 Cada carril debe registrar:
  - Número de coches.
  - Capacidad.
  - Velocidad.
  - Destino.
  - Tiempo de espera.

## 🧱 Primera versión: algoritmo proporcional

Usar esta versión como línea base:

1. Contar los coches que esperan en cada fase.
2. Repartir el tiempo verde proporcionalmente.
3. Aplicar límites mínimos y máximos.

```text
tiempo_verde_fase = tiempo_disponible
                   × coches_de_la_fase
                   / coches_totales
```

✅ Es sencillo, fácil de probar y permite comparar mejoras.

## ⚡ Segunda versión: Max-Pressure

Para cada fase, calcular:

```text
presión = (coches_de_entrada - capacidad_de_salida)
          × capacidad_del_movimiento
```

Después:

- 🥇 Activar la fase con mayor presión.
- ⏱️ Respetar el tiempo verde mínimo.
- 🟡 Incluir tiempo amarillo y transición segura.
- 🧮 Añadir una bonificación por tiempo de espera.
- 🚫 Penalizar salidas llenas o muy congestionadas.

## 🛡️ Reglas imprescindibles

- El verde debe estar entre un mínimo y un máximo.
- Las fases incompatibles nunca pueden estar activas a la vez.
- Ningún carril debe esperar indefinidamente.
- No permitir la entrada si el carril de salida está lleno.
- Evitar cambios de fase demasiado frecuentes.

## 📊 Métricas para evaluar

- ⏳ Tiempo medio y máximo de espera.
- 🚙 Número de vehículos que llegan a su destino.
- 🐍 Longitud media de las colas.
- 🛑 Número de paradas por vehículo.
- 🚀 Velocidad media.
- 🔒 Número de intersecciones bloqueadas.

## 🧭 Orden recomendado

```text
Línea base proporcional
        ↓
Max-Pressure
        ↓
Penalización por saturación de salida
        ↓
Memoria del tiempo de espera
        ↓
Onda verde y prioridades especiales
```

### ✅ Enfoque inicial

Implementar primero un controlador **Max-Pressure sencillo**, con límites de tiempo y penalización por congestión de salida. Es una solución adaptable, relativamente simple y con buenas posibilidades de generalizar a mapas nuevos.
