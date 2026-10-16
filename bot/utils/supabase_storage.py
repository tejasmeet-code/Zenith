# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   ░█▀▀░█▀█░█▀▄░█▀▀░█░█   ░█▀▄░█▀▀░█░█░█▀▀                     ║
# ║   ░█░░░█░█░█░█░█▀▀░▄▀▄   ░█░█░█▀▀░▀▄▀░▀▀█                     ║
# ║   ░▀▀▀░▀▀▀░▀▀░░▀▀▀░▀░▀   ░▀▀░░▀▀▀░░▀░░▀▀▀                     ║
# ║                                                                  ║
# ║            © 2026 Zenith Development — All Rights Reserved       ║
# ║                                                                  ║
# ║   discord  ──  https://discord.gg/WqJGXrQX4                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import json
import asyncio
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = logging.getLogger("Zenith.Supabase")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nmeqxucqhufcovqcdhuk.supabase.co").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("Supabse_servicerole_key", os.getenv("SUPABASE_ANON_KEY", "")))
DEFAULT_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "zenith-data")


class SupabaseStorageManager:
    """
    Manages cloud persistence for Zenith Discord Bot using Supabase Storage
    and Supabase REST database tables.
    """
    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_KEY, bucket: str = DEFAULT_BUCKET):
        self.url = url
        self.key = key
        self.bucket = bucket
        self.last_backup_time: Optional[datetime] = None
        self.backup_history: List[Dict[str, Any]] = []

    def _headers(self, content_type: str = "application/json", upsert: bool = True) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers

    def ensure_bucket(self) -> bool:
        """Ensure that the default storage bucket exists."""
        if not self.key:
            logger.warning("[Supabase] No API key configured. Skipping storage initialization.")
            return False
        try:
            req = urllib.request.Request(
                f"{self.url}/storage/v1/bucket",
                headers=self._headers()
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                buckets = json.loads(resp.read().decode("utf-8"))
                for b in buckets:
                    if b.get("name") == self.bucket or b.get("id") == self.bucket:
                        return True

            # If not found, attempt to create it
            create_req = urllib.request.Request(
                f"{self.url}/storage/v1/bucket",
                data=json.dumps({"id": self.bucket, "name": self.bucket, "public": True}).encode("utf-8"),
                headers=self._headers(),
                method="POST"
            )
            with urllib.request.urlopen(create_req, timeout=10) as resp:
                logger.info(f"[Supabase] Created bucket '{self.bucket}' successfully.")
                return True
        except Exception as e:
            logger.error(f"[Supabase] Error ensuring bucket '{self.bucket}': {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str, mime_type: str = "application/octet-stream") -> bool:
        """Uploads a local file to Supabase Storage."""
        if not os.path.exists(local_path):
            logger.warning(f"[Supabase] Local file not found: {local_path}")
            return False

        try:
            with open(local_path, "rb") as f:
                data = f.read()

            endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{remote_path}"
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers=self._headers(content_type=mime_type, upsert=True),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status in (200, 201)
        except urllib.error.HTTPError as e:
            logger.error(f"[Supabase] Upload failed for {remote_path}: HTTP {e.code} - {e.read().decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            logger.error(f"[Supabase] Upload exception for {remote_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Downloads a file from Supabase Storage to local filesystem."""
        try:
            endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{remote_path}"
            req = urllib.request.Request(
                endpoint,
                headers=self._headers(content_type="", upsert=False)
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(data)
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            logger.error(f"[Supabase] Download failed for {remote_path}: HTTP {e.code}")
            return False
        except Exception as e:
            logger.error(f"[Supabase] Download exception for {remote_path}: {e}")
            return False

    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Lists files in the Supabase Storage bucket."""
        try:
            endpoint = f"{self.url}/storage/v1/object/list/{self.bucket}"
            norm_prefix = prefix.strip()
            if norm_prefix and not norm_prefix.endswith("/"):
                norm_prefix = f"{norm_prefix}/"
            payload = json.dumps({"prefix": norm_prefix, "limit": limit}).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers=self._headers(content_type="application/json", upsert=False),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"[Supabase] Error listing files with prefix '{prefix}': {e}")
            return []

    # ── Table Persistence (bot_json_store) ──────────────────────────────────────────

    def save_json_store(self, store_name: str, payload: Any) -> bool:
        """Saves a JSON payload to the Supabase bot_json_store table."""
        try:
            endpoint = f"{self.url}/rest/v1/bot_json_store"
            body = json.dumps({
                "store_name": store_name,
                "payload": payload,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }).encode("utf-8")

            headers = self._headers(content_type="application/json", upsert=True)
            headers["Prefer"] = "resolution=merge-duplicates"

            req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 201, 204)
        except Exception as e:
            pass
            return False

    def get_json_store(self, store_name: str) -> Optional[Any]:
        """Fetches a JSON payload from the Supabase bot_json_store table."""
        try:
            endpoint = f"{self.url}/rest/v1/bot_json_store?store_name=eq.{urllib.parse.quote(store_name)}&select=payload"
            headers = self._headers(content_type="", upsert=False)
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                items = json.loads(resp.read().decode("utf-8"))
                if items and len(items) > 0:
                    return items[0].get("payload")
            return None
        except Exception as e:
            logger.error(f"[Supabase] Error fetching json store '{store_name}': {e}")
            return None

    # ── Database & State Backup / Restore ─────────────────────────────────────────

    def backup_databases(self, base_dir: str = ".") -> Dict[str, Any]:
        """
        Backs up all SQLite databases and JSON state files to Supabase Storage.
        """
        results = {"success": [], "failed": [], "timestamp": datetime.utcnow().isoformat()}

        # 1. Back up SQLite databases
        db_dir = os.path.join(base_dir, "db")
        if os.path.exists(db_dir):
            for fname in os.listdir(db_dir):
                if fname.endswith(".db"):
                    lpath = os.path.join(db_dir, fname)
                    rpath = f"db/{fname}"
                    if self.upload_file(lpath, rpath, mime_type="application/x-sqlite3"):
                        results["success"].append(rpath)
                    else:
                        results["failed"].append(rpath)

        # Root databases
        for root_db in ["j2c_data.db", "rr.db"]:
            lpath = os.path.join(base_dir, root_db)
            if os.path.exists(lpath):
                rpath = f"db/{root_db}"
                if self.upload_file(lpath, rpath, mime_type="application/x-sqlite3"):
                    results["success"].append(rpath)
                else:
                    results["failed"].append(rpath)

        # 2. Back up JSON databases
        jsondb_dir = os.path.join(base_dir, "jsondb")
        if os.path.exists(jsondb_dir):
            for fname in os.listdir(jsondb_dir):
                if fname.endswith(".json"):
                    lpath = os.path.join(jsondb_dir, fname)
                    rpath = f"jsondb/{fname}"
                    if self.upload_file(lpath, rpath, mime_type="application/json"):
                        results["success"].append(rpath)
                    else:
                        results["failed"].append(rpath)
                    
                    # Also persist to bot_json_store table
                    try:
                        with open(lpath, "r", encoding="utf-8") as jf:
                            self.save_json_store(fname, json.load(jf))
                    except Exception:
                        pass

        # 3. Save manifest
        manifest_data = json.dumps(results, indent=2).encode("utf-8")
        try:
            req = urllib.request.Request(
                f"{self.url}/storage/v1/object/{self.bucket}/backup_manifest.json",
                data=manifest_data,
                headers=self._headers(content_type="application/json", upsert=True),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception:
            pass

        self.last_backup_time = datetime.utcnow()
        self.backup_history.append(results)
        return results

    def restore_databases(self, base_dir: str = ".") -> Dict[str, Any]:
        """
        Restores SQLite databases and JSON state files from Supabase Storage.
        Only overwrites local files if they don't exist or are empty (0 bytes).
        """
        results = {"restored": [], "skipped": [], "failed": []}

        # Check files in storage
        remote_db_files = self.list_files(prefix="db")
        for item in remote_db_files:
            fname = item.get("name")
            if not fname:
                continue
            rpath = f"db/{fname}"
            if fname in ["j2c_data.db", "rr.db"]:
                lpath = os.path.join(base_dir, fname)
            else:
                lpath = os.path.join(base_dir, "db", fname)

            # If local file is missing or 0 bytes, restore it
            if not os.path.exists(lpath) or os.path.getsize(lpath) == 0:
                if self.download_file(rpath, lpath):
                    results["restored"].append(rpath)
                else:
                    results["failed"].append(rpath)
            else:
                results["skipped"].append(rpath)

        # Check JSON files in storage
        remote_json_files = self.list_files(prefix="jsondb")
        for item in remote_json_files:
            fname = item.get("name")
            if not fname:
                continue
            rpath = f"jsondb/{fname}"
            lpath = os.path.join(base_dir, "jsondb", fname)

            if not os.path.exists(lpath) or os.path.getsize(lpath) == 0:
                if self.download_file(rpath, lpath):
                    results["restored"].append(rpath)
                else:
                    results["failed"].append(rpath)
            else:
                results["skipped"].append(rpath)

        # Also restore existing table stores from bot_json_store (e.g. jail.json, music_247_sessions.json)
        try:
            for store_name in ["jail.json", "music_247_sessions.json"]:
                lpath = os.path.join(base_dir, "jsondb", store_name)
                if not os.path.exists(lpath):
                    data = self.get_json_store(store_name)
                    if data:
                        os.makedirs(os.path.dirname(lpath), exist_ok=True)
                        with open(lpath, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        results["restored"].append(f"bot_json_store/{store_name}")
        except Exception as e:
            logger.error(f"[Supabase] Error restoring table stores: {e}")

        return results


# Global singleton instance
supabase_storage = SupabaseStorageManager()

async def run_periodic_backup(interval_minutes: int = 15, base_dir: str = "."):
    """Background loop to periodically sync SQLite and JSON data to Supabase."""
    await asyncio.sleep(60) # Initial startup delay
    while True:
        try:
            logger.info("[Supabase] Starting periodic background backup...")
            res = await asyncio.to_thread(supabase_storage.backup_databases, base_dir)
            success_count = len(res.get("success", []))
            failed_count = len(res.get("failed", []))
            logger.info(f"[Supabase] Periodic backup completed: {success_count} synced, {failed_count} failed.")
        except Exception as e:
            logger.error(f"[Supabase] Periodic backup error: {e}")
        await asyncio.sleep(interval_minutes * 60)

async def init_supabase_storage(client=None, base_dir: str = "."):
    """Restores databases from Supabase on startup and starts the periodic sync task."""
    try:
        print("\033[36m★ Supabase Storage: Initializing cloud persistence engine...\033[0m")
        res = await asyncio.to_thread(supabase_storage.restore_databases, base_dir)
        restored = len(res.get("restored", []))
        verified = len(res.get("verified", []))
        print(f"\033[32m◈ Supabase Storage: {restored} restored, {verified} cloud verified.\033[0m")
        asyncio.create_task(run_periodic_backup(15, base_dir))
    except Exception as e:
        print(f"\033[31m✖ Supabase Storage initialization error: {e}\033[0m")
