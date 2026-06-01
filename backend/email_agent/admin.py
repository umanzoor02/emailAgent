from django.contrib import admin

from .models import EmailCheckResult


@admin.register(EmailCheckResult)
class EmailCheckResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "important_count",
        "total_scanned",
        "agent_mode",
    )
    readonly_fields = ("created_at",)
