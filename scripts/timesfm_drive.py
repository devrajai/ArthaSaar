#!/usr/bin/env python3
"""
timesfm_drive.py - keep the TimesFM model cache and its output on Google Drive.

The checkpoint is about 1 GB. Downloading it from HuggingFace on every forecast run is
slow and rate-limited, so the workflow treats Drive as the store:

    --pull   restore the model cache from Drive into the local HF_HOME
    --push   save the local model cache to Drive (one zip, overwritten each time)
    --push-forecasts   copy data/timesfm_forecasts.json to Drive as well

The cache is uploaded as a single zip rather than synced file-by-file: the HuggingFace
cache is a deep tree of small files, and one archive is far fewer API calls.

Credentials: same service account as the rest of the hub.
  GOOGLE_SA_JSON  (the JSON itself, used in CI)  or  GOOGLE_APPLICATION_CREDENTIALS
  --folder-id     or  ARTHASAAR_DRIVE_FOLDER

Usage:
  python scripts/timesfm_drive.py --pull
  python scripts/timesfm_drive.py --push
  python scripts/timesfm_drive.py --push-forecasts
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import zipfile
from pathlib import Path

ARCHIVE_NAME = "timesfm_model_cache.zip"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    raw = os.environ.get("GOOGLE_SA_JSON")
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
    else:
        raise SystemExit("No Drive credentials. Set GOOGLE_SA_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_file(svc, folder_id: str, name: str):
    q = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    res = svc.files().list(q=q, fields="files(id,name,size)", pageSize=10).execute()
    files = res.get("files", [])
    return files[0] if files else None


def pull(svc, folder_id: str, cache_dir: Path) -> int:
    f = find_file(svc, folder_id, ARCHIVE_NAME)
    if not f:
        print(f"no {ARCHIVE_NAME} on Drive yet - will download from HuggingFace instead")
        return 0
    from googleapiclient.http import MediaIoBaseDownload

    cache_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=f["id"]), chunksize=8 << 20)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    with zipfile.ZipFile(buf) as z:
        z.extractall(cache_dir)
    print(f"restored model cache from Drive ({int(f.get('size', 0)) / 1e6:.1f} MB) -> {cache_dir}")
    return 1


def push(svc, folder_id: str, cache_dir: Path) -> int:
    if not cache_dir.exists() or not any(cache_dir.iterdir()):
        print(f"nothing to push - {cache_dir} is empty")
        return 0
    from googleapiclient.http import MediaFileUpload

    tmp = Path("/tmp") / ARCHIVE_NAME
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in cache_dir.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(cache_dir))
    size = tmp.stat().st_size
    existing = find_file(svc, folder_id, ARCHIVE_NAME)
    media = MediaFileUpload(str(tmp), mimetype="application/zip", resumable=True)
    if existing:
        svc.files().update(fileId=existing["id"], media_body=media).execute()
        print(f"updated {ARCHIVE_NAME} on Drive ({size / 1e6:.1f} MB)")
    else:
        svc.files().create(body={"name": ARCHIVE_NAME, "parents": [folder_id]},
                           media_body=media, fields="id").execute()
        print(f"uploaded {ARCHIVE_NAME} to Drive ({size / 1e6:.1f} MB)")
    tmp.unlink(missing_ok=True)
    return 1


def push_file(svc, folder_id: str, local: Path) -> int:
    if not local.exists():
        print(f"{local} does not exist - nothing to upload")
        return 0
    from googleapiclient.http import MediaFileUpload

    existing = find_file(svc, folder_id, local.name)
    media = MediaFileUpload(str(local), mimetype="application/json", resumable=False)
    if existing:
        svc.files().update(fileId=existing["id"], media_body=media).execute()
    else:
        svc.files().create(body={"name": local.name, "parents": [folder_id]},
                           media_body=media, fields="id").execute()
    print(f"uploaded {local.name} to Drive ({local.stat().st_size / 1e3:.1f} KB)")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="TimesFM model cache <-> Google Drive")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--push-forecasts", action="store_true")
    ap.add_argument("--cache-dir", default=os.environ.get("HF_HOME", "/tmp/hf"))
    ap.add_argument("--forecasts", default="data/timesfm_forecasts.json")
    ap.add_argument("--folder-id", default=os.environ.get("ARTHASAAR_DRIVE_FOLDER", ""))
    ap.add_argument("--local-dir", default="", help="skip Drive entirely; copy cache here")
    args = ap.parse_args()

    cache = Path(args.cache_dir)

    if args.local_dir:
        # offline mode, used for testing
        dest = Path(args.local_dir)
        if args.pull and cache.exists():
            shutil.copytree(cache, dest, dirs_exist_ok=True)
            print(f"copied {cache} -> {dest}")
        return 0

    if not args.folder_id:
        raise SystemExit("Need --folder-id or ARTHASAAR_DRIVE_FOLDER.")

    svc = service()
    rc = 0
    if args.pull:
        rc |= pull(svc, args.folder_id, cache)
    if args.push:
        rc |= push(svc, args.folder_id, cache)
    if args.push_forecasts:
        rc |= push_file(svc, args.folder_id, Path(args.forecasts))
    if not (args.pull or args.push or args.push_forecasts):
        print("nothing to do - pass --pull, --push or --push-forecasts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
