# Traffic Lights Arena — Guía del agente

Cursor Build Night Málaga · Challenge 01 · 23.07.2026

Controla cada cruce de una ciudad simulada. Tu estrategia debe mover más coches, reducir la espera y adaptarse a mapas que no has visto.

## Objetivo

Tienes **105 minutos** para modificar **un único archivo**: el controlador de semáforos.

El motor se encarga de los amarillos, los tiempos mínimos y la seguridad. Tú solo decides qué eje recibe el verde en cada cruce (`NS_GREEN` o `EW_GREEN`).

## API del controlador

Implementa una sola función:

```python
def control(state):
    return {
        "A1": "NS_GREEN",
        "A2": "EW_GREEN",
    }
```

### Qué contiene `state`

- Colas
- Tiempo de espera
- Fase actual
- Edad de fase
- Ocupación de carreteras

### Restricciones

- Puedes guardar **memoria entre ticks dentro de un mapa**.
- Puedes usar la **biblioteca estándar de Python** y **NumPy**.
- Cada mapa arranca un **proceso nuevo** — la memoria no pasa de un mapa a otro.
- Modifica solo el archivo del controlador; no cambies el motor de simulación.

## Puntuación

| Hito | Puntos por mapa |
|------|-----------------|
| Floor | 1 |
| Igualar baseline | 10.000 |
| Gold (alcanzar o superar) | 25.000 |
| Máximo | 25.000 |

### Curva de score por mapa

- Por encima del coste del baseline → el score baja en proporción al coste.
- Entre baseline y gold → el avance se **eleva al cuadrado**: acercarte al gold importa mucho más que una pequeña mejora.

### Clasificación provisional (durante el evento)

| Componente | Peso |
|------------|------|
| Media geométrica de **3 mapas públicos** | 20% |
| Media geométrica de **6 mapas privados de validación** | 80% |

- Verás el **orden** provisional, no las puntuaciones de los demás equipos.
- La proyección del evento muestra únicamente el total combinado cada 20 minutos.

### Clasificación final (al cerrar entregas)

1. Se elige el **mejor envío provisional** de cada equipo (no necesariamente el más reciente).
2. Se evalúa **una sola vez** en **12 mapas finales sellados** agrupados en **6 familias**.
3. Cada familia aporta el **menor** de sus dos scores.
4. Las seis familias se combinan con **media geométrica**.
5. El mismo reparto **20/80** público/privado decide la clasificación final.

Optimiza para generalizar a mapas no vistos, no solo a los públicos.

## Flujo de trabajo

```bash
python run.py                    # prueba local
python submit.py login MLG-XXXX  # una vez, con el código de tu equipo
python submit.py                 # envía el controlador actual
```

### Límites de envío

- Hasta **20 envíos aceptados** durante los 105 minutos.
- **1 minuto** de cooldown entre envíos.
- Volver a enviar **exactamente el mismo controller** devuelve el envío existente y **no** consume intento ni cooldown.
- Los **errores del controller sí consumen** un intento aceptado — prueba en local antes de enviar.

## Control de versiones

- Todos los cambios se **commitean de forma incremental** usando [Conventional Commits](https://www.conventionalcommits.org/).
- Tras cada cambio relevante, el agente debe **hacer commit y push** de inmediato (no acumular cambios sin subir).
- Ejemplos de mensajes: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `chore: ...`.

## Prioridades del agente

1. Mantén los cambios dentro del único archivo del controlador.
2. Prioriza estrategias que generalicen; los mapas privados dominan el score (80%).
3. Prueba con `python run.py` antes de cada envío.
4. Trata los envíos como escasos (máx. 20); no gastes intentos en controllers rotos.
5. Apunta más allá del baseline hacia el gold — el avance al cuadrado premia el rendimiento cerca del gold.
6. Commitea y haz push de forma incremental con Conventional Commits tras cada cambio.
