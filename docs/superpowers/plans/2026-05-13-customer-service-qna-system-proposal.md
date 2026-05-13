# Customer Service Q&A Knowledge System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Node.js based customer service knowledge operation system that imports existing documents, retrieves reliable candidate answers, captures agent feedback, and turns reviewed feedback into versioned reusable knowledge.

**Architecture:** Use a dedicated backend service as the system of record, with Skill or chat entry points calling HTTPS APIs only. Start with PostgreSQL + pgvector for strong consistency, simple operations, full-text retrieval, and vector search in one database; keep repository interfaces for later migration to Qdrant, Milvus, Elasticsearch, Redis, and message queues.

**Tech Stack:** Node.js, TypeScript, NestJS, Prisma, PostgreSQL 16, pgvector, BullMQ or database-backed jobs, React, Ant Design, Docker Compose, object storage compatible with S3.

---

## 1. Executive Decision

This project should be positioned as a **customer service knowledge operation system**, not a simple FAQ page and not a generic chatbot.

The final proposal is:

```text
Customer Service Workspace / Skill / IM Bot / Browser Extension
        |
        | HTTPS API, JWT or API Token
        v
Node.js Backend, NestJS
        |
        +-- Auth, RBAC, users, roles
        +-- Knowledge import, parsing, versioning, review
        +-- Search orchestration: exact match + full-text + vector + rerank
        +-- Feedback loop: select, edit, reject, no-answer
        +-- Audit logs, data quality jobs, operational reports
        |
        v
PostgreSQL + pgvector, MVP system of record
        |
        +-- Structured business data
        +-- Full-text indexes
        +-- Vector indexes
        +-- Rebuildable derived embeddings
```

Skill must not contain the full product. A Skill should only collect the user question, call backend APIs, display candidate answers, and submit the final selected or edited answer. Authentication, authorization, persistence, review, audit, data consistency, and retrieval orchestration belong in the backend.

## 2. Inputs Reviewed

Source documents:

- `my/需求.md`
- `my/chatGPT.md`
- `my/claude.md`
- `my/deepseek.md`
- `my/zai.md`

The four model outputs agree on the core direction:

- The system is RAG + knowledge management + feedback loop.
- Existing files need import, parse, chunk, embedding, search, and traceable source records.
- Structured business data should live in a relational database.
- MongoDB is not the first choice for this domain.
- Skill should call backend APIs instead of becoming the backend.
- Customer edits should not directly pollute production knowledge.
- A Node.js backend with admin/user management is necessary.
- Existing open-source RAG products are useful for POC and reference, but customer-service-specific workflow still needs custom business logic.

## 3. Reasonableness Analysis

### 3.1 Correct Points

The strongest shared conclusion is the backend boundary: **complete backend system + thin Skill/API entry**. This is correct because the domain requires long-lived data, permissions, workflows, audit, and repeatable operations.

The second correct conclusion is relational-first storage. Users, roles, knowledge lifecycle, review status, document source, feedback, version history, and audit logs are strongly related. PostgreSQL gives constraints, transactions, JSONB where needed, full-text search, backups, migrations, and mature operations.

The third correct conclusion is feedback as first-class data. The system improves only if every search, selection, edit, rejection, and no-answer event is recorded and reviewed.

### 3.2 Points That Need Adjustment

Several analyses suggest PostgreSQL + Qdrant or PostgreSQL + separate vector database as the default. This is technically valid, but not the best MVP default. With a separate vector database, every insert, update, disable, review, rollback, and delete creates cross-store consistency work. For an internal customer service knowledge system, this complexity should be delayed until there is measurable scale pressure.

Some analyses recommend deep secondary development on Flowise, AnythingLLM, Dify, or similar products. These are valuable for POC, but the production system should not be locked into a generic chat product's data model. The required workflow is not only "chat with documents"; it is "operate reviewed, versioned, auditable customer service knowledge."

Some analyses mention LLM-generated answers. This should be optional and controlled. The MVP should prioritize returning source-backed candidate answers. LLM rewriting or synthesis can be added later, but every generated answer must show sources and should not become approved knowledge without review.

## 4. Final Technical Choices

### 4.1 Database

Use **PostgreSQL + pgvector** for MVP.

