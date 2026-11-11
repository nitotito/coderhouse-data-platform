"""Check SQL grammar and PDF/source agreement locally; never claims AWS success.

Dependencies: sqlglot and pypdf. Regenerate consolidated SQL and PDF first.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlglot
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
    runner=load('runner','scripts/redshift-checkpoint6.py')
    regression=load('regression','scripts/redshift-sql-regression.py')
    pdf=PdfReader(ROOT/'output/pdf/CheckPoint_Redshift_Lopez_Nicolas.pdf')
    text='\n'.join(page.extract_text() for page in pdf.pages)
    appendix=text.split('Anexo: SQL fuente de esta revisión',1)[1]
    pdf_lines={line.strip() for line in appendix.splitlines()}
    missing=[]
    for part in runner.PARTS:
        for line in part.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('--') and line.strip() not in pdf_lines:
                missing.append({'file':part.name,'line':line.strip()})
    if missing:raise AssertionError('PDF/source mismatch: '+json.dumps(missing))
    consolidated=(ROOT/'sql/redshift/checkpoint_6_complete.sql').read_text(encoding='utf-8')
    before=consolidated;runner.consolidate()
    if before!=(ROOT/'sql/redshift/checkpoint_6_complete.sql').read_text(encoding='utf-8'):
        raise AssertionError('Consolidated SQL was stale; regenerate the PDF')
    parsed={}
    for name in ['03_analytics.sql','04_iceberg.sql']:
        trees=sqlglot.parse((ROOT/'sql/redshift'/name).read_text(encoding='utf-8'),read='redshift')
        if any(t is None or isinstance(t,sqlglot.exp.Command) for t in trees):
            raise AssertionError('Parser did not inspect the SQL: '+name)
        parsed[name]=len(trees)
    for statement in regression.build():sqlglot.parse_one(statement,read='redshift')
    digest=hashlib.sha256((ROOT/'sql/redshift/checkpoint_6_complete.sql').read_bytes()).hexdigest()
    if digest not in text:raise AssertionError('PDF consolidated hash differs')
    result={'status':'LOCAL_CHECKS_PASSED','pdf_pages':len(pdf.pages),'parsed_view_statements':parsed,
            'temporary_fixture_statements':len(regression.build()),'fixture_cases':len(regression.fixture()),
            'all_source_code_lines_present_in_pdf':True,'consolidated_sha256':digest,
            'aws_clean_execution':'PENDING_AUTHORIZATION','effective_role_membership_capture':'PENDING'}
    evidence=ROOT/'docs/evidence/checkpoint-6/revision'
    if (evidence/'full-script-summary.json').exists():
        full=json.loads((evidence/'full-script-summary.json').read_text())
        if full['status']!='PASSED':raise AssertionError('Full script did not pass')
        executions=[json.loads(f.read_text()) for f in evidence.glob('*execution.json')]
        proof=[]
        for part in runner.PARTS:
            for index,statement in enumerate(runner.statements(part.read_text(encoding='utf-8'))):
                matches=[e for e in executions if e.get('Status')=='FINISHED' and e.get('QueryString')==statement]
                comparison='exact_returned_sql'
                if not matches and statement.startswith('CREATE EXTERNAL SCHEMA'):
                    # Redshift removes REGION and replaces IAM_ROLE in its
                    # returned statement text. Do not claim those hidden clauses
                    # were compared byte-for-byte.
                    prefix=statement.split('IAM_ROLE',1)[0].strip()
                    matches=[e for e in executions if e.get('Status')=='FINISHED'
                             and e.get('QueryString','').split('IAM_ROLE',1)[0].strip()==prefix]
                    comparison='external_schema_prefix_authentication_redacted_by_service'
                if not matches:raise AssertionError('No successful actual execution: '+part.name+':'+str(index+1))
                proof.append({'source':part.name,'statement':index+1,'execution_id':matches[0]['Id'],
                              'db_user':matches[0]['DbUser'],'status':'FINISHED','comparison':comparison})
        (evidence/'executed-source-proof.json').write_text(json.dumps({'status':'PASSED',
            'consolidated_sha256':digest,'statements':proof},indent=2)+'\n',encoding='utf-8')
        result['aws_clean_execution']='PASSED_ALL_SOURCE_STATEMENTS'
        result['verified_actual_statements']=len(proof)
    result['effective_role_membership_capture']='PRESENT' if (evidence/'membresia.png').exists() else 'PENDING'
    out=ROOT/'docs/evidence/checkpoint-6/revision/local-validation.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
