"""
dr_orchestrator.py
--------------------
Ties together CloudInstance, S3BackupStorage, HealthMonitor,
FailoverController and NotificationService into one runnable
CloudRescue disaster-recovery system, and plays out a demo timeline:

  1. Primary + secondary instances start up, primary serves live traffic.
  2. A background thread takes periodic S3 backups of the primary.
  3. CloudWatch-style health checks run continuously in the background.
  4. A simulated disaster takes the primary down.
  5. Health checks detect the failure and an alarm fires.
  6. FailoverController restores the secondary from the latest backup,
     promotes it, and reroutes traffic — all automatically.
  7. Live traffic continues uninterrupted (beyond the failover window)
     on the newly-promoted instance.
"""

import os
import time
import threading
import logging

from src.cloud_instance import CloudInstance
from src.s3_backup_storage import S3BackupStorage
from src.health_monitor import HealthMonitor
from src.notification_service import NotificationService
from src.failover_controller import FailoverController


class CloudRescueSystem:
    def __init__(self, log_path):
        self.logger = self._setup_logger(log_path)

        self.primary = CloudInstance("i-primary-01", role="PRIMARY", region="ap-south-1")
        self.secondary = CloudInstance("i-secondary-01", role="SECONDARY", region="ap-south-2")

        bucket_path = os.path.join(os.path.dirname(log_path), "..", "backup_bucket")
        self.storage = S3BackupStorage(bucket_path, logger=self.log)
        self.notifier = NotificationService(logger=self.log)
        self.controller = FailoverController(
            self.primary, self.secondary, self.storage, self.notifier, logger=self.log
        )
        self.monitor = HealthMonitor(
            self.primary, interval=0.5, failure_threshold=3, logger=self.log
        )
        self.monitor.on_alarm(self.controller.trigger_failover)

        self._backup_thread_stop = threading.Event()
        self._traffic_thread_stop = threading.Event()

    def _setup_logger(self, log_path):
        logger = logging.getLogger("CloudRescue")
        logger.setLevel(logging.INFO)
        logger.handlers = []
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        logger.addHandler(fh)
        return logger

    def log(self, msg):
        print(msg)
        self.logger.info(msg)

    def _periodic_backup_loop(self, interval):
        counter = 0
        while not self._backup_thread_stop.is_set():
            counter += 1
            self.primary.write_data(f"txn_{counter}", f"order-{counter}-confirmed")
            snapshot = self.primary.snapshot()
            self.storage.upload_snapshot(snapshot)
            time.sleep(interval)

    def _traffic_loop(self, interval):
        while not self._traffic_thread_stop.is_set():
            try:
                result = self.controller.route_request()
                self.log(f"[Traffic] {result}")
            except RuntimeError as e:
                self.log(f"[Traffic] ERROR: {e}")
            time.sleep(interval)

    def run_demo(self):
        self.log("=" * 70)
        self.log("CloudRescue - Automated Disaster Recovery System")
        self.log("=" * 70)
        self.log(f"Primary   : {self.primary}")
        self.log(f"Secondary : {self.secondary}")
        self.log("-" * 70)

        self.monitor.start()
        backup_thread = threading.Thread(target=self._periodic_backup_loop, args=(1.0,), daemon=True)
        traffic_thread = threading.Thread(target=self._traffic_loop, args=(0.7,), daemon=True)
        backup_thread.start()
        traffic_thread.start()

        self.log("[Phase 1] System running normally. Serving traffic + taking backups...")
        time.sleep(4)

        self.log("-" * 70)
        self.log("[Phase 2] SIMULATING DISASTER: primary region ap-south-1 goes DOWN")
        self.primary.simulate_disaster()
        self.log("-" * 70)

        # Wait long enough for health checks to detect failure and failover to trigger
        time.sleep(5)

        self.log("-" * 70)
        self.log("[Phase 3] Post-failover: verifying traffic continuity on promoted instance")
        time.sleep(3)

        self._backup_thread_stop.set()
        self._traffic_thread_stop.set()
        self.monitor.stop()

        self.log("-" * 70)
        self.log("[Summary]")
        self.log(f"  Requests served (active endpoint): {self.controller.active_endpoint.requests_served}")
        self.log(f"  Backups stored in S3 bucket: {len(self.storage.list_snapshots('i-primary-01'))}")
        for event in self.controller.failover_events:
            self.log(f"  Failover event: {event}")
        self.log(f"  Notifications sent: {len(self.notifier.sent_notifications)}")
        self.log("=" * 70)
        self.log("Demo complete.")
