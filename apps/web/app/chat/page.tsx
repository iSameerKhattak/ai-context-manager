"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useMyOrgs, useProjects, useCreateConversation, useConversation, useSendMessage } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Send, Plus, MessageSquare, FileText, ChevronDown } from "lucide-react";

interface Citation {
  chunk_id: string;
  score: number;
  source_type: string;
  path: string;
  snippet: string;
}

interface Message {
  id: string;
  role: string;
  content: string;
  citations?: Citation[];
}

export default function ChatPage() {
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [showCitations, setShowCitations] = useState<string | null>(null);

  const { data: projectsData } = useProjects(firstOrg?.id ?? null);
  const firstProject = projectsData?.projects?.[0];

  const { data: conversation } = useConversation(activeConversationId);
  const createConv = useCreateConversation();
  const sendMsg = useSendMessage(activeConversationId);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages]);

  const handleNewChat = useCallback(() => {
    if (!firstProject?.id) return;
    createConv.mutate(firstProject.id, {
      onSuccess: (conv) => setActiveConversationId(conv.id),
    });
  }, [firstProject?.id, createConv]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConversationId) return;
    const msg = input;
    setInput("");
    sendMsg.mutate({ content: msg });
  }, [input, activeConversationId, sendMsg]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const messages: Message[] = conversation?.messages ?? [];

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <div className="flex w-64 flex-col border-r bg-muted/30">
        <div className="border-b p-3">
          <Button
            variant="outline"
            className="w-full justify-start gap-2"
            onClick={handleNewChat}
            disabled={createConv.isPending}
          >
            {createConv.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            New Chat
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {activeConversationId && (
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-md bg-accent px-3 py-2 text-left text-sm"
              onClick={() => setActiveConversationId(null)}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate">{conversation?.title ?? "Current Chat"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {!activeConversationId ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="max-w-md text-center">
              <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h2 className="mb-2 text-xl font-semibold">ContextClaw Chat</h2>
              <p className="mb-6 text-sm text-muted-foreground">
                Ask questions about your codebase. ContextClaw searches indexed
                repositories and generates answers with citations.
              </p>
              {firstProject ? (
                <Button onClick={handleNewChat} disabled={createConv.isPending}>
                  {createConv.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Start a Conversation
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Create a project first to start chatting.
                </p>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
              {messages.length === 0 && (
                <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
                  Send a message to start the conversation.
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className="mb-4">
                  <div
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                    </div>
                  </div>

                  {/* Citations */}
                  {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-1 px-1">
                      <button
                        type="button"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                        onClick={() =>
                          setShowCitations(
                            showCitations === msg.id ? null : msg.id,
                          )
                        }
                      >
                        <FileText className="h-3 w-3" />
                        {msg.citations.length} sources
                        <ChevronDown
                          className={`h-3 w-3 transition-transform ${
                            showCitations === msg.id ? "rotate-180" : ""
                          }`}
                        />
                      </button>

                      {showCitations === msg.id && (
                        <div className="mt-1 space-y-1">
                          {msg.citations.map((c, i) => (
                            <div
                              key={i}
                              className="rounded border bg-muted/50 px-2 py-1 text-xs"
                            >
                              <span className="font-medium">{c.path}</span>
                              <span className="ml-2 text-muted-foreground">
                                (score: {c.score.toFixed(2)})
                              </span>
                              <p className="mt-0.5 italic text-muted-foreground">
                                {c.snippet.slice(0, 120)}
                                {c.snippet.length > 120 ? "..." : ""}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {sendMsg.isPending && (
                <div className="flex justify-start">
                  <div className="rounded-lg bg-muted px-4 py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t p-4">
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your codebase..."
                  disabled={sendMsg.isPending}
                  className="flex-1"
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || sendMsg.isPending}
                  size="icon"
                >
                  {sendMsg.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
