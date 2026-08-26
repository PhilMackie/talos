import json
import os
import re
from datetime import date

from flask import Flask, render_template, jsonify, request, abort

from routine_parser import (
    parse_routine, toggle_checkbox, update_field, update_weight, reset_checkboxes, set_exercise_skip,
)

VAULT_ROUTINES_DIR = os.environ.get(
    'TALOS_ROUTINES_DIR',
    '/home/phil/Documents/philVault/dev/Talos/routines',
)

VAULT_TALOS_DIR = os.path.dirname(VAULT_ROUTINES_DIR.rstrip('/'))
ROTATION_STATE_PATH = os.path.join(VAULT_TALOS_DIR, 'rotation_state.json')
SESSION_LOG_PATH = os.path.join(VAULT_TALOS_DIR, 'session_log.md')

ROTATION = [
    'arms-a', 'back-shoulders-a', 'chest-a', 'legs-a',
    'arms-b', 'back-shoulders-b', 'chest-b', 'legs-b',
]

DEBUG_SLUG = 'debug'
DEBUG_ROUTINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'debug.md')

app = Flask(__name__)


def load_next_slug():
    try:
        with open(ROTATION_STATE_PATH) as f:
            data = json.load(f)
        slug = data.get('next_slug')
        if slug in ROTATION:
            return slug
    except (FileNotFoundError, ValueError, OSError):
        pass
    return ROTATION[0]


def save_next_slug(slug):
    with open(ROTATION_STATE_PATH, 'w') as f:
        json.dump({'next_slug': slug}, f)


def advance_rotation(completed_slug):
    if completed_slug not in ROTATION:
        return
    if load_next_slug() != completed_slug:
        return
    idx = ROTATION.index(completed_slug)
    save_next_slug(ROTATION[(idx + 1) % len(ROTATION)])


def routine_path(slug):
    if slug == DEBUG_SLUG:
        if not os.path.isfile(DEBUG_ROUTINE_PATH):
            abort(404)
        return DEBUG_ROUTINE_PATH
    if not re.match(r'^[a-z0-9-]+$', slug):
        abort(404)
    path = os.path.join(VAULT_ROUTINES_DIR, f'{slug}.md')
    if not os.path.isfile(path):
        abort(404)
    return path


@app.template_filter('clean_weight')
def clean_weight(weight):
    if '___' in weight:
        return ''
    return weight


@app.template_filter('rest_seconds')
def rest_seconds(rest):
    if not rest:
        return ''
    nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', rest)]
    if not nums:
        return ''
    value = max(nums)
    seconds = value * 60 if re.search(r'\bmin', rest, re.I) else value
    return int(round(seconds))


@app.template_filter('clean_value')
def clean_value(field):
    value = field['value']
    if field['label'].strip().lower() == 'energy':
        m = re.search(r'\d+', value)
        return m.group(0) if m else ''
    cleaned = re.sub(r'_+', '', value).strip()
    return cleaned


def build_session_log_entry(routine):
    lines = [f"## {date.today().isoformat()} — {routine['title']}", '']

    notes_section = next((s for s in routine['sections'] if s['is_notes']), None)
    if notes_section:
        summary_bits = []
        notes_text = ''
        for f in notes_section['fields']:
            val = clean_value(f)
            if not val:
                continue
            if f['label'].strip().lower() == 'notes':
                notes_text = val
            else:
                summary_bits.append(f"**{f['label']}:** {val}")
        if summary_bits:
            lines.append(' · '.join(summary_bits))
            lines.append('')

    for section in routine['sections']:
        if section['is_notes'] or not section['exercises']:
            continue
        lines.append(f"**{section['name']}**")
        for ex in section['exercises']:
            weight = clean_weight(ex['weight'])
            reps = ex['reps']
            if weight and reps:
                spec = f"{weight} × {reps}"
            else:
                spec = weight or reps
            total = len(ex['sets'])
            done = sum(1 for s in ex['sets'] if s['checked'])
            skipped = total > 0 and all(s['skipped'] for s in ex['sets'])
            line = f"- {ex['name']}"
            if spec:
                line += f" — {spec}"
            if total:
                line += f" ({done}/{total} sets)"
            if skipped:
                line += " — Skipped"
            lines.append(line)
        lines.append('')

    if notes_section and notes_text:
        lines.append(f"**Notes:** {notes_text}")
        lines.append('')

    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def append_session_log(routine):
    if not os.path.exists(SESSION_LOG_PATH):
        with open(SESSION_LOG_PATH, 'w') as f:
            f.write('# Talos — Session Log\n\n')
    with open(SESSION_LOG_PATH, 'a') as f:
        f.write(build_session_log_entry(routine) + '\n')