Reasons:

- One transaction boundary for business data.
- Lower operational complexity.
- Easier backup, restore, migration, and audit.
- SQL can combine tenant, permission, status, review, full-text, and vector conditions.
- Vector data is derived and rebuildable, so it can be moved later.

Do not use MongoDB as the primary database. The domain needs constraints, transactions, relational queries, lifecycle state, and auditability more than flexible document storage.

Introduce Qdrant, Milvus, or Elasticsearch only when one of these is true:

- Knowledge chunks reach the million-level and pgvector latency is unacceptable.
- Query concurrency requires independent scaling of retrieval infrastructure.
- Search needs specialized vector payload filtering or distributed indexing.
- Full-text ranking needs features PostgreSQL cannot satisfy.

### 4.2 Backend Framework

Use **NestJS + Prisma**.

Reasons:

- Node.js and TypeScript match the requirement.
- NestJS gives modules, dependency injection, guards, interceptors, validation pipes, and a clean boundary for enterprise backend work.
- Prisma provides schema migrations and strong typing.
- Raw SQL can be used for pgvector and specialized ranking while Prisma manages normal relational access.

### 4.3 Frontend

Use **React + Ant Design** for admin and customer service workbench.

Primary views:

- Login and account management.
- Knowledge list with filters, status, tags, versions, source.
- Document upload and parsing status.
- Search workbench for customer service.
- Review queue for edited or extracted knowledge.
- Audit and quality reports.

### 4.4 Open Source Strategy

Use open-source projects for POC and reference, not as the default production foundation.

Recommended POC references:

- FastGPT: close to knowledge base and workflow concepts, but check license constraints before commercial or SaaS use.
- AnythingLLM: MIT license, mature document and local RAG experience, useful to test general document question answering.
- Flowise: useful for visual RAG prototype, but treat public exposure and plugin/node execution as a security risk.
- Dify: mature workflow/RAG platform, but Python-heavy backend and license constraints make it less aligned with a Node.js-first custom backend.

The production route should be custom business system + borrowed lessons from these products.

## 5. Domain Model

Core principles:

- PostgreSQL is the source of truth.
- Embeddings are derived indexes and must be rebuildable.
- Knowledge versions are immutable.
- Publishing switches the current version pointer.
- Agent edits enter review by default.
- Disable and archive are soft-state transitions, not physical deletion.
- Every important operation writes audit logs.

Core tables:

```text
users
roles
user_roles

knowledge_items
  id
  tenant_id
  type                  # faq, document_chunk, answer_template
  status                # draft, pending_review, active, disabled, archived
  category_id
  current_version_id
  created_by
  created_at
  updated_at

knowledge_versions
  id
  knowledge_item_id
  version_no
  question
  answer
  content
  source_type           # manual, file, feedback, api, llm_extract
  review_status         # pending, approved, rejected
  reviewed_by
  reviewed_at
  created_by
  created_at

documents
  id
  tenant_id
  filename
  file_type
  storage_key
  checksum
  parse_status          # uploaded, parsing, parsed, failed
  parse_error
  uploaded_by
  created_at

document_chunks
  id
  document_id
  knowledge_item_id
  chunk_index
  content
  token_count
  metadata

embeddings
  id
  knowledge_item_id
  knowledge_version_id
  vector
  model
  dimension
  status                # pending, ready, failed, stale
  created_at

search_sessions
  id
  tenant_id
  user_id
  query
  normalized_query
  result_count
  confidence
  selected_result_id
  created_at

feedback_records
  id
  search_session_id
  user_id
  action                # selected, edited, rejected, no_answer
  selected_item_id
  edited_question
  edited_answer
  generated_item_id
  created_at

outbox_events
  id
  event_type
  payload
  status                # pending, processing, done, failed
  retry_count
  next_retry_at
  created_at

audit_logs
  id
  actor_id
  action
  resource_type
  resource_id
  before
  after
  created_at
```

## 6. Retrieval Flow

### 6.1 Import Flow

