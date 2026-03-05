import { useCallback, useEffect, useState } from "react";
import type {
  CallLogChatResponse,
  CallLogStatus,
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

interface CallLogTurn {
  question: string;
  response: CallLogChatResponse;
}

const FILTER_LABELS: Record<string, string> = {
  all: "All",
  high_priority: "High priority",
  at_risk: "At risk",
  intent_spike: "Intent spike",
  needs_outreach: "Needs outreach",
};

const GENIE_SAMPLE_QUESTIONS = [
  "Show me accounts and their primary product company and brand.",
  "Which product companies have the highest net sales?",
  "How much open pipeline do we have by stage?",
  "Who are the top 10 accounts by lifetime_net_sales?",
  "What is total net sales by region?",
];

const NBA_PLACEHOLDER_RECOMMENDATION = "Personalized re-engagement email with rapid follow-up.";
const NBA_PLACEHOLDER_SUBJECT = "Quick 15-min check-in this week?";
const NBA_PLACEHOLDER_BODY = "I'm reaching out because it's been a little over a month since our last touch.";

function App() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [nba, setNba] = useState<NbaRecommendation | null>(null);
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [nbaLoading, setNbaLoading] = useState(false);
  const [isNbaModalOpen, setIsNbaModalOpen] = useState(false);
  const [emailRecipient, setEmailRecipient] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  // Genie (Sales data Q&A) tab state
  const [genieStatus, setGenieStatus] = useState<GenieStatus | null>(null);
  const [genieConversationId, setGenieConversationId] = useState<string | null>(null);
  const [genieTurns, setGenieTurns] = useState<GenieTurn[]>([]);
  const [genieInput, setGenieInput] = useState("");
  const [genieLoading, setGenieLoading] = useState(false);
  const [openSqlPanels, setOpenSqlPanels] = useState<Record<number, boolean>>({});
  const [callLogStatus, setCallLogStatus] = useState<CallLogStatus | null>(null);
  const [callLogTurns, setCallLogTurns] = useState<CallLogTurn[]>([]);
  const [callLogInput, setCallLogInput] = useState("");
  const [callLogLoading, setCallLogLoading] = useState(false);

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

  const loadCallLogStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/call-logs/status`);
      const data = await r.json().catch(() => ({}));
      if (r.ok && data && typeof data.configured === "boolean") {
        setCallLogStatus(data as CallLogStatus);
      } else {
        const msg = data?.detail ?? data?.message ?? "Could not load Call Analysis status.";
        setCallLogStatus({ configured: false, message: msg });
      }
    } catch (_) {
      setCallLogStatus({ configured: false, message: "Could not load Call Analysis status." });
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
    loadCallLogStatus();
  }, [loadStats, loadLlmStatus, loadGenieStatus, loadCallLogStatus]);
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
    setEmailStatus(null);
    setCopyStatus(null);
    try {
      const r = await fetch(`${API}/contacts/${selected.contact_id}/nba/generate`, { method: "POST" });
      if (r.ok) {
        setNba(await r.json());
        setIsNbaModalOpen(true);
      }
    } catch (_) {}
    setNbaLoading(false);
  };

  const handleCopyEmailDraft = async () => {
    if (!nba?.email_draft_subject && !nba?.email_draft_body) return;
    const content = [`Subject: ${nba?.email_draft_subject ?? ""}`, "", nba?.email_draft_body ?? ""].join("\n");
    try {
      await navigator.clipboard.writeText(content);
      setCopyStatus("Copied to clipboard");
    } catch (_) {
      setCopyStatus("Could not copy");
    }
  };

  const handleSendEmail = async () => {
    if (!nba?.email_draft_subject || !nba?.email_draft_body || sendingEmail) return;
    setSendingEmail(true);
    setEmailStatus(null);
    try {
      const r = await fetch(`${API}/email/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient: emailRecipient.trim() || undefined,
          subject: nba.email_draft_subject,
          message: nba.email_draft_body,
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        setEmailStatus(data?.message ?? "Email sent");
      } else {
        setEmailStatus(data?.detail ?? "Failed to send email");
      }
    } catch (e) {
      setEmailStatus(e instanceof Error ? e.message : "Failed to send email");
    }
    setSendingEmail(false);
  };

  const submitGenieQuestion = async (question: string) => {
    const q = question.trim();
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
      };
      const hasParsedContent =
        Boolean((response.text_response ?? "").trim()) ||
        Boolean((response.sql ?? "").trim()) ||
        Boolean(Array.isArray(response.data) && response.data.length > 0);
      if (!hasParsedContent && !response.error) {
        response.text_response =
          "Genie returned an empty response for this question in the hosted app context. Try rephrasing or click Ask again.";
      }
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

  const handleGenieAsk = async () => {
    await submitGenieQuestion(genieInput);
  };

  const submitCallLogQuestion = async (question: string) => {
    const q = question.trim();
    if (!q || callLogLoading) return;
    setCallLogLoading(true);
    setCallLogInput("");
    try {
      const r = await fetch(`${API}/call-logs/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data: CallLogChatResponse & { detail?: string } = await r.json().catch(() => ({}));
      const response: CallLogChatResponse = {
        answer: r.ok ? (data?.answer ?? "") : (data?.detail ?? "Call analysis request failed"),
        citations: Array.isArray(data?.citations) ? data.citations : [],
        retrieved_chunks: Array.isArray(data?.retrieved_chunks) ? data.retrieved_chunks : [],
      };
      setCallLogTurns((prev) => [...prev, { question: q, response }]);
    } catch (e) {
      setCallLogTurns((prev) => [
        ...prev,
        { question: q, response: { answer: e instanceof Error ? e.message : "Call analysis request failed" } },
      ]);
    }
    setCallLogLoading(false);
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

  const formatDate = (value: string | null) => {
    if (!value) return "—";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString();
  };

  const displayName = (name: string | null | undefined) => {
    if (!name) return "—";
    return name.replace(/\s+\d+$/, "").trim();
  };

  const isPlaceholderNba =
    (nba?.recommendation_text ?? "").trim() === NBA_PLACEHOLDER_RECOMMENDATION &&
    (nba?.email_draft_subject ?? "").trim() === NBA_PLACEHOLDER_SUBJECT &&
    (nba?.email_draft_body ?? "").trim() === NBA_PLACEHOLDER_BODY;
  const hasRealNbaContent =
    !isPlaceholderNba &&
    Boolean((nba?.recommendation_text ?? "").trim() || (nba?.email_draft_subject ?? "").trim() || (nba?.email_draft_body ?? "").trim());
  const totalTrxVolume = contacts.reduce((sum, c) => sum + (c.trx_volume_3m ?? 0), 0);
  const totalNrxVolume = contacts.reduce((sum, c) => sum + (c.nrx_volume_3m ?? 0), 0);
  const highRiskAccounts = contacts.filter((c) => c.risk_level === "High").length;
  const avgPriority = contacts.length
    ? contacts.reduce((sum, c) => sum + (Number.isFinite(c.priority_score) ? c.priority_score : 0), 0) / contacts.length
    : 0;
  const riskBreakdown = ["High", "Medium", "Low"].map((risk) => ({
    label: risk,
    count: contacts.filter((c) => c.risk_level === risk).length,
  }));
  const channelBreakdown = Object.entries(
    contacts.reduce<Record<string, number>>((acc, c) => {
      const key = c.preferred_channel || "Unknown";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {}),
  )
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
  const topAccountsByPriority = [...contacts]
    .sort((a, b) => b.priority_score - a.priority_score)
    .slice(0, 8);

  const renderInlineMarkdown = (text: string) => {
    const parts: Array<string | JSX.Element> = [];
    const regex = /\*\*(.+?)\*\*/g;
    let lastIndex = 0;
    let match = regex.exec(text);
    while (match) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      parts.push(
        <strong key={`bold-${match.index}`} className="font-semibold text-slate-900">
          {match[1]}
        </strong>,
      );
      lastIndex = regex.lastIndex;
      match = regex.exec(text);
    }
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }
    return parts;
  };

  const renderGenieText = (text: string) => {
    const lines = text.split("\n");
    return (
      <div className="space-y-1.5">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={`spacer-${idx}`} className="h-2" />;
          const heading = trimmed.match(/^#{1,6}\s+(.*)$/);
          if (heading) {
            return (
              <p key={`heading-${idx}`} className="font-semibold text-slate-900">
                {renderInlineMarkdown(heading[1])}
              </p>
            );
          }
          const bullet = trimmed.match(/^-\s+(.*)$/);
          if (bullet) {
            return (
              <p key={`bullet-${idx}`} className="pl-3 text-slate-700">
                <span className="mr-2 text-slate-400">•</span>
                {renderInlineMarkdown(bullet[1])}
              </p>
            );
          }
          return (
            <p key={`line-${idx}`} className="text-slate-700">
              {renderInlineMarkdown(trimmed)}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#f3f5f8]">
      <div className="flex min-h-screen">
        <aside className="w-64 shrink-0 border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-6">
            <div className="flex items-center">
              <div>
                <h1 className="text-lg font-bold text-slate-900">Butterfly Customer Intelligence</h1>
                <p className="text-xs text-slate-500">Jackson and Jackson</p>
              </div>
            </div>
          </div>
          <nav className="space-y-2 p-4">
            <button
              type="button"
              onClick={() => setActiveTab("overview")}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                activeTab === "overview"
                  ? "bg-[#D71500] text-white"
                  : "text-slate-700 hover:bg-red-50 hover:text-[#D71500]"
              }`}
            >
              Overview
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("nba")}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                activeTab === "nba"
                  ? "bg-[#D71500] text-white"
                  : "text-slate-700 hover:bg-red-50 hover:text-[#D71500]"
              }`}
            >
              Next Best Action
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("genie")}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                activeTab === "genie"
                  ? "bg-[#D71500] text-white"
                  : "text-slate-700 hover:bg-red-50 hover:text-[#D71500]"
              }`}
            >
              Ask Genie (CxM)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("call_logs")}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                activeTab === "call_logs"
                  ? "bg-[#D71500] text-white"
                  : "text-slate-700 hover:bg-red-50 hover:text-[#D71500]"
              }`}
            >
              Call Analysis Agent
            </button>
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="p-6">
      {activeTab === "overview" ? (
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Account Summary</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Portfolio-level view of your territory with account health and engagement trends.
                </p>
              </div>
              <div className="text-xs text-slate-500">
                Avg Priority: <span className="font-semibold text-slate-900">{avgPriority.toFixed(1)}</span>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">Accounts</p>
                <p className="text-2xl font-semibold text-slate-900">{contacts.length}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">3M TRX Volume</p>
                <p className="text-2xl font-semibold text-slate-900">{Math.round(totalTrxVolume).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">3M NRX Volume</p>
                <p className="text-2xl font-semibold text-slate-900">{Math.round(totalNrxVolume).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs text-slate-500">High-Risk Accounts</p>
                <p className="text-2xl font-semibold text-slate-900">{highRiskAccounts}</p>
              </div>
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Account Risk Breakdown</h3>
              <p className="mt-1 text-xs text-slate-500">Distribution by risk level</p>
              <div className="mt-4 space-y-3">
                {riskBreakdown.map((item) => {
                  const max = Math.max(...riskBreakdown.map((r) => r.count), 1);
                  const widthPct = (item.count / max) * 100;
                  return (
                    <div key={item.label}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="text-slate-600">{item.label}</span>
                        <span className="font-medium text-slate-900">{item.count}</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100">
                        <div className="h-2 rounded-full bg-[#D71500]" style={{ width: `${widthPct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Channel Mix</h3>
              <p className="mt-1 text-xs text-slate-500">Accounts by preferred engagement channel</p>
              <div className="mt-4 space-y-3">
                {channelBreakdown.length === 0 ? (
                  <p className="text-sm text-slate-500">No channel data available.</p>
                ) : (
                  channelBreakdown.map((item) => {
                    const max = Math.max(...channelBreakdown.map((c) => c.count), 1);
                    const widthPct = (item.count / max) * 100;
                    return (
                      <div key={item.label}>
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span className="text-slate-600">{item.label}</span>
                          <span className="font-medium text-slate-900">{item.count}</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div className="h-2 rounded-full bg-slate-700" style={{ width: `${widthPct}%` }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm xl:col-span-2">
              <h3 className="text-sm font-semibold text-slate-900">Top Accounts by Priority</h3>
              <p className="mt-1 text-xs text-slate-500">Highest-priority accounts in your portfolio</p>
              <div className="mt-4 space-y-3">
                {topAccountsByPriority.map((account) => {
                  const max = Math.max(...topAccountsByPriority.map((a) => a.priority_score), 1);
                  const widthPct = (account.priority_score / max) * 100;
                  return (
                    <div key={account.contact_id}>
                      <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                        <span className="truncate text-slate-700">{displayName(account.name)}</span>
                        <span className="font-medium text-slate-900">{Math.round(account.priority_score)}</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100">
                        <div className="h-2 rounded-full bg-cyan-600" style={{ width: `${widthPct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Portfolio Snapshot</h3>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Growth opportunities</dt>
                  <dd className="font-medium text-slate-900">{stats?.growth_opportunities ?? 0}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">At-risk accounts</dt>
                  <dd className="font-medium text-slate-900">{stats?.at_risk_accounts ?? 0}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Assigned contacts</dt>
                  <dd className="font-medium text-slate-900">{stats?.assigned_contacts ?? contacts.length}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Avg at-risk priority</dt>
                  <dd className="font-medium text-slate-900">{stats?.at_risk_avg_priority?.toFixed(1) ?? "0.0"}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Account Drilldown Table</h3>
            <p className="mt-1 text-xs text-slate-500">Quick scan of account-level summary data</p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <th className="py-2 pr-4">Account ID</th>
                    <th className="py-2 pr-4">Account Name</th>
                    <th className="py-2 pr-4">Territory</th>
                    <th className="py-2 pr-4">Preferred Channel</th>
                    <th className="py-2 pr-4">Risk</th>
                    <th className="py-2 pr-4">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {topAccountsByPriority.map((account) => (
                    <tr key={account.contact_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{account.contact_id}</td>
                      <td className="py-2 pr-4 font-medium text-slate-900">{displayName(account.name)}</td>
                      <td className="py-2 pr-4 text-slate-700">{account.territory_id ?? "—"}</td>
                      <td className="py-2 pr-4 text-slate-700">{account.preferred_channel}</td>
                      <td className="py-2 pr-4">{riskBadge(account.risk_level)}</td>
                      <td className="py-2 pr-4 text-slate-900">{Math.round(account.priority_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : activeTab === "genie" ? (
        <div className="mx-auto w-full">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-4">
              <h2 className="font-semibold text-slate-900">Investigate with Ask Genie</h2>
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
            <div className="flex h-[calc(100vh-210px)] min-h-[640px] flex-col">
              <div className="px-4 pt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Sample questions</p>
                <div className="flex flex-wrap gap-2">
                  {GENIE_SAMPLE_QUESTIONS.map((question) => (
                    <button
                      key={question}
                      type="button"
                      onClick={() => submitGenieQuestion(question)}
                      disabled={genieLoading}
                      className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      title="Ask Genie this question"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
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
                      {res.text_response != null && res.text_response !== "" && renderGenieText(String(res.text_response))}
                      {res.sql != null && res.sql !== "" && (
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() =>
                              setOpenSqlPanels((prev) => ({
                                ...prev,
                                [i]: !prev[i],
                              }))
                            }
                            className="text-xs font-medium text-[#D71500] hover:text-[#c01200] hover:underline"
                          >
                            {openSqlPanels[i] ? "Hide code" : "Show code"}
                          </button>
                          <div
                            aria-hidden={!openSqlPanels[i]}
                            className={`grid transition-all duration-300 ease-out ${
                              openSqlPanels[i] ? "grid-rows-[1fr] opacity-100 mt-2" : "grid-rows-[0fr] opacity-0"
                            }`}
                          >
                            <div className="overflow-hidden">
                              <pre className="overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                                {String(res.sql)}
                              </pre>
                            </div>
                          </div>
                        </div>
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
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm placeholder:text-slate-400 focus:border-[#D71500] focus:outline-none focus:ring-1 focus:ring-[#D71500] disabled:opacity-60 disabled:bg-slate-50"
                    disabled={genieLoading}
                  />
                  <button
                    type="submit"
                    disabled={genieLoading || !genieInput.trim()}
                    className="rounded-lg bg-[#D71500] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#c01200] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Ask
                  </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : activeTab === "call_logs" ? (
        <div className="mx-auto w-full">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50/80 px-5 py-4">
              <h2 className="font-semibold text-slate-900">Call Analysis Agent</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Ask natural language questions over the call-log vector index.
              </p>
              {!callLogStatus?.configured && (
                <p className="mt-2 text-xs text-amber-700">
                  {callLogStatus?.message ?? "Call Analysis is not configured yet."}
                </p>
              )}
              {callLogStatus?.configured && (
                <p className="mt-2 text-xs text-slate-500">
                  Index: {callLogStatus.vector_index ?? "—"}
                </p>
              )}
            </div>

            <div className="flex h-[calc(100vh-210px)] min-h-[640px] flex-col">
              <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
                {callLogTurns.length === 0 && !callLogLoading && (
                  <p className="py-8 text-center text-sm text-slate-500">
                    Ask about call summaries, objections, products discussed, and next-best follow-up actions.
                  </p>
                )}
                {callLogTurns.map((turn, i) => (
                  <div key={i} className="space-y-2">
                    <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800">
                      <span className="font-medium text-slate-500">You: </span>
                      {turn.question}
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm">
                      <div className="text-slate-700">{renderGenieText(turn.response.answer)}</div>
                      {Array.isArray(turn.response.citations) && turn.response.citations.length > 0 && (
                        <div className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-500">
                          <p className="font-medium text-slate-600">Citations</p>
                          <ul className="mt-1 space-y-1">
                            {turn.response.citations.map((c, ci) => (
                              <li key={ci}>- {c.document_name ?? "call_log"} ({c.chunk_id ?? "chunk"})</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {callLogLoading && (
                  <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#D71500] border-t-transparent" />
                    Querying call index…
                  </div>
                )}
              </div>

              <div className="border-t border-slate-200 p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitCallLogQuestion(callLogInput);
                  }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    value={callLogInput}
                    onChange={(e) => setCallLogInput(e.target.value)}
                    placeholder="Ask a question about the call log index…"
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm placeholder:text-slate-400 focus:border-[#D71500] focus:outline-none focus:ring-1 focus:ring-[#D71500] disabled:bg-slate-50 disabled:opacity-60"
                    disabled={callLogLoading}
                  />
                  <button
                    type="submit"
                    disabled={callLogLoading || !callLogInput.trim()}
                    className="rounded-lg bg-[#D71500] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#c01200] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Ask
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : (
      <div className="mx-auto flex max-w-7xl gap-6">
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
                contacts.map((c) => (
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
                    <div className="flex items-center justify-end gap-2">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                        {Math.round(c.priority_score)}
                      </span>
                    </div>
                    <p className="mt-1 font-semibold text-slate-900">{displayName(c.name)}</p>
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
                    <h2 className="text-lg font-bold text-slate-900">{displayName(selected.name)}</h2>
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
                  <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#D71500] border-t-transparent" />
                    Generating recommendation and email...
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleGenerateNba}
                    className="mt-4 rounded-lg bg-[#D71500] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#c01200] focus:outline-none focus:ring-2 focus:ring-[#D71500] focus:ring-offset-2"
                  >
                    Generate Next Best Action
                  </button>
                )}
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

              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="font-semibold text-slate-900">Correspondence context</h3>
                <p className="mt-0.5 text-xs text-slate-500">This context is passed into NBA and email generation.</p>
                <dl className="mt-4 grid grid-cols-1 gap-y-2 text-sm sm:grid-cols-2 sm:gap-x-8">
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Last interaction channel</dt><dd className="font-medium">{selected.last_interaction_channel ?? "—"}</dd></div>
                  <div className="flex justify-between border-b border-slate-100 pb-2"><dt className="text-slate-500">Last interaction date</dt><dd className="font-medium">{formatDate(selected.last_interaction_date)}</dd></div>
                  <div className="sm:col-span-2 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Last interaction summary</dt>
                    <dd className="mt-1 font-medium text-slate-800">{selected.last_interaction_summary ?? "—"}</dd>
                  </div>
                  <div className="sm:col-span-2 border-b border-slate-100 pb-2">
                    <dt className="text-slate-500">Last products discussed</dt>
                    <dd className="mt-1 font-medium text-slate-800">{selected.last_products_discussed ?? "—"}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-slate-500">Next follow-up objective</dt>
                    <dd className="mt-1 font-medium text-slate-800">{selected.next_follow_up_objective ?? "—"}</dd>
                  </div>
                </dl>
              </section>

              {isNbaModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
                  <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900">Generated email draft</h3>
                        <p className="mt-1 text-sm text-slate-500">Review, copy, or send directly.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsNbaModalOpen(false)}
                        className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                      >
                        Close
                      </button>
                    </div>

                    {!hasRealNbaContent || !nba?.email_draft_subject ? (
                      <p className="mt-4 text-sm text-slate-600">No email draft yet. Click Generate Next Best Action first.</p>
                    ) : (
                      <>
                        <div className="mt-4 space-y-2">
                          <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Send to</label>
                          <input
                            type="email"
                            value={emailRecipient}
                            onChange={(e) => setEmailRecipient(e.target.value)}
                            placeholder="Enter recipient email (or use default from server config)"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-[#D71500] focus:outline-none focus:ring-1 focus:ring-[#D71500]"
                          />
                        </div>

                        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                          <p className="text-sm font-semibold text-slate-900">{nba.email_draft_subject}</p>
                          <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{nba.email_draft_body ?? ""}</div>
                        </div>

                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={handleCopyEmailDraft}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                          >
                            Copy
                          </button>
                          <button
                            type="button"
                            onClick={handleSendEmail}
                            disabled={sendingEmail}
                            className="rounded-lg bg-[#D71500] px-3 py-2 text-sm font-semibold text-white hover:bg-[#c01200] disabled:opacity-50"
                          >
                            {sendingEmail ? "Sending..." : "Send email"}
                          </button>
                          {copyStatus && <span className="text-xs text-slate-500">{copyStatus}</span>}
                          {emailStatus && <span className="text-xs font-medium text-slate-700">{emailStatus}</span>}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

            </>
          )}
        </main>
      </div>
      )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
