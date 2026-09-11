import os

from fastapi import FastAPI, HTTPException

from .chunk_policy import AccountNotWritable
from .infrai_client import InfraiClient, InfraiError
from .models import CollectionSetup, IngestResult, SaaSDocument
from .tenant_ingest import TenantDocumentIngestor

service = FastAPI(title="SaaS document ingest")


def client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail=error.detail)


@service.post("/admin/collections")
def create_collection(request: CollectionSetup) -> dict[str, str]:
    client = InfraiClient()
    try:
        client.create_collection(request.collection, request.dimension, request.metric)
        return {"collection": request.collection, "status": "ready"}
    except InfraiError as error:
        raise client_error(error) from error
    finally:
        client.close()


@service.post("/tenants/{tenant_id}/documents", response_model=IngestResult)
def ingest_document(tenant_id: str, document: SaaSDocument) -> IngestResult:
    if tenant_id != document.tenant_id:
        raise HTTPException(status_code=400, detail="Path tenant does not match document tenant")
    client = InfraiClient()
    try:
        collection = os.environ.get("INFRAI_COLLECTION", "saas-lifecycle-docs")
        return TenantDocumentIngestor(client, collection).ingest(document)
    except AccountNotWritable as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InfraiError as error:
        raise client_error(error) from error
    finally:
        client.close()

