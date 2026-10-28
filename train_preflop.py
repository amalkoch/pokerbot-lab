"""Leakage-aware preflop candidate ranking; offline supervised baseline only."""
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import time
import warnings
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, classification_report
from threadpoolctl import threadpool_limits
import joblib
from audit_pokerbench import FILES, ROOT, REVISION

POSITIONS = ['UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB']
RANKS = '23456789TJQKA'
FAMILIES = ['fold', 'check', 'call', 'raise', 'allin']


def family(action):
    return 'raise' if action.endswith('bb') else action


def holding(cards):
    if len(cards) != 4 or cards[:2] == cards[2:]:
        raise ValueError('Invalid hole cards')
    ranks = sorted([RANKS.index(cards[0])+2, RANKS.index(cards[2])+2], reverse=True)
    return ranks + [int(cards[1] == cards[3])]


def menu(row):
    return sorted(set(ast.literal_eval(row['available_moves'])))


def identity(row):
    # Suit permutations and reversed hole-card order are equivalent preflop.
    return (row['prev_line'], row['hero_pos'], tuple(holding(row['hero_holding'])),
            float(row['pot_size']), int(row['num_players']), int(row['num_bets']), tuple(menu(row)))


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def clean(rows):
    groups = defaultdict(list)
    for row in rows:
        if row['correct_decision'] not in menu(row):
            raise ValueError('Target outside provided menu')
        groups[identity(row)].append(row)
    conflicts = {k for k, v in groups.items() if len({r['correct_decision'] for r in v}) > 1}
    kept = [v[0] for k,v in groups.items() if k not in conflicts]
    return kept, {'input_rows':len(rows), 'canonical_observations':len(groups),
                  'conflicting_groups':len(conflicts),
                  'quarantined_rows':sum(len(groups[k]) for k in conflicts),
                  'clean_rows':len(kept)}, set(groups)


def features(row, candidate):
    """Allowlisted inputs only; target and row index are never accessed."""
    hi, lo, suited = holding(row['hero_holding'])
    values = [hi, lo, suited, int(hi == lo), hi-lo,
              float(row['pot_size']), int(row['num_players']), int(row['num_bets'])]
    values += [int(row['hero_pos'] == p) for p in POSITIONS]
    tokens = row['prev_line'].split('/') if row['prev_line'] else []
    if len(tokens) % 2:
        raise ValueError('Malformed public history')
    events = list(zip(tokens[::2], tokens[1::2]))
    # Positions of last action, action counts and last numeric raise per seat.
    for pos in POSITIONS:
        actions = [a for p,a in events if p == pos]
        values += [sum(family(a) == f for a in actions) for f in FAMILIES]
        amounts = [float(a[:-2]) for a in actions if a.endswith('bb')]
        values += [amounts[-1] if amounts else 0, int(bool(events) and events[-1][0] == pos)]
    choices = menu(row)
    values += [sum(family(a) == f for a in choices) for f in FAMILIES]
    amounts = [float(a[:-2]) for a in choices if a.endswith('bb')]
    values += [min(amounts,default=0), max(amounts,default=0)]
    values += [int(family(candidate) == f) for f in FAMILIES]
    amount = float(candidate[:-2]) if candidate.endswith('bb') else 100 if candidate == 'allin' else 0
    values += [amount, amount / max(float(row['pot_size']), .5)]
    return values


def expand(rows):
    x, y, weights, choices, lengths = [], [], [], [], []
    for row in rows:
        actions = menu(row); lengths.append(len(actions)); choices.extend(actions)
        for action in actions:
            x.append(features(row, action))
            y.append(int(action == row['correct_decision']))
            weights.append(1/len(actions))
    return np.asarray(x), np.asarray(y), np.asarray(weights), choices, lengths


class LegalFrequencyBaseline:
    """Choose the most frequent training target among supplied candidates."""
    def fit(self, x, y, sample_weight=None):
        self.counts = Counter(tuple(row[-7:-1]) for row, target in zip(x,y) if target)
        self.total = sum(self.counts.values())
        return self

    def predict_proba(self, x):
        p = np.asarray([self.counts[tuple(row[-7:-1])] / self.total for row in x])
        return np.column_stack((1-p,p))


def select(scores, choices, lengths):
    answers, offset = [], 0
    for length in lengths:
        answers.append(choices[offset + int(np.argmax(scores[offset:offset+length]))])
        offset += length
    return answers


def evaluate(model, rows):
    x, _, _, choices, lengths = expand(rows)
    predictions = select(model.predict_proba(x)[:,1], choices, lengths)
    labels = [r['correct_decision'] for r in rows]
    return {'hands':len(rows), 'exact_accuracy':accuracy_score(labels,predictions),
            'family_accuracy':accuracy_score(list(map(family,labels)),list(map(family,predictions))),
            'family_macro_f1':f1_score(list(map(family,labels)),list(map(family,predictions)),
                                      labels=FAMILIES,average='macro',zero_division=0),
            'outside_supplied_menu':sum(p not in menu(r) for p,r in zip(predictions,rows)),
            'target_family_counts':dict(Counter(map(family,labels))),
            'per_family':classification_report(list(map(family,labels)),list(map(family,predictions)),
                labels=FAMILIES,output_dict=True,zero_division=0)}