```text
Upload file
  -> Validate file type, size, MIME, extension
  -> Calculate checksum and detect duplicates
  -> Store file in object storage
  -> Create documents row
  -> Create parse job through outbox_events
  -> Parse txt, md, docx, xlsx, csv
  -> Excel or CSV with question/answer columns becomes FAQ candidates
  -> Long text becomes document chunks
  -> Create knowledge_items and knowledge_versions as pending or active according to import policy
  -> Create embedding jobs
  -> Embedding jobs write embeddings.status=ready
```

Suggested chunking:

- FAQ: embed normalized question; optionally also embed answer.
- Document chunks: 300 to 800 Chinese characters, 50 to 100 character overlap.
- Excel or CSV: support column mapping when headers are not recognized.
- LLM extraction: allowed only as pending review.

### 6.2 Search Flow

```text
Agent asks a question
  -> Authenticate request
  -> Apply tenant and permission filters
  -> Normalize text
  -> Exact FAQ candidate match
  -> PostgreSQL full-text or trigram recall
  -> pgvector semantic recall
  -> Merge and deduplicate candidates
  -> Apply status, visibility, and ready embedding filters
  -> Optional rerank
  -> Calculate confidence
  -> Return one answer or candidate list
  -> Write search_sessions
```

Confidence behavior:

- High confidence: return recommended answer plus candidates.
- Medium confidence: return multiple candidates and require agent selection.
- Low confidence: return no confident answer, allow agent to create or edit a proposed answer.

### 6.3 Feedback Flow

```text
Agent selects existing answer
  -> Write feedback_records.action=selected
  -> Update usage metrics
  -> Do not change knowledge content

Agent edits or creates answer
  -> Write feedback_records.action=edited
  -> Create pending_review knowledge version
  -> Reviewer approves or rejects
  -> Approved version becomes active and triggers embedding refresh

Agent rejects all answers or marks no answer
  -> Write feedback_records.action=rejected or no_answer
  -> Add to knowledge gap report
```

## 7. API Proposal

Customer service and Skill APIs:

```text
POST /api/v1/qna/search
GET  /api/v1/qna/search-sessions/:id
POST /api/v1/qna/search-sessions/:id/select
POST /api/v1/qna/search-sessions/:id/edit
POST /api/v1/qna/search-sessions/:id/reject
```

Example response:

```json
{
  "sessionId": "s_123",
  "mode": "candidates",
  "confidence": 0.78,
  "results": [
    {
      "id": "k_1",
      "question": "退款多久到账？",
      "answer": "退款通常 1-3 个工作日到账，具体以支付渠道为准。",
      "score": 0.91,
      "source": {
        "type": "faq",
        "documentName": "售后FAQ.xlsx",
        "versionNo": 3
      }
    }
  ]
}
```

Admin APIs:

```text
POST   /api/v1/documents
GET    /api/v1/documents
GET    /api/v1/documents/:id

GET    /api/v1/knowledge
POST   /api/v1/knowledge
GET    /api/v1/knowledge/:id
PATCH  /api/v1/knowledge/:id
POST   /api/v1/knowledge/:id/disable
POST   /api/v1/knowledge/:id/archive

GET    /api/v1/reviews
POST   /api/v1/reviews/:id/approve
POST   /api/v1/reviews/:id/reject

GET    /api/v1/users
POST   /api/v1/users
PATCH  /api/v1/users/:id

GET    /api/v1/audit-logs
GET    /api/v1/reports/knowledge-gaps
```

## 8. High Availability, Scalability, Integrity, Consistency

### 8.1 High Availability

- API service is stateless and can run multiple instances behind a load balancer.
- PostgreSQL uses managed HA or primary-replica deployment with tested backup and restore.
- Uploaded files are stored in object storage; database stores metadata only.
- Parsing, embedding, and reindexing run in workers and can retry safely.
- External model calls have timeouts, retry limits, circuit breakers, and graceful degradation.
- Search still works through full-text retrieval when embedding generation fails.

### 8.2 Scalability

- `VectorStore` interface isolates pgvector, Qdrant, and Milvus.
- `EmbeddingProvider` interface isolates OpenAI-compatible APIs, Azure OpenAI, domestic providers, and local models.
- `DocumentParser` interface supports new file types.
- Retrieval pipeline supports exact match, full-text, vector, rerank, and business weights.
- `tenant_id` is included in core tables from the beginning, even if MVP has one tenant.
- Read-heavy reporting can later move to materialized views or a warehouse.

