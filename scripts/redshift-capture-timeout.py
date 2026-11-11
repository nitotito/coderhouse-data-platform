"""Close this exact, authorized capture warehouse after a bounded window.

Runs as a hidden local helper. It never creates AWS resources and never removes
resources outside module.redshift[0]. A different workgroup ID cancels teardown.
"""
import argparse
import datetime as dt
import importlib.util
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/checkpoint-6/capture-session'


def aws(*args):
    return subprocess.run(['aws',*args,'--profile','coderhouse-dev','--region','us-east-1',
                           '--output','json','--no-cli-pager'],capture_output=True,
                          text=True,encoding='utf-8',timeout=90)


def main():
    global OUT
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workgroup-id',required=True)
    p.add_argument('--minutes',type=int,default=30)
    p.add_argument('--evidence-dir',type=Path)
    args=p.parse_args()
    if args.evidence_dir:OUT=args.evidence_dir.resolve()
    deadline=dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=args.minutes)
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/'capture-window.json'
    marker.write_text(json.dumps({'workgroup_id':args.workgroup_id,
                                  'deadline_utc':deadline.isoformat(),'minutes':args.minutes,
                                  'status':'WAITING'},indent=2)+'\n',encoding='utf-8')
    while dt.datetime.now(dt.timezone.utc)<deadline:
        if (OUT/'cleanup-done.json').exists():
            return
        time.sleep(10)
    current=aws('redshift-serverless','get-workgroup','--workgroup-name','coderhouse-dev-analytics')
    if current.returncode:
        (OUT/'timeout-status.json').write_text(json.dumps({'status':'NOT_FOUND_OR_INACCESSIBLE',
                                                          'error':current.stderr},indent=2),encoding='utf-8')
        return
    if json.loads(current.stdout)['workgroup']['workgroupId']!=args.workgroup_id:
        (OUT/'timeout-status.json').write_text('{"status":"DIFFERENT_WORKGROUP_NO_ACTION"}\n',encoding='utf-8')
        return
    spec=importlib.util.spec_from_file_location('cleanup',ROOT/'scripts/redshift-cleanup.py')
    cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
    cleanup.OUT=OUT
    import sys
    sys.argv=['redshift-cleanup.py','--execute']
    try:
        cleanup.main()
    except RuntimeError:
        # Some operator versions lack the provider's profile enumeration action.
        # Only handle the known final-role error after billable resources are gone.
        log=(OUT/'terraform-cleanup-apply.txt').read_text(encoding='utf-8')
        if 'iam:ListInstanceProfilesForRole' not in log:
            raise
        result=aws('iam','delete-role','--role-name','coderhouse-dev-analytics-execution')
        if result.returncode and 'NoSuchEntity' not in result.stderr:
            raise RuntimeError(result.stderr)
        cleanup.main()
    (OUT/'cleanup-done.json').write_text(json.dumps({'reason':'capture deadline',
                                                    'completed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
