from typing import Protocol

from .chunk_policy import chunks_for
from .models import IngestResult, SaaSDocument


class IngestClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def upsert(self, collection: str, vectors: list[dict[str, object]]) -> object: ...


class TenantDocumentIngestor:
    def __init__(self, client: IngestClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    def ingest(self, document: SaaSDocument) -> IngestResult:
        chunks = chunks_for(document)
        embeddings = self.client.embed(chunks)
        vectors = [
            {
                "id": f"{document.tenant_id}:{document.document_id}:{index}",
                "values": embedding,
                "metadata": {
                    "tenant_id": document.tenant_id,
                    "document_id": document.document_id,
                    "title": document.title,
                    "lifecycle_stage": document.lifecycle_stage,
                    "chunk_index": index,
                    "text": chunk,
                },
            }
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        self.client.upsert(self.collection, vectors)
        return IngestResult(
            tenant_id=document.tenant_id,
            document_id=document.document_id,
            collection=self.collection,
            chunks_upserted=len(vectors),
            status="indexed",
        )
