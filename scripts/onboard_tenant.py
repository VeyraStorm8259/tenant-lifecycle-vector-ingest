import os

from saas_ingest.infrai_client import InfraiClient
from saas_ingest.models import AccountState, SaaSDocument
from saas_ingest.tenant_ingest import TenantDocumentIngestor


def main() -> None:
    collection = os.environ.get("INFRAI_COLLECTION", "saas-lifecycle-docs")
    client = InfraiClient()
    try:
        document = SaaSDocument(
            tenant_id="acme-eu",
            account_state=AccountState.ACTIVE,
            document_id="admin-runbook-v1",
            title="Acme tenant administration",
            lifecycle_stage="onboarding",
            body=(
                "Workspace owners invite teammates and assign least-privilege roles.\n\n"
                "Before activation, an admin verifies billing contacts and data residency.\n\n"
                "When an account closes, export requests finish before access is removed."
            ),
        )
        result = TenantDocumentIngestor(client, collection).ingest(document)
        print(result.model_dump_json(indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
