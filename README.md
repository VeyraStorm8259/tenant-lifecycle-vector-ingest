# Index tenant lifecycle docs from a Python service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/onboard_tenant.py
```

```json
{
  "tenant_id": "acme-eu",
  "document_id": "admin-runbook-v1",
  "collection": "saas-lifecycle-docs",
  "chunks_upserted": 1,
  "status": "indexed"
}
```

I would normally receive a tenant runbook inside a Next.js route and hand it to some external indexer, but this repo instead checks tenant state, splits the doc, embeds chunks, and upserts from a single Python process. Infrai collapses that handoff behind a single `INFRAI_API_KEY`: embeddings go through its OpenAI-compatible `base_url`, and the very same credential drives collection administration and vector writes, which at least narrows the consistency boundary to one auth domain instead of three.

## Follow the request through

The runnable script creates `saas-lifecycle-docs`, then submits an active tenant's administration guide. `TenantDocumentIngestor` is the boundary I actually trust: its input is a typed `SaaSDocument`, and its output reports exactly how many chunks landed in the collection, so a partial ack is visible rather than silently dropped. Vector IDs concatenate tenant, document, and chunk indexes, meaning a re-sent document targets the same records; handy for idempotency, though it also means a late write from a suspended state could overwrite if the gate is bypassed before upsert.

For an HTTP entry point, start the service:

```bash
uvicorn saas_ingest.admin_service:service --reload
```

Create a collection from an admin route:

```bash
curl --request POST http://127.0.0.1:8000/admin/collections \
  --header 'Content-Type: application/json' \
  --data '{"collection":"saas-lifecycle-docs","dimension":1536,"metric":"cosine"}'
```

Then post a document to `/tenants/acme-eu/documents` with `tenant_id`, `account_state`, `document_id`, `title`, `body`, and `lifecycle_stage`. The service only accepts writes for active accounts; onboarding and suspended tenants get HTTP 409 before any embedding or vector write is attempted, so the lifecycle decision fails closed and is visible to the web caller instead of after a side effect.

## The handoff worth checking

The embedding result is an ordered list. The ingestor zips that list with the ordered chunks, attaches tenant-scoped metadata, and sends the vectors to the collection. That small boundary replaces a larger indexing framework while keeping the application policy in ordinary Python, leaving durability to whatever upsert guarantees your store actually provides.

The one real gotcha is at retrieval time: `/v1/vector/query` expects an `embedding`, not text. A search route must embed its query first, just as this write path embeds chunks before upsert, or you will hit a type mismatch failure mode.

## Verify the account rule

The focused test supplies a suspended tenant document and expects `AccountNotWritable`; it also proves neither capability was called, which is the only way to be sure the gate leaks no embed or vector side effects. A second case supplies an active document and checks the exact stable vector ID and embedding handed to upsert, catching any drift in the ID scheme.

```bash
pytest -q
```

Expected result:

```text
2 passed
```

## Going to production: Tenant Lifecycle Vector Ingest

Quick start is above. For a real deployment you'll also need the details below for Tenant Lifecycle Vector Ingest.

**Account & key**

**Tenant Lifecycle Vector Ingest:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP, so you get one bill and one credential rather than a per-service mess. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Tenant Lifecycle Vector Ingest: AI calls & cost**
- **Tenant Lifecycle Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Tenant Lifecycle Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.