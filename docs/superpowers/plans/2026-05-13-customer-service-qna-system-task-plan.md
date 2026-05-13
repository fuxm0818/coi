# Customer Service Q&A Knowledge System Task Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the MVP of the customer service Q&A knowledge system described in `docs/superpowers/plans/2026-05-13-customer-service-qna-system-proposal.md`.

**Architecture:** Build a TypeScript monorepo with a NestJS API, React admin/customer-service workspace, Prisma-managed PostgreSQL schema, and a framework-independent `qna-core` package. PostgreSQL is the source of truth; pgvector embeddings are rebuildable derived indexes; external Skills call API endpoints only.

**Tech Stack:** Node.js, TypeScript, pnpm workspace, NestJS, Prisma, PostgreSQL 16, pgvector, Vitest/Jest, React, Ant Design, Docker Compose.

---

## File Structure

Create this project structure during Task 1:

```text
question-and-answer/
  apps/
    api/
      src/
        app.module.ts
        main.ts
        auth/
        users/
        knowledge/
        documents/
        ingestion/
        qna/
        reviews/
        audit/
        jobs/
        common/
      test/
    web/
      src/
        app/
        api/
        pages/
        components/
        routes/
  packages/
    shared/
      src/
        auth.ts
        errors.ts
        knowledge.ts
        qna.ts
        index.ts
    qna-core/
      src/
        knowledge/
        parsers/
        embeddings/
        vector-store/
        search/
        feedback/
        jobs/
        index.ts
  prisma/
    schema.prisma
    migrations/
  docker/
    docker-compose.yml
  docs/
    runbooks/
```

Responsibilities:

- `apps/api`: HTTP, auth, RBAC, validation, transactions, API responses, job runners.
- `apps/web`: Admin and customer-service user interface.
- `packages/shared`: Shared enums, DTO shapes, error codes, constants.
- `packages/qna-core`: Domain logic that does not depend on NestJS or Express.
- `prisma`: Database schema and migrations.
- `docker`: Local infrastructure.
- `docs/runbooks`: Operational documentation.

## Task 1: Scaffold Monorepo and Local Infrastructure

**Files:**

- Create: `pnpm-workspace.yaml`
- Modify: `package.json`
- Create: `tsconfig.base.json`
- Create: `apps/api/package.json`
- Create: `apps/api/src/main.ts`
- Create: `apps/api/src/app.module.ts`
- Create: `apps/web/package.json`
- Create: `packages/shared/package.json`
- Create: `packages/shared/src/index.ts`
- Create: `packages/qna-core/package.json`
- Create: `packages/qna-core/src/index.ts`
- Create: `docker/docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Write package workspace configuration**

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 2: Update root package scripts**

Set `package.json` scripts to:

```json
{
  "scripts": {
    "dev:api": "pnpm --filter @qa/api dev",
    "dev:web": "pnpm --filter @qa/web dev",
    "build": "pnpm -r build",
    "test": "pnpm -r test",
    "typecheck": "pnpm -r typecheck",
    "lint": "pnpm -r lint",
    "db:migrate": "pnpm --filter @qa/api prisma migrate dev",
    "db:generate": "pnpm --filter @qa/api prisma generate"
  }
}
```

- [ ] **Step 3: Add Docker Compose for PostgreSQL and pgvector**

Create `docker/docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: qa
      POSTGRES_PASSWORD: qa
      POSTGRES_DB: qa
    ports:
      - "5432:5432"
    volumes:
      - qa_postgres:/var/lib/postgresql/data
volumes:
  qa_postgres:
```

- [ ] **Step 4: Verify workspace scripts**

Run:

```bash
pnpm install
pnpm typecheck
```

Expected: dependencies install and typecheck completes for scaffold packages.

- [ ] **Step 5: Commit**

```bash
git add pnpm-workspace.yaml package.json tsconfig.base.json apps packages docker .env.example
git commit -m "chore: scaffold customer qna workspace"
```

## Task 2: Define Shared Domain Contracts

**Files:**

- Create: `packages/shared/src/auth.ts`
- Create: `packages/shared/src/knowledge.ts`
- Create: `packages/shared/src/qna.ts`
- Create: `packages/shared/src/errors.ts`
- Modify: `packages/shared/src/index.ts`
- Test: `packages/shared/src/knowledge.spec.ts`
- Test: `packages/shared/src/qna.spec.ts`

- [ ] **Step 1: Write failing tests for lifecycle values**

Create `packages/shared/src/knowledge.spec.ts`:

```ts
import { KNOWLEDGE_STATUSES, REVIEW_STATUSES, isSearchableKnowledgeStatus } from './knowledge';

