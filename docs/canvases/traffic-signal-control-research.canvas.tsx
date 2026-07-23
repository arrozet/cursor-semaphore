import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Link,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

const methods = [
  {
    method: "Max-Pressure con histéresis",
    verdict: "Implementar primero",
    fit: "Muy alto",
    reason: "Local, barato, adaptativo y alineado con throughput; corrige cambios inútiles y spillback.",
    tone: "success" as const,
  },
  {
    method: "SOTL / actuado con deuda roja",
    verdict: "Fallback y ablation",
    fit: "Alto",
    reason: "No necesita topología completa; integra demanda durante el rojo y evita inanición.",
    tone: "success" as const,
  },
  {
    method: "Split proporcional",
    verdict: "Baseline de control",
    fit: "Medio",
    reason: "Simple y estable, pero ignora ocupación aguas abajo y reacciona peor a cambios rápidos.",
    tone: "neutral" as const,
  },
  {
    method: "Onda verde",
    verdict: "Solo desempate débil",
    fit: "Bajo–medio",
    reason: "Puede ayudar a corredores, pero una sincronía fija es frágil ante mapas y demandas privados.",
    tone: "warning" as const,
  },
  {
    method: "MPC / rolling horizon",
    verdict: "No para v1",
    fit: "Bajo",
    reason: "Necesita modelo de transición, rutas y predicción que control(state) probablemente no expone.",
    tone: "warning" as const,
  },
  {
    method: "RL multiagente",
    verdict: "Descartar en el evento",
    fit: "Muy bajo",
    reason: "Sin entrenamiento reproducible ni garantía de transferencia a redes selladas.",
    tone: "danger" as const,
  },
  {
    method: "Algoritmo genético online",
    verdict: "Descartar",
    fit: "Muy bajo",
    reason: "No puede evaluar candidatos sin clonar el simulador y desperdicia el presupuesto temporal.",
    tone: "danger" as const,
  },
];

const sources = [
  {
    source: "Traffic Lights Arena — reglas oficiales",
    year: "2026",
    supports: "API pública, 20/80, media geométrica, familias finales y límites de envío.",
    url: "https://www.cursorspain.com/mlg/es/challenge",
  },
  {
    source: "Levin — Max-Pressure Traffic Signal Timing: A Summary",
    year: "2023",
    supports: "Revisión de garantías, variantes prácticas, lost time y límites respecto a delay.",
    url: "https://par.nsf.gov/servlets/purl/10419441",
  },
  {
    source: "Varaiya — Max pressure control of a network of signalized intersections",
    year: "2013",
    supports: "Formulación clásica y estabilidad máxima con información local.",
    url: "https://doi.org/10.1016/j.trc.2013.08.014",
  },
  {
    source: "Wongpiromsarn et al. — Distributed traffic signal control",
    year: "2012",
    supports: "Control distribuido para máximo throughput y modelo de ocupación por enlace.",
    url: "https://doi.org/10.1109/ITSC.2012.6338817",
  },
  {
    source: "Le et al. — Throughput-Optimal Scheduling with Switch-Over Delay",
    year: "2017",
    supports: "Sesgo hacia la fase actual e histéresis para absorber el coste de transición.",
    url: "https://doi.org/10.1145/3084041.3084065",
  },
  {
    source: "Gregoire et al. — Capacity-Aware Backpressure",
    year: "2015",
    supports: "Presión normalizada, capacidad finita, conservación de trabajo y spillback.",
    url: "https://doi.org/10.1109/TCNS.2014.2378871",
  },
  {
    source: "Li & Jabari — Position weighted backpressure",
    year: "2019",
    supports: "Spillback, capacidad finita y valor de la distribución espacial.",
    url: "https://doi.org/10.1016/j.trb.2019.08.005",
  },
  {
    source: "Liu & Gayah — Delay-based Max Pressure",
    year: "2022",
    supports: "Incorporar demora mejora equidad; MP clásico no minimiza delay por sí solo.",
    url: "https://doi.org/10.1016/j.trc.2022.103803",
  },
  {
    source: "Wang et al. — Max Pressure with phase switching loss",
    year: "2022",
    supports: "Curva de conmutación e histéresis dependiente de carga con switching loss.",
    url: "https://doi.org/10.1016/j.trc.2022.103670",
  },
  {
    source: "Gershenson — Self-Organizing Traffic Lights",
    year: "2005/2008",
    supports: "Contador coche×tick, fase mínima y preservación emergente de pelotones.",
    url: "https://doi.org/10.25088/complexsystems.16.1.29",
  },
  {
    source: "Lämmer & Helbing — Self-control of traffic lights",
    year: "2008",
    supports: "Combinar optimización local con estabilización por intervalo máximo de servicio.",
    url: "https://doi.org/10.1088/1742-5468/2008/04/P04019",
  },
  {
    source: "FHWA — Traffic Signal Timing Manual, capítulo 5",
    year: "2008",
    supports: "Minimum green, gap-out, passage time y max-out en control actuado.",
    url: "https://ops.fhwa.dot.gov/publications/fhwahop08024/chapter5.htm",
  },
  {
    source: "Mei et al. — LibSignal",
    year: "2023",
    supports: "Sensibilidad a simulador, hiperparámetros y necesidad de comparativas unificadas.",
    url: "https://doi.org/10.1007/s10994-023-06412-y",
  },
  {
    source: "Jamshidnejad et al. — MPC with endpoint penalties",
    year: "2016",
    supports: "Importancia de penalizar vehículos restantes y oscilaciones al final del horizonte.",
    url: "https://doi.org/10.1016/j.ifacol.2016.07.025",
  },
  {
    source: "Wei et al. — PressLight",
    year: "2019",
    supports: "RL obtiene fuerza al reutilizar presión; entrenamiento sensible y costoso.",
    url: "https://doi.org/10.1145/3292500.3330949",
  },
  {
    source: "Zhang et al. — Advanced-MP / Advanced-XLight",
    year: "2022",
    supports: "Una heurística con cola y vehículos aproximándose puede superar baselines aprendidos.",
    url: "https://proceedings.mlr.press/v162/zhang22ah.html",
  },
];

