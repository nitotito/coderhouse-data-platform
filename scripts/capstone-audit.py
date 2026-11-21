"""Read-only capstone inventory. No deployment, producer or service start calls."""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/capstone'


def command(args):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
    return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aws',action='store_true')
    p.add_argument('--profile',default=os.getenv('AWS_PROFILE','coderhouse-dev'))
    p.add_argument('--region',default='us-east-1')
    p.add_argument('--label',default='initial')
    p.add_argument('--environment',default='dev')
    a=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    files=command(['git','ls-files'])['stdout'].splitlines()
    inventory=[];suspects=[]
    for name in files:
        file=ROOT/name
        if not file.is_file():continue
        data=file.read_bytes()
        inventory.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        if file.suffix.lower() not in ['.png','.pdf']:
            for pattern in [rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']:
                if re.search(pattern,data):suspects.append({'path':name,'pattern':pattern.decode()})
    report={'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'git_branch':command(['git','branch','--show-current'])['stdout'].strip(),
            'files':inventory,'credential_pattern_findings':suspects,
            'note':'Pattern scan is not proof that every historical secret is absent.'}
    (OUT/f'{a.label}-repository.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Tracked files:',len(inventory),'credential pattern findings:',len(suspects),flush=True)
    if not a.aws:return
    tf='terraform' if (ROOT/'terraform/main.tf').exists() else 'terraform'
    output=command(['terraform',f'-chdir={tf}','output','-json'])
    if output['exit_code']:raise RuntimeError(output['stderr'])
    values={k:v['value'] for k,v in json.loads(output['stdout']).items()}
    bucket=values['data_lake_bucket_name'];stream=values['kinesis_stream_name']
    lake=values['lakehouse'];app=f"coderhouse-{a.environment}-transactions-flink"
    commands={
      'identity':['sts','get-caller-identity'],
      'stream':['kinesis','describe-stream-summary','--stream-name',stream],
      'flink':['kinesisanalyticsv2','describe-application','--application-name',app,'--query',
               'ApplicationDetail.{Name:ApplicationName,Status:ApplicationStatus,Runtime:RuntimeEnvironment,Configuration:ApplicationConfigurationDescription}'],
      'glue':['glue','get-table','--database-name',lake['database'],'--name',lake['table']],
      'versioning':['s3api','get-bucket-versioning','--bucket',bucket],
      's3_encryption':['s3api','get-bucket-encryption','--bucket',bucket],
      's3_public_access':['s3api','get-public-access-block','--bucket',bucket],
      'redshift':['redshift-serverless','list-workgroups'],
      'redshift_namespaces':['redshift-serverless','list-namespaces'],
      'flink_role':['iam','get-role','--role-name',f'coderhouse-{a.environment}-flink','--query','Role.AssumeRolePolicyDocument']}
    aws={}
    for name,args in commands.items():
        r=command(['aws',*args,'--profile',a.profile,'--region',a.region,'--output','json','--no-cli-pager'])
        aws[name]={'exit_code':r['exit_code'],'response':json.loads(r['stdout']) if r['exit_code']==0 else None,
                   'error':r['stderr'].strip() if r['exit_code'] else None}
        print(name,'OK' if r['exit_code']==0 else 'DENIED/FAILED',flush=True)
    (OUT/f'{a.label}-aws.json').write_text(json.dumps({'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                                                    'checks':aws},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
