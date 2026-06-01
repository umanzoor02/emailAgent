from django.db import models


class EmailCheckResult(models.Model):
    """Persisted output from the job-email agent for the React dashboard."""

    created_at = models.DateTimeField(auto_now_add=True)
    gmail_connected = models.BooleanField(default=False)
    total_scanned = models.PositiveIntegerField(default=0)
    important_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True)
    agent_mode = models.CharField(max_length=32, default="heuristic")
    important_emails = models.JSONField(default=list)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Check {self.created_at:%Y-%m-%d %H:%M} ({self.important_count} important)"
