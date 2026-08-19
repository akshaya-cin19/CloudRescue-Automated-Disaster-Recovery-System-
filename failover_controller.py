"""
failover_controller.py
------------------------
The core disaster-recovery brain. When the HealthMonitor raises an alarm
on the PRIMARY instance, this controller:
  1. Restores the SECONDARY from the latest S3 snapshot (ensures no data loss
     beyond the last backup interval — RPO).
  2. Promotes the SECONDARY to PRIMARY.
  3. Updates the simulated Route53 traffic target so new requests go to
     the newly-promoted instance (RTO is the time this whole process takes).
  4. Notifies operators via the NotificationService.
"""

import time


class FailoverController:
    def __init__(self, primary, secondary, storage, notifier, logger=None):
        self.primary = primary
        self.secondary = secondary
        self.storage = storage
        self.notifier = notifier
        self.logger = logger
        self.active_endpoint = primary   # simulates a Route53 DNS record
        self.failover_events = []

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    def trigger_failover(self, failed_instance):
        start = time.time()
        self._log(f"[DR-Controller] Disaster detected on {failed_instance.instance_id}. Initiating failover...")

        # Step 1: restore secondary from latest backup to minimize data loss (RPO)
        snapshot = self.storage.get_latest_snapshot(self.primary.instance_id)
        if snapshot:
            self.secondary.restore(snapshot)
            self._log(f"[DR-Controller] Secondary restored from snapshot taken at "
                      f"{time.strftime('%H:%M:%S', time.localtime(snapshot['timestamp']))}")
        else:
            self._log("[DR-Controller] WARNING: No snapshot found, secondary starting with empty state")

        # Step 2: promote secondary
        self.secondary.role = "PRIMARY"
        failed_instance.role = "SECONDARY"

        # Step 3: redirect traffic (simulated Route53 update)
        self.active_endpoint = self.secondary
        self._log(f"[Route53] DNS record updated -> traffic now routed to {self.secondary.instance_id} "
                  f"({self.secondary.region})")

        rto = time.time() - start
        self.failover_events.append({
            "failed_instance": failed_instance.instance_id,
            "promoted_instance": self.secondary.instance_id,
            "rto_seconds": round(rto, 3),
            "timestamp": time.time(),
        })

        # Step 4: notify
        self.notifier.send(
            subject="CloudRescue DR ALERT: Automatic Failover Triggered",
            message=(f"{failed_instance.instance_id} went DOWN in {failed_instance.region}. "
                     f"Traffic automatically failed over to {self.secondary.instance_id} "
                     f"in {self.secondary.region}. RTO = {rto:.3f}s")
        )
        self._log(f"[DR-Controller] Failover complete. RTO = {rto:.3f}s")
        return self.secondary

    def route_request(self):
        """All live traffic goes through here, always hitting the active endpoint."""
        return self.active_endpoint.process_request()
