import { z } from "zod";

// ── IDs ───────────────────────────────────────────────────────────

export const uuidSchema = z.string().uuid();

// ── Organizations ─────────────────────────────────────────────────

export const planTierSchema = z.enum([
  "free",
  "starter",
  "pro",
  "enterprise",
]);

export const organizationSchema = z.object({
  id: uuidSchema,
  slug: z.string().min(2).max(64),
  name: z.string().min(1).max(256),
  plan: planTierSchema.default("free"),
  settings: z.record(z.unknown()).default({}),
  createdAt: z.date(),
});

// ── Projects ──────────────────────────────────────────────────────

export const projectSchema = z.object({
  id: uuidSchema,
  orgId: uuidSchema,
  slug: z.string().min(2).max(64),
  name: z.string().min(1).max(256),
  description: z.string().optional(),
  createdAt: z.date(),
});

// ── Repositories ──────────────────────────────────────────────────

export const repoProviderSchema = z.enum(["github", "gitlab", "bitbucket"]);
export const repoStatusSchema = z.enum([
  "pending",
  "indexing",
  "active",
  "error",
  "disabled",
]);

export const repositorySchema = z.object({
  id: uuidSchema,
  projectId: uuidSchema,
  provider: repoProviderSchema,
  externalId: z.string(),
  fullName: z.string(),
  defaultBranch: z.string().default("main"),
  lastIndexedSha: z.string().optional(),
  lastIndexedAt: z.date().optional(),
  status: repoStatusSchema.default("pending"),
});

// ── Chat ──────────────────────────────────────────────────────────

export const messageRoleSchema = z.enum([
  "user",
  "assistant",
  "system",
  "tool",
]);

export const citationSchema = z.object({
  chunkId: uuidSchema,
  score: z.number().min(0).max(1),
  sourceType: z.string(),
  path: z.string(),
  snippet: z.string(),
});

export const messageSchema = z.object({
  id: uuidSchema,
  conversationId: uuidSchema,
  role: messageRoleSchema,
  content: z.string(),
  model: z.string().optional(),
  tokensIn: z.number().int().optional(),
  tokensOut: z.number().int().optional(),
  costCents: z.number().optional(),
  citations: z.array(citationSchema).default([]),
  createdAt: z.date(),
});

export const conversationSchema = z.object({
  id: uuidSchema,
  projectId: uuidSchema,
  userId: uuidSchema.optional(),
  title: z.string().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// ── Search ────────────────────────────────────────────────────────

export const searchRequestSchema = z.object({
  projectId: uuidSchema,
  query: z.string().min(1),
  k: z.number().int().min(1).max(100).default(10),
  filters: z.record(z.unknown()).optional(),
});

export const searchResultSchema = z.object({
  chunkId: uuidSchema,
  score: z.number(),
  source: z.record(z.unknown()),
  snippet: z.string(),
});

export const searchResponseSchema = z.object({
  results: z.array(searchResultSchema),
  tookMs: z.number().int(),
});

// ── Memory ────────────────────────────────────────────────────────

export const memoryFactSchema = z.object({
  id: uuidSchema,
  projectId: uuidSchema,
  scope: z.enum(["org", "project", "repo", "user"]),
  statement: z.string().min(1),
  source: z.enum(["user", "agent", "auto"]),
  confidence: z.number().min(0).max(1).default(1),
  assertedBy: uuidSchema.optional(),
  createdAt: z.date(),
});

// ── API Types ─────────────────────────────────────────────────────

export type Organization = z.infer<typeof organizationSchema>;
export type Project = z.infer<typeof projectSchema>;
export type Repository = z.infer<typeof repositorySchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type Message = z.infer<typeof messageSchema>;
export type SearchResult = z.infer<typeof searchResultSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;
export type MemoryFact = z.infer<typeof memoryFactSchema>;
