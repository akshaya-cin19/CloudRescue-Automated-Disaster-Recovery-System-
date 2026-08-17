"""
CloudRescue - Automated Disaster Recovery System
==================================================
Entry point for the demo. Run with:

    python main.py

This simulates a two-region AWS-style deployment (primary + secondary
EC2 instances), periodic S3 backups, CloudWatch-style health monitoring,
and an automatic failover controller that promotes the secondary and
reroutes traffic (simulated Route53) the moment the primary is declared
down — with zero manual intervention.

No real AWS account or credentials are required; all cloud services
(EC2, S3, CloudWatch, SNS, Route53) are simulated locally so the project
can be run and evaluated anywhere.
"""

import os
from src.dr_orchestrator import CloudRescueSystem

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logs", "cloudrescue.log")

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    system = CloudRescueSystem(LOG_PATH)
    system.run_demo()
