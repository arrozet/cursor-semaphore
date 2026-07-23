# Traffic replay viewer

Plain HTML/CSS/JS (no frameworks) canvas viewer for the three public Traffic Lights Arena replay files in `../maps/basic/`.

## Run (hot reload, macOS + Windows)

From the **repository root** (needs Python 3 only):

```bash
python3 viz/serve.py
```

Windows (if `python3` is not on PATH):

```bat
python viz\serve.py
```

Opens [http://localhost:8765/viz/](http://localhost:8765/viz/) and reloads when files under `viz/` change.

Optional port:

```bash
python3 viz/serve.py --port 9000
```

Wrappers (same thing): `./viz/serve.sh` (Unix) · `viz\serve.cmd` (Windows).

Do **not** open `index.html` with a `file://` URL — browsers block local `fetch()` of the JSON maps.

## Notes

- Live cost estimate: cumulative waiting ticks + `300 ×` unfinished (spawned but not completed). Matches recorded final cost on the last frame.
- Does not modify the replay JSON files.
