"""Configure local Terraform backend metadata, never create AWS infrastructure."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',required=True)
    p.add_argument('--region',default='us-east-1')
    p.add_argument('--existing-dev',action='store_true')
    p.add_argument('--initialize',action='store_true')
    a=p.parse_args()
    if not a.existing_dev:raise SystemExit('Use --existing-dev only to attach the original dev state; isolated setup is capstone.py prepare.')
    identity=json.loads(subprocess.check_output(['aws','sts','get-caller-identity','--profile',a.profile,'--region',a.region,'--output','json']))
    config={'bucket':'coderhouse-terraform-'+identity['Account'],'key':'environments/dev/terraform.tfstate',
            'region':a.region,'profile':a.profile,'encrypt':True,'dynamodb_table':'coderhouse-terraform-locks'}
    cache=ROOT/'terraform/.terraform/terraform.tfstate'
    if cache.exists():
        before=json.loads(cache.read_text())['backend']['config']
        if any(before.get(key)!=config[key] for key in ['bucket','key']):
            raise SystemExit('Refusing to switch an existing backend cache to a different bucket/key')
    path=ROOT/'terraform/existing.backend.hcl'
    path.write_text('\n'.join(k+' = '+json.dumps(v) for k,v in config.items())+'\n',encoding='utf-8')
    print('Existing backend bucket/key preserved; local file:',path)
    if a.initialize:
        subprocess.run(['terraform','-chdir=terraform','init','-input=false','-reconfigure',
                        '-backend-config=existing.backend.hcl'],cwd=ROOT,check=True)

if __name__=='__main__':main()
