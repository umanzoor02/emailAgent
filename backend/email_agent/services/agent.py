import json
import re
from typing import Any

from django.conf import settings

from .gmail import find_matched_keywords


def _build_job_context(user_keywords: list[str] | None = None) -> str:
    parts = []
    if settings.JOB_TITLE:
        parts.append(f"Job title: {settings.JOB_TITLE}")
    if settings.JOB_COMPANY:
        parts.append(f"Company: {settings.JOB_COMPANY}")
    if settings.JOB_SENDER_DOMAINS:
        parts.append(f"Work domains: {', '.join(settings.JOB_SENDER_DOMAINS)}")
    if user_keywords:
        parts.append(f"User search keywords: {', '.join(user_keywords)}")
    elif settings.JOB_KEYWORDS:
        parts.append(f"Default keywords: {', '.join(settings.JOB_KEYWORDS)}")
    return "\n".join(parts) if parts else "General professional/work email context."


def _heuristic_score(
    email: dict, user_keywords: list[str] | None = None
) -> tuple[float, str, list[str]]:
    """Score 0–1, reason, and keywords matched in subject/body."""
    user_keywords = user_keywords or []
    text = " ".join(
        [
            email.get("subject", ""),
            email.get("from", ""),
            email.get("snippet", ""),
            email.get("body_preview", ""),
        ]
    ).lower()

    score = 0.0
    reasons: list[str] = []
    matched_user = find_matched_keywords(email, user_keywords)
    for kw in matched_user:
        score += 0.4
        reasons.append(f"your keyword '{kw}'")

    urgent_patterns = [
        r"\burgent\b",
        r"\basap\b",
        r"\baction required\b",
        r"\bdeadline\b",
        r"\bdue\b",
        r"\btoday\b",
        r"\btomorrow\b",
        r"\binterview\b",
        r"\boffer\b",
        r"\bmeeting\b",
        r"\breschedule\b",
        r"\bapproval\b",
        r"\bescalat",
    ]
    for pat in urgent_patterns:
        if re.search(pat, text):
            score += 0.12
            label = pat.replace("\\b", "").strip()
            reasons.append(f"matched '{label}'")

    keyword_source = user_keywords if user_keywords else settings.JOB_KEYWORDS
    for kw in keyword_source:
        if kw.lower() in text and kw not in matched_user:
            score += 0.08
            reasons.append(f"keyword '{kw}'")

    from_email = email.get("from_email", "")
    for domain in settings.JOB_SENDER_DOMAINS:
        if domain.lower() in from_email:
            score += 0.25
            reasons.append(f"sender domain '{domain}'")
            break

    if settings.JOB_COMPANY and settings.JOB_COMPANY.lower() in text:
        score += 0.15
        reasons.append("mentions company")

    if "UNREAD" in email.get("labels", []):
        score += 0.05
        reasons.append("unread")

    score = min(score, 1.0)
    reason = "; ".join(reasons[:5]) if reasons else "no strong signals (generic digest)"
    return score, reason, matched_user


def _analyze_with_heuristics(
    emails: list[dict], user_keywords: list[str] | None = None
) -> dict[str, Any]:
    user_keywords = user_keywords or []
    important: list[dict] = []
    threshold = 0.25 if user_keywords else 0.35

    for email in emails:
        score, reason, matched_user = _heuristic_score(email, user_keywords)
        if matched_user:
            score = max(score, 0.55)
        if score >= threshold or matched_user:
            important.append(
                {
                    **email,
                    "importance_score": round(score, 2),
                    "importance_reason": reason,
                    "matched_keywords": matched_user
                    or email.get("matched_keywords", []),
                    "priority": "high" if score >= 0.6 else "medium",
                }
            )

    important.sort(key=lambda e: e["importance_score"], reverse=True)
    if user_keywords:
        summary = (
            f"Found {len(emails)} email(s) matching your keywords "
            f"({', '.join(user_keywords)}). "
            f"{len(important)} marked important (keyword match or high score ≥ {threshold})."
        )
    else:
        summary = (
            f"Scanned {len(emails)} Indeed email(s). "
            f"Found {len(important)} important (score ≥ {threshold}). "
            "Tip: add keywords in the app to search subject/body and flag matches."
        )
    return {
        "important_emails": important,
        "summary": summary,
        "agent_mode": "heuristic",
        "importance_threshold": threshold,
    }


