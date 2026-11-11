"""Read-only proof that this revision's exact temporary resources are gone."""
import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/checkpoint-6/revision'

def aws(*args):
    p=subprocess.run(['aws',*args,'--profile','coderhouse-dev','--region','us-east-1',
                      '--output','json','--no-cli-pager'],capture_output=True,text=True,encoding='utf-8',timeout=90)
    return p,json.loads(p.stdout) if not p.returncode and p.stdout.strip() else {}

def main():
    resources=json.loads((OUT/'deployed-resources.json').read_text())
    checks=[]
    for r in resources:
        typ=r['type'];ident=r['id']
        if typ=='aws_redshiftserverless_workgroup':cmd=['redshift-serverless','get-workgroup','--workgroup-name',ident]
        elif typ=='aws_redshiftserverless_namespace':cmd=['redshift-serverless','get-namespace','--namespace-name',ident]
        elif typ=='aws_redshiftserverless_usage_limit':cmd=['redshift-serverless','get-usage-limit','--usage-limit-id',ident]
        elif typ=='aws_iam_role':cmd=['iam','get-role','--role-name',ident]
        elif typ=='aws_iam_role_policy':
            role,policy=ident.split(':',1);cmd=['iam','get-role-policy','--role-name',role,'--policy-name',policy]
        elif typ=='aws_security_group':cmd=['ec2','describe-security-groups','--group-ids',ident]
        elif typ=='aws_vpc_endpoint':cmd=['ec2','describe-vpc-endpoints','--vpc-endpoint-ids',ident]
        else:raise AssertionError('Unexpected resource '+typ)
        result,data=aws(*cmd)
        absent=result.returncode!=0 and any(code in result.stderr for code in
            ['ResourceNotFoundException','NoSuchEntity','InvalidGroup.NotFound','InvalidVpcEndpointId.NotFound'])
        if typ=='aws_redshiftserverless_usage_limit' and result.returncode:
            # This API reports a removed usage-limit ID as ValidationException.
            absent=absent or ('ValidationException' in result.stderr and ident in result.stderr
                             and 'does not exist' in result.stderr)
        checks.append({'address':r['address'],'id':ident,'absent':absent,'exit_code':result.returncode,
                       'response':data,'error':result.stderr.strip() if result.returncode else None})
    priors={}
    result,data=aws('kinesis','describe-stream-summary','--stream-name','dev-transactions-stream')
    priors['stream_active']=not result.returncode and data['StreamDescriptionSummary']['StreamStatus']=='ACTIVE'
    result,data=aws('kinesisanalyticsv2','describe-application','--application-name','coderhouse-dev-transactions-flink')
    priors['flink_still_ready']=not result.returncode and data['ApplicationDetail']['ApplicationStatus']=='READY'
    result,data=aws('glue','get-table','--database-name','lakehouse_db','--name','transaction_aggregates')
    expected=json.loads((OUT/'iceberg-read-summary.json').read_text())['metadata_location']
    priors['iceberg_metadata_unchanged']=not result.returncode and data['Table']['Parameters']['metadata_location']==expected
    passed=all(r['absent'] for r in checks) and all(priors.values())
    report={'passed':passed,'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'temporary_resources':checks,'prior_components':priors}
    (OUT/'after-cleanup-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not passed:raise AssertionError('Retirement verification failed; inspect after-cleanup-verification.json')
    (OUT/'cleanup-done.json').write_text(json.dumps({'reason':'Authorized revision completed',
        'completed_at_utc':report['checked_at_utc'],'all_eight_temporary_resources_absent':True,
        'prior_components_preserved':True},indent=2)+'\n',encoding='utf-8')
    print('All eight temporary resources absent. Prior stream/Flink/Iceberg preserved.')

if __name__=='__main__':main()
