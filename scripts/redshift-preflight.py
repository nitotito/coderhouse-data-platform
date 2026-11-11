"""Read-only AWS inventory; saves errors as evidence, never deploys resources."""
import datetime
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root/'docs/evidence/checkpoint-6'
out.mkdir(parents=True, exist_ok=True)
commands = {
    'identity': ['sts','get-caller-identity'],
    'glue-table': ['glue','get-table','--database-name','lakehouse_db','--name','transaction_aggregates'],
    'stream': ['kinesis','describe-stream-summary','--stream-name','dev-transactions-stream'],
    'versioning': ['s3api','get-bucket-versioning','--bucket','coderhouse-data-lake-672049777597'],
    'subnets': ['ec2','describe-subnets','--filters','Name=tag:Name,Values=dev-private-*',
                '--query','Subnets[].{Id:SubnetId,Vpc:VpcId,AZ:AvailabilityZone,Free:AvailableIpAddressCount,Cidr:CidrBlock}'],
    'flink': ['kinesisanalyticsv2','describe-application','--application-name','coderhouse-dev-transactions-flink',
              '--query','ApplicationDetail.{Name:ApplicationName,Status:ApplicationStatus,Runtime:RuntimeEnvironment}'],
    'redshift-serverless': ['redshift-serverless','list-workgroups'],
    'redshift-provisioned': ['redshift','describe-clusters','--query','Clusters[].ClusterIdentifier'],
    'kinesis-key': ['kms','describe-key','--key-id','alias/aws/kinesis','--query','KeyMetadata.Arn'],
}
for name, args in commands.items():
    run = subprocess.run(['aws',*args,'--profile','coderhouse-dev','--region','us-east-1',
                          '--output','json','--no-cli-pager'],capture_output=True,text=True,
                         encoding='utf-8',timeout=90)
    result = {'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command':['aws',*args], 'exit_code':run.returncode}
    if run.returncode:
        result['error'] = run.stderr.strip()
    else:
        result['response'] = json.loads(run.stdout)
    (out/f'preflight-{name}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(name, 'OK' if run.returncode == 0 else 'DENIED/FAILED')
