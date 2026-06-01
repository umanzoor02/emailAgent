import { useCallback, useEffect, useState } from "react";
import {
  disconnectGmail,
  ensureCsrf,
  fetchGmailStatus,
  fetchHealth,
  fetchHistory,
  fetchLatestResult,
  runEmailAgent,
  startGmailAuth,
} from "./api.js";

function EmailCard({ email, showPriority = true }) {
  return (
    <li className="email-item">
      <header>
        <h3>{email.subject || "(no subject)"}</h3>
        {showPriority && (
          <span className={`priority ${email.priority || "medium"}`}>
            {email.priority || "medium"}
          </span>
        )}
      </header>
      <div className="meta">
        {email.from} · {email.date}
        {email.importance_score != null && (
          <span className="score"> · score {email.importance_score}</span>
        )}
      </div>
      {email.matched_keywords?.length > 0 && (
        <p className="keyword-tags">
          Keywords: {email.matched_keywords.join(", ")}
        </p>
      )}
      {email.importance_reason && (
        <p className="reason">{email.importance_reason}</p>
      )}
      {email.recommended_action && (
        <p className="action-hint">{email.recommended_action}</p>
      )}
      {email.body_preview && (
        <p className="meta" style={{ marginTop: "0.5rem" }}>
          {email.body_preview}
        </p>
      )}
    </li>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [gmail, setGmail] = useState({ connected: false, configured: false });
  const [result, setResult] = useState(null);
  const [matchedEmails, setMatchedEmails] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);
  const [lastSearch, setLastSearch] = useState(null);
  const [keywords, setKeywords] = useState("");
  const [indeedOnly, setIndeedOnly] = useState(true);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [h, g, latest, hist] = await Promise.all([
        fetchHealth(),
        fetchGmailStatus(),
        fetchLatestResult(),
        fetchHistory(),
      ]);
      setHealth(h);
      setGmail(g);
      setResult(latest.result);
      setMatchedEmails([]);
      setHistory(hist.history || []);
      if (h?.email_filter) {
        setLastSearch(h.email_filter);
      }
    } catch (e) {
      setError(e.message || "Could not reach the API. Is Django running on port 8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gmailParam = params.get("gmail");
    const reason = params.get("reason");

    ensureCsrf().then(async () => {
      await refresh();
      if (gmailParam === "connected") {
        window.history.replaceState({}, "", window.location.pathname);
      } else if (gmailParam === "error") {
        const messages = {
          session:
            "OAuth session was lost. Click Connect Gmail again (do not open multiple tabs).",
          config: "Google OAuth is not configured in backend .env.",
        };
        setError(messages[reason] || `Gmail connection failed (${reason || "unknown"}).`);
        window.history.replaceState({}, "", window.location.pathname);
      }
    });
  }, [refresh]);

  async function handleConnect() {
    setError(null);
    try {
      await startGmailAuth();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDisconnect() {
    setError(null);
    try {
      await disconnectGmail();
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleCheck() {
    setChecking(true);
    setError(null);
    try {
      const data = await runEmailAgent({ keywords: keywords.trim(), indeedOnly });
      setLastSearch(data.search || null);
      setMatchedEmails(data.matched_emails || []);
      setResult({
        id: data.result_id,
        created_at: data.created_at,
        total_scanned: data.total_scanned,
        important_count: data.important_count,
        summary: data.summary,
        agent_mode: data.agent_mode,
        important_emails: data.important_emails,
        importance_threshold: data.importance_threshold,
      });
      const hist = await fetchHistory();
      setHistory(hist.history || []);
    } catch (e) {
      setError(e.data?.error || e.message);
    } finally {
      setChecking(false);
    }
  }

  const importantEmails = result?.important_emails || [];

  return (
    <>
      <h1>Indeed Email Agent</h1>
      <p className="subtitle">
        Search Gmail by keywords in subject or body. Optionally limit to Indeed
        senders, then highlight what needs your attention.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <section className="card">
        <h2>Search</h2>
        <label className="field-label" htmlFor="keywords">
          Keywords (comma-separated)
        </label>
        <input
          id="keywords"
          className="text-input"
          type="text"
          placeholder="interview, offer, application, urgent"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          disabled={!gmail.connected || checking}
        />
        <p className="field-hint">
          Gmail searches subject, body, and snippet. Example:{" "}
          <code>interview, rejected, assessment</code>
        </p>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={indeedOnly}
            onChange={(e) => setIndeedOnly(e.target.checked)}
            disabled={!gmail.connected || checking}
          />
          Only emails from Indeed
        </label>
        <details className="how-it-works">
          <summary>How is &quot;important&quot; decided?</summary>
          <p>
            Without your keywords, the app scores each email (0–1) using rules
            like <em>interview</em>, <em>offer</em>, <em>deadline</em> from{" "}
            <code>JOB_KEYWORDS</code> in <code>.env</code>. Generic Indeed job
            digests often score below the threshold (0.35), so you see 0
            important.
          </p>
          <p>
            When you enter keywords above, matching emails are searched in Gmail
            and marked important automatically (+0.4 score per keyword).
          </p>
        </details>
      </section>

      <section className="card">
        <h2>Status</h2>
        {loading ? (
          <p className="empty">Loading…</p>
        ) : (
          <div className="status-row">
            <span className={`badge ${gmail.connected ? "ok" : "off"}`}>
              Gmail {gmail.connected ? "connected" : "not connected"}
            </span>
            {(lastSearch || health?.email_filter) && (
              <span className="badge ok">
                {(lastSearch || health.email_filter).time_label || "Indeed"} ·{" "}
                {(lastSearch || health.email_filter).search_scope || "all"} mail
              </span>
            )}
            {health && (
              <span className={`badge ${health.cursor_agent ? "ok" : "off"}`}>
                Agent: {health.cursor_agent ? "Cursor AI" : "heuristic"}
              </span>
            )}
          </div>
        )}
        <div className="actions">
          {!gmail.connected ? (
            <button
              type="button"
              className="btn-primary"
              onClick={handleConnect}
              disabled={!gmail.configured || loading}
            >
              Connect Gmail
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn-primary"
                onClick={handleCheck}
                disabled={checking || loading}
              >
                {checking && <span className="spinner" />}
                {checking ? "Searching…" : "Search emails"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDisconnect}
                disabled={loading}
              >
                Disconnect
              </button>
            </>
          )}
        </div>
      </section>

      {result && (
        <section className="card">
          <h2>Summary</h2>
          <p className="summary">{result.summary}</p>
          <p className="meta" style={{ marginTop: "0.75rem" }}>
            {matchedEmails.length} matched search · {result.important_count}{" "}
            important · {result.agent_mode}
            {result.importance_threshold != null &&
              ` · threshold ${result.importance_threshold}`}
            {lastSearch?.time_label && ` · ${lastSearch.time_label}`}
          </p>
          {lastSearch && (
            <p className="meta" style={{ marginTop: "0.35rem", fontSize: "0.8rem" }}>
              Gmail: {lastSearch.gmail_query}
              {lastSearch.user_keywords?.length > 0 &&
                ` · keywords: ${lastSearch.user_keywords.join(", ")}`}
            </p>
          )}
        </section>
      )}

      {matchedEmails.length > 0 && (
        <section className="card">
          <h2>Search results ({matchedEmails.length})</h2>
          <ul className="email-list">
            {matchedEmails.map((email) => (
              <EmailCard key={email.id} email={email} showPriority={false} />
            ))}
          </ul>
        </section>
      )}

      <section className="card">
        <h2>Important emails ({importantEmails.length})</h2>
        {importantEmails.length === 0 ? (
          <p className="empty">
            {result
              ? "None crossed the importance threshold. Try adding keywords above."
              : "Run a search after connecting Gmail."}
          </p>
        ) : (
          <ul className="email-list">
            {importantEmails.map((email) => (
              <EmailCard key={email.id} email={email} />
            ))}
          </ul>
        )}
      </section>

      {history.length > 0 && (
        <section className="card">
          <h2>Recent checks</h2>
          {history.map((h) => (
            <div key={h.id} className="history-item">
              {new Date(h.created_at).toLocaleString()} — {h.important_count}/
              {h.total_scanned} important ({h.agent_mode})
            </div>
          ))}
        </section>
      )}
    </>
  );
}