function DecisionStep({
  number,
  title,
  body,
}: {
  number: string;
  title: string;
  body: string;
}) {
  const theme = useHostTheme();
  return (
    <Row gap={12} align="start">
      <div
        style={{
          width: 24,
          height: 24,
          flex: "0 0 24px",
          borderRadius: 12,
          display: "grid",
          placeItems: "center",
          color: theme.text.onAccent,
          background: theme.accent.control,
          fontSize: 11,
          fontWeight: 700,
        }}
      >
        {number}
      </div>
      <Stack gap={3} style={{ minWidth: 0 }}>
        <Text weight="semibold">{title}</Text>
        <Text size="small" tone="secondary">
          {body}
        </Text>
      </Stack>
    </Row>
  );
}

function Strategy() {
  const theme = useHostTheme();
  return (
    <Stack gap={22}>
      <Grid columns="minmax(0, 1.35fr) minmax(260px, 0.65fr)" gap={18}>
        <Stack gap={12}>
          <H2>Política recomendada</H2>
          <Callout tone="success" title="H-MP Lite: presión + histéresis + deuda de servicio">
            Un controlador descentralizado por cruce. Usa la presión como señal principal,
            conserva la fase cuando la ventaja rival no amortiza los 3 ticks perdidos y añade
            una deuda creciente para que una aproximación pequeña no quede olvidada.
          </Callout>
          <Text tone="secondary">
            No es Max-Pressure “puro”. Esa versión supone enlaces infinitos y normalmente ignora
            el lost time; ambos supuestos son peligrosos en este simulador.
          </Text>
        </Stack>
        <Card size="lg">
          <CardHeader trailing={<Pill size="sm" active>v1</Pill>}>
            Regla normalizada por cruce
          </CardHeader>
          <CardBody>
            <Stack gap={10}>
              <Code>q̂ₐ = qₐ / (qNS + qEW + 1)</Code>
              <Code>ŵₐ = waitₐ / (waitNS + waitEW + 1)</Code>
              <Code>Pₐ = q̂ₐ · (1 − occupancyOutₐ)ᵞ</Code>
              <Code>Uₐ = Pₐ + α · ŵₐ + β · redDebtₐ</Code>
              <Divider />
              <Text size="small" tone="secondary">
                Cambiar a la fase rival solo si <Code>age ≥ minHold</Code> y
                <Code> Ualt − Ucur &gt; Habs + hrel · max(|Ucur|, |Ualt|)</Code>. Calibrar
                <Code> Habs</Code> contra la descarga que se perdería durante la transición.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Orden de decisión en cada tick</H2>
      <Grid columns={2} gap={16}>
        <DecisionStep
          number="1"
          title="Adaptar el estado, sin asumir nombres"
          body="Descubrir cruces y ejes desde state. Agregar colas, espera y salidas por NS/EW; no codificar A1, B2 ni tamaños de mapa."
        />
        <DecisionStep
          number="2"
          title="Bloquear spillback"
          body="Si la ocupación de salida está casi llena, reducir con fuerza la utilidad de ese eje. Un verde que no descarga no es servicio."
        />
        <DecisionStep
          number="3"
          title="Respetar la fase actual"
          body="Durante minHold, mantener. Después, exigir margen material antes de pagar amarillo + ALL_RED."
        />
        <DecisionStep
          number="4"
          title="Gap-out cuando deja de fluir"
          body="Cambiar si desaparecen cola y aproximaciones durante una ventana y el rojo tiene demanda. Cola cero por sí sola no prueba ausencia de un pelotón en movimiento."
        />
        <DecisionStep
          number="5"
          title="Acumular deuda roja"
          body="Integrar demanda×tick únicamente mientras el eje está rojo; resetear o decaer al recibir servicio."
        />
        <DecisionStep
          number="6"
          title="Entrar en endgame con payback"
          body="Si se confirma horizonte H, no iniciar un cambio cuando resten ≤ transición + mínimo verde. Antes, priorizar descarga realizable hacia enlaces libres."
        />
      </Grid>

      <Divider />
      <H2>Parámetros que deberían generalizar</H2>
      <Text tone="secondary">
        Ajustar proporciones normalizadas, no umbrales absolutos de coches. Los rangos son puntos
        de partida para barrido local, no valores finales.
      </Text>
      <Table
        headers={["Parámetro", "Rango inicial", "Función", "Señal de exceso"]}
        rows={[
          ["γ downstream", "1–3", "Vetar progresivamente salidas llenas", "Se desperdicia verde con salida libre"],
          ["α espera", "0,15–0,35", "Alinear presión con waitTicks", "Se sirve tráfico pequeño demasiado pronto"],
          ["β deuda roja", "0,05–0,25", "Evitar inanición", "Alternancia casi periódica pese a gran asimetría"],
          ["hrel histéresis", "0,10–0,25", "Amortizar transición", "Muchas transiciones con poca mejora de cola"],
          ["gap window", "3–6 ticks", "Detectar fin de pelotón", "El verde queda vacío demasiado tiempo"],
          ["Gmax con rival", "30–60 ticks", "Evitar monopolio sin ciclo fijo", "Corta repetidamente el flujo dominante"],
          ["Tforce", "60–90 ticks", "Rescate anti-starvation", "Fuerza salidas bloqueadas o vacías"],
        ]}
        columnAlign={["left", "left", "left", "left"]}
        striped
      />

      <Callout tone="warning" title="Fallback si state no expone topología">
        Sustituir <Code>occupancyOut</Code> por una política SOTL/actuada:
        <Code> redDebt += queueRed</Code>, mínimo verde, gap-out y max-out por deuda.
        No inventar el enlace aguas abajo a partir del ID del cruce.
      </Callout>

      <Callout tone="info" title="Mejora v2 solo después del híbrido reactivo">
        Estimar con EWMA llegadas y descarga por eje, proyectar una única transición y comparar
        las dos acciones con colas cuadráticas, spillback y coste de cambio. Es lookahead local de
        un paso, no MPC: debe retirarse si la estimación ruidosa empeora alguna familia.
      </Callout>

      <div
        style={{
          padding: 14,
          borderTop: `1px solid ${theme.stroke.tertiary}`,
          color: theme.text.tertiary,
          fontSize: 12,
        }}
      >
        La forma exacta de q, wait y occupancy queda pendiente del starter: a 23-07-2026 18:14 UTC
        el evento seguía “upcoming” y el ZIP devolvía 403 challenge_not_started. En particular,
        no debe asumirse que wait sea instantáneo o esté desglosado por eje.
      </div>
    </Stack>
  );
}

