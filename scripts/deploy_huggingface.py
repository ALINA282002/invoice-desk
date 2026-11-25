"""Deploy the app to a Hugging Face Space (Docker) without git credentials.

    .venv\\Scripts\\python scripts\\deploy_huggingface.py [space_id] [branch]
        space_id defaults to alina282002/invoice-desk, branch to hf-space

Asks for a Hugging Face *write* token (hidden input; also read from HF_TOKEN if set), uploads the files
committed on the branch (exactly what git would push — nothing local or untracked), and replaces whatever
the Space held before. The Space then builds the Dockerfile and serves the app on https://<user>-<name>.hf.space.
"""
from __future__ import annotations

import getpass
import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
SPACE = ARGS[0] if len(ARGS) > 0 else "alina282002/invoice-desk"
BRANCH = ARGS[1] if len(ARGS) > 1 else "hf-space"


def main() -> int:
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token and "--visible" not in sys.argv:
        token = getpass.getpass(
            f"Paste your Hugging Face WRITE token for {SPACE.split('/')[0]} (input is hidden), then press Enter: ").strip()
    if not token.startswith("hf_"):
        # hidden input often ignores paste on Windows terminals: fall back to a visible prompt
        token = input("Paste your Hugging Face WRITE token (starts with hf_; it will be visible — revoke it after "
                      "deploying), then press Enter: ").strip().strip("'\"")
    if not token:
        print("No token entered — nothing uploaded.")
        return 1
    api = HfApi(token=token)
    try:
        who = api.whoami()["name"]
    except Exception as e:
        print(f"That token was rejected by Hugging Face: {e}")
        return 1
    if who.lower() != SPACE.split("/")[0].lower():
        print(f"This token belongs to '{who}', not '{SPACE.split('/')[0]}'. Create the token while signed in as the Space owner.")
        return 1
    print(f"Signed in to Hugging Face as {who}.")

    tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", BRANCH], capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(tmp, filter="data")
        n = sum(1 for p in Path(tmp).rglob("*") if p.is_file())
        print(f"Uploading {n} files from branch '{BRANCH}' to https://huggingface.co/spaces/{SPACE} …")
        api.upload_folder(folder_path=tmp, repo_id=SPACE, repo_type="space", delete_patterns=["*"],
                          commit_message=f"Deploy Invoice Desk from branch {BRANCH}")
    user, name = SPACE.split("/")
    print("\nDone. The Space is now building (about 5-10 minutes).")
    print(f"  Build log : https://huggingface.co/spaces/{SPACE}")
    print(f"  App link  : https://{user.lower()}-{name.lower().replace('_', '-')}.hf.space")
    return 0


if __name__ == "__main__":
    sys.exit(main())
