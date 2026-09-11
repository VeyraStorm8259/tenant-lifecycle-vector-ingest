import re

from .models import SaaSDocument


class AccountNotWritable(ValueError):
    pass


def chunks_for(document: SaaSDocument, max_characters: int = 700) -> list[str]:
    if document.account_state.value != "active":
        raise AccountNotWritable(
            f"Tenant {document.tenant_id} must be active before document ingestion"
        )

    sections = [part.strip() for part in re.split(r"\n\s*\n", document.body) if part.strip()]
    chunks: list[str] = []
    current = document.title
    for section in sections:
        candidate = f"{current}\n\n{section}"
        if len(candidate) <= max_characters:
            current = candidate
            continue
        if current != document.title:
            chunks.append(current)
        current = f"{document.title}\n\n{section}"
    if current != document.title:
        chunks.append(current)
    return chunks