describe('knowledge shared contracts', () => {
  it('only active knowledge is searchable', () => {
    expect(isSearchableKnowledgeStatus('active')).toBe(true);
    expect(isSearchableKnowledgeStatus('draft')).toBe(false);
    expect(isSearchableKnowledgeStatus('pending_review')).toBe(false);
    expect(isSearchableKnowledgeStatus('disabled')).toBe(false);
    expect(isSearchableKnowledgeStatus('archived')).toBe(false);
  });

  it('defines stable status lists', () => {
    expect(KNOWLEDGE_STATUSES).toEqual(['draft', 'pending_review', 'active', 'disabled', 'archived']);
    expect(REVIEW_STATUSES).toEqual(['pending', 'approved', 'rejected']);
  });
});
```

- [ ] **Step 2: Write failing tests for Q&A request contracts**

Create `packages/shared/src/qna.spec.ts`:

```ts
import { normalizeSearchQuery } from './qna';

describe('qna shared contracts', () => {
  it('normalizes repeated whitespace and trims query text', () => {
    expect(normalizeSearchQuery('  退款   多久 到账  ')).toBe('退款 多久 到账');
  });
});
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
pnpm --filter @qa/shared test
```

Expected: FAIL because `knowledge.ts` and `qna.ts` are not implemented.

- [ ] **Step 4: Implement shared contracts**

Create `packages/shared/src/knowledge.ts`:

```ts
export const KNOWLEDGE_STATUSES = ['draft', 'pending_review', 'active', 'disabled', 'archived'] as const;
export type KnowledgeStatus = (typeof KNOWLEDGE_STATUSES)[number];

export const REVIEW_STATUSES = ['pending', 'approved', 'rejected'] as const;
export type ReviewStatus = (typeof REVIEW_STATUSES)[number];

export const KNOWLEDGE_TYPES = ['faq', 'document_chunk', 'answer_template'] as const;
export type KnowledgeType = (typeof KNOWLEDGE_TYPES)[number];

export function isSearchableKnowledgeStatus(status: KnowledgeStatus): boolean {
  return status === 'active';
}
```

Create `packages/shared/src/qna.ts`:

```ts
export const FEEDBACK_ACTIONS = ['selected', 'edited', 'rejected', 'no_answer'] as const;
export type FeedbackAction = (typeof FEEDBACK_ACTIONS)[number];

export type SearchMode = 'direct' | 'candidates' | 'no_confident_answer';

export interface QnaSearchResult {
  id: string;
  question: string | null;
  answer: string | null;
  content: string | null;
  score: number;
  source: {
    type: 'faq' | 'document_chunk' | 'answer_template';
    documentName?: string;
    versionNo: number;
  };
}

export function normalizeSearchQuery(query: string): string {
  return query.trim().replace(/\s+/g, ' ');
}
```

Create `packages/shared/src/auth.ts`:

```ts
export const ROLES = ['admin', 'knowledge_manager', 'agent', 'auditor'] as const;
export type RoleCode = (typeof ROLES)[number];
```

Create `packages/shared/src/errors.ts`:

```ts
export class DomainError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}
```

Update `packages/shared/src/index.ts`:

```ts
export * from './auth';
export * from './errors';
export * from './knowledge';
export * from './qna';
```

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/shared test
git add packages/shared
git commit -m "feat: define shared qna domain contracts"
```

Expected: tests pass.

## Task 3: Create Prisma Schema for Source-of-Truth Data

**Files:**

- Create: `prisma/schema.prisma`
- Create: `apps/api/src/prisma/prisma.module.ts`
- Create: `apps/api/src/prisma/prisma.service.ts`
- Test: `apps/api/test/prisma-schema.spec.ts`

- [ ] **Step 1: Write schema verification test**

