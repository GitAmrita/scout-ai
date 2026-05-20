"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Job {
  title: string;
  url?: string;
  description?: string;
}

interface Company {
  name: string;
  website?: string;
  careers_url?: string;
  description?: string;
  funding?: string;
  hiring_signals: string[];
  jobs: Job[];
}

interface Analysis {
  name: string;
  fit_score: number;
  fit_label: string;
  tech_stack: string[];
  fit_reasons: string[];
  gaps: string[];
  recommendation: string;
}

interface ApplicationMaterials {
  why_this_company: string;
  tailored_bullets: string[];
  application_tips: string[];
}

interface AutoApplyField {
  label: string;
  type: string;
  value: string;
  confidence: "high" | "medium" | "low";
  skip: boolean;
}

type AutoFillStatus = "idle" | "analyzing" | "awaiting_confirmation" | "filling" | "filled" | "submitting" | "submitted" | "error";

interface AutoFillState {
  status: AutoFillStatus;
  screenshot?: string;
  fields?: AutoApplyField[];
  formUrl?: string;
  notes?: string;
  hasResumeUpload?: boolean;
  filledScreenshot?: string;
  confirmScreenshot?: string;
  skipped?: string[];
  sessionId?: string;
  error?: string;
}

interface CompanyWithAnalysis extends Company {
  analysis?: Analysis;
  materials?: ApplicationMaterials;
  materialsLoading?: boolean;
}

interface AgentEvent {
  type: "agent_start" | "agent_thinking" | "tool_call" | "tool_error" | "company_found" | "done" | "analysis_start" | "company_analyzed" | "analysis_done" | "error";
  message?: string;
  tool?: string;
  input?: Record<string, string>;
  company?: Company;
  companies?: Company[];
  analysis?: Analysis;
  analyses?: Analysis[];
}

const TOOL_LABELS: Record<string, string> = {
  search_web: "Searching web",
  scrape_url: "Reading page",
};

