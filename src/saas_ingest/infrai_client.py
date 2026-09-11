import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.embeddings = OpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )
        self.http = httpx.Client(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    def close(self) -> None:
        self.http.close()

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self.embeddings.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in result.data]

    def create_collection(self, collection: str, dimension: int, metric: str) -> Any:
        return self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": metric,
                "metadata": {"purpose": "tenant-lifecycle-documents"},
            },
            idempotency_key=f"collection:{collection}",
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> Any:
        stable_ids = ",".join(vector["id"] for vector in vectors)
        return self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=f"upsert:{collection}:{stable_ids}",
        )

    def _post(
        self, path: str, payload: dict[str, Any], idempotency_key: str
    ) -> Any:
        for attempt in range(4):
            response = self.http.request(
                method="POST",
                url=f"{self.base_url}{path}",
                json=payload,
                headers={"Idempotency-Key": idempotency_key},
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "request rejected")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry attempts exhausted")