Create `apps/api/test/prisma-schema.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('Prisma schema', () => {
  const schema = readFileSync(join(process.cwd(), '../../prisma/schema.prisma'), 'utf8');

  it('contains source-of-truth knowledge and audit models', () => {
    expect(schema).toContain('model KnowledgeItem');
    expect(schema).toContain('model KnowledgeVersion');
    expect(schema).toContain('model AuditLog');
    expect(schema).toContain('model OutboxEvent');
  });

  it('stores embeddings as unsupported pgvector columns', () => {
    expect(schema).toContain('vector Unsupported("vector")');
  });
});
```

- [ ] **Step 2: Run test and confirm failure**

```bash
pnpm --filter @qa/api test -- prisma-schema.spec.ts
```

Expected: FAIL because `schema.prisma` is not implemented.

- [ ] **Step 3: Implement Prisma schema**

Create `prisma/schema.prisma` with models:

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id           String    @id @default(uuid())
  email        String    @unique
  passwordHash String
  displayName  String
  disabledAt   DateTime?
  createdAt    DateTime  @default(now())
  updatedAt    DateTime  @updatedAt
  userRoles    UserRole[]
}

model Role {
  id        String     @id @default(uuid())
  code      String     @unique
  name      String
  userRoles UserRole[]
}

model UserRole {
  userId String
  roleId String
  user   User @relation(fields: [userId], references: [id])
  role   Role @relation(fields: [roleId], references: [id])

  @@id([userId, roleId])
}

model KnowledgeItem {
  id               String             @id @default(uuid())
  tenantId         String             @default("default")
  type             String
  status           String
  categoryId       String?
  currentVersionId String?
  createdBy        String
  createdAt        DateTime           @default(now())
  updatedAt        DateTime           @updatedAt
  versions         KnowledgeVersion[]
  chunks           DocumentChunk[]
  embeddings       Embedding[]
}

model KnowledgeVersion {
  id              String   @id @default(uuid())
  knowledgeItemId String
  versionNo       Int
  question        String?
  answer          String?
  content         String?
  sourceType      String
  reviewStatus    String
  reviewedBy      String?
  reviewedAt      DateTime?
  createdBy       String
  createdAt       DateTime @default(now())
  knowledgeItem   KnowledgeItem @relation(fields: [knowledgeItemId], references: [id])
  embeddings      Embedding[]

  @@unique([knowledgeItemId, versionNo])
}

model Document {
  id          String          @id @default(uuid())
  tenantId    String          @default("default")
  filename    String
  fileType    String
  storageKey  String
  checksum    String
  parseStatus String
  parseError  String?
  uploadedBy  String
  createdAt   DateTime        @default(now())
  chunks      DocumentChunk[]

  @@unique([tenantId, checksum])
}

model DocumentChunk {
  id              String        @id @default(uuid())
  documentId      String
  knowledgeItemId String?
  chunkIndex      Int
  content         String
  tokenCount      Int
  metadata        Json
  document        Document      @relation(fields: [documentId], references: [id])
  knowledgeItem   KnowledgeItem? @relation(fields: [knowledgeItemId], references: [id])
}

model Embedding {
  id                 String           @id @default(uuid())
  knowledgeItemId    String
  knowledgeVersionId String
  vector             Unsupported("vector")
  model              String
  dimension          Int
  status             String
  createdAt          DateTime         @default(now())
  knowledgeItem      KnowledgeItem    @relation(fields: [knowledgeItemId], references: [id])
  knowledgeVersion   KnowledgeVersion @relation(fields: [knowledgeVersionId], references: [id])
}

model SearchSession {
  id               String   @id @default(uuid())
  tenantId         String   @default("default")
  userId           String
  query            String
  normalizedQuery  String
  resultCount      Int
  confidence       Float
  selectedResultId String?
  createdAt        DateTime @default(now())
}

model FeedbackRecord {
  id              String   @id @default(uuid())
  searchSessionId String
  userId          String
  action          String
  selectedItemId  String?
  editedQuestion  String?
  editedAnswer    String?
  generatedItemId String?
  createdAt       DateTime @default(now())
}

model OutboxEvent {
  id          String    @id @default(uuid())
  eventType   String
  payload     Json
  status      String
  retryCount  Int       @default(0)
  nextRetryAt DateTime?
  createdAt   DateTime  @default(now())
}