const FIT_LABEL_STYLES: Record<string, string> = {
  "Strong Match": "bg-emerald-500 text-zinc-950",
  "Good Match": "bg-blue-500 text-white",
  "Partial Match": "bg-amber-500 text-zinc-950",
  "Weak Match": "bg-zinc-600 text-white",
};

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [companies, setCompanies] = useState<CompanyWithAnalysis[]>([]);
  const [hasRun, setHasRun] = useState(false);
  const [resumeUploaded, setResumeUploaded] = useState(false);
  const [autoFillUrl, setAutoFillUrl] = useState("");
  const [autoFill, setAutoFill] = useState<AutoFillState>({ status: "idle" });
  const feedRef = useRef<HTMLDivElement>(null);

  const startDiscovery = async () => {
    if (!prompt.trim() || isRunning) return;

    setIsRunning(true);
    setHasRun(true);
    setEvents([]);
    setCompanies([]);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: AgentEvent = JSON.parse(line.slice(6));
            setEvents((prev) => [...prev, event]);
            if (event.type === "company_found" && event.company) {
              setCompanies((prev) => [...prev, event.company!]);
            }
            if (event.type === "company_analyzed" && event.analysis) {
              setCompanies((prev) =>
                prev.map((c) =>
                  c.name === event.analysis!.name
                    ? { ...c, analysis: event.analysis }
                    : c
                )
              );
            }
            if (event.type === "analysis_done") {
              setCompanies((prev) =>
                [...prev].sort(
                  (a, b) => (b.analysis?.fit_score ?? 0) - (a.analysis?.fit_score ?? 0)
                )
              );
              setIsRunning(false);
            }
            // scroll feed to bottom
            setTimeout(() => {
              feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
            }, 50);
          } catch {}
        }
      }
    } catch {
      setEvents((prev) => [...prev, { type: "error", message: "Could not connect to backend." }]);
      setIsRunning(false);
    }
  };

  const prepareApplication = async (company: CompanyWithAnalysis) => {
    setCompanies((prev) =>
      prev.map((c) => c.name === company.name ? { ...c, materialsLoading: true } : c)
    );
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company, analysis: company.analysis }),
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "application_ready" && event.materials) {
              setCompanies((prev) =>
                prev.map((c) =>
                  c.name === company.name
                    ? { ...c, materials: event.materials, materialsLoading: false }
                    : c
                )
              );
            }
          } catch {}
        }
      }
    } catch {
      setCompanies((prev) =>
        prev.map((c) => c.name === company.name ? { ...c, materialsLoading: false } : c)
      );
    }
  };

  const uploadResume = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/upload-resume`, {
      method: "POST",
      body: formData,
    });
    setResumeUploaded(true);
  };

  const analyzeForm = async () => {
    if (!autoFillUrl.trim()) return;
    setAutoFill({ status: "analyzing" });
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auto-apply/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_url: autoFillUrl.trim() }),
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "auto_apply_analyzed") {
              setAutoFill({
                status: "awaiting_confirmation",
                screenshot: event.screenshot,
                fields: event.fields,
                formUrl: event.form_url,
                notes: event.notes,
                hasResumeUpload: event.has_resume_upload,
                sessionId: event.session_id,
              });
            }
          } catch {}
        }
      }
    } catch {
      setAutoFill({ status: "error", error: "Failed to analyze form." });
    }
  };

  const fillForm = async () => {
    if (!autoFill.sessionId || !autoFill.fields) return;
    setAutoFill((prev) => ({ ...prev, status: "filling" }));
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auto-apply/fill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: autoFill.sessionId, fields: autoFill.fields }),
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "auto_apply_filled") {
              setAutoFill((prev) => ({
                ...prev,
                status: "filled",
                filledScreenshot: event.screenshot,
                skipped: event.skipped,
                sessionId: event.session_id,
              }));
            }
            if (event.type === "auto_apply_error") {
              setAutoFill((prev) => ({ ...prev, status: "error", error: event.message }));
            }
          } catch {}
        }
      }
    } catch {
      setAutoFill((prev) => ({ ...prev, status: "error", error: "Failed to fill form." }));
    }
  };

  const submitForm = async () => {
    if (!autoFill.sessionId) return;
    setAutoFill((prev) => ({ ...prev, status: "submitting" }));
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auto-apply/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: autoFill.sessionId }),
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "auto_apply_submitted") {
              setAutoFill((prev) => ({ ...prev, status: "submitted", confirmScreenshot: event.screenshot }));
            }
            if (event.type === "auto_apply_error") {
              setAutoFill((prev) => ({ ...prev, status: "error", error: event.message }));
            }
          } catch {}
        }
      }
    } catch {
      setAutoFill((prev) => ({ ...prev, status: "error", error: "Failed to submit." }));
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800 px-8 py-5 flex items-center gap-3">
        <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
          <span className="text-xs font-bold text-zinc-950">S</span>
        </div>
        <span className="font-semibold text-zinc-100 tracking-tight">Scout</span>
        <span className="text-zinc-500 text-sm">Autonomous AI Career Intelligence</span>
      </header>

      {/* Main */}
      <main className="flex flex-col flex-1 max-w-6xl w-full mx-auto px-8 py-12">
        {/* Search */}
        <div className="flex flex-col gap-4 mb-10">
          <h1 className="text-2xl font-semibold text-zinc-100">
            Find your next role
          </h1>
          <p className="text-zinc-400 text-sm">
            Describe what you&apos;re looking for. Scout will discover companies, scrape careers pages, and surface the best matches.
          </p>
          <div className="flex gap-3">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && startDiscovery()}
              placeholder="e.g. healthcare AI startups hiring backend engineers"
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
            <button
              onClick={startDiscovery}
              disabled={isRunning || !prompt.trim()}
              className="px-5 py-3 rounded-lg bg-emerald-500 text-zinc-950 font-medium text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-emerald-400 transition-colors"
            >
              {isRunning ? "Searching..." : "Start Discovery"}
            </button>
          </div>
        </div>

        {/* Results area */}
        {hasRun && (
          <div className="flex gap-6 flex-1">
            {/* Activity Feed */}
            <div className="w-80 flex-shrink-0 flex flex-col gap-3">
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">
                Agent Activity
              </h2>
              <div
                ref={feedRef}
                className="flex flex-col gap-2 max-h-[560px] overflow-y-auto pr-1"
              >
                <AnimatePresence initial={false}>
                  {events.map((event, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`rounded-lg px-3 py-2 text-xs leading-relaxed ${
                        event.type === "tool_call"
                          ? "bg-zinc-800 text-zinc-300"
                          : event.type === "company_found"
                          ? "bg-emerald-950 border border-emerald-800 text-emerald-300"
                          : event.type === "company_analyzed"
                          ? "bg-blue-950 border border-blue-800 text-blue-300"
                          : event.type === "done" || event.type === "analysis_done"
                          ? "bg-zinc-800 text-emerald-400 font-medium"
                          : event.type === "error" || event.type === "tool_error"
                          ? "bg-red-950 border border-red-800 text-red-400"
                          : "text-zinc-400"
                      }`}
                    >
                      {event.type === "tool_call" && (
                        <span className="font-mono">
                          {TOOL_LABELS[event.tool ?? ""] ?? event.tool}
                          {event.input && (
                            <span className="text-zinc-500 ml-1">
                              ({Object.values(event.input)[0]?.slice(0, 50)})
                            </span>
                          )}
                        </span>
                      )}
                      {event.type === "company_found" && (
                        <span>Found: <strong>{event.company?.name}</strong></span>
                      )}
                      {event.type === "company_analyzed" && (
                        <span>
                          Analyzed: <strong>{event.analysis?.name}</strong>
                          {event.analysis?.fit_score !== undefined && (
                            <span className="ml-1 text-zinc-400">— {Math.round(event.analysis.fit_score / 10)}/10</span>
                          )}
                        </span>
                      )}
                      {(event.type === "agent_start" ||
                        event.type === "agent_thinking" ||
                        event.type === "analysis_start" ||
                        event.type === "done" ||
                        event.type === "analysis_done" ||
                        event.type === "error" ||
                        event.type === "tool_error") &&
                        event.message}
                    </motion.div>
                  ))}
                </AnimatePresence>
                {isRunning && (
                  <div className="flex gap-1 px-3 py-2">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-emerald-500"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Company Cards */}
            <div className="flex-1 flex flex-col gap-4">
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">
                Discovered Companies{companies.length > 0 && ` (${companies.length})`}
              </h2>
              <div className="flex flex-col gap-4 overflow-y-auto max-h-[560px] pr-1">
                <AnimatePresence initial={false}>
                  {companies.map((company, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-3"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-zinc-100">{company.name}</h3>
                            {company.funding && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
                                {company.funding}
                              </span>
                            )}
                            {company.analysis && (
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FIT_LABEL_STYLES[company.analysis.fit_label] ?? "bg-zinc-700 text-white"}`}>
                                {company.analysis.fit_label}
                              </span>
                            )}
                          </div>
                          {company.website && (
                            <a
                              href={company.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors"
                            >
                              {company.website.replace(/^https?:\/\//, "")}
                            </a>
                          )}
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          {company.analysis && (
                            <div className="flex flex-col items-center">
                              <span className="text-2xl font-bold text-zinc-100 leading-none">{Math.round(company.analysis.fit_score / 10)}</span>
                              <span className="text-xs text-zinc-500">/ 10</span>
                            </div>
                          )}
                          {company.careers_url && (
                            <a
                              href={company.careers_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs px-3 py-1.5 rounded-lg border border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400 transition-colors whitespace-nowrap"
                            >
                              View careers
                            </a>
                          )}
                        </div>
                      </div>

                      {company.description && (
                        <p className="text-sm text-zinc-400 leading-relaxed">{company.description}</p>
                      )}

                      {/* Tech stack */}
                      {company.analysis?.tech_stack && company.analysis.tech_stack.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {company.analysis.tech_stack.map((tech, j) => (
                            <span key={j} className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700">
                              {tech}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Fit reasons */}
                      {company.analysis?.fit_reasons && company.analysis.fit_reasons.length > 0 && (
                        <div className="flex flex-col gap-1">
                          {company.analysis.fit_reasons.map((reason, j) => (
                            <div key={j} className="flex items-start gap-2 text-xs text-emerald-400">
                              <span className="flex-shrink-0 mt-0.5">✓</span>
                              <span>{reason}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Gaps */}
                      {company.analysis?.gaps && company.analysis.gaps.length > 0 && (
                        <div className="flex flex-col gap-1">
                          {company.analysis.gaps.map((gap, j) => (
                            <div key={j} className="flex items-start gap-2 text-xs text-amber-400">
                              <span className="flex-shrink-0 mt-0.5">△</span>
                              <span>{gap}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {company.hiring_signals.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {company.hiring_signals.map((signal, j) => (
                            <span
                              key={j}
                              className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-900"
                            >
                              {signal}
                            </span>
                          ))}
                        </div>
                      )}

                      {company.jobs.length > 0 && (
                        <div className="flex flex-col gap-1.5 border-t border-zinc-800 pt-3">
                          {company.jobs.map((job, j) => (
                            <div key={j} className="flex items-center justify-between">
                              <span className="text-sm text-zinc-300">{job.title}</span>
                              <a
                                href={job.url || company.careers_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors"
                              >
                                View
                              </a>
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Prepare Application */}
                      {company.analysis && Math.round(company.analysis.fit_score / 10) >= 6 && (
                        <div className="border-t border-zinc-800 pt-3">
                          {!company.materials && !company.materialsLoading && (
                            <button
                              onClick={() => prepareApplication(company)}
                              className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-zinc-950 font-medium hover:bg-emerald-400 transition-colors"
                            >
                              Prepare Application
                            </button>
                          )}
                          {company.materialsLoading && (
                            <div className="flex items-center gap-2 text-xs text-zinc-400">
                              <div className="flex gap-1">
                                {[0, 1, 2].map((i) => (
                                  <motion.div
                                    key={i}
                                    className="w-1 h-1 rounded-full bg-emerald-500"
                                    animate={{ opacity: [0.3, 1, 0.3] }}
                                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                                  />
                                ))}
                              </div>
                              Preparing application...
                            </div>
                          )}
                          {company.materials && (
                            <div className="flex flex-col gap-4">
                              <div>
                                <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">Why This Company</p>
                                <p className="text-sm text-zinc-300 leading-relaxed">{company.materials.why_this_company}</p>
                              </div>
                              {company.materials.tailored_bullets.length > 0 && (
                                <div>
                                  <div className="flex items-center justify-between mb-1">
                                    <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Tailored Resume Bullets</p>
                                    <button
                                      onClick={() => navigator.clipboard.writeText(company.materials!.tailored_bullets.join("\n"))}
                                      className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors"
                                    >
                                      Copy all
                                    </button>
                                  </div>
                                  <div className="flex flex-col gap-1.5">
                                    {company.materials.tailored_bullets.map((bullet, j) => (
                                      <div key={j} className="flex items-start gap-2 text-xs text-zinc-300">
                                        <span className="flex-shrink-0 mt-0.5 text-emerald-500">•</span>
                                        <span>{bullet}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {company.materials.application_tips.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">Application Tips</p>
                                  <div className="flex flex-col gap-1.5">
                                    {company.materials.application_tips.map((tip, j) => (
                                      <div key={j} className="flex items-start gap-2 text-xs text-zinc-400">
                                        <span className="flex-shrink-0 mt-0.5">→</span>
                                        <span>{tip}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>

                {!isRunning && companies.length === 0 && (
                  <p className="text-sm text-zinc-600">No companies discovered yet.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {!hasRun && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-600 text-sm">Enter a search goal above to start.</p>
          </div>
        )}
      </main>

      {/* Auto Fill Bar */}
      <div className="sticky bottom-0 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur px-8 py-4">
        <div className="max-w-6xl mx-auto flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2.5 focus-within:border-emerald-500 transition-colors">
              <span className="text-xs text-zinc-500 whitespace-nowrap">Auto Fill →</span>
              <input
                type="text"
                value={autoFillUrl}
                onChange={(e) => setAutoFillUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && analyzeForm()}
                placeholder="Paste job application URL here"
                className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none"
              />
            </div>
            {!resumeUploaded ? (
              <label className="text-xs px-3 py-2.5 rounded-lg border border-zinc-700 text-zinc-400 cursor-pointer hover:border-zinc-500 transition-colors whitespace-nowrap">
                Upload Resume PDF
                <input type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadResume(f); }} />
              </label>
            ) : (
              <span className="text-xs text-emerald-400 whitespace-nowrap">Resume ready ✓</span>
            )}
            <button
              onClick={analyzeForm}
              disabled={!autoFillUrl.trim() || autoFill.status === "analyzing" || autoFill.status === "submitting"}
              className="px-4 py-2.5 rounded-lg bg-emerald-500 text-zinc-950 font-medium text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-emerald-400 transition-colors whitespace-nowrap"
            >
              {autoFill.status === "analyzing" ? "Analyzing..." : "Analyze Form"}
            </button>
          </div>

          {/* Auto Fill Panel */}
          <AnimatePresence>
            {autoFill.status !== "idle" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="rounded-lg border border-zinc-700 bg-zinc-900 p-4 flex flex-col gap-3 overflow-hidden"
              >
                {autoFill.status === "analyzing" && (
                  <div className="flex items-center gap-2 text-xs text-zinc-400">
                    <div className="flex gap-1">
                      {[0,1,2].map((k) => (
                        <motion.div key={k} className="w-1 h-1 rounded-full bg-emerald-500"
                          animate={{ opacity: [0.3,1,0.3] }}
                          transition={{ duration: 1.2, repeat: Infinity, delay: k * 0.2 }}
                        />
                      ))}
                    </div>
                    Analyzing application form...
                  </div>
                )}

                {/* Step 1: Field plan preview */}
                {autoFill.status === "awaiting_confirmation" && autoFill.fields && (
                  <div className="flex gap-4">
                    {autoFill.screenshot && (
                      <img
                        src={`data:image/png;base64,${autoFill.screenshot}`}
                        alt="Form preview"
                        className="rounded border border-zinc-700 w-48 flex-shrink-0 object-top object-cover self-start"
                      />
                    )}
                    <div className="flex flex-col gap-3 flex-1 min-w-0">
                      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Fields to fill</p>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                        {autoFill.fields.filter(f => !f.skip && f.value).map((field, k) => (
                          <div key={k} className="flex items-start justify-between gap-2 text-xs">
                            <span className={`flex-shrink-0 ${field.confidence === "high" ? "text-emerald-400" : field.confidence === "medium" ? "text-amber-400" : "text-zinc-500"}`}>
                              {field.label}
                            </span>
                            <span className="text-zinc-400 truncate max-w-36">{field.type === "file" ? "resume.pdf" : field.value}</span>
                          </div>
                        ))}
                      </div>
                      {autoFill.notes && <p className="text-xs text-zinc-500 italic">{autoFill.notes}</p>}
                      <div className="flex items-center gap-3">
                        <button
                          onClick={fillForm}
                          className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-zinc-950 font-medium hover:bg-emerald-400 transition-colors"
                        >
                          Fill Form
                        </button>
                        <button
                          onClick={() => setAutoFill({ status: "idle" })}
                          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 2: Filled form review */}
                {(autoFill.status === "filled" || autoFill.status === "submitting") && autoFill.filledScreenshot && (
                  <div className="flex flex-col gap-3">
                    <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Review filled form</p>
                    <div className="overflow-y-auto max-h-96 rounded border border-zinc-700">
                      <img
                        src={`data:image/png;base64,${autoFill.filledScreenshot}`}
                        alt="Filled form"
                        className="w-full"
                      />
                    </div>
                    {autoFill.skipped && autoFill.skipped.length > 0 && (
                      <p className="text-xs text-amber-400">
                        Could not auto-fill: {autoFill.skipped.join(", ")} — fill these manually in the browser window before submitting.
                      </p>
                    )}
                    <p className="text-xs text-zinc-500">The browser window is still open — make any edits, then click Submit.</p>
                    <div className="flex items-center gap-3">
                      {autoFill.status === "filled" && (
                        <>
                          <button
                            onClick={submitForm}
                            className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-zinc-950 font-medium hover:bg-emerald-400 transition-colors"
                          >
                            Submit Application
                          </button>
                          <button
                            onClick={() => setAutoFill({ status: "idle" })}
                            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                      {autoFill.status === "submitting" && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <div className="flex gap-1">
                            {[0,1,2].map((k) => (
                              <motion.div key={k} className="w-1 h-1 rounded-full bg-emerald-500"
                                animate={{ opacity: [0.3,1,0.3] }}
                                transition={{ duration: 1.2, repeat: Infinity, delay: k * 0.2 }}
                              />
                            ))}
                          </div>
                          Submitting...
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {autoFill.status === "filling" && (
                  <div className="flex items-center gap-2 text-xs text-zinc-400">
                    <div className="flex gap-1">
                      {[0,1,2].map((k) => (
                        <motion.div key={k} className="w-1 h-1 rounded-full bg-emerald-500"
                          animate={{ opacity: [0.3,1,0.3] }}
                          transition={{ duration: 1.2, repeat: Infinity, delay: k * 0.2 }}
                        />
                      ))}
                    </div>
                    Filling form...
                  </div>
                )}

                {autoFill.status === "submitted" && (
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-emerald-400 font-medium">Application submitted!</p>
                    {autoFill.confirmScreenshot && (
                      <img
                        src={`data:image/png;base64,${autoFill.confirmScreenshot}`}
                        alt="Confirmation"
                        className="rounded border border-zinc-700 h-20 object-top object-cover"
                      />
                    )}
                    <button
                      onClick={() => { setAutoFill({ status: "idle" }); setAutoFillUrl(""); }}
                      className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors ml-auto"
                    >
                      Dismiss
                    </button>
                  </div>
                )}

                {autoFill.status === "error" && (
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-red-400">{autoFill.error}</p>
                    <button onClick={() => setAutoFill({ status: "idle" })} className="text-xs text-zinc-500 hover:text-zinc-300">Dismiss</button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
