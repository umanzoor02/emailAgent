import base64
import re
from email.utils import parseaddr
from typing import Any

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


def _client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def gmail_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def create_oauth_flow(
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=settings.GMAIL_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        code_verifier=code_verifier,
        autogenerate_code_verifier=code_verifier is None,
    )
    if state:
        flow.oauth2session.state = state
    return flow


def credentials_from_session(session: dict) -> Credentials | None:
    token = session.get("gmail_token")
    if not token:
        return None
    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.GMAIL_SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["gmail_token"] = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at": creds.expiry.isoformat() if creds.expiry else None,
        }
        session.modified = True
    return creds


def save_credentials_to_session(session: dict, creds: Credentials) -> None:
    session["gmail_token"] = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": creds.expiry.isoformat() if creds.expiry else None,
    }
    session.modified = True


def is_gmail_connected(session: dict) -> bool:
    return bool(session.get("gmail_token", {}).get("access_token"))


def _decode_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        raw = base64.urlsafe_b64decode(payload["body"]["data"])
        return raw.decode("utf-8", errors="replace")
    parts = payload.get("parts") or []
    text_parts: list[str] = []
    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain" and part.get("body", {}).get("data"):
            raw = base64.urlsafe_b64decode(part["body"]["data"])
            text_parts.append(raw.decode("utf-8", errors="replace"))
        elif part.get("parts"):
            text_parts.append(_decode_body(part))
    return "\n".join(text_parts)


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _snippet(text: str, max_len: int = 400) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def _quote_gmail_keyword(term: str) -> str:
    term = term.strip()
    if not term:
        return ""
    if " " in term:
        return f'"{term}"'
    return term


def build_email_search_query(
    keywords: list[str] | None = None,
    indeed_only: bool = True,
    days: int | None = None,
) -> str:
    """Build Gmail query (searches subject, body, and headers)."""
    days = settings.EMAIL_SEARCH_DAYS if days is None else days
    clauses: list[str] = []

    if indeed_only:
        base = (settings.EMAIL_GMAIL_QUERY or "from:indeed OR from:indeedemail").strip()
        clauses.append(f"({base})" if " OR " in base and not base.startswith("(") else base)

    if keywords:
        kw_parts = " OR ".join(
            q for k in keywords if (q := _quote_gmail_keyword(k))
        )
        if kw_parts:
            clauses.append(f"({kw_parts})")

    if not clauses:
        clauses.append("indeed")

    query = " ".join(clauses)
    if days > 0:
        query = f"{query} newer_than:{days}d"
    return f"{query} -in:spam -in:trash"


def build_indeed_search_query(days: int | None = None) -> str:
    return build_email_search_query(keywords=None, indeed_only=True, days=days)


def email_text_blob(email: dict) -> str:
    return " ".join(
        [
            email.get("subject", ""),
            email.get("snippet", ""),
            email.get("body_preview", ""),
            email.get("from", ""),
        ]
    ).lower()


def find_matched_keywords(email: dict, keywords: list[str]) -> list[str]:
    text = email_text_blob(email)
    return [kw for kw in keywords if kw.lower() in text]


def filter_emails_by_keywords(emails: list[dict], keywords: list[str]) -> list[dict]:
    """Keep emails where any keyword appears in subject, snippet, or body preview."""
    if not keywords:
        return emails
    filtered: list[dict] = []
    for email in emails:
        matched = find_matched_keywords(email, keywords)
        if matched:
            email = {**email, "matched_keywords": matched}
            filtered.append(email)
    return filtered


def is_indeed_email(email: dict) -> bool:
    from_email = email.get("from_email", "").lower()
    from_raw = email.get("from", "").lower()
    combined = f"{from_email} {from_raw}"
    return any(hint in combined for hint in settings.INDEED_SENDER_HINTS)


def _list_message_refs(service, query: str, limit: int) -> tuple[list[dict], str]:
    """Page through Gmail list API until we have up to `limit` message refs."""
    refs: list[dict] = []
    page_token: str | None = None
    used_query = query

    while len(refs) < limit:
        list_kwargs: dict[str, Any] = {
            "userId": "me",
            "q": used_query,
            "maxResults": min(100, limit - len(refs)),
        }
        if settings.EMAIL_SEARCH_SCOPE == "inbox":
            list_kwargs["labelIds"] = ["INBOX"]

        if page_token:
            list_kwargs["pageToken"] = page_token

        list_resp = service.users().messages().list(**list_kwargs).execute()
        refs.extend(list_resp.get("messages") or [])
        page_token = list_resp.get("nextPageToken")
        if not page_token:
            break

    return refs[:limit], used_query


def fetch_recent_emails(
    session: dict,
    max_results: int | None = None,
    keywords: list[str] | None = None,
    indeed_only: bool = True,
) -> dict[str, Any]:
    """
    Fetch emails via Gmail search.

    Returns {"emails": [...], "search": {...}} with search metadata for the UI.
    """
    creds = credentials_from_session(session)
    if not creds:
        raise ValueError("Gmail is not connected. Complete OAuth first.")

    keywords = keywords or []
    limit = max_results or settings.EMAIL_FETCH_MAX
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    days = settings.EMAIL_SEARCH_DAYS

    primary_query = build_email_search_query(
        keywords=keywords or None, indeed_only=indeed_only, days=days
    )
    message_refs, used_query = _list_message_refs(service, primary_query, limit)

    if not message_refs and indeed_only and not keywords and days > 0:
        fallback_query = f"indeed newer_than:{days}d -in:spam -in:trash"
        message_refs, used_query = _list_message_refs(service, fallback_query, limit)

    if not message_refs and keywords:
        fallback_query = build_email_search_query(
            keywords=keywords, indeed_only=False, days=days
        )
        message_refs, used_query = _list_message_refs(service, fallback_query, limit)

    listed_count = len(message_refs)
    results: list[dict] = []
    skipped_sender = 0

    for item in message_refs:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        subject = _header(headers, "Subject")
        from_raw = _header(headers, "From")
        date = _header(headers, "Date")
        _, from_email = parseaddr(from_raw)
        body = _decode_body(msg.get("payload", {}))
        email = {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "subject": subject,
            "from": from_raw,
            "from_email": from_email.lower(),
            "date": date,
            "snippet": msg.get("snippet", ""),
            "body_preview": _snippet(body or msg.get("snippet", "")),
            "labels": msg.get("labelIds", []),
        }

        if settings.EMAIL_STRICT_SENDER_FILTER and not is_indeed_email(email):
            skipped_sender += 1
            continue
        results.append(email)

    time_label = (
        f"last {days} day (24 hours)"
        if days == 1
        else f"last {days} days"
        if days > 0
        else "all time (no day limit)"
    )

    if keywords:
        results = filter_emails_by_keywords(results, keywords)

    return {
        "emails": results,
        "search": {
            "gmail_query": used_query,
            "days": days,
            "time_label": time_label,
            "scope": settings.EMAIL_SEARCH_SCOPE,
            "max_fetched": limit,
            "listed_by_gmail": listed_count,
            "returned_after_filter": len(results),
            "skipped_sender_filter": skipped_sender,
            "strict_sender_filter": settings.EMAIL_STRICT_SENDER_FILTER,
            "user_keywords": keywords,
            "indeed_only": indeed_only,
        },
    }