def predict_one(model, row):
    choices = menu(row)
    scores = model.predict_proba(np.asarray([features(row,a) for a in choices]))[:,1]
    return choices[int(np.argmax(scores))]


def load(split):
    with (ROOT/FILES['preflop'][split]).open(newline='') as f:
        return list(csv.DictReader(f))


def run():
    raw_train, raw_test = load('train'), load('test')
    rows, cleaning, train_keys = clean(raw_train)
    external, external_cleaning, _ = clean(raw_test)
    external = [r for r in external if identity(r) not in train_keys]
    # Split by entire exact public action line; all seats/cards of that line stay together.
    groups = [r['prev_line'] for r in rows]
    development, test_idx = next(GroupShuffleSplit(n_splits=1,test_size=.15,random_state=42).split(rows,groups=groups))
    fit_idx, val_idx = next(GroupShuffleSplit(n_splits=1,test_size=.17647,random_state=43).split(
        development,groups=[groups[i] for i in development]))
    train = [rows[development[i]] for i in fit_idx]
    valid = [rows[development[i]] for i in val_idx]
    test = [rows[i] for i in test_idx]
    group_sets = [{r['prev_line'] for r in split} for split in (train,valid,test)]
    assert not any(group_sets[i]&group_sets[j] for i,j in [(0,1),(0,2),(1,2)])
    report = {'seed':42,'dataset_revision':REVISION,'cleaning':cleaning,'external_cleaning':external_cleaning,
              'external_rows_after_train_overlap_removal':len(external),
              'environment':{'python':platform.python_version(),'sklearn':sklearn.__version__},
              'split':{name:{'rows':len(split),'public_action_lines':len(gs)}
                       for name,split,gs in zip(('train','validation','test'),(train,valid,test),group_sets)},
              'models':{},'source_sha256':{s:hashlib.sha256((ROOT/FILES['preflop'][s]).read_bytes()).hexdigest() for s in ('train','test')},
              'notes':['Rank only supplied legal candidates; legality is by construction, not simulator validation.',
                       'Group split uses exact public action histories, not semantic bet-size equivalence.',
                       'External test removes canonical train overlap but may share public histories.',
                       'Macro-F1 averages the fixed five action families, including zero-support families.',
                       'No hyperparameter search; choose on validation exact accuracy, then evaluate all fixed models once.',
                       'This is solver-label imitation, not a measured poker win rate.']}
    output=Path('data/preflop_clean'); output.mkdir(parents=True,exist_ok=True)
    manifest = {}
    for name,split in [('train',train),('validation',valid),('test',test),('external_test',external)]:
        path=output/(name+'.jsonl')
        path.write_text(''.join(json.dumps({'observation':{k:v for k,v in r.items() if k not in ('','correct_decision')},
                                          'target':r['correct_decision']})+'\n' for r in split))
        manifest[name]={'rows':len(split),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'group_hashes':sorted({digest(r['prev_line']) for r in split})}
    Path('results/preflop_split_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    x,y,weights,_,_=expand(train)
    models = {'majority_legal':LegalFrequencyBaseline(),
              'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=42)),
              'decision_tree':DecisionTreeClassifier(max_depth=8,min_samples_leaf=40,random_state=42),
              'boosted_trees':HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=15,
                                l2_regularization=1,early_stopping=False,random_state=42)}
    for name,model in models.items():
        start=time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            if name=='logistic': model.fit(x,y,logisticregression__sample_weight=weights)
            else: model.fit(x,y,sample_weight=weights)
        report['models'][name]={'fit_seconds':time.perf_counter()-start,
                              'fit_warnings':[str(w.message) for w in caught], 'validation':evaluate(model,valid)}
        print(name,report['models'][name],flush=True)
    selected=max(models,key=lambda name:report['models'][name]['validation']['exact_accuracy'])
    report['selected_by_validation']=selected
    for name,model in models.items():
        result=report['models'][name]
        result['grouped_test']=evaluate(model,test)
        result['external_test']=evaluate(model,external)
        for row in test[:20]: predict_one(model,row)
        times=[]
        for row in test[:1000]:
            start=time.perf_counter_ns(); answer=predict_one(model,row); times.append((time.perf_counter_ns()-start)/1000)
            assert answer in menu(row)
        result['latency']={'samples':len(times),'p50_us':float(np.percentile(times,50)),
                           'p99_us':float(np.percentile(times,99)),'max_us':max(times),
                           'over_1ms':sum(t>1000 for t in times),
                           'scope':'Warm single-hand feature extraction, candidate scoring and selection; one CPU thread; excludes process/JSON loading.'}
        print(name,'test',result['grouped_test']['exact_accuracy'],'timing',result['latency'],flush=True)
    Path('data/models').mkdir(exist_ok=True)
    path=Path('data/models/preflop.joblib'); joblib.dump(models[selected],path)
    report['saved_model']={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    Path('results/preflop_training.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    with threadpool_limits(limits=1):
        run()