function Comparison() {
  return (
    <Stack gap={20}>
      <H2>Comparativa crítica</H2>
      <Text tone="secondary">
        La clasificación prioriza utilidad dentro de este challenge, no sofisticación académica.
      </Text>
      <Table
        headers={["Approach", "Decisión", "Encaje", "Por qué"]}
        rows={methods.map((item) => [
          <Text weight="semibold">{item.method}</Text>,
          item.verdict,
          item.fit,
          <Text size="small" tone="secondary">{item.reason}</Text>,
        ])}
        rowTone={methods.map((item) => item.tone)}
        striped
      />

      <Grid columns="minmax(0, 1fr) minmax(260px, 0.8fr)" gap={20}>
        <Stack gap={8}>
          <H3>Coste de transición observado en el DEMO</H3>
          <Text size="small" tone="secondary">
            Eje X: mapa público. Eje Y: porcentaje de ticks en amarillo o ALL_RED.
          </Text>
          <BarChart
            categories={["balanced-grid", "northbound", "city-rush"]}
            series={[{ name: "Ticks sin verde", data: [24.7, 18.7, 10.7], tone: "warning" }]}
            valueSuffix="%"
            height={220}
            yMax={30}
            showValues
          />
          <Text size="small" tone="tertiary">
            Fuente: replays públicos DEMO, 900 ticks por mapa. Cálculo: (yellow NS + yellow EW +
            ALL_RED) / 900. No son resultados de baseline ni gold.
          </Text>
        </Stack>
        <Stack gap={12}>
          <H3>Qué demuestra y qué no</H3>
          <Callout tone="info" title="Sí demuestra">
            Cambiar tiene coste de capacidad observable. Los verdes más largos del mapa cargado
            reducen la fracción de transición.
          </Callout>
          <Callout tone="neutral" title="No demuestra">
            Que debamos copiar ciclos de 9, 17 o 27 ticks. Son decisiones del controlador DEMO y
            sobreajustar esos valores dañaría los mapas privados.
          </Callout>
        </Stack>
      </Grid>

      <Divider />
      <H2>Por qué no elegir RL o MPC ahora</H2>
      <Grid columns={2} gap={18}>
        <Stack gap={6}>
          <H3>RL</H3>
          <Text tone="secondary">
            PressLight y CoLight pueden superar heurísticas en escenarios entrenados, pero requieren
            rollouts, dependencias y validación de transferencia. LibSignal muestra que simulador,
            dataset, métrica e hiperparámetros alteran el ranking. Aquí no hay presupuesto fiable
            para aprender una política general antes de ver los mapas sellados.
          </Text>
        </Stack>
        <Stack gap={6}>
          <H3>MPC</H3>
          <Text tone="secondary">
            Un MPC serio necesita modelo de flujos, capacidades, turning ratios, horizonte y
            endpoint penalty. Sin clonar el motor desde <Code>control(state)</Code>, el “MPC” sería
            una heurística cara y mal calibrada. Sí conviene destilar dos ideas: penalizar
            oscilaciones y tratar explícitamente el final del episodio.
          </Text>
        </Stack>
      </Grid>
    </Stack>
  );
}

