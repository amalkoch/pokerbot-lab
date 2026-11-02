"""Offline, unofficial 60-minute build-drill log reviewer, not a submission tool."""
import argparse
import json
import math
from pathlib import Path

CHECKPOINTS = (
    ('baseline', 10, 'Runnable baseline and one completed practice match'),
    ('legality', 20, 'Legal-action and failure tests, with local timing report'),
    ('candidate', 35, 'One strategy change and a preserved baseline'),
    ('holdout', 50, 'Fresh-seed comparisons against multiple opponents; retain losses'),
    ('freeze', 60, 'Final tests, exact code hash and decision to keep or reject candidate'),
)


def review(entries, elapsed_minutes):
    """Review self-reported evidence; never certify tests or code from log text."""
    def minute(value):
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Minutes must be finite nonnegative numbers')
        return value
    elapsed_minutes = minute(elapsed_minutes)
    if not isinstance(entries, list): raise ValueError('Log must be a list')
    known = {name for name, _, _ in CHECKPOINTS}
    completed = {}
    previous = -1
    for item in entries:
        if not isinstance(item, dict): raise ValueError('Each entry must be an object')
        name = item.get('checkpoint')
        if not isinstance(name,str) or name not in known or name in completed:
            raise ValueError('Checkpoint must be known and recorded once')
        at = minute(item.get('minute'))
        if at < previous or at > elapsed_minutes: raise ValueError('Entries must be chronological and not in the future')
        evidence = item.get('evidence')
        if not isinstance(evidence,str) or not evidence.strip(): raise ValueError('Supply a nonempty evidence reference')
        completed[name] = item
        previous = at
    rows = []
    for name, deadline, goal in CHECKPOINTS:
        entry = completed.get(name)
        status = ('on_time' if entry['minute'] <= deadline else 'late') if entry else ('overdue' if elapsed_minutes >= deadline else 'pending')
        rows.append({'checkpoint':name, 'deadline_minutes':deadline, 'goal':goal,
                     'status':status, 'evidence':entry['evidence'] if entry else None})
    return {'practice_only':True, 'evidence_verified':False, 'elapsed_minutes':elapsed_minutes,
            'remaining_minutes':max(0,60-elapsed_minutes), 'session_finished':elapsed_minutes>=60,
            'all_checkpoints_recorded':len(completed)==len(CHECKPOINTS),
            'all_on_time':all(r['status']=='on_time' for r in rows), 'checkpoints':rows}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log',type=Path,help='JSON list of checkpoint, minute and evidence entries')
    p.add_argument('--elapsed',type=float,default=0,help='Actual elapsed minutes from your session timer')
    args = p.parse_args()
    try:
        entries = json.loads(args.log.read_text()) if args.log else []
        result = review(entries,args.elapsed)
    except (ValueError,OSError) as e: p.error(str(e))
    print(json.dumps(result,indent=2))
