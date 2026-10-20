"""Reuse a reviewed mapping without the browser, Ollama or any network calls."""
import argparse
import json
from pathlib import Path
import sys

from .close import packet, reconcile
from .engine import SafetyError


def read_bounded(path, maximum):
    with Path(path).open('rb') as source:
        content = source.read(maximum + 1)
    if len(content) > maximum:
        raise SafetyError(f'Input exceeds {maximum} bytes: {path}')
    return content.decode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, help='Mapping or tested studio workflow JSON')
    parser.add_argument('--payments', required=True, help='Explicit payment CSV path')
    parser.add_argument('--bank', required=True, help='Explicit bank CSV path')
    parser.add_argument('--mapping-approved', action='store_true', help='Confirm you reviewed this mapping and source completeness')
    parser.add_argument('--packet', help='Create a NEW ZIP file only for an approved clean report')
    parser.add_argument('--approved-sha256', help='Exact report SHA-256 from a previous review')
    args = parser.parse_args(argv)
    try:
        if not args.mapping_approved:
            raise SafetyError('Review the mapping and supply --mapping-approved. Nothing was reconciled.')
        contract = json.loads(read_bounded(args.profile, 64000))
        payments = read_bounded(args.payments, 350000)
        bank = read_bounded(args.bank, 350000)
        report = reconcile(contract, payments, bank)
        if args.packet:
            if not args.approved_sha256:
                raise SafetyError('Review the report first, then supply its --approved-sha256 to export a packet.')
            content = packet(contract, payments, bank, args.approved_sha256)
            # Exclusive creation prevents clobbering an input, an earlier packet or user work.
            with Path(args.packet).open('xb') as output:
                output.write(content)
        print(json.dumps(report, indent=2))
        return 0 if report['ready'] else 2
    except (SafetyError, OSError, ValueError, TypeError) as error:
        print(f'Doze: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
