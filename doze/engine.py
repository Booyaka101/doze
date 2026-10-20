"""Constrained recipes and reversible, no-overwrite local file moves."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4


class SafetyError(ValueError):
    pass


PROTECTED = {'.exe', '.dll', '.com', '.bat', '.cmd', '.ps1', '.sh', '.py', '.js',
             '.msi', '.lnk', '.key', '.pem', '.sqlite', '.db'}
FIELDS = {'extensions', 'name_contains', 'name_starts_with', 'min_bytes', 'max_bytes'}
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['name', 'description', 'rules'],
    'properties': {
        'name': {'type': 'string'}, 'description': {'type': 'string'},
        'rules': {'type': 'array', 'minItems': 1, 'maxItems': 12, 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['label', 'when', 'folder'],
            'properties': {
                'label': {'type': 'string'}, 'folder': {'type': 'string'},
                'when': {'type': 'object', 'additionalProperties': False,
                         'properties': {
                             'extensions': {'type': 'array', 'items': {'type': 'string'}},
                             'name_contains': {'type': 'array', 'items': {'type': 'string'}},
                             'name_starts_with': {'type': 'string'},
                             'min_bytes': {'type': 'integer', 'minimum': 0},
                             'max_bytes': {'type': 'integer', 'minimum': 0}}}}}}}}


def validate_recipe(raw):
    if not isinstance(raw, dict) or set(raw) != {'name', 'description', 'rules'}:
        raise SafetyError('Recipe must contain only name, description and rules.')
    for field in ('name', 'description'):
        if not isinstance(raw[field], str) or not 1 <= len(raw[field]) <= 1000:
            raise SafetyError(f'Invalid {field}.')
    if not isinstance(raw['rules'], list) or not 1 <= len(raw['rules']) <= 12:
        raise SafetyError('Use 1 to 12 rules.')
    for rule in raw['rules']:
        if not isinstance(rule, dict) or set(rule) != {'label', 'when', 'folder'}:
            raise SafetyError('A rule needs only label, when and folder.')
        if not isinstance(rule['label'], str) or not 1 <= len(rule['label']) <= 200:
            raise SafetyError('Invalid rule label.')
        folder = rule['folder']
        if not isinstance(folder, str) or len(folder) > 150 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _/-]*', folder):
            raise SafetyError('Folders must be plain relative names, without templates or commands.')
        parts = folder.split('/')
        if len(parts) > 4 or any(not part or part.strip() != part or part.upper() in
                               {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                                *(f'LPT{i}' for i in range(1, 10))} for part in parts):
            raise SafetyError('Unsafe folder name.')
        when = rule['when']
        if not isinstance(when, dict) or not when or not set(when) <= FIELDS:
            raise SafetyError('Rules require at least one supported condition.')
        for key, value in when.items():
            if key in {'extensions', 'name_contains'}:
                if not isinstance(value, list) or not 1 <= len(value) <= 30 or any(
                    not isinstance(item, str) or not item.strip() or len(item) > 100 for item in value
                ):
                    raise SafetyError(f'Invalid {key}.')
                if key == 'extensions' and any(not re.fullmatch(r'\.[A-Za-z0-9]{1,12}', item) for item in value):
                    raise SafetyError('Extensions must look like .png or .pdf.')
            elif key == 'name_starts_with':
                if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
                    raise SafetyError('Invalid prefix.')
            elif type(value) is not int or not 0 <= value <= 2**40:
                raise SafetyError('Size conditions must be non-negative integers.')
        if when.get('min_bytes', 0) > when.get('max_bytes', 2**40):
            raise SafetyError('Minimum size exceeds maximum size.')
    return json.loads(json.dumps(raw))


def matches(when, name, size):
    lower = name.lower()
    return (('extensions' not in when or Path(lower).suffix in [e.lower() for e in when['extensions']])
            and ('name_contains' not in when or any(s.lower() in lower for s in when['name_contains']))
            and ('name_starts_with' not in when or lower.startswith(when['name_starts_with'].lower()))
            and size >= when.get('min_bytes', 0) and size <= when.get('max_bytes', 2**40))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def is_link(path):
    # Python 3.11 lacks Path.is_junction. Windows reparse points include junctions.
    if not path.exists() and not path.is_symlink():
        return False
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)


class Engine:
    def __init__(self, workspace, state):
        original = Path(workspace).absolute()
        if any(is_link(p) for p in (original, *original.parents)):
            raise SafetyError('Workspace cannot be a link.')
        original.mkdir(parents=True, exist_ok=True)
        self.root = original.resolve()
        state = Path(state)
        state.mkdir(parents=True, exist_ok=True)
        self.database = state / 'doze.sqlite'
        self.lock = threading.RLock()
        with self.db() as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS recipes(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, payload TEXT NOT NULL, used INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, plan_id TEXT UNIQUE NOT NULL,
                    payload TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS actions(run_id TEXT NOT NULL, position INTEGER NOT NULL,
                    payload TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(run_id,position));
            ''')
            binding = con.execute("SELECT value FROM settings WHERE key='workspace'").fetchone()
            if binding is not None and binding[0] != str(self.root):
                raise SafetyError('This state directory belongs to a different workspace. Choose a separate --state directory.')
            con.execute("INSERT OR IGNORE INTO settings VALUES('workspace',?)", (str(self.root),))
            con.execute("UPDATE runs SET status='interrupted' WHERE status='running'")

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.database, timeout=20)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def path(self, relative):
        if not isinstance(relative, str) or not relative or '\\' in relative:
            raise SafetyError('Invalid relative path.')
        parts = relative.split('/')
        if any(p in {'', '.', '..'} or ':' in p for p in parts) or relative.startswith('/'):
            raise SafetyError('Path escapes the workspace.')
        path = self.root
        for part in parts:
            path = path / part
            if is_link(path):
                raise SafetyError('Links and junctions are never followed.')
        if not path.resolve().is_relative_to(self.root):
            raise SafetyError('Path escapes the workspace.')
        return path

    def inventory(self):
        result = []
        for path in sorted(self.root.iterdir(), key=lambda p: p.name.lower()):
            reason = None
            if path.name.startswith('.') or path.suffix.lower() in PROTECTED:
                reason = 'Protected file'
            elif is_link(path):
                reason = 'Link or junction'
            elif not path.is_file():
                reason = 'Folder: not scanned recursively'
            elif path.stat().st_size > 128 * 1024 * 1024:
                reason = 'Over the 128 MiB per-file limit'
            result.append({'name': path.name, 'size': path.lstat().st_size, 'held': reason})
            if len(result) > 1000:
                raise SafetyError('Limit is 1,000 top-level entries. Use a smaller folder.')
        return result

    def save_recipe(self, recipe):
        recipe = validate_recipe(recipe)
        ident = uuid4().hex
        with self.db() as con:
            con.execute('INSERT INTO recipes VALUES(?,?,?)', (ident, json.dumps(recipe), stamp()))
        return {'id': ident, 'recipe': recipe}

    def recipes(self):
        with self.db() as con:
            return [{'id': row['id'], 'recipe': json.loads(row['payload'])}
                    for row in con.execute('SELECT * FROM recipes ORDER BY created DESC')]

    def recipe(self, ident):
        with self.db() as con:
            row = con.execute('SELECT payload FROM recipes WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise SafetyError('Recipe not found.')
        return json.loads(row['payload'])

    def preview(self, ident):
        with self.lock:
            recipe = self.recipe(ident)
            moves, held, targets = [], [], set()
            for item in self.inventory():
                name = item['name']
                if item['held']:
                    held.append({'name': name, 'reason': item['held']})
                    continue
                rule = next((r for r in recipe['rules'] if matches(r['when'], name, item['size'])), None)
                if rule is None:
                    held.append({'name': name, 'reason': 'No matching rule: left for you'})
                    continue
                target = rule['folder'] + '/' + name
                try:
                    dst = self.path(target)
                    if dst.exists() or target.casefold() in targets:
                        raise SafetyError('Destination already exists')
                    # A source file may occupy a requested destination directory.
                    if any(parent.exists() and not parent.is_dir() for parent in dst.parents if parent != self.root.parent):
                        raise SafetyError('Destination parent is not a folder')
                    moves.append({'source': name, 'destination': target, 'sha256': digest(self.path(name)),
                                  'bytes': item['size'], 'rule': rule['label']})
                    targets.add(target.casefold())
                except (SafetyError, OSError) as error:
                    held.append({'name': name, 'reason': str(error)})
            plan = {'id': uuid4().hex, 'recipe_id': ident, 'name': recipe['name'], 'created': stamp(),
                    'moves': moves, 'held': held, 'model_calls': 0}
            with self.db() as con:
                con.execute('INSERT INTO plans(id,payload) VALUES(?,?)', (plan['id'], json.dumps(plan)))
            return plan

    def probe(self, ident, cases):
        if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
            raise SafetyError('Provide 1 to 100 hypothetical files.')
        recipe = self.recipe(ident)
        results = []
        for case in cases:
            name, expected = case.get('name'), case.get('expected')
            size = case.get('bytes', 1024)
            if not isinstance(name, str) or not 1 <= len(name) <= 255 or '/' in name or '\\' in name:
                raise SafetyError('Probes require plain filenames, not paths.')
            if not isinstance(expected, str) or type(size) is not int or size < 0:
                raise SafetyError('Invalid probe expectation or size.')
            protected = name.startswith('.') or Path(name).suffix.lower() in PROTECTED or size > 128 * 1024 * 1024
            rule = None if protected else next((r for r in recipe['rules'] if matches(r['when'], name, size)), None)
            actual = rule['folder'] if rule else 'HOLD'
            results.append({'name': name, 'expected': expected, 'actual': actual, 'passed': expected == actual})
        return {'cases': results, 'passed': all(r['passed'] for r in results), 'model_calls': 0}

    def _check_move(self, action):
        src, dst = self.path(action['source']), self.path(action['destination'])
        if not src.is_file() or digest(src) != action['sha256']:
            raise SafetyError(f"Source changed since preview: {action['source']}. Rehearse again.")
        if dst.exists():
            raise SafetyError(f"Destination exists: {action['destination']}. Nothing overwritten.")
        return src, dst

    def _action_status(self, run_id, position, status):
        with self.db() as con:
            con.execute('UPDATE actions SET status=? WHERE run_id=? AND position=?', (status, run_id, position))

    def execute(self, plan_id):
        with self.lock:
            with self.db() as con:
                row = con.execute('SELECT * FROM plans WHERE id=?', (plan_id,)).fetchone()
                if row is None or row['used']:
                    raise SafetyError('Preview not found or already used. Rehearse again.')
                plan = json.loads(row['payload'])
                if not plan['moves']:
                    raise SafetyError('There are no approved moves to run.')
                for action in plan['moves']:
                    self._check_move(action)
                run_id = uuid4().hex
                con.execute('UPDATE plans SET used=1 WHERE id=?', (plan_id,))
                con.execute('INSERT INTO runs VALUES(?,?,?,?,?)', (run_id, plan_id, json.dumps(plan), 'running', stamp()))
                for position, action in enumerate(plan['moves']):
                    con.execute('INSERT INTO actions VALUES(?,?,?,?)', (run_id, position, json.dumps(action), 'pending'))
            try:
                for position, action in enumerate(plan['moves']):
                    src, dst = self._check_move(action)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    self.path(action['destination'])
                    # Exclusive hard-link creation cannot clobber a destination. Both paths
                    # stay on one volume; unlink happens only after the intent is durable.
                    self._action_status(run_id, position, 'linking')
                    os.link(src, dst)
                    self._action_status(run_id, position, 'linked')
                    src.unlink()
                    self._action_status(run_id, position, 'moved')
                with self.db() as con:
                    con.execute('UPDATE runs SET status=? WHERE id=?', ('completed', run_id))
            except Exception:
                with self.db() as con:
                    con.execute('UPDATE runs SET status=? WHERE id=?', ('interrupted', run_id))
                # Never guess at recovery. The receipt remains available for checked undo.
                raise SafetyError(f'Run interrupted. Review receipt {run_id} and use Undo to recover.')
            return self.run(run_id)

    def run(self, ident):
        with self.db() as con:
            row = con.execute('SELECT * FROM runs WHERE id=?', (ident,)).fetchone()
            if row is None:
                raise SafetyError('Run not found.')
            actions = [dict(a) for a in con.execute('SELECT * FROM actions WHERE run_id=? ORDER BY position', (ident,))]
        return {'id': ident, 'created': row['created'], 'status': row['status'],
                'plan': json.loads(row['payload']),
                'actions': [{'position': a['position'], 'status': a['status'], **json.loads(a['payload'])} for a in actions]}

    def runs(self):
        with self.db() as con:
            ids = [row[0] for row in con.execute('SELECT id FROM runs ORDER BY created DESC LIMIT 50')]
        return [self.run(ident) for ident in ids]

    def undo(self, ident):
        with self.lock:
            run = self.run(ident)
            if run['status'] == 'undone':
                raise SafetyError('This run was already undone.')
            recover = []
            for action in reversed(run['actions']):
                if action['status'] in {'pending', 'undone'}:
                    continue
                src, dst = self.path(action['source']), self.path(action['destination'])
                if not dst.exists():
                    if src.is_file() and digest(src) == action['sha256']:
                        continue
                    raise SafetyError('Recovery conflict: both expected paths are missing or changed.')
                if not dst.is_file() or digest(dst) != action['sha256']:
                    raise SafetyError(f"Undo blocked: {action['destination']} changed after the run.")
                if src.exists() and not os.path.samefile(src, dst):
                    raise SafetyError(f"Undo blocked: {action['source']} already exists.")
                recover.append((action, src, dst))
            for action, src, dst in recover:
                if not src.exists():
                    os.link(dst, src)
                dst.unlink()
                self._action_status(ident, action['position'], 'undone')
            with self.db() as con:
                con.execute('UPDATE runs SET status=? WHERE id=?', ('undone', ident))
            return self.run(ident)