### 8.3 Data Integrity

- Foreign keys protect core relationships.
- Enum or check constraints protect lifecycle states.
- Unique constraints protect duplicate users, roles, and imported checksums.
- Knowledge versions are immutable once approved.
- Current active version is switched through a transaction.
- All review, disable, archive, and rollback actions write audit logs.

### 8.4 Data Consistency

- Knowledge write, review, publish, disable, and archive operations use database transactions.
- Embedding generation is eventually consistent and driven by `outbox_events`.
- Queries only return `active` knowledge with visible scope and non-stale indexes.
- Failed embedding jobs remain visible to operators and can be retried.
- A scheduled consistency checker verifies active knowledge has ready embeddings and stale embeddings are excluded.

## 9. Security and Governance

- All APIs require authentication.
- Skill uses API Token or OAuth/JWT with least-privilege scopes.
- RBAC roles: administrator, knowledge manager, customer service agent, auditor.
- File upload restricts type, size, MIME, extension, and parsing sandbox.
- Sensitive configuration lives in environment variables or secret manager.
- Rate limits protect search and embedding cost.
- Audit logs are append-only from the application perspective.
- PII masking should be added if historical service documents contain customer data.

## 10. Implementation Tasks

### Task 1: Project Foundation

**Files:**

- Create: `apps/api`
- Create: `apps/web`
- Create: `packages/qna-core`
- Create: `packages/shared`
- Create: `prisma/schema.prisma`
- Create: `docker/docker-compose.yml`

- [ ] Initialize a pnpm workspace with NestJS API, React web, shared packages, PostgreSQL, and pgvector.
- [ ] Add lint, format, typecheck, test, and migration commands.
- [ ] Add Docker Compose for PostgreSQL with pgvector enabled.
- [ ] Add environment templates for API, database, object storage, and model provider.

### Task 2: Auth and RBAC

**Files:**

- Modify: `apps/api/src/auth`
- Modify: `apps/api/src/users`
- Modify: `packages/shared`
- Modify: `prisma/schema.prisma`

- [ ] Implement users, roles, user_roles, password hashing, login, JWT, refresh token, and role guards.
- [ ] Add tests for login, forbidden access, disabled user, and role-gated admin endpoints.

### Task 3: Knowledge and Versioning

**Files:**

- Modify: `apps/api/src/knowledge`
- Modify: `packages/qna-core/src/knowledge`
- Modify: `prisma/schema.prisma`

- [ ] Implement knowledge_items and knowledge_versions.
- [ ] Enforce immutable approved versions.
- [ ] Implement draft, pending_review, active, disabled, archived transitions.
- [ ] Add audit logs for create, approve, disable, archive, and rollback.

### Task 4: Document Import Pipeline

**Files:**

- Modify: `apps/api/src/documents`
- Modify: `apps/api/src/ingestion`
- Modify: `packages/qna-core/src/parsers`
- Modify: `prisma/schema.prisma`

- [ ] Implement upload validation and checksum duplicate detection.
- [ ] Parse txt, md, docx, xlsx, and csv.
- [ ] Convert recognized Excel or CSV question/answer columns into FAQ candidates.
- [ ] Convert long documents into chunks with source metadata.

### Task 5: Embedding and Index Jobs

**Files:**

- Modify: `apps/api/src/jobs`
- Modify: `packages/qna-core/src/embeddings`
- Modify: `packages/qna-core/src/vector-store`
- Modify: `prisma/schema.prisma`

- [ ] Implement outbox_events for embedding creation and refresh.
- [ ] Implement pgvector storage behind `VectorStore`.
- [ ] Add retry, failed, ready, and stale statuses.
- [ ] Add a rebuild command for embeddings from approved knowledge versions.

### Task 6: Search and Feedback

**Files:**

- Modify: `apps/api/src/qna`
- Modify: `packages/qna-core/src/search`
- Modify: `packages/qna-core/src/feedback`
- Modify: `prisma/schema.prisma`

- [ ] Implement exact, full-text, and vector recall.
- [ ] Merge, deduplicate, rank, and return candidates with source information.
- [ ] Implement select, edit, reject, and no_answer feedback actions.
- [ ] Convert edited answers into pending review knowledge versions.

