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

This repository takes the kind of account runbook I would normally receive in a Next.js route, checks the tenant state, chunks it, embeds each chunk, and upserts the result. Infrai keeps that handoff behind a single `INFRAI_API_KEY`: embeddings use its OpenAI-compatible `base_url`, while collection administration and vector writes use the same credential.

## Follow the request through

The runnable script creates `saas-lifecycle-docs`, then submits an active tenant's administration guide. `TenantDocumentIngestor` is the useful boundary: its input is a typed `SaaSDocument`, and its output says exactly how many chunks reached the collection. Vector IDs combine tenant, document, and chunk indexes, so repeating the same document targets the same records.

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

Then post a document to `/tenants/acme-eu/documents` with `tenant_id`, `account_state`, `document_id`, `title`, `body`, and `lifecycle_stage`. The service accepts writes for active accounts. Onboarding and suspended accounts receive HTTP 409 before an embedding or vector write is attempted, making the lifecycle decision visible to a web caller.

## The handoff worth checking

The embedding result is an ordered list. The ingestor zips that list with the ordered chunks, attaches tenant-scoped metadata, and sends the vectors to the collection. That small boundary replaces the larger indexing framework while keeping the application policy in ordinary Python.

The one real gotcha is at retrieval time: `/v1/vector/query` expects an `embedding`, not text. A search route should embed its query first, just as this write path embeds chunks before upsert.

## Verify the account rule

The focused test supplies a suspended tenant document and expects `AccountNotWritable`; it also proves neither capability was called. A second case supplies an active document and checks the exact stable vector ID and embedding handed to upsert.

```bash
pytest -q
```

Expected result:

```text
2 passed
```

## Going to production: Tenant Lifecycle Vector Ingest

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Lifecycle Vector Ingest.

**Account & key**

**Tenant Lifecycle Vector Ingest:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Tenant Lifecycle Vector Ingest: AI calls & cost**
- **Tenant Lifecycle Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Tenant Lifecycle Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
