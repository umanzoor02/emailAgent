from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EmailCheckResult
from .services import agent as agent_service
from .services import gmail as gmail_service


def _parse_keywords(data) -> list[str]:
    raw = data.get("keywords", "")
    if isinstance(raw, list):
        return [str(k).strip() for k in raw if str(k).strip()]
    if isinstance(raw, str):
        return [k.strip() for k in raw.split(",") if k.strip()]
    return []


def _parse_indeed_only(data) -> bool:
    value = data.get("indeed_only", True)
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


@ensure_csrf_cookie
@api_view(["GET"])
def health(request):
    return Response(
        {
            "status": "ok",
            "gmail_configured": gmail_service.gmail_configured(),
            "gmail_connected": gmail_service.is_gmail_connected(request.session),
            "cursor_agent": bool(settings.CURSOR_API_KEY),
            "email_filter": {
                "source": "indeed",
                "gmail_query": gmail_service.build_indeed_search_query(),
                "search_days": settings.EMAIL_SEARCH_DAYS,
                "search_scope": settings.EMAIL_SEARCH_SCOPE,
                "time_label": (
                    "last 24 hours"
                    if settings.EMAIL_SEARCH_DAYS == 1
                    else f"last {settings.EMAIL_SEARCH_DAYS} days"
                ),
            },
            "job_context": {
                "title": settings.JOB_TITLE,
                "company": settings.JOB_COMPANY,
                "sender_domains": settings.JOB_SENDER_DOMAINS,
            },
        }
    )


@api_view(["GET"])
def gmail_auth_start(request):
    if not gmail_service.gmail_configured():
        return Response(
            {"error": "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend .env"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    flow = gmail_service.create_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    request.session["oauth_code_verifier"] = flow.code_verifier
    request.session.modified = True
    return Response({"auth_url": auth_url})


@api_view(["GET"])
def gmail_auth_callback(request):
    frontend = settings.FRONTEND_URL.rstrip("/")

    if not gmail_service.gmail_configured():
        return HttpResponseRedirect(f"{frontend}/?gmail=error&reason=config")

    state = request.session.get("oauth_state")
    code_verifier = request.session.get("oauth_code_verifier")
    if not state or not code_verifier:
        return HttpResponseRedirect(f"{frontend}/?gmail=error&reason=session")

    flow = gmail_service.create_oauth_flow(
        state=state, code_verifier=code_verifier
    )
    # Must match the redirect URI registered in Google Console (not the proxied Host).
    query = request.META.get("QUERY_STRING", "")
    redirect_base = settings.GOOGLE_REDIRECT_URI.rstrip("/")
    authorization_response = (
        f"{redirect_base}?{query}" if query else redirect_base
    )
    flow.fetch_token(authorization_response=authorization_response)
    gmail_service.save_credentials_to_session(request.session, flow.credentials)
    request.session.pop("oauth_state", None)
    request.session.pop("oauth_code_verifier", None)

    return HttpResponseRedirect(f"{frontend}/?gmail=connected")


@api_view(["GET"])
def gmail_status(request):
    return Response(
        {
            "connected": gmail_service.is_gmail_connected(request.session),
            "configured": gmail_service.gmail_configured(),
        }
    )


@api_view(["POST"])
def gmail_disconnect(request):
    request.session.pop("gmail_token", None)
    request.session.modified = True
    return Response({"connected": False})


@api_view(["POST"])
def run_email_agent(request):
    """Fetch inbox via Gmail API and run the job-email agent."""
    if not gmail_service.is_gmail_connected(request.session):
        return Response(
            {"error": "Connect Gmail first.", "code": "gmail_not_connected"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    keywords = _parse_keywords(request.data)
    indeed_only = _parse_indeed_only(request.data)

    try:
        fetched = gmail_service.fetch_recent_emails(
            request.session,
            keywords=keywords,
            indeed_only=indeed_only,
        )
        emails = fetched["emails"]
        search = fetched["search"]
        analysis = agent_service.analyze_job_emails(emails, user_keywords=keywords)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        result = EmailCheckResult.objects.create(
            gmail_connected=True,
            error=str(exc),
            summary="Email check failed.",
        )
        return Response(
            {
                "error": str(exc),
                "result_id": result.id,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    important = analysis.get("important_emails", [])
    summary = analysis.get("summary", "")
    if len(emails) == 0:
        summary = (
            f"No Indeed emails found ({search['time_label']}, "
            f"scope: {search['scope']}). "
            f"Gmail matched {search['listed_by_gmail']} message(s) before filtering. "
            "Try EMAIL_SEARCH_DAYS=90 or EMAIL_SEARCH_SCOPE=all in backend .env."
        )

    record = EmailCheckResult.objects.create(
        gmail_connected=True,
        total_scanned=len(emails),
        important_count=len(important),
        summary=summary,
        agent_mode=analysis.get("agent_mode", "heuristic"),
        important_emails=important,
    )

    return Response(
        {
            "result_id": record.id,
            "created_at": record.created_at.isoformat(),
            "total_scanned": record.total_scanned,
            "important_count": record.important_count,
            "summary": record.summary,
            "agent_mode": record.agent_mode,
            "matched_emails": emails,
            "important_emails": record.important_emails,
            "search": search,
            "importance_threshold": analysis.get("importance_threshold"),
        }
    )


@api_view(["GET"])
def latest_result(request):
    record = EmailCheckResult.objects.first()
    if not record:
        return Response({"result": None})
    return Response(
        {
            "result": {
                "id": record.id,
                "created_at": record.created_at.isoformat(),
                "total_scanned": record.total_scanned,
                "important_count": record.important_count,
                "summary": record.summary,
                "agent_mode": record.agent_mode,
                "important_emails": record.important_emails,
                "error": record.error,
            }
        }
    )


@api_view(["GET"])
def result_history(request):
    records = EmailCheckResult.objects.all()[:10]
    return Response(
        {
            "history": [
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat(),
                    "important_count": r.important_count,
                    "total_scanned": r.total_scanned,
                    "agent_mode": r.agent_mode,
                    "summary": r.summary[:200],
                }
                for r in records
            ]
        }
    )
