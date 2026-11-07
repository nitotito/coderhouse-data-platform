"""Capstone isolated workflow. Prepare is local/read-only; mutations require --execute.

No boto3: AWS CLI owns credentials. Never pass account IDs or dev resource names
as deployment defaults. The protected legacy Glue DB is never deleted by this tool.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence/capstone'

def run(args):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=900)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def aws(profile,region,*args):
    common=['--region',region,'--output','json','--no-cli-pager']
    if profile:common+=['--profile',profile]
    text=run(['aws',*args,*common]);return json.loads(text) if text.strip() else {}

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def prepare(args):
    identity=aws(args.profile,args.region,'sts','get-caller-identity')
    name='cap-'+uuid.uuid4().hex[:10]
    account=identity['Account']
    jar=ROOT/'flink-app/target/flink-transactions-1.2.0.jar'
    if not jar.exists():raise RuntimeError('Build flink-app/pom.xml before prepare')
    key=aws(args.profile,args.region,'kms','describe-key','--key-id','alias/aws/kinesis')['KeyMetadata']['Arn']
    folder=ROOT/'.capstone'/name;folder.mkdir(parents=True,exist_ok=False)
    manifest={'environment':name,'account':account,'region':args.region,'profile':args.profile,
              'state_bucket':f'coderhouse-{name}-tf-{account}',
              'state_key':f'{name}/terraform.tfstate','data_bucket':f'coderhouse-{name}-lake-{account}',
              'glue_database':name.replace('-','_')+'_lakehouse',
              'application':f'coderhouse-{name}-transactions-flink',
              'stream':name+'-transactions-stream','workgroup':f'coderhouse-{name}-analytics',
              'jar':str(jar),'jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
              'prepared_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'state':'PREPARED_NOT_DEPLOYED'}
    save(folder/'manifest.json',manifest)
    save(folder/'bootstrap.tfvars.json',{'environment':name,'aws_region':args.region,'aws_profile':args.profile})
    save(folder/'platform.tfvars.json',{'environment':name,'aws_region':args.region,'aws_profile':args.profile,
                                      'artifact_source_path':str(jar),'kinesis_kms_key_arn':key})
    backend={'bucket':manifest['state_bucket'],'key':manifest['state_key'],'region':args.region,
             'profile':args.profile,'encrypt':True,'use_lockfile':True}
    (folder/'isolated.backend.hcl').write_text('\n'.join(k+' = '+json.dumps(v) for k,v in backend.items())+'\n',encoding='utf-8')
    # Read-only fresh-state plan preview before a billable backend exists.
    # Never apply this local-state preview; the authorized deployment uses S3.
    preview=folder/'preview';preview.mkdir()
    source=(ROOT/'terraform/isolated/main.tf').read_text(encoding='utf-8')
    source=source.replace('backend "s3" {}','backend "local" {}')
    relative=os.path.relpath(ROOT/'terraform',preview).replace('\\','/')
    source=re.sub(r'source\s*=\s*"\./\.\."','source = '+json.dumps(relative),source)
    (preview/'main.tf').write_text(source,encoding='utf-8')
    print('PREPARED ONLY:',folder/'manifest.json')
    print('No apply, producer or service start was executed.')

def context(path):
    m=json.loads(Path(path).read_text())
    env=m['environment']
    if not re.fullmatch(r'cap-[a-f0-9]{10}',env):raise RuntimeError('Not an isolated manifest')
    current=aws(m['profile'],m['region'],'sts','get-caller-identity')
    if current['Account']!=m['account']:raise RuntimeError('AWS account differs from manifest')
    expected={'data_bucket':f'coderhouse-{env}-lake-{m["account"]}',
              'glue_database':env.replace('-','_')+'_lakehouse',
              'application':f'coderhouse-{env}-transactions-flink',
              'stream':env+'-transactions-stream','workgroup':f'coderhouse-{env}-analytics'}
    if any(m.get(k)!=v for k,v in expected.items()):raise RuntimeError('Manifest resource names do not match isolated environment')
    return m

def initialize(args):
    if not args.execute:print('Dry run: initialize requires --execute in the authorized apply');return
    names={k:os.environ.get('CAPSTONE_'+k,'') for k in ['PROFILE','REGION','STREAM','DATABASE','TABLE','WORKGROUP']}
    if not names['WORKGROUP'].startswith('coderhouse-cap-'):raise RuntimeError('SQL bootstrap refuses non-capstone workgroups')
    for key in ['REGION','STREAM','DATABASE','TABLE','WORKGROUP']:
        if not re.fullmatch(r'[a-z0-9_-]+',names[key]):raise RuntimeError('Invalid SQL identifier '+key)
    spec=importlib.util.spec_from_file_location('redshift',ROOT/'scripts/redshift-checkpoint6.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    out=EVIDENCE/names['WORKGROUP'];mod.EVIDENCE=out
    r=mod.Runner(argparse.Namespace(profile=names['PROFILE'],region=names['REGION'],workgroup=names['WORKGROUP']))
    # Flink owns valid Iceberg table creation. Wait for its constructor, never
    # create a generic Glue table with a fabricated metadata_location.
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        try:
            table=aws(names['PROFILE'],names['REGION'],'glue','get-table','--database-name',names['DATABASE'],'--name',names['TABLE'])
            if table['Table']['Parameters'].get('table_type')=='ICEBERG':break
        except RuntimeError as error:
            if 'EntityNotFoundException' not in str(error):raise
        time.sleep(10)
    else:raise TimeoutError('Flink did not initialize the Iceberg table within 300 s')
    all_sql=[]
    for part in mod.PARTS:
        if int(part.name[:2])>5:continue
        text=part.read_text(encoding='utf-8').replace('dev-transactions-stream',names['STREAM'])
        text=text.replace("'lakehouse_db'","'"+names['DATABASE']+"'").replace("'us-east-1'","'"+names['REGION']+"'")
        for index,statement in enumerate(mod.statements(text)):
            all_sql.append(statement+';')
            # SQL bootstrap is restartable without dropping an existing MV/role.
            if statement.startswith('CREATE MATERIALIZED VIEW'):
                exists=r.query("SELECT COUNT(*) AS n FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='streaming' AND c.relname='transactions_raw'",'existing-mv')
                if int(exists[0]['n']):continue
            if statement.startswith('CREATE ROLE'):
                exists=r.query("SELECT COUNT(*) AS n FROM svv_roles WHERE role_name='checkpoint6_analyst'",'existing-role')
                if int(exists[0]['n']):continue
            r.query(statement,'bootstrap-'+part.stem+'-'+str(index))
    (out/'bootstrap.sql').write_text('\n\n'.join(all_sql)+'\n',encoding='utf-8')
    save(out/'bootstrap-result.json',{'status':'PASSED','workgroup':names['WORKGROUP'],
                                     'note':'SQL initialized; E2E reconciliation is a separate test.'})

def fixture(run_id,window=None):
    base=window or dt.datetime.now(dt.timezone.utc).replace(second=0,microsecond=0)-dt.timedelta(minutes=2)
    method='card_'+run_id
    def event(suffix,seconds,amount,status='approved'):
        return {'transaction_id':run_id+'-'+suffix,'timestamp':(base+dt.timedelta(seconds=seconds)).isoformat(),
                'amount':amount,'payment_method':method,'status':status,
                'produced_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    repeated=event('duplicate',1,'10.00')
    initial=[event('out-of-order',12,'10.01'),repeated,dict(repeated),
             event('rejected',14,'999.00','rejected'),event('pending',15,'22.00','pending'),
             '{invalid-json',{'transaction_id':run_id+'-missing','amount':'1.00'},
             event('barrier-1',75,'0.00','rejected')]
    late=event('late',3,'1000.00')
    return {'run_id':run_id,'window_start':base.isoformat(),'method':method,'initial':initial,
            'after_commit':[late,event('barrier-2',135,'0.00','rejected')],
            'late_id_sha256':hashlib.sha256(late['transaction_id'].encode()).hexdigest(),
            'expected':{'iceberg_count':3,'iceberg_total':'30.01','iceberg_average':'10.003333',
                        'redshift_approved_count_all':4,'redshift_approved_total_all':'1030.01',
                        'excluded_late_count':1,'duplicates_counted':True}}


def e2e(args):
    """One-shot fixture; never republish automatically after a partial failure."""
    if not args.execute:
        print('Dry run. Requires an authorized isolated deployment and --execute.');return
    m=context(args.manifest)
    folder=EVIDENCE/m['environment'];folder.mkdir(parents=True,exist_ok=True)
    guard=folder/'send-started.json'
    if guard.exists():raise RuntimeError('One-shot guard exists. Inspect receipts; do not replay the fixture.')
    spec=importlib.util.spec_from_file_location('redshift',ROOT/'scripts/redshift-checkpoint6.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.EVIDENCE=folder
    r=mod.Runner(argparse.Namespace(profile=m['profile'],region=m['region'],workgroup=m['workgroup']))
    data=fixture('cap_'+uuid.uuid4().hex[:12]);save(folder/'fixture.json',data)
    # A brand-new stream avoids other producers advancing the global watermark.
    if int(r.query('SELECT COUNT(*) AS n FROM streaming.transactions_raw','empty-stream')[0]['n']):
        raise RuntimeError('The isolated MV is not empty. Use a new isolated environment.')
    save(guard,{'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'run_id':data['run_id']})
    receipts=[]
    def send(events):
        for event in events:
            payload=event if isinstance(event,str) else json.dumps(event)
            response=aws(m['profile'],m['region'],'kinesis','put-record','--stream-name',m['stream'],
                         '--partition-key',data['run_id'],'--data',base64.b64encode(payload.encode()).decode())
            receipts.append({'sent_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),**response})
            save(folder/'put-record-receipts.json',receipts)
    method=data['method'];start=data['window_start'].replace('T',' ').split('+')[0]
    predicate=f"payment_method='{method}' AND window_start=TIMESTAMP '{start}'"
    iceberg_sql='SELECT transaction_count,total_amount,average_amount FROM lakehouse.transaction_aggregates WHERE '+predicate
    def wait_iceberg():
        deadline=time.monotonic()+360
        while time.monotonic()<deadline:
            rows=r.query(iceberg_sql,'iceberg-window')
            if rows:return rows
            time.sleep(10)
        raise TimeoutError('No committed Iceberg window after 360 seconds')
    send(data['initial'])
    before=wait_iceberg()
    if len(before)!=1 or int(before[0]['transaction_count'])!=3 or Decimal(str(before[0]['total_amount']))!=Decimal('30.01'):
        raise AssertionError('Initial Iceberg window differs; late phase was not sent')
    send(data['after_commit'])
    # Require explicit late side-output evidence, not an arbitrary wall-clock delay.
    deadline=time.monotonic()+180;late_events=[]
    while time.monotonic()<deadline:
        late_events=aws(m['profile'],m['region'],'logs','filter-log-events',
                        '--log-group-name','/aws/kinesis-analytics/'+m['application'],
                        '--filter-pattern','"'+data['late_id_sha256']+'"').get('events',[])
        if late_events:break
        time.sleep(10)
    if not late_events:raise TimeoutError('Late-drop audit record not observed; reconciliation remains unverified')
    save(folder/'late-drop-log.json',late_events)
    late_id=data['after_commit'][0]['transaction_id']
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        r.query('REFRESH MATERIALIZED VIEW streaming.transactions_raw','refresh')
        count=r.query('SELECT COUNT(*) AS n FROM streaming.transactions_raw','raw-count')
        if int(count[0]['n'])==10:break
        time.sleep(10)
    else:raise TimeoutError('Redshift did not consume all ten fixture records')
    sql=f"""SELECT DATE_TRUNC('minute',event_time) AS window_start,payment_method,
      COUNT(*) AS transaction_count,SUM(amount) AS total_amount,
      AVG(amount::decimal(24,6))::decimal(38,6) AS average_amount,
      MAX(approximate_arrival_timestamp) AS arrival_timestamp
      FROM analytics.transactions_typed WHERE validation_error IS NULL AND status='approved'
      AND payment_method='{method}' AND transaction_id<>'{late_id}' GROUP BY 1,2"""
    equivalent=r.query(sql,'equivalent-metrics');after=r.query(iceberg_sql,'iceberg-after-late')
    joined=r.query('SELECT r.window_start,r.payment_method,r.transaction_count AS recent_count,'
        'h.transaction_count AS iceberg_count,r.total_amount AS recent_total,h.total_amount AS iceberg_total '
        'FROM ('+sql+') r JOIN lakehouse.transaction_aggregates h '
        'ON r.window_start=h.window_start AND r.payment_method=h.payment_method','same-session-join')
    if len(joined)!=1:raise AssertionError('Same-session JOIN did not produce one reconciled window')
    all_approved=r.query(f"SELECT COUNT(*) AS n,SUM(amount) AS total FROM analytics.transactions_typed WHERE validation_error IS NULL AND status='approved' AND payment_method='{method}'",'raw-approved-including-late')
    if len(equivalent)!=1 or len(after)!=1:raise AssertionError('Expected one equivalent window per route')
    for field in ['transaction_count','total_amount','average_amount']:
        if Decimal(str(equivalent[0][field]))!=Decimal(str(after[0][field])):
            raise AssertionError('Mismatch in '+field)
    if int(all_approved[0]['n'])!=4 or Decimal(str(all_approved[0]['total']))!=Decimal('1030.01'):
        raise AssertionError('Raw approved metrics differ from the fixture')
    table=aws(m['profile'],m['region'],'glue','get-table','--database-name',m['glue_database'],'--name','transaction_aggregates')
    save(folder/'glue-table.json',table)
    location=table['Table']['Parameters']['metadata_location'];bucket,key=location[5:].split('/',1)
    aws(m['profile'],m['region'],'s3api','get-object','--bucket',bucket,'--key',key,str(folder/'iceberg-metadata.json'))
    metadata=json.loads((folder/'iceberg-metadata.json').read_text())
    snapshot=next(s for s in metadata['snapshots'] if s['snapshot-id']==metadata['current-snapshot-id'])
    if int(snapshot['summary'].get('flink.max-committed-checkpoint-id','0'))<=0:
        raise AssertionError('No Flink checkpoint ID in the current snapshot')
    save(folder/'application.json',aws(m['profile'],m['region'],'kinesisanalyticsv2','describe-application',
                                     '--application-name',m['application']))
    r.query("SELECT * FROM sys_stream_scan_states WHERE external_schema_name='kinesis_source' ORDER BY record_time DESC LIMIT 20",'stream-scan-states')
    r.query("SELECT * FROM sys_stream_scan_errors WHERE external_schema_name='kinesis_source' ORDER BY record_time DESC LIMIT 20",'stream-scan-errors')
    r.query("SELECT * FROM sys_mv_refresh_history WHERE schema_name='streaming' ORDER BY start_time DESC LIMIT 20",'mv-refresh-history')
    (folder/'reconciliation.sql').write_text(sql+';\n',encoding='utf-8')
    save(folder/'reconciliation.json',{'status':'PASSED','expected':data['expected'],
         'redshift_equivalent':equivalent,'iceberg':after,'raw_approved':all_approved,'same_session_join':joined,
         'late_exclusion':'Only the controlled event confirmed by the Flink late side output is excluded. '
                          'This is a fixture oracle, not a general production late-event classifier.',
         'guarantee':'Equivalent window metrics, not global exactly-once across independent consumers.'})
    print('Controlled reconciliation PASSED:',folder)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('prepare');s.add_argument('--profile',required=True);s.add_argument('--region',default='us-east-1')
    s=sub.add_parser('initialize');s.add_argument('--execute',action='store_true')
    s=sub.add_parser('fixture');s.add_argument('--run-id',default='cap_'+uuid.uuid4().hex[:12])
    s=sub.add_parser('e2e');s.add_argument('--manifest',required=True);s.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.command=='prepare':prepare(args)
    elif args.command=='initialize':initialize(args)
    elif args.command=='e2e':e2e(args)
    else:
        data=fixture(args.run_id);save(EVIDENCE/'fixture.json',data);print(json.dumps(data,indent=2))

if __name__=='__main__':main()