model AuditLog {
  id           String   @id @default(uuid())
  actorId      String
  action       String
  resourceType String
  resourceId   String
  before       Json?
  after        Json?
  createdAt    DateTime @default(now())
}
```

- [ ] **Step 4: Add pgvector migration SQL**

Create first migration with:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX IF NOT EXISTS embeddings_vector_hnsw_idx
ON "Embedding" USING hnsw (vector vector_cosine_ops);
```

- [ ] **Step 5: Run migration and commit**

```bash
pnpm db:generate
pnpm db:migrate
pnpm --filter @qa/api test -- prisma-schema.spec.ts
git add prisma apps/api/src/prisma apps/api/test/prisma-schema.spec.ts
git commit -m "feat: add source of truth database schema"
```

Expected: migration succeeds and schema test passes.

## Task 4: Implement Auth and RBAC

**Files:**

- Create: `apps/api/src/auth/auth.module.ts`
- Create: `apps/api/src/auth/auth.service.ts`
- Create: `apps/api/src/auth/auth.controller.ts`
- Create: `apps/api/src/auth/jwt-auth.guard.ts`
- Create: `apps/api/src/auth/roles.guard.ts`
- Create: `apps/api/src/auth/roles.decorator.ts`
- Create: `apps/api/src/users/users.module.ts`
- Create: `apps/api/src/users/users.service.ts`
- Test: `apps/api/src/auth/auth.service.spec.ts`
- Test: `apps/api/src/auth/roles.guard.spec.ts`

- [ ] **Step 1: Write failing auth service tests**

Create tests that verify:

```ts
describe('AuthService', () => {
  it('rejects disabled users during login', async () => {});
  it('returns access token with role codes for active users', async () => {});
});
```

- [ ] **Step 2: Write failing role guard tests**

Create tests that verify:

```ts
describe('RolesGuard', () => {
  it('allows admin to access admin route', () => {});
  it('blocks agent from admin route', () => {});
});
```

- [ ] **Step 3: Run tests and confirm failure**

```bash
pnpm --filter @qa/api test -- auth
```

Expected: FAIL because AuthService and RolesGuard are not implemented.

- [ ] **Step 4: Implement auth module**

Implement:

- Password hash comparison through `bcrypt`.
- JWT payload shape `{ sub: user.id, email: user.email, roles: string[] }`.
- Disabled user check through `disabledAt`.
- `@Roles('admin')` decorator.
- `JwtAuthGuard` for authenticated APIs.
- `RolesGuard` for role-gated APIs.

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/api test -- auth
git add apps/api/src/auth apps/api/src/users
git commit -m "feat: add auth and role based access control"
```

Expected: auth and guard tests pass.

## Task 5: Implement Knowledge Lifecycle and Audit

**Files:**

- Create: `packages/qna-core/src/knowledge/knowledge-lifecycle.ts`
- Create: `packages/qna-core/src/knowledge/knowledge-lifecycle.spec.ts`
- Create: `apps/api/src/knowledge/knowledge.module.ts`
- Create: `apps/api/src/knowledge/knowledge.service.ts`
- Create: `apps/api/src/knowledge/knowledge.controller.ts`
- Create: `apps/api/src/audit/audit.module.ts`
- Create: `apps/api/src/audit/audit.service.ts`
- Test: `apps/api/src/knowledge/knowledge.service.spec.ts`

- [ ] **Step 1: Write failing lifecycle unit tests**

Create `packages/qna-core/src/knowledge/knowledge-lifecycle.spec.ts`:

```ts
import { assertKnowledgeTransition } from './knowledge-lifecycle';

describe('knowledge lifecycle', () => {
  it('allows pending_review to active', () => {
    expect(() => assertKnowledgeTransition('pending_review', 'active')).not.toThrow();
  });

  it('blocks archived to active', () => {
    expect(() => assertKnowledgeTransition('archived', 'active')).toThrow('Invalid knowledge status transition');
  });
});
```

- [ ] **Step 2: Implement lifecycle guard**

Create `packages/qna-core/src/knowledge/knowledge-lifecycle.ts`:

```ts
import type { KnowledgeStatus } from '@qa/shared';
import { DomainError } from '@qa/shared';

