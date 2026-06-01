from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("email_agent.urls")),
]

if settings.SERVE_SPA:
    urlpatterns += [
        re_path(
            r"^(?!api/|admin/|assets/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="spa",
        ),
    ]
