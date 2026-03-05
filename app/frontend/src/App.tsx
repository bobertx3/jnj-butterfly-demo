import { useCallback, useEffect, useState } from "react";
import type {
  Contact,
  GenieAskResponse,
  GenieStatus,
  LlmStatus,
  NbaRecommendation,
  Stats,
  TabId,
} from "./types";

const API = "/api";

interface GenieTurn {
  question: string;
  response: GenieAskResponse;
}

const FILTER_LABELS: Record<string, string> = {
  all: "All",
  high_priority: "High priority",
  at_risk: "At risk",
  intent_spike: "Intent spike",
  needs_outreach: "Needs outreach",
};

function App() {
  const [activeTab, setActiveTab] = useState<TabId>("nba");
  const [stats, setStats] = useState<Stats | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [nba, setNba] = useState<NbaRecommendation | null>(null);
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [nbaLoading, setNbaLoading] = useState(false);
  const [generateSuccess, setGenerateSuccess] = useState(false);

  // Genie (Sales data Q&A) tab state
  const [genieStatus, setGenieStatus] = useState<GenieStatus | null>(null);
  const [genieConversationId, setGenieConversationId] = useState<string | null>(null);
  const [genieTurns, setGenieTurns] = useState<GenieTurn[]>([]);
  const [genieInput, setGenieInput] = useState("");
  const [genieLoading, setGenieLoading] = useState(false);
  const [genieDebug, setGenieDebug] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const r = await fetch(`${API}/contacts/stats`);
      if (r.ok) setStats(await r.json());
    } catch (_) {}
  }, []);

  const loadLlmStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/contacts/llm-status`);
      if (r.ok) setLlmStatus(await r.json());
    } catch (_) {}
  }, []);

  const loadGenieStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/genie/status`);
      const data = await r.json().catch(() => ({}));
      if (r.ok && data && typeof data.configured === "boolean") {
        setGenieStatus({
          configured: data.configured,
          space_id: data.space_id ?? null,
          message: data.message,
        });
      } else {
        const msg = data?.detail ?? data?.message ?? "Could not load Genie status.";
        setGenieStatus({ configured: false, space_id: null, message: msg });
      }
    } catch (_) {
      setGenieStatus({ configured: false, space_id: null, message: "Could not load Genie status." });
    }
  }, []);

  const loadContacts = useCallback(async () => {
    setLoading(true);
    try {
      const q = filter === "all" ? "" : `?filter=${filter}`;
      const r = await fetch(`${API}/contacts${q}`);
      if (r.ok) setContacts(await r.json());
    } catch (_) {}
    setLoading(false);
  }, [filter]);

  const loadNba = useCallback(async (contactId: string) => {
    setNbaLoading(true);
    setGenerateSuccess(false);
    try {
      const r = await fetch(`${API}/contacts/${contactId}/nba`);
      if (r.ok) setNba(await r.json());
    } catch (_) {
      setNba(null);
    }
    setNbaLoading(false);
  }, []);

  useEffect(() => {
    loadStats();
    loadLlmStatus();
    loadGenieStatus();
  }, [loadStats, loadLlmStatus, loadGenieStatus]);
  useEffect(() => {
    loadContacts();
  }, [loadContacts]);
  useEffect(() => {
    if (selected) loadNba(selected.contact_id);
    else setNba(null);
  }, [selected?.contact_id, loadNba]);

  const handleGenerateNba = async () => {
    if (!selected) return;
    setNbaLoading(true);
    setGenerateSuccess(false);
    try {
      const r = await fetch(`${API}/contacts/${selected.contact_id}/nba/generate`, { method: "POST" });
      if (r.ok) {
        setNba(await r.json());
        setGenerateSuccess(true);
      }
    } catch (_) {}
    setNbaLoading(false);
  };

  const handleGenieAsk = async () => {
    const q = genieInput.trim();
    if (!q || genieLoading) return;
    setGenieLoading(true);
    setGenieInput("");
    try {
      const r = await fetch(`${API}/genie/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          conversation_id: genieConversationId ? String(genieConversationId) : undefined,
          debug: genieDebug,
        }),
      });
      const data: GenieAskResponse & { detail?: string } = await r.json().catch(() => ({}));
      const errorMsg = data?.detail ?? data?.error ?? r.statusText ?? "Request failed";
      const convId = data?.conversation_id != null ? String(data.conversation_id) : null;
      const response: GenieAskResponse = {
        conversation_id: convId,
        message_id: data?.message_id ?? null,
        status: typeof data?.status === "string" ? data.status : "COMPLETED",
        text_response: typeof data?.text_response === "string" ? data.text_response : "",
        sql: typeof data?.sql === "string" ? data.sql : null,
        columns: Array.isArray(data?.columns) ? data.columns : null,
        data: Array.isArray(data?.data) ? data.data : null,
        row_count: typeof data?.row_count === "number" ? data.row_count : null,
        error: typeof data?.error === "string" ? data.error : typeof data?.detail === "string" ? data.detail : undefined,
        _raw_message: data?._raw_message,
      };
      if (convId ?? response.conversation_id) {
        setGenieConversationId(convId ?? response.conversation_id ?? null);
      }
      if (!r.ok) {
        setGenieTurns((prev) => [
          ...prev,
          { question: q, response: { ...response, status: "FAILED", text_response: "", error: errorMsg } },
        ]);
      } else {
        setGenieTurns((prev) => [...prev, { question: q, response }]);
      }
    } catch (e) {
      setGenieTurns((prev) => [
        ...prev,
        {
          question: q,
          response: {
            status: "FAILED",
            text_response: "",
            error: e instanceof Error ? e.message : "Request failed",
          },
        },
      ]);
    }
    setGenieLoading(false);
  };

  const riskBadge = (risk: string) => {
    const c =
      risk === "High"
        ? "bg-red-100 text-red-800"
        : risk === "Medium"
          ? "bg-amber-100 text-amber-800"
          : "bg-emerald-100 text-emerald-800";
    return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${c}`}>{risk}</span>;
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#D71500]" />
              <div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900">Next Best Action</h1>
                <p className="text-sm text-slate-500">
                  Johnson & Johnson MedTech — Surgical, vision & heart recovery
                </p>
              </div>
            </div>
            <div className="flex gap-10">
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-900">{stats?.assigned_contacts ?? "—"}</p>
                <p className="text-xs font-medium text-slate-500">Assigned contacts</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-900">{stats?.growth_opportunities ?? "—"}</p>
                <p className="text-xs font-medium text-slate-500">Growth opportunities</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-900">{stats?.at_risk_accounts ?? "—"}</p>
                <p className="text-xs font-medium text-slate-500">At-risk accounts</p>
                {stats?.at_risk_avg_priority != null && (
                  <p className="text-xs text-slate-400">Avg priority {stats.at_risk_avg_priority}</p>
                )}
              </div>
            </div>
            <nav className="mt-4 flex gap-1 border-t border-slate-100 pt-4">
              <button
                type="button"
                onClick={() => setActiveTab("nba")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  activeTab === "nba"
                    ? "bg-[#D71500] text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                Next Best Action
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("genie")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  activeTab === "genie"
                    ? "bg-[#D71500] text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                Sales data Q&A
              </button>
            </nav>
          </div>
        </div>
      </header>

      {activeTab === "genie" ? (
        <div className="mx-auto max-w-4xl p-6">
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-4">
              <h2 className="font-semibold text-slate-900">Ask about your sales data</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Natural language questions over Butterfly analytics (accounts, transactions, pipeline, regions).
              </p>
              {!genieStatus?.configured && (
                <p className="mt-2 text-xs text-amber-700">
                  {genieStatus?.message
                    ? genieStatus.message
                    : "When running on Databricks, host and auth are usually set automatically. If needed, set GENIE_SPACE_ID in the app Environment."}
                </p>
              )}
            </div>
            <div className="flex max-h-[calc(100vh-320px)] flex-col">
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {genieTurns.length === 0 && !genieLoading && (
                  <p className="text-center text-sm text-slate-500 py-8">
                    Type a question below, e.g. &quot;What is total net sales by region?&quot; or &quot;Top 10 accounts by lifetime net sales&quot;
                  </p>
                )}
                {(Array.isArray(genieTurns) ? genieTurns : []).map((turn, i) => {
                  if (!turn || typeof turn !== "object" || !turn.response) return null;
                  const res = turn.response as GenieAskResponse;
                  return (
                  <div key={i} className="space-y-2">
                    <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800">
                      <span className="font-medium text-slate-500">You: </span>
                      {typeof turn.question === "string" ? turn.question : ""}
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm">
                      {res.error != null && res.error !== "" && (
                        <p className="text-red-600">{String(res.error)}</p>
                      )}
                      {res.text_response != null && res.text_response !== "" && (
                        <p className="text-slate-700 whitespace-pre-wrap">{String(res.text_response)}</p>
                      )}
                      {res.sql != null && res.sql !== "" && (
                        <pre className="mt-3 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                          {String(res.sql)}
                        </pre>
                      )}
                      {Array.isArray(res.columns) &&
                        Array.isArray(res.data) &&
                        res.columns.length > 0 &&
                        res.data.length > 0 && (
                        <div className="mt-3 overflow-x-auto">
                          <table className="min-w-full text-left text-sm">
                            <thead>
                              <tr className="border-b border-slate-200">
                                {res.columns.map((col, j) => (
                                  <th key={j} className="py-2 pr-4 font-medium text-slate-600">
                                    {typeof col === "string" ? col : `col_${j}`}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {res.data.slice(0, 100).map((row, ri) => (
                                <tr key={ri} className="border-b border-slate-100">
                                  {res.columns!.map((col, ci) => {
                                    const colName = typeof col === "string" ? col : `col_${ci}`;
                                    let val: unknown = null;
                                    if (Array.isArray(row)) {
                                      val = row[ci];
                                    } else if (typeof row === "object" && row !== null && colName in (row as object)) {
                                      val = (row as Record<string, unknown>)[colName];
                                    }
                                    return (
                                      <td key={ci} className="py-2 pr-4 text-slate-800">
                                        {val != null && val !== undefined ? String(val) : ""}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {typeof res.row_count === "number" && res.row_count > 100 && (
                            <p className="mt-1 text-xs text-slate-500">Showing first 100 of {res.row_count} rows.</p>
                          )}
                        </div>
                      )}
                      {res._raw_message != null && (
                        <details className="mt-3">
                          <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700">Raw Genie payload (debug)</summary>
                          <pre className="mt-1 max-h-60 overflow-auto rounded bg-slate-100 p-2 text-xs text-slate-600">
                            {JSON.stringify(res._raw_message, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                  );
                })}
                {genieLoading && (
                  <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#D71500] border-t-transparent" />
                    Asking Genie…
                  </div>
                )}
              </div>
              <div className="border-t border-slate-200 p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleGenieAsk();
                  }}
                  className="flex flex-col gap-2"
                >
                  <div className="flex gap-2">
                  <input
                    type="text"
                    value={genieInput}
                    onChange={(e) => setGenieInput(e.target.value)}
                    placeholder="Ask a question about sales, pipeline, regions…"
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm placeholder:text-slate-400 focus:border-[#D71500] focus:outline-none focus:ring-1 focus:ring-[#D71500]"
                    disabled={!genieStatus?.configured || genieLoading}
                  />
                  <button
                    type="submit"
                    disabled={!genieStatus?.configured || genieLoading || !genieInput.trim()}
                    className="rounded-lg bg-[#D71500] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#c01200] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Ask
                  </button>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-500">
                    <input
                      type="checkbox"
                      checked={genieDebug}
                      onChange={(e) => setGenieDebug(e.target.checked)}
                      className="rounded border-slate-300"
                    />
                    Include raw response (debug) — show Genie API payload below. Or use Chrome DevTools → Network → select the &quot;ask&quot; request → Preview/Response.
                  </label>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : (
      <div className="mx-auto flex max-w-7xl gap-6 p-6">
        {/* Left: Contact queue */}
        <aside className="w-80 shrink-0">
          <div className="sticky top-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-3">
              <h2 className="font-semibold text-slate-900">Contact queue</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Ranked by priority, intent & recency
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {Object.entries(FILTER_LABELS).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFilter(key)}
                    className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
                      filter === key
                        ? "bg-[#D71500] text-white shadow-sm"
                        : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-[calc(100vh-280px)] overflow-y-auto p-2">
              {loading ? (
                <div className="flex justify-center py-12">
                  <div className="h-7 w-7 animate-spin rounded-full border-2 border-[#D71500] border-t-transparent" />
                </div>
              ) : (
                contacts.map((c, idx) => (
                  <button
                    key={c.contact_id}
                    type="button"
                    onClick={() => setSelected(c)}
                    className={`mb-2 w-full rounded-lg border p-3 text-left transition ${
                      selected?.contact_id === c.contact_id
                        ? "border-[#D71500] bg-red-50/50 ring-1 ring-[#D71500]/30"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-slate-400">#{idx + 1}</span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                        {Math.round(c.priority_score)}
                      </span>
                    </div>
                    <p className="mt-1 font-semibold text-slate-900">{c.name}</p>
                    <p className="text-xs text-slate-600">{c.role_specialty ?? "—"}</p>
                    <p className="text-xs text-slate-500">{c.institution ?? "—"}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {riskBadge(c.risk_level)}
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                        {c.preferred_channel}
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs text-slate-400">Last touch: {c.last_touch_days} days</p>
                  </button>
                ))
              )}
            </div>
          </div>
        </aside>

        {/* Right: Detail + NBA */}
        <main className="min-w-0 flex-1 space-y-6">
          {!selected ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-20 text-center">
              <p className="text-slate-500">Select a contact from the queue to view details and generate a recommendation.</p>
            </div>
          ) : (
            <>
              {/* Contact detail */}
              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">{selected.name}</h2>
                    <p className="text-sm text-slate-600">{selected.role_specialty ?? "—"}</p>
                    <p className="text-sm text-slate-500">{selected.institution ?? "—"}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {riskBadge(selected.risk_level)}
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                        {selected.preferred_channel}
                      </span>
                    </div>
                    <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
                      <div><dt className="text-slate-500">Institution</dt><dd className="font-medium text-slate-900">{selected.institution ?? "—"}</dd></div>
                      <div><dt className="text-slate-500">Last touch</dt><dd className="font-medium text-slate-900">{selected.last_touch_days} days ago</dd></div>
                      <div><dt className="text-slate-500">Intent score</dt><dd className="font-medium text-slate-900">{selected.intent_score}</dd></div>
                      <div><dt className="text-slate-500">3M RX growth</dt><dd className="font-medium text-slate-900">{selected.rx_growth_3m_pct != null ? `${selected.rx_growth_3m_pct}%` : "—"}</dd></div>
                    </dl>
                  </div>
                  <div className="rounded-xl bg-slate-50 px-4 py-3 text-center">
                    <p className="text-3xl font-bold text-[#D71500]">{Math.round(selected.priority_score)}</p>
                    <p className="text-xs font-medium text-slate-500">Priority</p>
                  </div>
                </div>
              </section>

              {/* Signals snapshot */}
              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="font-semibold text-slate-900">Signals snapshot</h3>
                <p className="mt-0.5 text-xs text-slate-500">TRX/NRX, engagement and channel from your territory data.</p>
                <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-3">
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">3M TRX volume</dt><dd className="font-medium">{selected.trx_volume_3m ?? "—"}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">3M NRX volume</dt><dd className="font-medium">{selected.nrx_volume_3m ?? "—"}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Site visits</dt><dd className="font-medium">{selected.site_visits ?? "—"}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Webinar signups</dt><dd className="font-medium">{selected.webinar_signups ?? "—"}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Preferred channel</dt><dd className="font-medium">{selected.preferred_channel}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Days since last touch</dt><dd className="font-medium">{selected.last_touch_days}</dd></div>
                </dl>
              </section>

              {/* Next best action + email */}
              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-semibold text-slate-900">Next best action & email draft</h3>
                  <div className="flex items-center gap-2">
                    {llmStatus?.llm_configured ? (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800">
                        Databricks LLM
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800" title="Set DATABRICKS_HOST and DATABRICKS_TOKEN in app environment for AI generation">
                        Template mode
                      </span>
                    )}
                  </div>
                </div>

                {nbaLoading ? (
                  <div className="mt-6 flex flex-col items-center justify-center py-12">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#D71500] border-t-transparent" />
                    <p className="mt-3 text-sm text-slate-500">Generating recommendation and email…</p>
                  </div>
                ) : (
                  <>
                    <div className="mt-4 rounded-lg bg-slate-50 p-4">
                      <p className="text-sm leading-relaxed text-slate-700">
                        {nba?.recommendation_text ?? "No recommendation yet. Click the button below to generate a next best action and email draft for this contact."}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={handleGenerateNba}
                      className="mt-4 flex items-center gap-2 rounded-lg bg-[#D71500] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#c01200] focus:outline-none focus:ring-2 focus:ring-[#D71500] focus:ring-offset-2"
                    >
                      Generate recommendation & email
                    </button>
                    {generateSuccess && (
                      <p className="mt-2 text-xs font-medium text-emerald-600">Generated successfully. Content saved below.</p>
                    )}

                    {nba?.email_draft_subject && (
                      <div className="mt-6 border-t border-slate-200 pt-5">
                        <h4 className="text-sm font-semibold text-slate-900">Email draft</h4>
                        <p className="mt-1 text-xs text-slate-500">Subject and body — copy and use in your outreach.</p>
                        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
                          <p className="text-sm font-medium text-slate-900">{nba.email_draft_subject}</p>
                          <div className="mt-2 max-h-32 overflow-y-auto text-sm text-slate-600 whitespace-pre-wrap">
                            {nba.email_draft_body ?? ""}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </section>
            </>
          )}
        </main>
      </div>
      )}
    </div>
  );
}

export default App;
