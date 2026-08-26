# Talos — Claude Code Context

**Phil's Notes (features/bugs):** `philVault/dev/Talos/phils_notes.md`

---

## What It Is

Fitness routine tracker and benchmarking tool — the best fitness app.

---

## Architecture

Flask app. Obsidian markdown is the database — no SQL/JSON store for workout data. Every UI interaction (checkbox tap, weight edit, notes field) writes straight to the routine's `.md` file on save; every page load re-parses the file fresh. No caching layer.

- `app.py` — routes, template filters, rotation/session-log logic
- `routine_parser.py` — parses the custom routine markdown format (title/meta header, `# Section` groups, `## Exercise - [weight] - [reps]` headers with `**Instruction:**`/`**Rest:**`/`**Progression:**` fields and `- [ ] Set N` checkboxes) and writes back to specific lines (`toggle_checkbox`, `update_weight`, `update_field`, `reset_checkboxes`)
- `templates/routine.html` — Focus Mode (full-screen one-exercise-at-a-time), rest timer, progress-chart navigation — all client-side JS, no framework
- Routine files: `philVault/dev/Talos/routines/*.md` (8 files: chest/back-shoulders/legs/arms × A/B)
- `philVault/dev/Talos/rotation_state.json` — which routine is "Up Next" (gold highlight on the index page). 8-day A→B rotation; advances when a workout is finished via the Focus Mode "Finish Workout" button.
- `philVault/dev/Talos/session_log.md` — permanent dated history, auto-appended on Finish (routine, sets completed, weights, session notes). Routine file checkboxes auto-reset after logging.

---

## Running & Deploying

```bash
# Local dev
python3 app.py   # http://localhost:5009
```

**Production:** deployed to `pi@duobrain.local` as systemd service `talos`, port 5009 (`http://duobrain.local:5009`). App dir `/opt/talos/app`, venv `/opt/talos/venv`, gunicorn via `deploy/gunicorn.conf.py` + `deploy/talos.service`. `TALOS_ROUTINES_DIR` env var (in `/opt/talos/app/.env`) points at `/opt/duobrain/vault/dev/Talos/routines` — the same Obsidian vault, kept in sync with Phil's desktop via Syncthing, so Pi edits and desktop Obsidian edits are the same data.

To redeploy: `bash deploy/deploy-to-pi.sh` (syncs files + restarts service — Phil must run this himself with the `!` prefix; Claude is blocked from executing Pi deploy commands directly by `~/.claude/hooks/block-deploy.py`).

---

## Key Paths

| Item | Path |
|------|------|
| Vault docs | `philVault/dev/Talos/` |
| Project dir | `/home/phil/Dev/Talos` |
