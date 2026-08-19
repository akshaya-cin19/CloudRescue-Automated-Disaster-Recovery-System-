"""
s3_backup_storage.py
---------------------
Simulates an AWS S3 bucket used for storing periodic snapshots/backups
of a CloudInstance. Backed by local JSON files on disk so the demo runs
with no real AWS credentials.
"""

import os
import json
import time


class S3BackupStorage:
    def __init__(self, bucket_path, logger=None):
        self.bucket_path = bucket_path
        self.logger = logger
        os.makedirs(self.bucket_path, exist_ok=True)

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    def upload_snapshot(self, snapshot):
        """Simulate an S3 PutObject call storing a backup snapshot."""
        instance_id = snapshot["instance_id"]
        ts = int(snapshot["timestamp"] * 1000)
        key = f"{instance_id}_{ts}.json"
        path = os.path.join(self.bucket_path, key)
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2)
        self._log(f"[S3] Snapshot uploaded -> s3://cloudrescue-dr-bucket/{key}")
        return key

    def list_snapshots(self, instance_id):
        """List all backup objects for a given instance, most recent last."""
        files = [
            f for f in os.listdir(self.bucket_path)
            if f.startswith(f"{instance_id}_")
        ]
        files.sort()
        return files

    def get_latest_snapshot(self, instance_id):
        """Fetch the most recent snapshot (simulated S3 GetObject)."""
        files = self.list_snapshots(instance_id)
        if not files:
            return None
        latest = files[-1]
        with open(os.path.join(self.bucket_path, latest)) as f:
            return json.load(f)