### Task 7: Admin and Agent Web UI

**Files:**

- Modify: `apps/web/src`

- [ ] Implement login.
- [ ] Implement customer service search workbench.
- [ ] Implement knowledge list, detail, status change, and version view.
- [ ] Implement document upload status view.
- [ ] Implement review queue.
- [ ] Implement knowledge gap report.

### Task 8: Production Readiness

**Files:**

- Modify: `apps/api/src/common`
- Modify: `apps/api/src/audit`
- Modify: `apps/api/src/reports`
- Modify: `docker`
- Create: `docs/runbooks`

- [ ] Add rate limiting, request IDs, structured logs, health checks, and metrics.
- [ ] Add backup and restore runbook.
- [ ] Add consistency checker for active knowledge and embeddings.
- [ ] Add API Token scopes for Skill integration.
- [ ] Add deployment documentation.

## 11. Phased Delivery

### Phase 0: POC, 1 week

- Deploy FastGPT or AnythingLLM locally.
- Upload real historical customer service documents.
- Test file parsing, answer quality, candidate retrieval, and API shape.
- Document which behavior should be copied and which should be avoided.

### Phase 1: MVP, 2 to 4 weeks

- NestJS + Prisma + PostgreSQL + pgvector.
- Login and basic RBAC.
- Import xlsx, md, docx, txt.
- Search returns Top 5 candidates.
- Agent can select, edit, reject, or mark no answer.
- Edited answers enter review.
- Knowledge manager can approve, disable, and archive.

### Phase 2: Production, 4 to 8 weeks

- Hybrid ranking with exact, full-text, vector, and business weights.
- Worker queue, retries, and job monitoring.
- Audit logs and reports.
- API Token Skill integration.
- Backups, monitoring, rate limits, and operational runbooks.

### Phase 3: Intelligence, after stable production

- Rerank model.
- LLM extraction from documents into pending review FAQ.
- Knowledge gap clustering.
- Multi-tenant permissions.
- Migration from pgvector to Qdrant or Milvus if metrics justify it.

## 12. Acceptance Criteria

MVP acceptance:

- At least three of txt, md, docx, xlsx, csv can be imported.
- Excel or CSV FAQ can become candidate knowledge.
- Customer service query returns Top 5 source-backed candidates.
- Agent can select an answer or edit a new one.
- Edited answer becomes pending review, not active knowledge.
- Disabled knowledge is never returned by search.
- Query, selection, edit, review, disable, and archive actions have logs.
- Embedding failure does not corrupt business data and can be retried.

Production acceptance:

- API can run multiple stateless instances.
- PostgreSQL backup and restore are tested.
- Parsing and embedding jobs are retryable and observable.
- APIs are authenticated, rate-limited, and audited.
- Knowledge versions can be rolled back.
- Search results show source and version.
- Knowledge gap report lists low-confidence and no-answer questions.

## 13. Final Recommendation

The recommended route is:

1. Build a custom Node.js customer service knowledge system.
2. Use PostgreSQL + pgvector for MVP.
3. Keep vector, embedding, parser, and retrieval provider interfaces replaceable.
4. Use FastGPT or AnythingLLM only for POC and design reference.
5. Treat review, versioning, audit, and data consistency as core product features.
6. Let Skill call the backend; do not put backend responsibilities into Skill.
7. Add LLM generation only after source-backed retrieval and review workflow are stable.

This route controls early complexity while keeping a clear path toward high availability, scalability, data integrity, and data consistency.

## 14. Current Reference Checks

Checked on 2026-05-13:

- FastGPT license includes Apache 2.0 based terms with additional commercial conditions for similar multi-tenant SaaS and logo/copyright handling: <https://github.com/labring/FastGPT/blob/main/LICENSE>
- AnythingLLM repository describes an all-in-one document chat, agents, multi-user, vector database product and shows MIT license: <https://github.com/Mintplex-Labs/anything-llm>
- Flowise license is Apache 2.0 for most code with enterprise/commercial exceptions: <https://github.com/FlowiseAI/Flowise/blob/main/LICENSE.md>
- Dify repository states its license is based on Apache 2.0 with additional conditions: <https://github.com/langgenius/dify>

