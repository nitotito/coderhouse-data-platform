"""Host-side read-only checks and receipt collection. No AWS credentials are used."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/evidence/capstone/local"

def command(args,name):
    result=subprocess.run(args,cwd=ROOT,text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (OUT/name).write_text(result.stdout,encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{name}: exit {result.returncode}")
    return result.stdout

def main():
    result=json.loads((OUT/"result.json").read_text())
    recovery=json.loads((OUT/"recovery-after.json").read_text())
    assert result["status"]==recovery["status"]=="PASSED"
    assert json.loads((OUT/"clean-precondition.json").read_text())["state_absent"]
    apply=(OUT/"clean-terraform-apply.txt").read_text()
    assert "20 added, 0 changed, 0 destroyed" in apply
    old_plan=OUT/"terraform-idempotent-plan.txt"
    if old_plan.exists() and "2 to change" in old_plan.read_text():
        old_plan.rename(OUT/"development-tag-drift-plan.txt")
    command(["docker","compose","run","--rm","terraform","tflocal plan -input=false -detailed-exitcode -no-color"],"terraform-idempotent-plan.txt")
    command(["docker","compose","run","--rm","terraform","terraform validate -json"],"terraform-local-validation.txt")
    command(["docker","compose","logs","--no-color","jobmanager","taskmanager"],"flink-runtime.txt")
    command(["docker","compose","ps","-a","--format","json"],"compose-services.jsonl")
    for name in ("terraform-aws-validation.json","terraform-bootstrap-validation.json","terraform-isolated-validation.json"):
        assert json.loads((OUT/name).read_text(encoding="utf-8-sig"))["valid"]
    shots=OUT/"screenshots"
    missing=[name for name in ("flink-checkpoints.png","postgres.png","duckdb.png") if not (shots/name).exists()]
    (OUT/"verification.json").write_text(json.dumps(dict(technical_checks="PASSED",run_id=result["run_id"],clean_deployment=True,aws_deployed=False,recovery=True,terraform_plan_exit=0,missing_screenshots=missing,ready_to_submit=not missing),indent=2)+"\n")
    print("Technical verification PASSED; missing screenshots:",missing)

if __name__=="__main__":
    main()
