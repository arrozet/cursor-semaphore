(() => {
  "use strict";

  // Polls the Python/Node hot-reload endpoint. No-ops on plain static hosts.
  const endpoints = ["/__viz_watch", "/viz/__viz_watch"];
  let current = null;
  let fails = 0;

  async function tick() {
    if (fails > 8) {
      return;
    }
    for (const endpoint of endpoints) {
      try {
        const response = await fetch(`${endpoint}?t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          continue;
        }
        const data = await response.json();
        fails = 0;
        if (current === null) {
          current = data.v;
        } else if (data.v !== current) {
          location.reload();
          return;
        }
        return;
      } catch (_) {
        // try next endpoint
      }
    }
    fails += 1;
  }

  setInterval(tick, 700);
  tick();
})();
