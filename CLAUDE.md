# Talos — Claude Code Context

**Phil's Notes (features/bugs):** `philVault/dev/Talos/phils_notes.md`

---

## What It Is

Fitness routine tracker and benchmarking tool — the best fitness app.

---

## Architecture

Flask app. Obsidian markdown is the database — no SQL/JSON store for workout data. Every UI interaction (checkbox tap, weight edit, notes field) writes straight to the routine's `.md` file on save; every page load re-parses the file fresh. No caching layer.

- `app.py` — routes, template filters, rotation/session-log/streak logic
- `routine_parser.py` — parses the custom routine markdown format (title/meta header, `# Section` groups, `## Exercise - [weight] - [reps]` headers with `**Instruction:**`/`**Targets:**`/`**Rest:**`/`**Progression:**`/`**Coaches Notes:**` fields and `- [ ] Set N` checkboxes) and writes back to specific lines (`toggle_checkbox`, `update_weight`, `update_field`, `clear_fields`, `reset_checkboxes`, `set_exercise_skip`). Checkboxes are 3-state: `[ ]` blank, `[x]` done, `[-]` skipped.
- `templates/base.html` — shared shell: topbar (brand + weekly streak indicator, always visible), the `.forge-embers` ambient background layer (drifting cinder/smoke particles, pure CSS, respects `prefers-reduced-motion`)
- `templates/routine.html` — Focus Mode (full-screen one-exercise-at-a-time), rest timer, progress-chart navigation, per-exercise **Skip** (yellow-dash, doesn't count as done) and **Defer to End** (client-side reorder to just before Stretch, not written to the `.md`), **Back** (exits Focus Mode without clearing progress), **Home Gym Day** toggle (top-right, jumps between a routine and its `alt-*` counterpart) — all client-side JS, no framework. A pencil icon next to the routine title (and, in Focus Mode, next to Back) toggles page-wide **edit mode** (`body.edit-mode`), swapping the read-only Targets/Rest/Progression/Coaches Notes/Instruction display for inline `field-input` text inputs wired through the same `/routine/<slug>/field` autosave path as Session Notes. Off by default so the normal view stays uncluttered. (Coaches Notes editing was briefly added, then reverted read-only on 2026-08-30, then reintroduced under this edit-mode toggle — see `phils_notes.md`.)
- `fixtures/debug.md` / `fixtures/alt-debug.md` — QA sandbox routines ("Lorum"/"Lorum2" exercises), served at `/routine/debug` and `/routine/alt-debug` via the `DEBUG_SLUGS` special-case in `app.py`. Live in the app repo, not the vault; finishing either never appends to `session_log.md`/`streak.md` or advances rotation.
- Routine files: `philVault/dev/Talos/routines/*.md` (16 files: chest/back-shoulders/legs/arms × A/B, plus an `alt-*` home/no-equipment version of each)
- `philVault/dev/Talos/rotation_state.json` — which routine is "Up Next" (gold highlight on the index page). 8-day A→B rotation; advances when a workout is finished via the Focus Mode "Finish Workout" button. `alt-*` (Home Gym Day) completions advance it too, mapped to their base slug (`alt-arms-b` advances the same as `arms-b`).
- `philVault/dev/Talos/session_log.md` — permanent dated history, auto-appended on Finish (routine, sets completed, weights, session notes). Routine file checkboxes auto-reset after logging, and the Session Notes fields (Energy/Pain/Notes) are blanked in the routine `.md` right after being logged, so they don't reappear pre-filled next rotation.
- `philVault/dev/Talos/streak.md` — weekly completion tracker (Monday-start week, min 3/goal 4), appended on the same Finish event as `session_log.md`. Drives the 4-square indicator in the topbar (orange <3, green at 3, gold at 4) via a Flask `context_processor` so it's injected into every template.

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
| GitHub repo | `git@github.com:PhilMackie/talos.git` (main) |
