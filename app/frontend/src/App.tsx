import { useEffect, useState } from "react";
import type { Action } from "./types";

const API = "/api/actions";

function App() {
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(API + "?limit=50")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then(setActions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const updateStatus = async (id: number, status: string) => {
    const res = await fetch(`${API}/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) return;
    const updated = await res.json();
    setActions((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "completed":
        return "bg-emerald-100 text-emerald-800";
      case "in_progress":
        return "bg-amber-100 text-amber-800";
      case "dismissed":
        return "bg-gray-200 text-gray-600";
      default:
        return "bg-jnj-red/10 text-jnj-red";
    }
  };

  const priorityLabel = (p: string) => p.charAt(0).toUpperCase() + p.slice(1);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-jnj-red" />
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-gray-900">
                Next Best Action
              </h1>
              <p className="text-sm text-gray-500">Johnson & Johnson MedTech</p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        )}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-jnj-red border-t-transparent" />
          </div>
        ) : (
          <div className="space-y-3">
            {actions.length === 0 ? (
              <p className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
                No actions yet. Run the setup script to seed the database.
              </p>
            ) : (
              actions.map((a) => (
                <article
                  key={a.id}
                  className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h2 className="font-medium text-gray-900">{a.title}</h2>
                      {a.description && (
                        <p className="mt-1 text-sm text-gray-500">{a.description}</p>
                      )}
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
                        <span>{a.account_id}</span>
                        {a.contact_id && <span>· {a.contact_id}</span>}
                        {a.due_date && (
                          <span>· Due {new Date(a.due_date).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(a.status)}`}
                      >
                        {a.status.replace("_", " ")}
                      </span>
                      <span className="rounded bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600">
                        {priorityLabel(a.priority)}
                      </span>
                      {a.status === "pending" && (
                        <>
                          <button
                            type="button"
                            onClick={() => updateStatus(a.id, "in_progress")}
                            className="rounded border border-jnj-red bg-white px-3 py-1.5 text-xs font-medium text-jnj-red hover:bg-jnj-red/5"
                          >
                            Start
                          </button>
                          <button
                            type="button"
                            onClick={() => updateStatus(a.id, "completed")}
                            className="rounded bg-jnj-red px-3 py-1.5 text-xs font-medium text-white hover:bg-jnj-red-dark"
                          >
                            Complete
                          </button>
                          <button
                            type="button"
                            onClick={() => updateStatus(a.id, "dismissed")}
                            className="rounded border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                          >
                            Dismiss
                          </button>
                        </>
                      )}
                      {a.status === "in_progress" && (
                        <>
                          <button
                            type="button"
                            onClick={() => updateStatus(a.id, "completed")}
                            className="rounded bg-jnj-red px-3 py-1.5 text-xs font-medium text-white hover:bg-jnj-red-dark"
                          >
                            Complete
                          </button>
                          <button
                            type="button"
                            onClick={() => updateStatus(a.id, "dismissed")}
                            className="rounded border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                          >
                            Dismiss
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