def _parse_agent_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _analyze_with_cursor(
    emails: list[dict], user_keywords: list[str] | None = None
) -> dict[str, Any]:
    from cursor_sdk import Agent, AgentOptions, CursorAgentError

    user_keywords = user_keywords or []
    compact = [
        {
            "id": e["id"],
            "subject": e["subject"],
            "from": e["from"],
            "date": e["date"],
            "snippet": e.get("snippet", "")[:300],
            "matched_keywords": e.get("matched_keywords", []),
        }
        for e in emails
    ]

    job_context = _build_job_context(user_keywords)
    kw_note = ""
    if user_keywords:
        kw_note = (
            f"4. Treat any email containing these user keywords as important: "
            f"{', '.join(user_keywords)}.\n"
        )

    prompt = f"""You are an email triage agent. Messages below were found by Gmail search.

Job context:
{job_context}

Emails (JSON array):
{json.dumps(compact, indent=2)}

Task:
1. Mark emails that need attention (interviews, offers, employer replies, deadlines, assessments).
2. Deprioritize generic job digests unless they match user keywords or mention urgency.
3. {kw_note}
Return ONLY valid JSON (no markdown):
{{
  "summary": "one paragraph",
  "important_emails": [
    {{
      "id": "<gmail message id>",
      "priority": "high|medium",
      "importance_score": 0.0 to 1.0,
      "importance_reason": "short explanation",
      "recommended_action": "what the user should do"
    }}
  ]
}}"""

    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=settings.CURSOR_API_KEY,
                model=settings.CURSOR_MODEL,
            ),
        )
    except CursorAgentError as exc:
        raise RuntimeError(f"Cursor agent failed to start: {exc.message}") from exc

    if result.status == "error":
        raise RuntimeError("Cursor agent run failed while analyzing email.")

    parsed = _parse_agent_json(result.result or "")
    if not parsed:
        raise RuntimeError("Cursor agent returned non-JSON output.")

    id_to_email = {e["id"]: e for e in emails}
    merged: list[dict] = []
    for item in parsed.get("important_emails") or []:
        base = id_to_email.get(item.get("id"))
        if not base:
            continue
        merged.append(
            {
                **base,
                "priority": item.get("priority", "medium"),
                "importance_score": float(item.get("importance_score", 0.5)),
                "importance_reason": item.get("importance_reason", ""),
                "recommended_action": item.get("recommended_action", ""),
                "matched_keywords": base.get("matched_keywords", []),
            }
        )

    if user_keywords:
        seen = {e["id"] for e in merged}
        for email in emails:
            matched = find_matched_keywords(email, user_keywords)
            if matched and email["id"] not in seen:
                merged.append(
                    {
                        **email,
                        "priority": "medium",
                        "importance_score": 0.55,
                        "importance_reason": f"Matches your keywords: {', '.join(matched)}",
                        "matched_keywords": matched,
                    }
                )
                seen.add(email["id"])

    merged.sort(key=lambda e: e.get("importance_score", 0), reverse=True)
    return {
        "important_emails": merged,
        "summary": parsed.get("summary", "Analysis complete."),
        "agent_mode": "cursor",
    }


def analyze_job_emails(
    emails: list[dict], user_keywords: list[str] | None = None
) -> dict[str, Any]:
    """Run the email agent: Cursor SDK when configured, else heuristics."""
    if settings.CURSOR_API_KEY:
        try:
            return _analyze_with_cursor(emails, user_keywords)
        except Exception:
            fallback = _analyze_with_heuristics(emails, user_keywords)
            fallback["summary"] = (
                "Cursor agent unavailable; used heuristic fallback. "
                + fallback["summary"]
            )
            fallback["agent_mode"] = "heuristic_fallback"
            return fallback
    return _analyze_with_heuristics(emails, user_keywords)
