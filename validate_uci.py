"""Validate PokerKit against UCI five-card labels (not strategy training)."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import urllib.request
import zipfile
from pokerkit import Label, StandardHighHand

URL = 'https://archive.ics.uci.edu/static/public/158/poker%2Bhand.zip'
SUITS = 'hsdc'
RANKS = 'A23456789TJQK'
LABELS = list(Label)


def classify(values):
    if len(values) != 10:
        raise ValueError('Exactly five suit/rank pairs required')
    cards = []
    for suit, rank in zip(values[::2], values[1::2]):
        if not 1 <= suit <= 4 or not 1 <= rank <= 13:
            raise ValueError('Invalid card encoding')
        cards.append(RANKS[rank - 1] + SUITS[suit - 1])
    if len(set(cards)) != 5:
        raise ValueError('Duplicate card')
    label = LABELS.index(StandardHighHand(''.join(cards)).entry.label)
    # UCI separates royal flushes; PokerKit includes them in straight flushes.
    return 9 if label == 8 and set(values[1::2]) == {1, 10, 11, 12, 13} else label


def validate(limit=0):
    path = Path('data/poker-hand.zip')
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        urllib.request.urlretrieve(URL, path)
    report = {'source': URL, 'citation': 'Cattral & Oppacher (2002), doi:10.24432/C5KW38',
              'license': 'CC BY 4.0', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'pokerkit_version': importlib.metadata.version('pokerkit'), 'splits': {},
              'purpose': 'Hand-evaluator validation; contains no betting decisions.'}
    with zipfile.ZipFile(path) as archive:
        for name in ('poker-hand-training-true.data', 'poker-hand-testing.data'):
            counts, errors, checked = Counter(), [], 0
            with archive.open(name) as raw:
                for line in io.TextIOWrapper(raw):
                    if limit and checked >= limit:
                        break
                    values = list(map(int, line.strip().split(',')))
                    prediction = classify(values[:10])
                    expected = values[10]
                    checked += 1
                    counts[expected] += 1
                    if prediction != expected:
                        errors.append({'row': checked, 'expected': expected, 'predicted': prediction})
            report['splits'][name] = {'checked': checked, 'class_counts': dict(counts),
                                      'mismatches': len(errors), 'first_errors': errors[:10]}
            print(name, checked, 'rows;', len(errors), 'mismatches', flush=True)
    Path('results').mkdir(exist_ok=True)
    Path('results/uci_validation.json').write_text(json.dumps(report, indent=2))
    if any(s['mismatches'] for s in report['splits'].values()):
        raise SystemExit('Evaluator disagreement: inspect report')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Rows per split; 0 means all')
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('limit must be nonnegative')
    validate(args.limit)
