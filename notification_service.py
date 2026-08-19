"""
notification_service.py
-------------------------
Simulates AWS SNS — sends alert notifications (email/SMS/Slack in a real
deployment) whenever a significant DR event occurs.
"""

import time


class NotificationService:
    def __init__(self, logger=None):
        self.logger = logger
        self.sent_notifications = []

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    def send(self, subject, message):
        record = {
            "timestamp": time.time(),
            "subject": subject,
            "message": message,
        }
        self.sent_notifications.append(record)
        self._log(f"[SNS] ALERT SENT -> Subject: '{subject}' | {message}")