@app.route('/')
def index():
    routines = []
    if os.path.isdir(VAULT_ROUTINES_DIR):
        for filename in sorted(os.listdir(VAULT_ROUTINES_DIR)):
            if not filename.endswith('.md'):
                continue
            slug = filename[:-3]
            try:
                routine = parse_routine(os.path.join(VAULT_ROUTINES_DIR, filename))
            except Exception:
                continue
            exercise_count = sum(len(s['exercises']) for s in routine['sections'] if not s['is_notes'])
            routines.append({
                'slug': slug,
                'title': routine['title'],
                'meta': routine['meta'],
                'exercise_count': exercise_count,
            })
    next_slug = load_next_slug()
    if next_slug in ROTATION:
        start = ROTATION.index(next_slug)
        order = ROTATION[start:] + ROTATION[:start]
    else:
        order = ROTATION
    order_index = {s: i for i, s in enumerate(order)}
    routines.sort(key=lambda r: order_index.get(r['slug'], len(order)))
    for r in routines:
        r['is_next'] = r['slug'] == next_slug
    return render_template('index.html', routines=routines)


@app.route('/routine/<slug>')
def routine_view(slug):
    path = routine_path(slug)
    routine = parse_routine(path)
    return render_template('routine.html', slug=slug, routine=routine)


@app.route('/routine/<slug>/toggle', methods=['POST'])
def toggle(slug):
    path = routine_path(slug)
    data = request.get_json(force=True)
    line = int(data['line'])
    try:
        checked = toggle_checkbox(path, line)
    except (ValueError, IndexError):
        abort(400)
    return jsonify({'checked': checked})


@app.route('/routine/<slug>/weight', methods=['POST'])
def weight(slug):
    path = routine_path(slug)
    data = request.get_json(force=True)
    line = int(data['line'])
    value = data.get('value', '')
    try:
        update_weight(path, line, value)
    except (ValueError, IndexError):
        abort(400)
    return jsonify({'ok': True, 'value': value})


@app.route('/routine/<slug>/skip', methods=['POST'])
def skip_exercise(slug):
    path = routine_path(slug)
    data = request.get_json(force=True)
    lines = [int(l) for l in data.get('lines', [])]
    skip = bool(data.get('skip', True))
    try:
        set_exercise_skip(path, lines, skip)
    except (ValueError, IndexError):
        abort(400)
    return jsonify({'ok': True, 'skipped': skip})


@app.route('/routine/<slug>/field', methods=['POST'])
def field(slug):
    path = routine_path(slug)
    data = request.get_json(force=True)
    label = data['label']
    start_line = int(data['start_line'])
    end_line = int(data['end_line'])
    value = data.get('value', '')
    update_field(path, label, start_line, end_line, value)
    return jsonify({'ok': True})


@app.route('/rotation/complete', methods=['POST'])
def rotation_complete():
    data = request.get_json(force=True)
    slug = data.get('slug', '')
    path = routine_path(slug)
    if slug != DEBUG_SLUG:
        append_session_log(parse_routine(path))
    reset_checkboxes(path)
    advance_rotation(slug)
    return jsonify({'next_slug': load_next_slug()})


@app.route('/rotation/set', methods=['POST'])
def rotation_set():
    data = request.get_json(force=True)
    slug = data.get('slug', '')
    if slug not in ROTATION:
        abort(400)
    save_next_slug(slug)
    return jsonify({'next_slug': slug})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)
