# Guía del agente

Estrategia de trabajo para resolver el reto. Lee primero [`challenge.md`](challenge.md) para las reglas, la API y la puntuación.

## Principios

1. **Solo el controlador** — todos los cambios de lógica van en el único archivo del controlador; no toques el motor de simulación.
2. **Generaliza** — el 80% del score viene de mapas privados; no sobreajustes a los públicos.
3. **Prueba antes de enviar** — ejecuta `python run.py` en local antes de cada `python submit.py`.
4. **Envíos escasos** — máximo 20 intentos; un controller roto consume intento. No envíes sin validar.
5. **Apunta al gold** — entre baseline y gold el avance se eleva al cuadrado; una mejora cerca del gold vale mucho más que una leve mejora temprana.

## Control de versiones

- Commitea de forma **incremental** con [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, …).
- Tras cada cambio relevante: **commit + push** de inmediato. No acumules trabajo sin subir.
- Un commit = una idea clara (una mejora de estrategia, un fix, un ajuste de docs).

## Ciclo de trabajo

1. Entiende el estado actual del controlador y los resultados locales.
2. Propón un cambio pequeño y medible (heurística, pesos, umbrales, memoria entre ticks).
3. Implementa solo ese cambio.
4. Valida con `python run.py`.
5. Commit + push con Conventional Commits.
6. Si el resultado mejora de forma estable, considera un envío (`python submit.py`).
7. Repite: itera rápido, mide, conserva lo que generaliza.

## Qué optimizar

- Mover más coches y reducir espera en cruces.
- Adaptarse a densidades y topologías distintas (mapas no vistos).
- Usar memoria **dentro** de un mapa (colas, fases, tendencias); asume proceso limpio entre mapas.
- Preferir reglas robustas frente a constantes mágicas afinadas a un solo mapa.
