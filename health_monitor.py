"""
health_monitor.py
------------------
Simulates AWS CloudWatch health checks + alarms. Polls a CloudInstance
at a fixed interval; if it sees N consecutive failed checks, it fires
an alarm callback (used by the FailoverController to trigger DR).
"""

import threading
import time


class HealthMonitor:
    def __init__(self, instance, interval=1.0, failure_threshold=2, logger=None):
        self.instance = instance
        self.interval = interval
        self.failure_threshold = failure_threshold
        self.logger = logger
        self._consecutive_failures = 0
        self._alarm_fired = False
        self._on_alarm = None
        self._stop_event = threading.Event()
        self._thread = None

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    def on_alarm(self, callback):
        """Register the function to call when the health alarm triggers."""
        self._on_alarm = callback

    def _run(self):
        while not self._stop_event.is_set():
            healthy = self.instance.health_check()
            if healthy:
                if self._consecutive_failures > 0:
                    self._log(f"[CloudWatch] {self.instance.instance_id} recovered, resetting failure count")
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                self._log(
                    f"[CloudWatch] Health check FAILED for {self.instance.instance_id} "
                    f"({self._consecutive_failures}/{self.failure_threshold})"
                )
                if self._consecutive_failures >= self.failure_threshold and not self._alarm_fired:
                    self._alarm_fired = True
                    self._log(f"[CloudWatch] ALARM: {self.instance.instance_id} declared UNREACHABLE")
                    if self._on_alarm:
                        self._on_alarm(self.instance)
            time.sleep(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def reset_alarm(self):
        self._alarm_fired = False
        self._consecutive_failures = 0
