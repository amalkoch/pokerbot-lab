"""Fetch and replay one fixed Pluribus session; no raw histories committed."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
from pokerkit import HandHistory


def audit():
    entries = json.loads(Path('pluribus_sample_manifest.json').read_text())
    def fetch(entry):
        path = Path('data/phh') / entry['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            urllib.request.urlretrieve(entry['url'], path)
        content = path.read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if blob != entry['git_blob']:
            raise ValueError('Downloaded blob does not match pinned revision')
        return path, content
    rows, failures = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for path, content in pool.map(fetch, entries):
            try:
                hh = HandHistory.loads(content.decode())
                last, count = None, 0
                for state in hh:
                    last = state
                    count += 1
                if last is None or last.status:
                    raise ValueError('Replay did not reach terminal state')
                if list(last.stacks) != hh.finishing_stacks:
                    raise ValueError('Replay finishing stacks differ from record')
                if sum(last.stacks) != sum(hh.starting_stacks):
                    raise ValueError('Chips not conserved')
                rows.append({'file': str(path.relative_to('data/phh')), 'states': count,
                             'players': len(hh.starting_stacks), 'variant': hh.variant,
                             'decision_actions': sum(a.startswith('p') for a in hh.actions),
                             'unknown_card_markers': sum('?' in a for a in hh.actions),
                             'sha256': hashlib.sha256(content).hexdigest()})
            except Exception as e:
                failures.append({'file':path.name,'error':str(e)})
    report = {'source':'https://github.com/uoftcprg/phh-dataset',
              'revision':'e47fbd5816372360bade4de5d712346fe1bb70f6',
              'selection':'Every file in data/pluribus/100; one session, not a random or representative sample',
              'files_checked':len(entries), 'successful_terminal_replays':len(rows),
              'failures':failures, 'details':rows,
              'warning':'Histories include opponent hole cards and future boards. Reconstruct acting-player observations before training.'}
    Path('results/pluribus_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k!='details'})
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    audit()
