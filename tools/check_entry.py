"""Check local competition claims without inference or any public actions."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    entry = (ROOT / 'submission/ENTRY.md').read_text(encoding='utf-8')
    teaching = load('evidence/close-grounded-teaching.json')
    workflow = load('evidence/close-workflow-smoke-gemma.json')
    year = load('evidence/close-synthetic-year-gemma.json')
    offline = load('evidence/close-offline-proof-gemma.json')
    recording = load('evidence/close-entry-demo.json')
    cases = teaching['cases']
    checks = {
        'unpublished frontmatter': 'published: false' in entry,
        'required tags': 'tags: devchallenge, hf26challenge,' in entry,
        'official template sections': all('## ' + title in entry for title in (
            'What I Built', 'Demo', 'Code', 'How I Built It', 'Why Does Open Innovation Matter?', 'Prize Categories')),
        'two successful mappings and one refusal': len(cases) == 3 and all(c['passed'] for c in cases)
            and all('result' in c for c in cases[:2]) and 'error' in cases[2],
        'observed studio call duration': cases[0]['result']['provenance']['seconds'] == 4.85,
        'eight witnesses and swapped mapping one of eight': workflow['witnesses_passed'] == 8
            and workflow['wrong_mapping_passed'] == 1 and workflow['wrong_mapping_total'] == 8,
        'actual model profile reused': workflow['profile_sha256'] == cases[0]['result']['profile']['sha256'],
        'synthetic year outcomes': year['synthetic'] and len(year['weeks']) == 52
            and (year['clean_weeks'], year['held_weeks'], year['exceptions'], year['model_calls']) == (41, 11, 19, 0),
        'twelve offline checks': len(offline['checks']) == 12 and offline['network_calls'] == 0
            and offline['model_calls'] == 0,
        'recording disclosure and assertions': recording['synthetic'] and recording['model_calls'] == 0
            and len(recording['checks']) == 7 and not recording['public_upload'],
        'local video exists': (ROOT / recording['output']).is_file(),
        'no invented usage or savings claim': 'There has been no real customer trial' in entry
            and 'not a year of customer history or a claim of hours saved' in entry,
        'AI assistance disclosed': 'Built with AI assistance through OpenCode' in entry,
        'no raw local machine paths or em dashes': not re.search(r'[A-Za-z]:\\|\u2014', entry),
    }
    blockers = re.findall(r'\bPUBLIC_[A-Z_]+\b', entry)
    result = {
        'evidence_checks_passed': all(checks.values()), 'checks': checks,
        'word_count_approximate': len(entry.split()),
        'publication_ready': False,
        'publication_blockers': sorted(set(blockers)) + ['Owner approval', 'Public-code review and exact-commit CI', 'Approved media upload'],
        'actions_performed': 'Read-only local claim comparison. No model calls, network, upload or publication.',
    }
    print(json.dumps(result, indent=2))
    return 0 if result['evidence_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
