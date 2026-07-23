(() => {
  "use strict";

  const REPLAY_PATH = "../maps/basic/";
  const BASE_TICKS_PER_SECOND = 30;
  const WORLD_MIN = -0.04;
  const WORLD_MAX = 1.04;

  const PHASE_COLORS = {
    NS_GREEN: "#35d69f",
    EW_GREEN: "#4ea1ff",
    NS_YELLOW: "#f4d35e",
    EW_YELLOW: "#ff9f43",
    ALL_RED: "#ef6262",
  };

  const canvas = document.querySelector("#map-canvas");
  const context = canvas.getContext("2d");
  const loadingState = document.querySelector("#loading-state");
  const loadingCopy = document.querySelector("#loading-copy");
  const scenarioName = document.querySelector("#scenario-name");
  const playbackState = document.querySelector("#playback-state");
  const playButton = document.querySelector("#play-button");
  const playLabel = document.querySelector("#play-label");
  const restartButton = document.querySelector("#restart-button");
  const tickSlider = document.querySelector("#tick-slider");
  const timelineOutput = document.querySelector("#timeline-output");
  const speedSelect = document.querySelector("#speed-select");
  const metricsCard = document.querySelector("#metrics-card");

  const hud = {
    tick: document.querySelector("#hud-tick"),
    completed: document.querySelector("#hud-completed"),
    waiting: document.querySelector("#hud-waiting"),
    vehicles: document.querySelector("#hud-vehicles"),
    cost: document.querySelector("#hud-cost"),
  };

  const metricFields = {
    spawned: document.querySelector("#metric-spawned"),
    completed: document.querySelector("#metric-completed"),
    unfinished: document.querySelector("#metric-unfinished"),
    waitTicks: document.querySelector("#metric-waiting"),
    cost: document.querySelector("#metric-cost"),
  };

  const state = {
    replay: null,
    frameIndex: 0,
    spawnedByFrame: [],
    playing: false,
    speed: 1,
    loadToken: 0,
    lastAnimationTime: null,
    tickAccumulator: 0,
  };

  const replayCache = new Map();
  const numberFormatter = new Intl.NumberFormat();

  function formatNumber(value) {
    return Number.isFinite(value) ? numberFormatter.format(value) : "—";
  }

  function setControlsEnabled(enabled) {
    playButton.disabled = !enabled;
    restartButton.disabled = !enabled;
    tickSlider.disabled = !enabled;
    speedSelect.disabled = !enabled;
  }

  function showLoading(message, isError = false) {
    loadingCopy.textContent = message;
    loadingState.classList.remove("is-hidden");
    loadingState.classList.toggle("is-error", isError);
  }

  function hideLoading() {
    loadingState.classList.add("is-hidden");
    loadingState.classList.remove("is-error");
  }

  function setPlaying(playing) {
    state.playing = playing && Boolean(state.replay);
    state.lastAnimationTime = null;
    state.tickAccumulator = 0;
    updatePlaybackUi();
  }

  function updatePlaybackUi() {
    const lastFrame = state.replay ? state.replay.frames.length - 1 : 0;
    const finished = Boolean(state.replay) && state.frameIndex >= lastFrame;

    playButton.classList.toggle("is-playing", state.playing);
    playButton.setAttribute("aria-label", state.playing ? "Pause replay" : "Play replay");
    playLabel.textContent = state.playing ? "Pause" : finished ? "Replay" : "Play";
    playbackState.textContent = state.playing
      ? "Playing"
      : finished
        ? "Complete"
        : state.replay
          ? state.frameIndex === 0
            ? "Ready"
            : "Paused"
          : "Loading";
    metricsCard.classList.toggle("is-finished", finished);
  }

  function buildSpawnedCounts(frames) {
    let highestVehicleId = 0;
    return frames.map((frame) => {
      for (const vehicle of frame.vehicles) {
        const numericId = Number(vehicle[0]);
        if (Number.isFinite(numericId)) {
          highestVehicleId = Math.max(highestVehicleId, numericId);
        }
      }
      return highestVehicleId;
    });
  }

  async function fetchReplay(scenarioId) {
    if (!replayCache.has(scenarioId)) {
      const request = fetch(`${REPLAY_PATH}${scenarioId}.json`).then((response) => {
        if (!response.ok) {
          throw new Error(`Replay request failed (${response.status})`);
        }
        return response.json();
      });
      replayCache.set(scenarioId, request);
    }

    try {
      return await replayCache.get(scenarioId);
    } catch (error) {
      replayCache.delete(scenarioId);
      throw error;
    }
  }

  async function loadScenario(scenarioId) {
    const token = ++state.loadToken;
    const activeTab = document.querySelector(
      `.scenario-tab[data-scenario="${scenarioId}"]`,
    );
    setPlaying(false);
    state.replay = null;
    state.frameIndex = 0;
    state.spawnedByFrame = [];
    setControlsEnabled(false);
    scenarioName.textContent =
      activeTab?.querySelector("span")?.textContent || "Loading replay";
    playbackState.textContent = "Loading";
    metricsCard.classList.remove("is-finished");
    tickSlider.value = "0";
    tickSlider.max = "0";
    timelineOutput.textContent = "— / —";
    Object.values(hud).forEach((element) => {
      element.textContent = "—";
    });
    Object.values(metricFields).forEach((element) => {
      element.textContent = "—";
    });
    document.querySelector("#metrics-badge").textContent = "— ticks";
    showLoading(`Loading ${scenarioId.replaceAll("-", " ")}…`);
    render();

    document.querySelectorAll(".scenario-tab").forEach((tab) => {
      const active = tab.dataset.scenario === scenarioId;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-pressed", String(active));
    });

    try {
      const replay = await fetchReplay(scenarioId);
      if (token !== state.loadToken) return;

      state.replay = replay;
      state.spawnedByFrame = buildSpawnedCounts(replay.frames);
      tickSlider.max = String(Math.max(0, replay.frames.length - 1));
      tickSlider.value = "0";
      scenarioName.textContent = replay.scenario.name;
      populateFinalMetrics(replay);
      setControlsEnabled(true);
      hideLoading();
      showFrame(0);
    } catch (error) {
      if (token !== state.loadToken) return;
      console.error(error);
      scenarioName.textContent = "Replay unavailable";
      playbackState.textContent = "Error";
      showLoading(
        "Could not load the replay. From the repo root run: python3 viz/serve.py (or python viz/serve.py on Windows), then open http://localhost:8765/viz/",
        true,
      );
    }
  }

  function populateFinalMetrics(replay) {
    for (const [key, element] of Object.entries(metricFields)) {
      element.textContent = formatNumber(replay.metrics[key]);
    }
    document.querySelector("#metrics-badge").textContent =
      `${formatNumber(replay.scenario.ticks)} ticks`;
  }

  function showFrame(index) {
    if (!state.replay) return;

    state.frameIndex = Math.max(0, Math.min(index, state.replay.frames.length - 1));
    const frame = state.replay.frames[state.frameIndex];
    const spawned = state.spawnedByFrame[state.frameIndex] ?? 0;
    const unfinishedEstimate = Math.max(0, spawned - frame.completed);
    const liveCost = frame.waiting + 300 * unfinishedEstimate;
    const finalIndex = state.replay.frames.length - 1;

    tickSlider.value = String(state.frameIndex);
    timelineOutput.textContent = `${formatNumber(frame.tick)} / ${formatNumber(
      state.replay.frames[finalIndex].tick,
    )}`;
    hud.tick.textContent = formatNumber(frame.tick);
    hud.completed.textContent = formatNumber(frame.completed);
    hud.waiting.textContent = formatNumber(frame.waiting);
    hud.vehicles.textContent = formatNumber(frame.vehicles.length);
    hud.cost.textContent = formatNumber(liveCost);

    if (state.frameIndex >= finalIndex && state.playing) {
      setPlaying(false);
    } else {
      updatePlaybackUi();
    }
    render();
  }

  function restart() {
    showFrame(0);
    setPlaying(true);
  }

  function togglePlayback() {
    if (!state.replay) return;
    if (!state.playing && state.frameIndex >= state.replay.frames.length - 1) {
      showFrame(0);
    }
    setPlaying(!state.playing);
  }

  function playbackLoop(timestamp) {
    if (state.playing && state.replay) {
      if (state.lastAnimationTime === null) {
        state.lastAnimationTime = timestamp;
      }

      const elapsed = Math.min(timestamp - state.lastAnimationTime, 250);
      state.lastAnimationTime = timestamp;
      state.tickAccumulator +=
        (elapsed / 1000) * BASE_TICKS_PER_SECOND * state.speed;

      const ticksToAdvance = Math.floor(state.tickAccumulator);
      if (ticksToAdvance > 0) {
        state.tickAccumulator -= ticksToAdvance;
        showFrame(state.frameIndex + ticksToAdvance);
      }
    }
    requestAnimationFrame(playbackLoop);
  }

  function canvasSize() {
    const rect = canvas.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  }

  function projectPoint(x, y, width, height) {
    const worldSize = WORLD_MAX - WORLD_MIN;
    const padding = Math.max(20, Math.min(width, height) * 0.045);
    const scale = Math.min(
      (width - padding * 2) / worldSize,
      (height - padding * 2) / worldSize,
    );
    const drawnSize = worldSize * scale;
    const left = (width - drawnSize) / 2;
    const top = (height - drawnSize) / 2;

    return {
      x: left + (x - WORLD_MIN) * scale,
      y: top + (y - WORLD_MIN) * scale,
      scale,
    };
  }

  function resizeCanvas() {
    const { width, height } = canvasSize();
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const pixelWidth = Math.max(1, Math.round(width * pixelRatio));
    const pixelHeight = Math.max(1, Math.round(height * pixelRatio));

    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    render();
  }

  function drawBackground(width, height) {
    context.fillStyle = "#0d1420";
    context.fillRect(0, 0, width, height);

    const gradient = context.createRadialGradient(
      width * 0.5,
      height * 0.45,
      0,
      width * 0.5,
      height * 0.45,
      Math.max(width, height) * 0.7,
    );
    gradient.addColorStop(0, "rgba(42, 63, 82, 0.22)");
    gradient.addColorStop(1, "rgba(13, 20, 32, 0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    context.strokeStyle = "rgba(143, 156, 175, 0.045)";
    context.lineWidth = 1;
    const spacing = 32;
    for (let x = spacing; x < width; x += spacing) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
    for (let y = spacing; y < height; y += spacing) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
  }

  function traceRoad(road, width, height) {
    const points =
      road.points?.length > 1
        ? road.points
        : [
            { x: road.x1, y: road.y1 },
            { x: road.x2, y: road.y2 },
          ];

    context.beginPath();
    points.forEach((point, index) => {
      const projected = projectPoint(point.x, point.y, width, height);
      if (index === 0) context.moveTo(projected.x, projected.y);
      else context.lineTo(projected.x, projected.y);
    });
  }

  function drawRoads(roads, width, height) {
    context.lineCap = "round";
    context.lineJoin = "round";

    for (const road of roads) {
      traceRoad(road, width, height);
      context.strokeStyle = "rgba(3, 7, 12, 0.72)";
      context.lineWidth = 14;
      context.stroke();

      traceRoad(road, width, height);
      context.strokeStyle = "#2c3848";
      context.lineWidth = 9;
      context.stroke();

      traceRoad(road, width, height);
      context.setLineDash([7, 9]);
      context.strokeStyle = "rgba(194, 207, 221, 0.28)";
      context.lineWidth = 1;
      context.stroke();
      context.setLineDash([]);
    }
  }

  function drawVehicle(vehicle, width, height) {
    const [, x, y, heading] = vehicle;
    const point = projectPoint(x, y, width, height);
    const size = Math.max(4.2, Math.min(6.2, point.scale * 0.012));

    context.save();
    context.translate(point.x, point.y);
    context.rotate((heading * Math.PI) / 180);
    context.beginPath();
    context.moveTo(size, 0);
    context.lineTo(-size * 0.7, size * 0.62);
    context.lineTo(-size * 0.45, 0);
    context.lineTo(-size * 0.7, -size * 0.62);
    context.closePath();
    context.fillStyle = "#f4f8fc";
    context.shadowColor = "rgba(110, 231, 216, 0.38)";
    context.shadowBlur = 5;
    context.fill();
    context.shadowBlur = 0;
    context.strokeStyle = "#0b111b";
    context.lineWidth = 1;
    context.stroke();
    context.restore();
  }

  function drawIntersection(intersection, phase, width, height) {
    const point = projectPoint(intersection.x, intersection.y, width, height);
    const color = PHASE_COLORS[phase] || PHASE_COLORS.ALL_RED;
    const radius = Math.max(6, Math.min(8.5, point.scale * 0.016));

    context.save();
    context.translate(point.x, point.y);
    context.fillStyle = "#0a1019";
    context.beginPath();
    context.arc(0, 0, radius + 4, 0, Math.PI * 2);
    context.fill();

    context.fillStyle = color;
    context.shadowColor = color;
    context.shadowBlur = 12;
    context.beginPath();
    context.arc(0, 0, radius, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;

    context.strokeStyle = "rgba(8, 15, 23, 0.72)";
    context.lineWidth = 2;
    context.beginPath();
    if (phase.startsWith("NS_")) {
      context.moveTo(0, -radius * 0.62);
      context.lineTo(0, radius * 0.62);
    } else if (phase.startsWith("EW_")) {
      context.moveTo(-radius * 0.62, 0);
      context.lineTo(radius * 0.62, 0);
    } else {
      context.moveTo(-radius * 0.45, -radius * 0.45);
      context.lineTo(radius * 0.45, radius * 0.45);
      context.moveTo(radius * 0.45, -radius * 0.45);
      context.lineTo(-radius * 0.45, radius * 0.45);
    }
    context.stroke();
    context.restore();

    context.fillStyle = "rgba(237, 243, 250, 0.72)";
    context.font = "600 10px ui-sans-serif, system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(intersection.id, point.x, point.y - radius - 8);
  }

  function render() {
    const { width, height } = canvasSize();
    if (width <= 0 || height <= 0) return;

    context.clearRect(0, 0, width, height);
    drawBackground(width, height);
    if (!state.replay) return;

    const frame = state.replay.frames[state.frameIndex];
    drawRoads(state.replay.map.roads, width, height);
    for (const vehicle of frame.vehicles) {
      drawVehicle(vehicle, width, height);
    }
    for (const intersection of state.replay.map.intersections) {
      drawIntersection(
        intersection,
        frame.signals[intersection.id] || "ALL_RED",
        width,
        height,
      );
    }
  }

  document.querySelectorAll(".scenario-tab").forEach((tab) => {
    tab.addEventListener("click", () => loadScenario(tab.dataset.scenario));
  });

  playButton.addEventListener("click", togglePlayback);
  restartButton.addEventListener("click", restart);
  tickSlider.addEventListener("input", () => {
    setPlaying(false);
    showFrame(Number(tickSlider.value));
  });
  speedSelect.addEventListener("change", () => {
    state.speed = Number(speedSelect.value);
  });

  document.addEventListener("keydown", (event) => {
    const tagName = document.activeElement?.tagName;
    if (["INPUT", "SELECT", "BUTTON"].includes(tagName)) return;

    if (event.code === "Space") {
      event.preventDefault();
      togglePlayback();
    } else if (event.code === "ArrowRight") {
      event.preventDefault();
      setPlaying(false);
      showFrame(state.frameIndex + 1);
    } else if (event.code === "ArrowLeft") {
      event.preventDefault();
      setPlaying(false);
      showFrame(state.frameIndex - 1);
    }
  });

  new ResizeObserver(resizeCanvas).observe(canvas);
  requestAnimationFrame(playbackLoop);
  loadScenario("balanced-grid");
})();
