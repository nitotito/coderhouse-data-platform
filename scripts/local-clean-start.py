"""Reset only this Compose laboratory, then prove a deployment with empty local state."""
import json
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/evidence/capstone/local"

def run(args,name):
    result=subprocess.run(args,cwd=ROOT,text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (OUT/name).write_text(result.stdout,encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}), see {name}")
    return result.stdout

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    previous=OUT/"development-run"
    previous.mkdir(exist_ok=True)
    for item in list(OUT.iterdir()):
        if item.is_file():
            shutil.copy2(item,previous/item.name)
    # docker compose scopes deletion to its own configured project and volumes.
    run(["docker","compose","down","--volumes","--remove-orphans"],"clean-down.txt")
    local=ROOT/"terraform/local"
    for name in ("terraform.tfstate","terraform.tfstate.backup","localstack_providers_override.tf"):
        target=local/name
        if target.parent.resolve()!=local.resolve():
            raise ValueError("Invalid local state path")
        target.unlink(missing_ok=True)
    (OUT/"clean-precondition.json").write_text(json.dumps(dict(state_absent=not (local/"terraform.tfstate").exists(),scope="only Compose project; AWS dev untouched"),indent=2))
    run(["docker","compose","up","-d","--build"],"clean-compose-up.txt")
    run(["docker","compose","logs","--no-color","terraform"],"clean-terraform-apply.txt")
    print("Clean deployment started. Run audit after Flink is RUNNING.")

if __name__=="__main__":
    main()
