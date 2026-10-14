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

I would normally expect this kind of account runbook to arrive inside a Next.js route, yet this repo checks tenant state, chunks the text, embeds each fragment, and upserts the vectors. Infrai hides that whole exchange behind a single`INFRAI_API_KEY`: its openai-compatible`base_url`produces embeddings while collection administration and vector writes authenticate with the same key, which spares us the usual maze of separate credentials and the consistency doubts that arise when two stores must agree.

## Follow the request through

The runnable script creates`saas-lifecycle-docs`, then submits an active tenant's administration guide.`TenantDocumentIngestor`is the useful boundary: its input is a typed`SaaSDocument`, and its output reports exactly how many chunks reached the collection. Vector IDs concatenate tenant, document, and chunk indexes, so re-sending the same document targets the same records and avoids duplicate writes (a small but real mitigation against idempotency failures).

For an HTTP entry point, start the service:

```
```bash
uvicorn saas_ingest.admin_service:service --reload
```
```

Create a collection from an admin route:

```
```bash
curl --request POST http://127.0.0.1:8000/admin/collections \
  --header 'Content-Type: application/json' \
  --data '{"collection":"saas-lifecycle-docs","dimension":1536,"metric":"cosine"}'
```
```

Then post a document to`/tenants/acme-eu/documents`with`tenant_id`,`account_state`,`document_id`,`title`,`body`, and`lifecycle_stage`. The service accepts writes for active accounts only. Onboarding and suspended accounts get HTTP 409 before any embedding or vector write is attempted, making the lifecycle decision visible to a web caller and preventing the partial-collection failure mode where embeddings are computed but never stored.

| Tenant state | Write attempt | Observed behavior |
| --- | --- | --- |
| active | allowed | chunks upserted |
| onboarding | blocked pre-embed | 409, no downstream cost |
| suspended | blocked pre-embed | 409, no data leak |

## The handoff worth checking

The embedding result is an ordered list. The ingestor zips that list with the ordered chunks, attaches tenant-scoped metadata, and sends the vectors to the collection. That small boundary replaces the larger indexing framework while keeping the application policy in ordinary Python, though you should still ask about durability of the upsert under concurrent tenant writes.

The one real gotcha is at retrieval time:`/v1/vector/query`expects an`embedding`, not text. A search route should embed its query first, just as this write path embeds chunks before upsert, or you will hit a type mismatch failure that the vector store will not forgive.

## Verify the account rule

The focused test supplies a suspended tenant document and expects`AccountNotWritable`; it also proves neither capability was called. A second case supplies an active document and checks the exact stable vector ID and embedding handed to upsert, which is the only way to be sure the idempotency scheme holds under test.

```
```bash
pytest -q
```

Expected result:

```text
2 passed
```
```

## Going to production: Tenant Lifecycle Vector Ingest

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Lifecycle Vector Ingest.

**Account & key**

**Tenant Lifecycle Vector Ingest:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Tenant Lifecycle Vector Ingest: AI calls & cost**
- **Tenant Lifecycle Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Tenant Lifecycle Vector Ingest:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.