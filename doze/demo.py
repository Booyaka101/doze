"""Original synthetic fixtures, never a user's actual Downloads."""
from .engine import SafetyError

PROMPT = ('Put PNG, JPG and WEBP files whose names start with screenshot into Screenshots. '
          'Put PDF files with invoice or receipt in their names into Finance. '
          'Put ZIP files into Archives. Leave everything else alone.')
RECIPE = {
    'name': 'The five-minute Friday reset',
    'description': 'Collect screenshots, financial PDFs and archives. Leave the rest alone.',
    'rules': [
        {'label': 'Screenshots together', 'when': {'extensions': ['.png', '.jpg', '.webp'],
                                                'name_starts_with': 'screenshot'}, 'folder': 'Screenshots'},
        {'label': 'Invoices and receipts', 'when': {'extensions': ['.pdf'],
                                                  'name_contains': ['invoice', 'receipt']}, 'folder': 'Finance'},
        {'label': 'Archives away', 'when': {'extensions': ['.zip']}, 'folder': 'Archives'}]}


def seed(engine, batch='first'):
    if batch not in {'first', 'next'}:
        raise SafetyError('Unknown sample batch.')
    suffix = '20' if batch == 'first' else '21'
    files = {
        f'Screenshot 2026-10-{suffix} dashboard.png': b'DOZE SYNTHETIC IMAGE FIXTURE\n' * 41,
        f'screenshot-2026-10-{suffix}-design.webp': b'DOZE SYNTHETIC WEBP FIXTURE\n' * 28,
        f'invoice-studio-oct{suffix}.pdf': b'%PDF-1.4\n% Synthetic Doze invoice, not a real PDF\n' * 22,
        f'coffee-receipt-{suffix}.pdf': b'%PDF-1.4\n% Synthetic Doze receipt, not a real PDF\n' * 17,
        f'assets-export-{suffix}.zip': b'PK\x03\x04DOZE SYNTHETIC ARCHIVE FIXTURE\n' * 31,
        f'holiday-{suffix}.jpg': b'DOZE SYNTHETIC PHOTO, not a screenshot\n' * 39,
        f'project-notes-{suffix}.txt': b'Decide what matters. Leave this file exactly where it is.\n',
        '.env.example': b'SYNTHETIC_ONLY=true\n',
        'do-not-run.ps1': b'# Synthetic protected script fixture. No executable commands.\n'}
    added = []
    with engine.lock:
        for name, content in files.items():
            path = engine.path(name)
            # Adding samples is idempotent and never overwrites even synthetic edits.
            if not path.exists():
                with path.open('xb') as stream:
                    stream.write(content)
                added.append(name)
    return added
