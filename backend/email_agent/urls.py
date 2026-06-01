from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/gmail/start/", views.gmail_auth_start, name="gmail-auth-start"),
    path("auth/gmail/callback/", views.gmail_auth_callback, name="gmail-auth-callback"),
    path("auth/gmail/status/", views.gmail_status, name="gmail-status"),
    path("auth/gmail/disconnect/", views.gmail_disconnect, name="gmail-disconnect"),
    path("agent/check/", views.run_email_agent, name="run-email-agent"),
    path("agent/latest/", views.latest_result, name="latest-result"),
    path("agent/history/", views.result_history, name="result-history"),
]