function Experiments() {
  return (
    <Stack gap={20}>
      <H2>Plan experimental de máxima información</H2>
      <Callout tone="info" title="Criterio de aceptación">
        Conservar un cambio si mejora la media geométrica y no abre una regresión grande en el peor
        mapa. El score final usa el mínimo de dos escenarios por familia: robustez antes que récord
        aislado.
      </Callout>

      <Table
        headers={["Paso", "Controlador", "Pregunta que responde", "Métricas mínimas"]}
        rows={[
          ["0", "Probe de schema + fixed", "¿Cómo se agrupa realmente state?", "Errores, keys, tipos, tick"],
          ["1", "Longest queue + minHold", "¿Cuánto aporta solo reaccionar?", "cost, wait, unfinished, switches"],
          ["2", "SOTL deuda roja", "¿Ayuda integrar demanda durante rojo?", "cost por mapa, p95 wait"],
          ["3", "MP sin downstream", "¿La diferencia de colas mejora throughput?", "completed, queue, cost"],
          ["4", "MP + downstream", "¿Se evita spillback?", "verdes bloqueados, unfinished"],
          ["5", "+ histéresis / gap-out", "¿Se amortizan transiciones sin perder reacción?", "switches, ticks sin verde"],
          ["6", "+ espera / deuda", "¿Mejora equidad sin perder capacidad?", "max wait, cost, peor mapa"],
          ["7", "+ endgame", "¿Baja la penalización terminal?", "unfinished en ticks 750–900"],
          ["8", "Lookahead de un paso", "¿La tendencia predice mejor que reacciona?", "cost vs v7, varianza por seed"],
        ]}
        rowTone={["neutral", "neutral", "info", "info", "success", "success", "success", "success", "warning"]}
        striped
      />

      <H2>Barrido pequeño, no búsqueda ciega</H2>
      <Grid columns={3} gap={14}>
        <Stat value="3–5" label="valores por parámetro activo" />
        <Stat value="1" label="idea cambiada por experimento" />
        <Stat value="≥3" label="mapas exigidos por decisión" />
      </Grid>
      <Text tone="secondary">
        Primero barrer <Code>histéresis × minHold</Code>; después
        <Code> λ downstream</Code>; por último espera/deuda. No buscar cinco pesos a la vez:
        con tres mapas públicos, el optimum aparente será ruido estructural.
      </Text>

      <Card collapsible defaultOpen>
        <CardHeader trailing={<Pill size="sm">checklist</Pill>}>
          Antes de cada submit
        </CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text>1. Ejecutar todos los mapas con <Code>python run.py</Code>.</Text>
            <Text>2. Confirmar retorno para todos los cruces y solo <Code>NS_GREEN/EW_GREEN</Code>.</Text>
            <Text>3. Comparar cost, waitTicks, unfinished y número de cambios frente al commit anterior.</Text>
            <Text>4. Inspeccionar el peor mapa, no solo el agregado.</Text>
            <Text>5. Commit y push de una sola idea antes de considerar el envío.</Text>
          </Stack>
        </CardBody>
      </Card>

      <Callout tone="warning" title="Ablation obligatoria">
        Si añadir coordinación, tendencia o endgame mejora solo un mapa público, retirarlo. El 80 %
        privado y la media geométrica castigan los trucos frágiles mucho más de lo que premian un
        pico local.
      </Callout>
    </Stack>
  );
}

