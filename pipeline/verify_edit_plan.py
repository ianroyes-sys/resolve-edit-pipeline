"""Validate a plan against explicit job feedback and reviewed source intervals.

Range approval is editorial evidence, not an automatic stability guarantee.
Usage: python3 verify_edit_plan.py PLAN CONSTRAINTS
"""
import json,sys
from pathlib import Path

def verify(plan, constraints):
    errors=[]; shots=plan['shots']; names=[s['clip'] for s in shots]
    for name in constraints.get('excluded_clips',[]):
        if name in names: errors.append(f'Rejected clip included: {name}')
    for name in constraints.get('required_clips',[]):
        if name not in names: errors.append(f'Important participant/shot absent: {name}')
    for shot in shots:
        name=shot['clip']; a=shot['in']; b=a+shot['duration']
        intervals=constraints['reviewed_ranges'].get(name,[])
        if not any(a>=x['in']-0.001 and b<=x['out']+0.001 for x in intervals):
            errors.append(f'{name} {a:.3f}–{b:.3f}s exceeds reviewed range; inspect new range before building')
        if not shot.get('role'):errors.append(f'Missing story purpose: {name}')
    for name,count in constraints.get('maximum_uses',{}).items():
        if names.count(name)>count:errors.append(f'Redundant source use: {name}')
    return errors

if __name__=='__main__':
    plan=json.loads(Path(sys.argv[1]).read_text()); constraints=json.loads(Path(sys.argv[2]).read_text())
    failures=verify(plan,constraints)
    if failures:
        print('\n'.join(failures));sys.exit(1)
    print(f'PASS: {len(plan["shots"])} shots satisfy explicit feedback and reviewed-range constraints. Playback review is a separate check.')
