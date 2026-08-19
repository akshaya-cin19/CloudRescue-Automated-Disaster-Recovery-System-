"""
cloud_instance.py
------------------
Simulates an AWS EC2-style compute instance that can act as either the
PRIMARY (active) or SECONDARY (standby) node in a disaster-recovery pair.
"""

import time
import random


class CloudInstance:
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    DOWN = "DOWN"

    def __init__(self, instance_id, role, region):
        self.instance_id = instance_id
        self.role = role                # "PRIMARY" or "SECONDARY"
        self.region = region            # simulated AWS region, e.g. ap-south-1
        self.status = self.HEALTHY
        self.data_store = {}            # simulated application data (in-memory "disk")
        self.requests_served = 0

    def write_data(self, key, value):
        """Simulate an application write (e.g. a DB transaction)."""
        self.data_store[key] = value

    def process_request(self):
        """Simulate serving live traffic. Fails if the instance is DOWN."""
        if self.status == self.DOWN:
            raise RuntimeError(f"{self.instance_id} is DOWN — cannot serve traffic")
        self.requests_served += 1
        return f"[{self.instance_id}] request served (total={self.requests_served})"

    def health_check(self):
        """
        Simulate an AWS CloudWatch-style health probe.
        Returns True if healthy, False otherwise.
        """
        if self.status == self.DOWN:
            return False
        # small random jitter to mimic transient network blips
        return random.random() > 0.02

    def simulate_disaster(self):
        """Simulate an outage — instance region/zone goes down."""
        self.status = self.DOWN

    def simulate_recovery(self):
        """Simulate the instance being repaired / region restored."""
        self.status = self.HEALTHY

    def snapshot(self):
        """Return a copy of current state, used to create an S3 backup."""
        return {
            "instance_id": self.instance_id,
            "region": self.region,
            "timestamp": time.time(),
            "data": dict(self.data_store),
        }

    def restore(self, snapshot):
        """Load state from a snapshot (used after promotion/failover)."""
        self.data_store = dict(snapshot["data"])

    def __repr__(self):
        return f"<CloudInstance {self.instance_id} role={self.role} region={self.region} status={self.status}>"
