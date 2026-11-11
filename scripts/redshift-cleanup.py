"""Plan and optionally remove ONLY the temporary Redshift module.

Default: plan/review only. --execute applies the reviewed module-only deletion.
Never uses terraform destroy. Keeps enable_ingestion=true for prior deliveries.
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/evidence/checkpoint-6'


def terraform(*args):
    result = subprocess.run(['terraform','-chdir=infra',*args],cwd=ROOT,
                            capture_output=True,text=True,encoding='utf-8',timeout=1800)
    if result.returncode:
        raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--profile',default='coderhouse-dev')
    parser.add_argument('--evidence-dir',type=Path)
    args = parser.parse_args()
    if args.evidence_dir:OUT=args.evidence_dir.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    plan = terraform('plan','-no-color','-input=false','-var=aws_profile='+args.profile,'-var=enable_ingestion=true',
                     '-var=enable_redshift=false','-out=checkpoint6-cleanup.tfplan')
    (OUT/'terraform-cleanup-plan.txt').write_text(plan,encoding='utf-8')
    data = json.loads(terraform('show','-json','checkpoint6-cleanup.tfplan'))
    deletions = []
    for change in data.get('resource_changes',[]):
        actions = change['change']['actions']
        if actions in (['no-op'],['read']):
            continue
        if not change['address'].startswith('module.redshift[0].') or actions != ['delete']:
            raise RuntimeError(f'Unsafe cleanup plan: {change["address"]}: {actions}')
        deletions.append(change['address'])
    summary = {'scope':'module.redshift[0] only','deletions':deletions,
               'other_resources_changed':False,'executed':False}
    (OUT/'cleanup-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    # Apply also when there are no deletions: refresh may have detected a resource
    # already removed through its authorized service API and must persist state.
    if args.execute:
        result = subprocess.run(['terraform','-chdir=infra','apply','-no-color','-input=false',
                                  'checkpoint6-cleanup.tfplan'],cwd=ROOT,
                                 stdout=(OUT/'terraform-cleanup-apply.txt').open('w',encoding='utf-8'),
                                 stderr=subprocess.STDOUT,timeout=1800)
        if result.returncode:
            raise RuntimeError('Cleanup apply failed; inspect terraform-cleanup-apply.txt and remove remaining temporary resources')
        summary['executed'] = True
        (OUT/'cleanup-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('Temporary Redshift module removed.',flush=True)


if __name__ == '__main__':
    main()