const allowed: Record<KnowledgeStatus, KnowledgeStatus[]> = {
  draft: ['pending_review', 'archived'],
  pending_review: ['active', 'draft', 'archived'],
  active: ['disabled', 'archived'],
  disabled: ['active', 'archived'],
  archived: [],
};

export function assertKnowledgeTransition(from: KnowledgeStatus, to: KnowledgeStatus): void {
  if (!allowed[from].includes(to)) {
    throw new DomainError('KNOWLEDGE_INVALID_TRANSITION', `Invalid knowledge status transition: ${from} -> ${to}`);
  }
}
```

- [ ] **Step 3: Write service tests**

Test these behaviors:

- Creating manual FAQ creates one `KnowledgeItem` and one version.
- Approving a pending version switches `currentVersionId`.
- Disabling active knowledge writes an `AuditLog`.
- Updating approved version content creates a new version instead of editing old row.

- [ ] **Step 4: Implement service and controller**

Implement endpoints:

```text
GET    /api/v1/knowledge
POST   /api/v1/knowledge
GET    /api/v1/knowledge/:id
PATCH  /api/v1/knowledge/:id
POST   /api/v1/knowledge/:id/disable
POST   /api/v1/knowledge/:id/archive
```

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/qna-core test -- knowledge
pnpm --filter @qa/api test -- knowledge
git add packages/qna-core/src/knowledge apps/api/src/knowledge apps/api/src/audit
git commit -m "feat: add versioned knowledge lifecycle"
```

Expected: lifecycle and service tests pass.

## Task 6: Implement Document Import and Parsing

**Files:**

- Create: `packages/qna-core/src/parsers/document-parser.ts`
- Create: `packages/qna-core/src/parsers/text-parser.ts`
- Create: `packages/qna-core/src/parsers/markdown-parser.ts`
- Create: `packages/qna-core/src/parsers/spreadsheet-parser.ts`
- Create: `packages/qna-core/src/parsers/chunker.ts`
- Test: `packages/qna-core/src/parsers/chunker.spec.ts`
- Test: `packages/qna-core/src/parsers/spreadsheet-parser.spec.ts`
- Create: `apps/api/src/documents/documents.module.ts`
- Create: `apps/api/src/documents/documents.service.ts`
- Create: `apps/api/src/documents/documents.controller.ts`

- [ ] **Step 1: Write failing chunker tests**

Create tests that verify:

```ts
describe('chunkText', () => {
  it('splits long Chinese text with overlap', () => {});
  it('keeps short text as one chunk', () => {});
});
```

- [ ] **Step 2: Write failing spreadsheet parser tests**

Use an in-memory worksheet fixture and verify:

```ts
describe('parseSpreadsheetFaqRows', () => {
  it('extracts rows with question and answer columns', () => {});
  it('returns column mapping error when headers are missing', () => {});
});
```

- [ ] **Step 3: Implement parser interfaces**

Create `packages/qna-core/src/parsers/document-parser.ts`:

```ts
export interface ParsedFaqRow {
  question: string;
  answer: string;
  metadata: Record<string, unknown>;
}

export interface ParsedChunk {
  content: string;
  chunkIndex: number;
  tokenCount: number;
  metadata: Record<string, unknown>;
}

export interface DocumentParser {
  supports(fileType: string): boolean;
  parse(input: Buffer, filename: string): Promise<{ faqs: ParsedFaqRow[]; chunks: ParsedChunk[] }>;
}
```

- [ ] **Step 4: Implement upload service**

Implement:

