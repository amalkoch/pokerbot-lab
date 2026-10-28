"""Download pinned structured PokerBench files and audit before model fitting."""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import urllib.request

REVISION = '7ac61f961c81a50fc0f667820b2fb0e432dfec0d'
FILES = {stage: {split: f'{stage}_{size}_{split}_set_game_scenario_information.csv'
                for split, size in zip(('train', 'test'), sizes)}
         for stage, sizes in [('preflop', ('60k', '1k')), ('postflop', ('500k', '10k'))]}
ROOT = Path('data/pokerbench')


def normalize(value):
    return ' '.join(value.strip().lower().split())


def observation(row):
    """Drop index, label and future community cards; preserve current legal menu."""
    result = {k: v for k, v in row.items() if k not in ('', 'correct_decision')}
    street = row.get('evaluation_at', '').lower()
    if street == 'flop':
        result.pop('board_turn', None)
        result.pop('board_river', None)
    elif street == 'turn':
        result.pop('board_river', None)
    return result


def fingerprint(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def inspect_file(path):
    keys, labels, actions = Counter(), Counter(), Counter()
    key_labels = {}
    issues = Counter()
    street_counts = Counter()
    with path.open(newline='', encoding='utf-8') as source:
        for row in csv.DictReader(source):
            obs = observation(row)
            key = fingerprint(obs)
            label = normalize(row['correct_decision'])
            keys[key] += 1
            key_labels.setdefault(key, set()).add(label)
            labels[label] += 1
            actions['raise_to_bb' if label.endswith('bb') else label.split()[0]] += 1
            street = row.get('evaluation_at', 'preflop').lower()
            street_counts[street] += 1
            moves = [normalize(v) for v in ast.literal_eval(row['available_moves'])]
            if label not in moves:
                issues['label_not_in_menu_exact_text'] += 1
            future = (['board_turn', 'board_river'] if street == 'flop' else
                      ['board_river'] if street == 'turn' else [])
            if any(row.get(k, '').strip().lower() not in ('', 'nan', 'none') for k in future):
                issues['rows_with_populated_future_board_fields'] += 1
            cards = ''.join(obs.get(k, '') for k in ('hero_holding', 'holding', 'board_flop', 'board_turn', 'board_river'))
            cards = re.findall(r'[2-9TJQKA][shdc]', cards)
            if len(cards) != len(set(cards)):
                issues['duplicate_visible_cards'] += 1
    result = {'rows': sum(keys.values()), 'unique_visible_observations': len(keys),
              'duplicate_observation_rows': sum(v-1 for v in keys.values()),
              'observations_with_conflicting_labels': sum(len(v)>1 for v in key_labels.values()),
              'label_counts': dict(labels), 'action_counts': dict(actions),
              'street_counts': dict(street_counts), 'issues': dict(issues),
              'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return result, keys, key_labels


def run(download=False):
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'dataset': 'RZ412/PokerBench', 'revision': REVISION,
              'license_as_declared': 'Apache-2.0', 'stages': {},
              'method': 'Exact visible-observation hashing; excludes row index, target label and future board columns. Not suit-canonical or semantic deduplication.'}
    for stage, files in FILES.items():
        splits, raw = {}, {}
        for split, name in files.items():
            path = ROOT / name
            if download and not path.exists():
                urllib.request.urlretrieve(f'https://huggingface.co/datasets/RZ412/PokerBench/resolve/{REVISION}/{name}', path)
            results, keys, labels = inspect_file(path)
            splits[split] = results
            raw[split] = (keys, labels)
        train, test = raw['train'][0], raw['test'][0]
        overlap = train.keys() & test.keys()
        splits['overlap'] = {'unique_visible_observations': len(overlap),
                             'test_rows_seen_in_train': sum(test[k] for k in overlap),
                             'test_rows_not_seen_in_train': sum(test[k] for k in test.keys()-train.keys())}
        report['stages'][stage] = splits
        print(stage, 'rows', splits['train']['rows'], splits['test']['rows'],
              'overlap', splits['overlap'], 'issues', {s:splits[s]['issues'] for s in ('train','test')}, flush=True)
    Path('results').mkdir(exist_ok=True)
    Path('results/pokerbench_audit.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    run(parser.parse_args().download)