function Sources() {
  return (
    <Stack gap={18}>
      <H2>Fuentes y trazabilidad</H2>
      <Text tone="secondary">
        Se han priorizado artículos originales, una revisión académica reciente y documentación
        operativa. Los resultados de simuladores externos orientan el diseño; no predicen el score
        de este motor.
      </Text>
      <Table
        headers={["Fuente", "Año", "Qué respalda"]}
        rows={sources.map((item) => [
          <Link href={item.url}>{item.source}</Link>,
          item.year,
          <Text size="small" tone="secondary">{item.supports}</Text>,
        ])}
        striped
        stickyHeader
      />
      <Callout tone="neutral" title="Límite epistemológico">
        Hasta abrir el starter no conocemos nombres, unidades, turning movements, capacidades ni si
        waiting es instantáneo o acumulado dentro de <Code>state</Code>. La recomendación de
        arquitectura es sólida; los adaptadores y pesos concretos aún no lo son.
      </Callout>
    </Stack>
  );
}

export default function TrafficSignalControlResearch() {
  const theme = useHostTheme();
  const [section, setSection] = useCanvasState("research-section", "strategy");
  return (
    <div
      style={{
        minHeight: "100%",
        background: theme.bg.editor,
        color: theme.text.primary,
        padding: "28px clamp(18px, 4vw, 48px) 48px",
      }}
    >
      <Stack gap={22} style={{ width: "100%", maxWidth: 1120, margin: "0 auto" }}>
        <Stack gap={8}>
          <Row gap={8} wrap>
            <Pill active size="sm">Research aplicada</Pill>
            <Pill size="sm">23 julio 2026</Pill>
            <Pill size="sm">16 fuentes</Pill>
          </Row>
          <H1>Traffic Lights Arena: estrategia con mayor probabilidad de generalizar</H1>
          <Text tone="secondary">
            Síntesis de reglas oficiales, replays públicos y literatura de control adaptativo,
            traducida a un controller Python de un solo archivo.
          </Text>
        </Stack>

        <Grid columns={4} gap={16}>
          <Stat value="80%" label="peso de validación privada" tone="warning" />
          <Stat value="300" label="ticks por vehículo unfinished" tone="danger" />
          <Stat value="~3" label="ticks perdidos por transición" />
          <Stat value="900" label="ticks observados por replay" />
        </Grid>

        <Row gap={8} wrap>
          <Pill active={section === "strategy"} onClick={() => setSection("strategy")}>
            Estrategia
          </Pill>
          <Pill active={section === "comparison"} onClick={() => setSection("comparison")}>
            Comparativa
          </Pill>
          <Pill active={section === "experiments"} onClick={() => setSection("experiments")}>
            Experimentos
          </Pill>
          <Pill active={section === "sources"} onClick={() => setSection("sources")}>
            Fuentes
          </Pill>
        </Row>

        <Divider />
        {section === "strategy" && <Strategy />}
        {section === "comparison" && <Comparison />}
        {section === "experiments" && <Experiments />}
        {section === "sources" && <Sources />}
      </Stack>
    </div>
  );
}
