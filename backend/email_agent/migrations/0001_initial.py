from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailCheckResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("gmail_connected", models.BooleanField(default=False)),
                ("total_scanned", models.PositiveIntegerField(default=0)),
                ("important_count", models.PositiveIntegerField(default=0)),
                ("summary", models.TextField(blank=True)),
                ("agent_mode", models.CharField(default="heuristic", max_length=32)),
                ("important_emails", models.JSONField(default=list)),
                ("error", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
