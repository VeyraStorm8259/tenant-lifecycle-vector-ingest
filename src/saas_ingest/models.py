from enum import Enum
from dataclasses import dataclass

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    BaseModel = None


class AccountState(str, Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"


if BaseModel is not None:
    class CollectionSetup(BaseModel):
        collection: str = Field(min_length=1)
        dimension: int = Field(gt=0)
        metric: str = "cosine"


    class SaaSDocument(BaseModel):
        tenant_id: str = Field(min_length=1)
        account_state: AccountState
        document_id: str = Field(min_length=1)
        title: str = Field(min_length=1)
        body: str = Field(min_length=1)
        lifecycle_stage: str = Field(min_length=1)


    class IngestResult(BaseModel):
        tenant_id: str
        document_id: str
        collection: str
        chunks_upserted: int
        status: str
else:
    @dataclass
    class CollectionSetup:
        collection: str
        dimension: int
        metric: str = "cosine"


    @dataclass
    class SaaSDocument:
        tenant_id: str
        account_state: AccountState
        document_id: str
        title: str
        body: str
        lifecycle_stage: str


    @dataclass
    class IngestResult:
        tenant_id: str
        document_id: str
        collection: str
        chunks_upserted: int
        status: str
