"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useMyOrgs, useProjects } from "@/hooks/use-api";
import { createApiClient } from "@/lib/api/client";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Bot, Play, CheckCircle2, XCircle, Clock, Search, FileText, Brain, Layers } from "lucide-react";

type AgentType = "repo" | "doc" | "memory" | "architecture";

const AGENT_INFO: Record<AgentType, { label: string; description: string; icon: typeof Bot }> = {
  repo: { label: "Repo Explorer", description: "Analyze repository structure and architecture", icon: Search },
  doc: { label: "Documenter", description: "Generate documentation from code", icon: FileText },
  memory: { label: "Memory Extractor", description: "Extract facts and store in project memory", icon: Brain },
  architecture: { label: "Architecture Analyzer", description: "Map service boundaries and data flow", icon: Layers },
};

interface Event {
  id: number | null;
  kind: string;
  payload: Record<string, unknown>;
  ts: string;
}

interface Session {
  id: string;
  agent_type: string;
  status: string;
  output: Record<string, unknown> | null;
  started_at: string;
  ended_at: string | null;
}

export default function AgentsPage() {
  const { getToken } = useAuth();
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];
  const { data: projectsData } = useProjects(firstOrg?.id ?? null);
  const firstProject = projectsData?.projects?.[0];

  const [agentType, setAgentType] = useState<AgentType>("repo");
  const [topic, setTopic] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [, setActiveSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [sessionResult, setSessionResult] = useState<Session | null>(null);
  const [pastSessions, setPastSessions] = useState<Session[]>([]);

  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const getClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient(() => Promise.resolve(token));
  }, [getToken]);

  const loadSessions = useCallback(async () => {
    if (!firstProject?.id) return;
    const client = await getClient();
    const data = await client.listAgentSessions(firstProject.id);
    setPastSessions(data.sessions ?? []);
  }, [firstProject?.id, getClient]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const pollEvents = useCallback(async (sessionId: string) => {
    const client = await getClient();
    const poll = setInterval(async () => {
      try {
        const data = await client.getAgentSessionEvents(sessionId);
        setEvents(data.events ?? []);

        const sessData = await client.getAgentSession(sessionId);
        if (sessData.status !== "running") {
          setSessionResult(sessData);
          setIsRunning(false);
          clearInterval(poll);
          loadSessions();
        }
      } catch {
        clearInterval(poll);
      }
    }, 1000);

    return () => clearInterval(poll);
  }, [getClient, loadSessions]);

  const handleRun = async () => {
    if (!firstProject?.id || isRunning) return;
    setIsRunning(true);
    setEvents([]);
    setSessionResult(null);

    const input: Record<string, string> = {};
    if (agentType === "doc") input.topic = topic || "the codebase";
    if (agentType === "repo") input.repo_path = "";

    try {
      const client = await getClient();
      const result = await client.runAgent({
        project_id: firstProject.id,
        agent_type: agentType,
        input,
      });
      setActiveSessionId(result.session_id);
      pollEvents(result.session_id);
    } catch (err) {
      setIsRunning(false);
      setEvents((prev) => [...prev, {
        id: null, kind: "error",
        payload: { message: String(err) },
        ts: new Date().toISOString(),
      }]);
    }
  };

  const formatTime = (ts: string) => {
    return new Date(ts).toLocaleTimeString();
  };

  return (
    <div className="container px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            Autonomous AI agents that analyze, document, and learn from your codebase.
          </p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left: Agent config */}
        <div className="space-y-4 lg:col-span-1">
          <div className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold">Agent Type</h2>
            <div className="space-y-2">
              {(Object.entries(AGENT_INFO) as [AgentType, typeof AGENT_INFO[AgentType]][]).map(
                ([key, info]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setAgentType(key)}
                    className={`flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                      agentType === key
                        ? "border-primary bg-primary/5"
                        : "hover:bg-accent"
                    }`}
                  >
                    <info.icon className="h-4 w-4 shrink-0" />
                    <div>
                      <div className="font-medium">{info.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {info.description}
                      </div>
                    </div>
                  </button>
                ),
              )}
            </div>

            {agentType === "doc" && (
              <div className="mt-4">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Topic
                </label>
                <Input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. authentication system"
                  disabled={isRunning}
                />
              </div>
            )}

            <Button
              className="mt-4 w-full"
              onClick={handleRun}
              disabled={isRunning || !firstProject}
            >
              {isRunning ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {isRunning ? "Running..." : "Run Agent"}
            </Button>
          </div>

          {/* Past sessions */}
          <div className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold">Recent Runs</h2>
            {pastSessions.length === 0 && (
              <p className="text-xs text-muted-foreground">No runs yet.</p>
            )}
            <div className="space-y-1">
              {pastSessions.slice(0, 10).map((s) => {
                const info = AGENT_INFO[s.agent_type as AgentType];
                const Icon = info?.icon ?? Bot;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setActiveSessionId(s.id);
                      setSessionResult(s);
                    }}
                    className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-xs hover:bg-accent"
                  >
                    <Icon className="h-3 w-3 shrink-0" />
                    <span className="flex-1 truncate">{info?.label ?? s.agent_type}</span>
                    {s.status === "completed" ? (
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                    ) : s.status === "failed" ? (
                      <XCircle className="h-3 w-3 text-red-500" />
                    ) : (
                      <Clock className="h-3 w-3 text-yellow-500" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Event log + results */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border">
            <div className="border-b px-4 py-3">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                <span className="font-semibold">
                  {AGENT_INFO[agentType].label}
                </span>
                {isRunning && (
                  <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Running
                  </span>
                )}
                {sessionResult?.status === "completed" && (
                  <span className="ml-auto flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle2 className="h-3 w-3" />
                    Completed
                  </span>
                )}
                {sessionResult?.status === "failed" && (
                  <span className="ml-auto flex items-center gap-1 text-xs text-red-600">
                    <XCircle className="h-3 w-3" />
                    Failed
                  </span>
                )}
              </div>
            </div>

            <div className="max-h-[500px] overflow-y-auto p-4">
              {events.length === 0 && !isRunning && !sessionResult && (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  <Bot className="mx-auto mb-3 h-8 w-8" />
                  Configure and run an agent to see its progress here.
                </div>
              )}

              {events.map((evt, i) => (
                <div key={i} className="mb-2 flex gap-2 text-sm">
                  <span className="mt-0.5 shrink-0 text-xs text-muted-foreground">
                    {formatTime(evt.ts)}
                  </span>
                  {evt.kind === "step" && (
                    <span className="text-foreground">
                      {String(evt.payload?.message ?? "")}
                    </span>
                  )}
                  {evt.kind === "tool_call" && (
                    <span className="text-blue-600 dark:text-blue-400">
                      <span className="font-medium">Tool:</span>{" "}
                      {String(evt.payload?.tool ?? "")}
                      {evt.payload?.fact
                        ? ` — "${String(evt.payload.fact).slice(0, 60)}..."`
                        : ""}
                    </span>
                  )}
                  {evt.kind === "error" && (
                    <span className="text-red-600 dark:text-red-400">
                      Error: {String(evt.payload?.message ?? "")}
                    </span>
                  )}
                </div>
              ))}

              {isRunning && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Processing...
                </div>
              )}

              <div ref={eventsEndRef} />
            </div>

            {/* Results */}
            {sessionResult?.output && (
              <div className="border-t p-4">
                <h3 className="mb-2 text-sm font-semibold">Results</h3>
                <div className="max-h-80 overflow-y-auto rounded bg-muted/50 p-3">
                  {sessionResult.agent_type === "repo" && (
                    <RepoResult output={sessionResult.output} />
                  )}
                  {sessionResult.agent_type === "doc" && (
                    <DocResult output={sessionResult.output} />
                  )}
                  {sessionResult.agent_type === "memory" && (
                    <MemoryResult output={sessionResult.output} />
                  )}
                  {sessionResult.agent_type === "architecture" && (
                    <ArchResult output={sessionResult.output} />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function RepoResult({ output: o }: { output: Record<string, unknown> }) {
  const patterns = Array.isArray(o.patterns) ? o.patterns as string[] : null;
  return (
    <div className="space-y-2 text-sm">
      <div className="flex gap-4">
        <span className="text-muted-foreground">Files found:</span>
        <span className="font-medium">{String(o.files_found ?? "?")}</span>
      </div>
      {patterns && (
        <div>
          <span className="text-muted-foreground">Patterns analyzed:</span>
          <ul className="mt-1 list-inside list-disc">
            {patterns.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2 whitespace-pre-wrap rounded bg-background p-2 text-xs">
        {String(o.summary ?? "")}
      </div>
    </div>
  );
}

function DocResult({ output: o }: { output: Record<string, unknown> }) {
  const sources = Array.isArray(o.sources_consulted) ? o.sources_consulted as string[] : null;
  return (
    <div className="space-y-2 text-sm">
      {sources && (
        <div>
          <span className="text-muted-foreground">Sources consulted:</span>
          <ul className="mt-1 list-inside list-disc text-xs">
            {sources.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2 whitespace-pre-wrap rounded bg-background p-2 text-xs">
        {String(o.documentation ?? "")}
      </div>
    </div>
  );
}

function MemoryResult({ output: o }: { output: Record<string, unknown> }) {
  const facts = Array.isArray(o.new_facts) ? o.new_facts as string[] : null;
  return (
    <div className="space-y-2 text-sm">
      <div className="flex gap-4">
        <span className="text-muted-foreground">Facts extracted:</span>
        <span className="font-medium">{String(o.facts_extracted ?? "?")}</span>
      </div>
      <div className="flex gap-4">
        <span className="text-muted-foreground">Facts stored:</span>
        <span className="font-medium">{String(o.facts_stored ?? "?")}</span>
      </div>
      {facts && (
        <div>
          <span className="text-muted-foreground">New facts:</span>
          <ul className="mt-1 list-inside list-disc text-xs">
            {facts.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ArchResult({ output: o }: { output: Record<string, unknown> }) {
  const areas = Array.isArray(o.areas_analyzed) ? o.areas_analyzed as string[] : null;
  return (
    <div className="space-y-2 text-sm">
      <div className="flex gap-4">
        <span className="text-muted-foreground">Components:</span>
        <span className="font-medium">{String(o.components_identified ?? "?")}</span>
      </div>
      {areas && (
        <div>
          <span className="text-muted-foreground">Areas:</span>
          <ul className="mt-1 list-inside list-disc">
            {areas.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2 whitespace-pre-wrap rounded bg-background p-2 text-xs">
        {String(o.architecture ?? "")}
      </div>
    </div>
  );
}