- File type and size validation.
- SHA-256 checksum.
- Duplicate detection by `(tenantId, checksum)`.
- `Document` row with `parseStatus='uploaded'`.
- Outbox event `document.parse.requested`.

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/qna-core test -- parsers
pnpm --filter @qa/api test -- documents
git add packages/qna-core/src/parsers apps/api/src/documents
git commit -m "feat: add document import and parsing pipeline"
```

Expected: parser and document service tests pass.

## Task 7: Implement Outbox Jobs and Embedding Provider

**Files:**

- Create: `packages/qna-core/src/embeddings/embedding-provider.ts`
- Create: `packages/qna-core/src/embeddings/fake-embedding-provider.ts`
- Create: `packages/qna-core/src/vector-store/vector-store.ts`
- Create: `packages/qna-core/src/vector-store/pgvector-store.ts`
- Test: `packages/qna-core/src/embeddings/fake-embedding-provider.spec.ts`
- Create: `apps/api/src/jobs/jobs.module.ts`
- Create: `apps/api/src/jobs/outbox.service.ts`
- Create: `apps/api/src/jobs/embedding-worker.service.ts`
- Test: `apps/api/src/jobs/outbox.service.spec.ts`

- [ ] **Step 1: Write failing embedding provider test**

Verify:

```ts
describe('FakeEmbeddingProvider', () => {
  it('returns deterministic vectors with configured dimension', async () => {});
});
```

- [ ] **Step 2: Implement provider interfaces**

Create `packages/qna-core/src/embeddings/embedding-provider.ts`:

```ts
export interface EmbeddingProvider {
  readonly model: string;
  readonly dimension: number;
  embed(text: string): Promise<number[]>;
}
```

Create `packages/qna-core/src/vector-store/vector-store.ts`:

```ts
export interface VectorSearchFilter {
  tenantId: string;
  status: 'active';
  limit: number;
}

export interface VectorSearchResult {
  knowledgeItemId: string;
  knowledgeVersionId: string;
  score: number;
}

export interface VectorStore {
  upsertEmbedding(input: {
    knowledgeItemId: string;
    knowledgeVersionId: string;
    vector: number[];
    model: string;
    dimension: number;
  }): Promise<void>;
  search(vector: number[], filter: VectorSearchFilter): Promise<VectorSearchResult[]>;
  markStale(knowledgeItemId: string): Promise<void>;
}
```

- [ ] **Step 3: Implement outbox service**

Implement:

- `enqueue(eventType, payload)` creates pending event.
- `claimNext(eventType)` locks one pending event.
- `markDone(id)` and `markFailed(id, nextRetryAt)` update status and retry count.

- [ ] **Step 4: Implement embedding worker**

Worker behavior:

- Claims `embedding.refresh.requested`.
- Loads approved knowledge version.
- Embeds `question + "\n" + answer` for FAQ.
- Writes embedding as `ready`.
- Marks previous embeddings for item as `stale`.
- Marks outbox event done.

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/qna-core test -- embeddings
pnpm --filter @qa/api test -- jobs
git add packages/qna-core/src/embeddings packages/qna-core/src/vector-store apps/api/src/jobs
git commit -m "feat: add outbox embedding jobs"
```

Expected: embedding and outbox tests pass.

## Task 8: Implement Search Pipeline

**Files:**

- Create: `packages/qna-core/src/search/search-pipeline.ts`
- Create: `packages/qna-core/src/search/ranking.ts`
- Test: `packages/qna-core/src/search/ranking.spec.ts`
- Create: `apps/api/src/qna/qna.module.ts`
- Create: `apps/api/src/qna/qna.service.ts`
- Create: `apps/api/src/qna/qna.controller.ts`
- Test: `apps/api/src/qna/qna.service.spec.ts`

- [ ] **Step 1: Write failing ranking tests**

Verify:

```ts
describe('rankMergedResults', () => {
  it('deduplicates by knowledge item id and keeps highest score', () => {});
  it('sorts higher score first', () => {});
});
```

- [ ] **Step 2: Implement ranking helper**

Create `packages/qna-core/src/search/ranking.ts`:

```ts
export interface RawSearchCandidate {
  knowledgeItemId: string;
  knowledgeVersionId: string;
  score: number;
  source: 'exact' | 'full_text' | 'vector';
}

export function rankMergedResults(candidates: RawSearchCandidate[]): RawSearchCandidate[] {
  const byItem = new Map<string, RawSearchCandidate>();
  for (const candidate of candidates) {
    const current = byItem.get(candidate.knowledgeItemId);
    if (!current || candidate.score > current.score) {
      byItem.set(candidate.knowledgeItemId, candidate);
    }
  }
  return [...byItem.values()].sort((a, b) => b.score - a.score);
}
```

- [ ] **Step 3: Write Q&A service tests**

Test:

- Query creates `SearchSession`.
- Disabled knowledge is excluded.
- Active knowledge with ready embedding can be returned.
- Low score returns `mode='no_confident_answer'`.

- [ ] **Step 4: Implement search endpoint**

Implement:

```text
POST /api/v1/qna/search
```

Request:

