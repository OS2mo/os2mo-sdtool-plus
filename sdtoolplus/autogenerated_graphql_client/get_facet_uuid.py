from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetFacetUuid(BaseModel):
    facets: "GetFacetUuidFacets"


class GetFacetUuidFacets(BaseModel):
    objects: List["GetFacetUuidFacetsObjects"]


class GetFacetUuidFacetsObjects(BaseModel):
    uuid: UUID


GetFacetUuid.update_forward_refs()
GetFacetUuidFacets.update_forward_refs()
GetFacetUuidFacetsObjects.update_forward_refs()
