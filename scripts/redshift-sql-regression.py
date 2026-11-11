"""Exercise the real typed SELECT against temporary fixtures in Redshift.

Dry run writes reproducible SQL only. --execute needs a separately authorized
warehouse. This verifies conversions, not Kinesis ingestion or an Iceberg JOIN.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def fixture():
    epoch=str(int(dt.datetime(2026,11,11,15,tzinfo=dt.timezone.utc).timestamp()*1000))
    rows=[]
    for ident,timestamp,amount,error in [
        ('iso-z','2026-11-11T15:00:00Z','10.01',None),
        ('iso-offset','2026-11-11T12:00:00-03:00','10.00',None),
        ('epoch-ms',epoch,'10.00',None),
        ('bad-date','2026-02-30T15:00:00Z','1.00','invalid_timestamp'),
        ('no-timezone','2026-11-11T15:00:00','1.00','invalid_timestamp'),
        ('empty-time','','1.00','invalid_timestamp'),
        ('missing-time',None,'1.00','invalid_timestamp'),
        ('bad-money','2026-11-11T15:00:00Z','bad','invalid_amount'),
        ('missing-money','2026-11-11T15:00:00Z',None,'invalid_amount')]:
        payload={'transaction_id':ident,'payment_method':'card','status':'approved'}
        if timestamp is not None:payload['timestamp']=timestamp
        if amount is not None:payload['amount']=amount
        rows.append((ident,payload,error))
    return rows

def build():
    sql=(ROOT/'sql/redshift/03_analytics.sql').read_text(encoding='utf-8')
    sql='\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
    select=re.split(r'CREATE OR REPLACE VIEW analytics.transactions_typed AS\s*',sql,maxsplit=1)[1].split(';',1)[0]
    select=select.replace('streaming.transactions_raw','pe6_raw_fixture')
    statements=["CREATE TEMP TABLE pe6_raw_fixture (approximate_arrival_timestamp timestamp, "
                "refresh_time timestamp,shard_id varchar(128),sequence_number varchar(128),"
                "valid_json boolean,payload SUPER)"]
    for ident,payload,error in fixture():
        literal=json.dumps(payload).replace("'","''")
        statements.append("INSERT INTO pe6_raw_fixture VALUES (GETDATE(),GETDATE(),'fixture','"+
                          ident+"',true,JSON_PARSE('"+literal+"'))")
    statements.append(select+' ORDER BY transaction_id')
    return statements

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--profile',default='coderhouse-dev')
    p.add_argument('--region',default='us-east-1');p.add_argument('--workgroup',default='coderhouse-dev-analytics')
    a=p.parse_args();out=ROOT/'docs/evidence/checkpoint-6/revision'
    out.mkdir(parents=True,exist_ok=True)
    statements=build();(out/'typed-regression.sql').write_text(';\n\n'.join(statements)+';\n',encoding='utf-8')
    if not a.execute:print('Prepared SQL only. Redshift execution pending cost approval.');return
    spec=importlib.util.spec_from_file_location('security',ROOT/'scripts/redshift-security-smoke.py')
    security=importlib.util.module_from_spec(spec);spec.loader.exec_module(security)
    security.m.EVIDENCE=out;r=security.SessionRunner(a)
    for i,sql in enumerate(statements):observed=r.query(sql,'typed-regression-'+str(i))
    expected={ident:error for ident,payload,error in fixture()}
    if len(observed)!=len(expected):raise AssertionError('Fixture row count differs')
    for row in observed:
        if row['validation_error']!=expected[row['transaction_id']]:raise AssertionError(row)
        if row['transaction_id'] in ['iso-z','iso-offset','epoch-ms']:
            if row['event_time']!='2026-11-11 15:00:00':raise AssertionError(row)
    r.save('typed-regression-summary.json',{'status':'PASSED','rows':observed,
        'scope':'Actual SELECT from 03_analytics.sql; temporary fixtures only, no ingestion/JOIN proof'})
    print('Typed SQL regression PASSED in Redshift')

if __name__=='__main__':main()
