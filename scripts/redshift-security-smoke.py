"""Run the analyst allow/deny checks in a retained Data API session.

Requires the explicitly authorized temporary warehouse. Creates one password-
disabled database-only test user, which disappears with namespace teardown.
"""
import importlib.util
import argparse
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('runner',Path(__file__).with_name('redshift-checkpoint6.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SessionRunner(m.Runner):
    session_id = None

    def aws(self,*command):
        if command[:2] == ('redshift-data','execute-statement'):
            if self.session_id:
                command = list(command)
                for flag in ('--workgroup-name','--database'):
                    index = command.index(flag)
                    del command[index:index+2]
                command = tuple(command)
            command += ('--session-keep-alive-seconds','60')
            if self.session_id:
                command += ('--session-id',self.session_id)
            response = super().aws(*command)
            self.session_id = response['SessionId']
            return response
        return super().aws(*command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--profile',default='coderhouse-dev')
    parser.add_argument('--region',default='us-east-1')
    parser.add_argument('--workgroup',default='coderhouse-dev-analytics')
    parser.add_argument('--evidence-dir',type=Path)
    args=parser.parse_args()
    if args.evidence_dir:m.EVIDENCE=args.evidence_dir.resolve()
    if not args.execute:
        print('Dry run. Use --execute only for an authorized temporary warehouse.')
        return
    r = SessionRunner(args)
    existing = r.query("SELECT COUNT(*) AS users FROM pg_user WHERE usename='checkpoint6_access_test'",'security-existing-user')
    if int(existing[0]['users']) == 0:
        r.query('CREATE USER checkpoint6_access_test PASSWORD DISABLE','security-create-user')
    r.query('GRANT ROLE checkpoint6_analyst TO checkpoint6_access_test','security-grant-role')
    membership = r.query("SELECT user_name,role_name,admin_option FROM svv_user_grants "
                         "WHERE user_name='checkpoint6_access_test' AND role_name='checkpoint6_analyst'",
                         'security-effective-membership')
    if len(membership) != 1:
        raise AssertionError('Expected explicit analyst role membership in SVV_USER_GRANTS')
    grants = r.query("SELECT * FROM svv_relation_privileges WHERE identity_name='checkpoint6_analyst'",'security-grants')
    r.query('SET SESSION AUTHORIZATION checkpoint6_access_test','security-switch-user')
    identity = r.query('SELECT current_user AS db_user','security-identity')
    if identity[0]['db_user'] != 'checkpoint6_access_test':
        raise AssertionError('Analyst identity did not take effect')
    metrics = r.query('SELECT COUNT(*) AS rows FROM analytics.transactions_per_minute','security-allowed-metrics')
    comparison = r.query('SELECT COUNT(*) AS rows FROM analytics.recent_vs_iceberg','security-allowed-join')
    denied = []
    try:
        for sql,label in [('SELECT COUNT(*) FROM streaming.transactions_raw','security-denied-raw'),
                          ('REFRESH MATERIALIZED VIEW streaming.transactions_raw','security-denied-refresh')]:
            try:
                r.query(sql,label)
            except RuntimeError as error:
                if 'permission denied' not in str(error).lower() and 'must be owner' not in str(error).lower():
                    raise
                denied.append(label)
            else:
                raise AssertionError('Analyst unexpectedly allowed: '+label)
    finally:
        r.query('RESET SESSION AUTHORIZATION','security-reset-user')
    r.save('security-summary.json',{'status':'PASSED','identity':identity,'grants':grants,'membership':membership,
                                   'allowed_metrics':metrics,'allowed_join':comparison,'denied':denied})
    print('Analyst SELECT allowed; raw access and refresh denied.',flush=True)


if __name__ == '__main__':
    main()
