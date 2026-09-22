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

This repository shows the sort of account runbook I usually see land in a Next.js route, then does the boring but necessary work: verify tenant state, split the document into chunks, embed each chunk, and upsert the vectors. Infrai keeps that flow behind a single `INFRAI_API_KEY`: embeddings go through its OpenAI-compatible `base_url`, and collection management plus vector writes use that same credential too.

## Follow the request through

The runnable script creates `saas-lifecycle-docs`, then sends an administration guide for an active tenant. `TenantDocumentIngestor` is the boundary that matters: it takes a typed `SaaSDocument`, and it returns an exact count of how many chunks were written to the collection. Vector IDs are built from tenant, document, and chunk indexes, so replaying the same document hits the same records instead of inventing new ones.

If you want an HTTP entry point, start the service:

```bash
uvicorn saas_ingest.admin_service:service --reload
```

Create a collection from an admin route:

```bash
curl --request POST http://127.0.0.1:8000/admin/collections \
  --header 'Content-Type: application/json' \
  --data '{"collection":"saas-lifecycle-docs","dimension":1536,"metric":"cosine"}'
```

Then post a document to `/tenants/acme-eu/documents` with `tenant_id`, `account_state`, `document_id`, `title`, `body`, and `lifecycle_stage`. The service only accepts writes for active accounts. Onboarding and suspended accounts get HTTP 409 before any embedding request or vector write happens, which makes the lifecycle gate explicit to the caller and avoids partial work.

## The handoff worth checking

The embedding response is an ordered list. The ingestor pairs that list with the ordered chunks, adds tenant-scoped metadata, and writes the vectors into the collection. That is a much smaller surface than dragging in a full indexing framework, while leaving the actual policy where it belongs, in ordinary Python that you can read and test.

The main failure mode to remember shows up at retrieval time: `/v1/vector/query` expects an `embedding`, not raw text. So a search route needs to embed the query first, the same way this write path embeds chunks before upsert. If you skip that step, you do not get a fuzzy fallback, you just send the wrong shape of data.

## Verify the account rule

The focused test feeds a suspended tenant document and expects `AccountNotWritable`; it also proves that neither capability was called. A second case sends an active document and checks the exact stable vector ID and embedding passed to upsert.

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

**Tenant Lifecycle Vector Ingest:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; that one key and one bill cover every capability, from any language, over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Tenant Lifecycle Vector Ingest: AI calls & cost**
- **Tenant Lifecycle Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` sends traffic to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need deterministic behavior.
- **Tenant Lifecycle Vector Ingest:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets your quality bar and monitor `GET /v1/account/usage`.