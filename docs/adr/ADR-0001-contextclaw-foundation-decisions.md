# ADR-0001: ContextClaw Foundation Decisions

**Status:** Accepted  
**Date:** 2026-06-03  
**Author:** Founding Team  
**Deciders:** Founding Team

---

## Context

ContextClaw is a greenfield SaaS platform. The founding team needs to align on critical technical and product decisions before building.

## Decisions

### 1. Monorepo with Turborepo + pnpm

**Decision:** Use a single Turborepo monorepo with pnpm workspaces.

**Rationale:**
- Single source of truth for shared types, schemas, and utilities
- Unified CI/CD with dependency-aware caching
- Easier refactoring across service boundaries
- pnpm provides strict dependency isolation

**Consequence:** All services, packages, apps, and extensions live in one repo. Teams must respect package boundaries and avoid tight coupling.

### 2. MVP: End-to-End Thin Slice

**Decision:** Build the full vertical (GitHub → index → hybrid search → streaming chat with citations → minimal web UI) before adding breadth.

**Rationale:**
- Validates the core value proposition fastest
- Allows internal dogfood by Week 8
- De-risks the RAG pipeline and retrieval quality
- Breadth (Slack, Jira, more surfaces) comes after core is proven

**Consequence:** We ship nothing that doesn't contribute to the first end-to-end query flow. Feature-cut aggressively until we have a working thin slice.

### 3. Clerk for MVP, Auth.js Migration Planned (Y1)

**Decision:** Use Clerk for authentication in MVP; abstract behind an internal `auth-service` wrapper.

**Rationale:**
- Fastest path to launch (pre-built UI components, JWT, org management)
- Wrapping behind our own service means Clerk-specific logic is contained
- Auth.js / custom IdP migration planned when enterprise SSO/SAML demand materializes

**Consequence:** Small migration risk in Y1. Abstract the `auth-service` contract tightly so swap is a behind-the-scenes refactor.

### 4. Self-Host-Ready from Day 1, SaaS First

**Decision:** Design for self-hostability from Day 1, but ship SaaS first.

**Rationale:**
- Self-hostability is a top enterprise buying criteria (data residency, compliance)
- Avoid proprietary managed-only services in hot paths
- Helm charts and Docker Compose maintained alongside SaaS codebase
- Cloud-only services (Aurora, MSK) abstracted behind interfaces with OSS substitutes (Patroni, Kafka-on-K8s)
- SaaS-first for revenue velocity; on-prem sold when a $500K+ deal requires it

**Consequence:** Slightly more abstraction work upfront, but avoids a painful "rewrite for enterprise" phase.

### 5. LLM Router Abstraction, 2 Providers at MVP

**Decision:** Ship the Model Router abstraction on Day 1; populate it with OpenAI + DeepSeek at MVP; add Gemini and MiniMax post-beta.

**Rationale:**
- Router abstraction prevents LLM provider lock-in from Day 1
- OpenAI for high quality (GPT-4o); DeepSeek for cost efficiency (V3)
- Adding providers is a config change + eval pass, not an architectural change
- Eval harness (Recall@10, MRR) running from W6 ensures we measure quality per provider

**Consequence:** Slightly more upfront design for the Model Router interface, but avoids single-provider concentration.

---

## Status

These five decisions are locked for the duration of the MVP phase (Months 0–4). Revisit each at the end of Month 4 with production data.

## References

- [Product Blueprint §16](TODO: link to blueprint)
- [System Architecture §5](TODO: link to architecture)
