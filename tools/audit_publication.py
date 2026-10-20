"""Bounded, read-only text/history preflight, not a comprehensive secret scanner."""
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.py', '.mjs', '.js', '.json', '.md', '.txt', '.yml', '.yaml', '.css', '.html', '.svg', '.ass'}
PATTERNS = {
    'private-key marker': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub-style access token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'AWS-style access key ID': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'OpenAI-style API key': re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b'),
    'Slack-style token': re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
}
PATHS = re.compile(rb'(?:[A-Za-z]:[/\\]{1,2}Users[/\\]{1,2}[^\s"\x27<>]+|/home[/][^\s"\x27<>]+)')


def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=ROOT)


def main():
    commits = git('rev-list', '--all').decode().splitlines()
    if len(commits) > 100:
        raise SystemExit('History exceeds the 100-commit review budget. Choose an explicit bounded range.')
    trees = [(commit, git('ls-tree', '-r', '-z', commit)) for commit in commits]
    trees.insert(0, ('INDEX', git('ls-files', '-s', '-z')))
    blobs = {}
    binary_paths = set()
    state_paths = set()
    for revision, tree in trees:
        for record in tree.split(b'\0'):
            if not record:
                continue
            metadata, path = record.split(b'\t', 1)
            fields = metadata.decode().split()
            sha = fields[1] if revision == 'INDEX' else fields[2]
            name = path.decode('utf-8', errors='replace')
            if any(part in {'.doze', '.env', '.venv', '__pycache__', 'node_modules'} for part in Path(name).parts):
                state_paths.add(name)
            if Path(name).suffix.lower() in TEXT_SUFFIXES or Path(name).name in {'LICENSE', '.gitignore'}:
                blobs.setdefault(sha, {'path': name, 'revision': revision})
            else:
                binary_paths.add(name)
    findings = []
    home_paths = []
    scanned_bytes = 0
    for sha, location in blobs.items():
        size = int(git('cat-file', '-s', sha))
        if size > 2_000_000 or scanned_bytes + size > 20_000_000:
            raise SystemExit('Text review exceeded its 2 MB per blob / 20 MB total budget.')
        content = git('cat-file', 'blob', sha)
        scanned_bytes += size
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                findings.append({**location, 'category': category, 'line': content[:match.start()].count(b'\n') + 1})
        for match in PATHS.finditer(content):
            home_paths.append({**location, 'line': content[:match.start()].count(b'\n') + 1})
    identities = git('log', '--all', '--format=%an <%ae>%n%cn <%ce>').decode().splitlines()
    report = {
        'scope': 'Index plus all reachable local commits, text blobs only. Pattern checks are not a security guarantee.',
        'commit_count': len(commits), 'unique_text_blobs': len(blobs), 'text_bytes': scanned_bytes,
        'credential_pattern_findings': findings,
        'home_directory_path_findings': home_paths,
        'tracked_runtime_state_paths': sorted(state_paths),
        'author_committer_identities': len(set(identities)),
        'identity_note': 'Commit identities are publication-visible. Values intentionally omitted; owner must review git log locally.',
        'binary_media_paths': sorted(binary_paths),
        'binary_note': 'Media pixels/audio/metadata are not scanned here. Previously reviewed cover and Friday Close contact sheet do not constitute a complete historical-media review.',
        'remote_count': len(git('remote').decode().splitlines()),
        'pattern_summary': dict(Counter(f['category'] for f in findings)),
        'publication_approved': False,
        'mutations': 'None. Reads Git index/history and emits a redacted JSON report on stdout.',
    }
    print(json.dumps(report, indent=2))
    return 1 if findings or state_paths else 0


if __name__ == '__main__':
    raise SystemExit(main())