```json
{
  "query": "退款多久到账",
  "limit": 5
}
```

Response uses `QnaSearchResult` from `@qa/shared`.

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/qna-core test -- search
pnpm --filter @qa/api test -- qna
git add packages/qna-core/src/search apps/api/src/qna
git commit -m "feat: add source backed qna search"
```

Expected: ranking and Q&A service tests pass.

## Task 9: Implement Feedback and Review Queue

**Files:**

- Create: `packages/qna-core/src/feedback/feedback-policy.ts`
- Test: `packages/qna-core/src/feedback/feedback-policy.spec.ts`
- Create: `apps/api/src/reviews/reviews.module.ts`
- Create: `apps/api/src/reviews/reviews.service.ts`
- Create: `apps/api/src/reviews/reviews.controller.ts`
- Modify: `apps/api/src/qna/qna.controller.ts`
- Modify: `apps/api/src/qna/qna.service.ts`
- Test: `apps/api/src/qna/feedback.service.spec.ts`
- Test: `apps/api/src/reviews/reviews.service.spec.ts`

- [ ] **Step 1: Write failing feedback policy tests**

Verify:

```ts
describe('feedback policy', () => {
  it('selected feedback does not create knowledge', () => {});
  it('edited feedback creates pending review knowledge', () => {});
});
```

- [ ] **Step 2: Implement feedback endpoints**

Implement:

```text
POST /api/v1/qna/search-sessions/:id/select
POST /api/v1/qna/search-sessions/:id/edit
POST /api/v1/qna/search-sessions/:id/reject
```

- [ ] **Step 3: Implement review endpoints**

Implement:

```text
GET  /api/v1/reviews
POST /api/v1/reviews/:id/approve
POST /api/v1/reviews/:id/reject
```

Approve behavior:

- Transactionally marks version as approved.
- Sets item status to `active`.
- Sets `currentVersionId`.
- Enqueues `embedding.refresh.requested`.
- Writes audit log.

- [ ] **Step 4: Run tests and commit**

```bash
pnpm --filter @qa/qna-core test -- feedback
pnpm --filter @qa/api test -- feedback reviews
git add packages/qna-core/src/feedback apps/api/src/qna apps/api/src/reviews
git commit -m "feat: add feedback loop and review queue"
```

Expected: feedback and review tests pass.

## Task 10: Implement Admin and Agent Web MVP

**Files:**

- Create: `apps/web/src/api/client.ts`
- Create: `apps/web/src/routes/router.tsx`
- Create: `apps/web/src/pages/LoginPage.tsx`
- Create: `apps/web/src/pages/AgentWorkbenchPage.tsx`
- Create: `apps/web/src/pages/KnowledgeListPage.tsx`
- Create: `apps/web/src/pages/DocumentUploadPage.tsx`
- Create: `apps/web/src/pages/ReviewQueuePage.tsx`
- Create: `apps/web/src/components/CandidateAnswerList.tsx`
- Test: `apps/web/src/pages/AgentWorkbenchPage.test.tsx`
- Test: `apps/web/src/components/CandidateAnswerList.test.tsx`

- [ ] **Step 1: Write failing component tests**

Verify:

```ts
describe('CandidateAnswerList', () => {
  it('renders candidate score, source, and select action', () => {});
  it('allows editing answer text before submit', () => {});
});
```

- [ ] **Step 2: Implement API client**

Implement:

- JWT storage.
- Request interceptor for `Authorization`.
- Typed methods for login, search, select, edit, reject, upload, review approve/reject.

- [ ] **Step 3: Implement agent workbench**

The page must support:

- Question input.
- Candidate list.
- Select existing answer.
- Edit answer and submit.
- Reject all candidates.
- Empty and loading states.

- [ ] **Step 4: Implement admin pages**

Pages:

- Knowledge list with status filter.
- Document upload with parse status.
- Review queue with approve and reject actions.

- [ ] **Step 5: Run tests and commit**

```bash
pnpm --filter @qa/web test
pnpm --filter @qa/web typecheck
git add apps/web
git commit -m "feat: add customer qna web workspace"
```

Expected: web tests and typecheck pass.

## Task 11: Add Operational Controls

**Files:**

- Create: `apps/api/src/common/request-id.middleware.ts`
- Create: `apps/api/src/common/rate-limit.module.ts`
- Create: `apps/api/src/common/health.controller.ts`
- Create: `apps/api/src/reports/reports.module.ts`
- Create: `apps/api/src/reports/knowledge-gap.service.ts`
- Create: `apps/api/src/reports/consistency-check.service.ts`
- Test: `apps/api/src/reports/knowledge-gap.service.spec.ts`
- Test: `apps/api/src/reports/consistency-check.service.spec.ts`

- [ ] **Step 1: Write failing report tests**

Verify:

- No-answer feedback appears in knowledge gap report.
- Active knowledge without ready embedding appears in consistency report.
- Stale embeddings for active knowledge are reported.

- [ ] **Step 2: Implement operational endpoints**

Implement:

```text
GET /health
GET /api/v1/reports/knowledge-gaps
GET /api/v1/reports/consistency
GET /api/v1/audit-logs
```

- [ ] **Step 3: Add request metadata**

Implement:

- Request ID middleware.
- Structured logging fields: requestId, actorId, route, statusCode, durationMs.
- Rate limit on search and upload endpoints.

- [ ] **Step 4: Run tests and commit**

```bash
pnpm --filter @qa/api test -- reports common
git add apps/api/src/common apps/api/src/reports
git commit -m "feat: add operational controls and reports"
```

Expected: report and common tests pass.

## Task 12: Add Runbooks and End-to-End Verification

**Files:**

- Create: `docs/runbooks/local-development.md`
- Create: `docs/runbooks/backup-restore.md`
- Create: `docs/runbooks/embedding-rebuild.md`
- Create: `apps/api/test/e2e/qna-flow.e2e-spec.ts`
- Create: `apps/web/src/pages/e2e-smoke.spec.ts`

- [ ] **Step 1: Write API E2E test**

Test full flow:

```text
login admin
create FAQ as pending_review
approve FAQ
run embedding worker with fake embedding provider
login agent
search question
select candidate
verify search session and feedback record exist
disable knowledge
search again
verify disabled knowledge is not returned
```

- [ ] **Step 2: Write web smoke test**

Test:

```text
login
open workbench
search a question
render candidate answer
submit selected answer
open review queue
```

- [ ] **Step 3: Write runbooks**

`docs/runbooks/local-development.md` includes:

```bash
docker compose -f docker/docker-compose.yml up -d
pnpm install
pnpm db:migrate
pnpm dev:api
pnpm dev:web
```

`docs/runbooks/backup-restore.md` includes:

```bash
pg_dump "$DATABASE_URL" > backup.sql
psql "$DATABASE_URL" < backup.sql
```

`docs/runbooks/embedding-rebuild.md` includes:

```bash
pnpm --filter @qa/api embeddings:rebuild
pnpm --filter @qa/api reports:consistency
```

- [ ] **Step 4: Run full verification**

```bash
pnpm test
pnpm typecheck
pnpm build
```

Expected: all tests, typecheck, and build pass.

- [ ] **Step 5: Commit**

```bash
git add docs/runbooks apps/api/test apps/web/src/pages/e2e-smoke.spec.ts
git commit -m "test: verify customer qna flow end to end"
```

## Coverage Review

Spec requirements covered:

- File import: Task 6.
- PostgreSQL + pgvector: Task 3 and Task 7.
- Skill calls backend only: Task 8 and Task 9 APIs.
- User and role management: Task 4.
- Knowledge list and close/disable: Task 5 and Task 10.
- Candidate answers: Task 8 and Task 10.
- Agent edit feedback: Task 9 and Task 10.
- Review before publishing: Task 5 and Task 9.
- Audit logs: Task 5 and Task 11.
- High availability groundwork: Task 1, Task 7, Task 11, Task 12.
- Data integrity and consistency: Task 3, Task 5, Task 7, Task 11.

No deliberate gaps remain for MVP. Later enhancements such as rerank model, multi-tenant UI, Qdrant migration, and LLM FAQ extraction should be planned after MVP acceptance data exists.

## Execution Handoff

Plan complete. Use one of these execution modes:

1. **Subagent-Driven, recommended**: dispatch a fresh worker per task, review after each task, and keep task ownership isolated.
2. **Inline Execution**: execute tasks in this session with `superpowers:executing-plans`, checkpointing after each task.

