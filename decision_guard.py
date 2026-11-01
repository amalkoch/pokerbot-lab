"""Unofficial offline decision guard; checks lateness AFTER a policy returns.

Not a sandbox or hard timeout. A policy that hangs will still hang this caller.
The optional budget covers the policy call, not serialization or validation.
"""
from time import perf_counter_ns


def guarded_decision(policy, observation, rng, deadline_ns=None, clock=perf_counter_ns):
    legal = observation.legal_actions
    if not legal or any(type(a) is not str for a in legal):
        raise ValueError('Require nonempty string legal actions')
    fallback = 'check' if 'check' in legal else 'fold' if 'fold' in legal else None
    if fallback is None:
        raise ValueError('Practice interface must allow check or fold')
    if deadline_ns is not None and (type(deadline_ns) is not int or deadline_ns <= 0):
        raise ValueError('deadline_ns must be a positive integer or None')
    start = clock()
    exception = False
    try:
        action = policy(observation, rng)
    except Exception:
        action = None
        exception = True
    elapsed = clock() - start
    # Do not invoke arbitrary equality on an invalid object returned by a bot.
    invalid = not exception and (type(action) is not str or action not in legal)
    late = deadline_ns is not None and elapsed > deadline_ns
    failed = exception or invalid or late
    return {'action': fallback if failed else action, 'elapsed_ns': elapsed,
            'exception': exception, 'invalid_action': invalid,
            'late': late, 'used_fallback': failed}


def fault_drill():
    """Deterministic synthetic clock: this tests behavior, NOT CPU performance."""
    from pokerbot_lab import LEGAL, Observation
    rows = []
    def crash(obs, rng): raise RuntimeError('injected failure')
    for card in range(3):
        for history, legal in LEGAL.items():
            obs = Observation(card, history, len(history) % 2, legal)
            for name, policy, elapsed in [
                ('valid', lambda o,r:o.legal_actions[-1], 100),
                ('invalid', lambda o,r:{'action':'check'}, 100),
                ('exception', crash, 100),
                ('at_budget', lambda o,r:o.legal_actions[-1], 1000000),
                ('late', lambda o,r:o.legal_actions[-1], 1000001),
            ]:
                ticks = iter((0, elapsed))
                result = guarded_decision(policy, obs, None, 1000000, lambda:next(ticks))
                assert result['action'] in legal
                rows.append({'card': card, 'history': history, 'case': name, **result})
    return {'practice_only': True, 'timing': 'Injected synthetic nanoseconds, not measured hardware latency',
            'cases': len(rows), 'fallbacks': sum(r['used_fallback'] for r in rows), 'records': rows}


if __name__ == '__main__':
    import json
    print(json.dumps(fault_drill(), indent=2))
