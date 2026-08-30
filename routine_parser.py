import re

CHECKBOX_RE = re.compile(r'^(\s*)-\s\[([ xX-])\]\s*(.*)$')
EXERCISE_RE = re.compile(r'^##\s+(.*?)\s*-\s*\[([^\]]*)\]\s*-\s*\[([^\]]*)\]\s*$')
BOLD_FIELD_RE = re.compile(r'^\*\*([^*]+):\*\*\s*(.*)$')
SECTION_RE = re.compile(r'^#\s+(.*)$')

NOTES_SECTION_NAMES = {'session notes'}


def parse_routine(path):
    with open(path, 'r') as f:
        lines = f.read().splitlines()

    title = None
    meta = {}
    sections = []
    current_section = None
    current_exercise = None
    in_preamble = True

    def ensure_section(name='Exercises'):
        nonlocal current_section
        current_section = {
            'name': name,
            'is_notes': name.strip().lower() in NOTES_SECTION_NAMES,
            'exercises': [],
            'fields': [],
        }
        sections.append(current_section)

    for i, raw_line in enumerate(lines):
        line_no = i + 1
        line = raw_line.rstrip()

        if not line.strip():
            continue
        if line.strip() == '---':
            continue

        m = SECTION_RE.match(line) if not line.startswith('##') else None
        if m:
            if title is None:
                title = m.group(1).strip()
                in_preamble = True
                continue
            in_preamble = False
            ensure_section(m.group(1).strip())
            current_exercise = None
            continue

        m = EXERCISE_RE.match(line)
        if m:
            in_preamble = False
            if current_section is None:
                ensure_section()
            current_exercise = {
                'name': m.group(1).strip(),
                'weight': m.group(2).strip(),
                'reps': m.group(3).strip(),
                'header_line': line_no,
                'instruction': '',
                'instruction_line': None,
                'targets': '',
                'rest': '',
                'progression': '',
                'coaches_notes': '',
                'coaches_notes_line': None,
                'sets': [],
            }
            current_section['exercises'].append(current_exercise)
            continue

        m = BOLD_FIELD_RE.match(line)
        if m:
            label, value = m.group(1).strip(), m.group(2).strip()
            key = label.lower()
            if current_exercise is not None and not current_exercise['sets']:
                if key == 'instruction':
                    current_exercise['instruction'] = value
                    current_exercise['instruction_line'] = line_no
                elif key == 'targets':
                    current_exercise['targets'] = value
                elif key == 'rest':
                    current_exercise['rest'] = value
                elif key == 'progression':
                    current_exercise['progression'] = value
                elif key == 'coaches notes':
                    current_exercise['coaches_notes'] = value
                    current_exercise['coaches_notes_line'] = line_no
                continue
            if in_preamble or current_section is None:
                meta[label] = value
                continue
            if current_section is not None:
                current_section['fields'].append({
                    'label': label,
                    'value': value,
                    'line': line_no,
                    'value_start_line': line_no,
                    'value_end_line': line_no,
                })
                continue

        m = CHECKBOX_RE.match(line)
        if m:
            if current_exercise is None:
                if current_section is None:
                    ensure_section()
                current_exercise = {
                    'name': current_section['name'],
                    'weight': '', 'reps': '', 'header_line': None, 'instruction': '',
                    'instruction_line': None, 'targets': '', 'rest': '', 'progression': '',
                    'coaches_notes': '', 'coaches_notes_line': None,
                    'sets': [],
                }
                current_section['exercises'].append(current_exercise)
            mark = m.group(2)
            checked = mark.lower() == 'x'
            skipped = mark == '-'
            label = m.group(3).strip() or f"Set {len(current_exercise['sets']) + 1}"
            current_exercise['sets'].append({
                'line': line_no,
                'checked': checked,
                'skipped': skipped,
                'label': label,
            })
            continue

        if current_section is not None and current_section['is_notes'] and current_section['fields']:
            last_field = current_section['fields'][-1]
            if last_field['label'].lower() == 'notes':
                if last_field['value']:
                    last_field['value'] += '\n' + line.strip()
                else:
                    last_field['value'] = line.strip()
                last_field['value_end_line'] = line_no

    return {
        'title': title or 'Untitled Routine',
        'meta': meta,
        'sections': sections,
    }


def reset_checkboxes(path):
    with open(path, 'r') as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines):
        m = CHECKBOX_RE.match(line)
        if m and m.group(2) != ' ':
            indent, _mark, rest = m.groups()
            lines[i] = f'{indent}- [ ] {rest}'.rstrip()
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def toggle_checkbox(path, line_no):
    with open(path, 'r') as f:
        lines = f.read().splitlines()
    idx = line_no - 1
    m = CHECKBOX_RE.match(lines[idx])
    if not m:
        raise ValueError('Line is not a checkbox')
    indent, mark, rest = m.groups()
    new_mark = ' ' if mark.lower() == 'x' else 'x'
    lines[idx] = f'{indent}- [{new_mark}] {rest}'.rstrip()
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return new_mark == 'x'


def set_exercise_skip(path, lines, skip):
    with open(path, 'r') as f:
        file_lines = f.read().splitlines()
    mark = '-' if skip else ' '
    for line_no in lines:
        idx = line_no - 1
        m = CHECKBOX_RE.match(file_lines[idx])
        if not m:
            raise ValueError('Line is not a checkbox')
        indent, _mark, rest = m.groups()
        file_lines[idx] = f'{indent}- [{mark}] {rest}'.rstrip()
    with open(path, 'w') as f:
        f.write('\n'.join(file_lines) + '\n')


def update_field(path, label, start_line, end_line, value):
    with open(path, 'r') as f:
        lines = f.read().splitlines()
    new_lines = value.split('\n') if value else ['']
    new_lines[0] = f'**{label}:** {new_lines[0]}'
    lines[start_line - 1:end_line] = new_lines
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def update_weight(path, line_no, new_weight):
    with open(path, 'r') as f:
        lines = f.read().splitlines()
    idx = line_no - 1
    m = EXERCISE_RE.match(lines[idx])
    if not m:
        raise ValueError('Line is not an exercise header')
    name, _weight, reps = m.groups()
    lines[idx] = f'## {name} - [{new_weight}] - [{reps}]'
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
