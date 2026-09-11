from unittest.mock import Mock

import pytest

from saas_ingest.chunk_policy import AccountNotWritable
from saas_ingest.models import AccountState, SaaSDocument
from saas_ingest.tenant_ingest import TenantDocumentIngestor


def document(state: AccountState) -> SaaSDocument:
    return SaaSDocument(
        tenant_id="tenant-42",
        account_state=state,
        document_id="onboarding-guide",
        title="Tenant onboarding",
        lifecycle_stage="onboarding",
        body="Invite the owner.\n\nConfirm the workspace policy.",
    )


def test_suspended_account_cannot_write_vectors() -> None:
    client = Mock()
    ingestor = TenantDocumentIngestor(client, "lifecycle-docs")

    with pytest.raises(AccountNotWritable):
        ingestor.ingest(document(AccountState.SUSPENDED))

    client.embed.assert_not_called()
    client.upsert.assert_not_called()


def test_active_account_hands_embeddings_to_stable_vector_ids() -> None:
    client = Mock()
    client.embed.return_value = [[0.1, 0.2, 0.3]]
    ingestor = TenantDocumentIngestor(client, "lifecycle-docs")

    result = ingestor.ingest(document(AccountState.ACTIVE))

    sent_vectors = client.upsert.call_args.args[1]
    assert sent_vectors[0]["id"] == "tenant-42:onboarding-guide:0"
    assert sent_vectors[0]["values"] == [0.1, 0.2, 0.3]
    assert sent_vectors[0]["metadata"]["lifecycle_stage"] == "onboarding"
    assert result.chunks_upserted == 1

