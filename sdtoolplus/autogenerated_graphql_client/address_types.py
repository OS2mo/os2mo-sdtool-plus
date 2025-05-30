from typing import List
from typing import Optional
from uuid import UUID

from .base_model import BaseModel


class AddressTypes(BaseModel):
    facets: "AddressTypesFacets"


class AddressTypesFacets(BaseModel):
    objects: List["AddressTypesFacetsObjects"]


class AddressTypesFacetsObjects(BaseModel):
    current: Optional["AddressTypesFacetsObjectsCurrent"]


class AddressTypesFacetsObjectsCurrent(BaseModel):
    user_key: str
    uuid: UUID
    classes: List["AddressTypesFacetsObjectsCurrentClasses"]


class AddressTypesFacetsObjectsCurrentClasses(BaseModel):
    uuid: UUID
    user_key: str
    name: str


AddressTypes.update_forward_refs()
AddressTypesFacets.update_forward_refs()
AddressTypesFacetsObjects.update_forward_refs()
AddressTypesFacetsObjectsCurrent.update_forward_refs()
AddressTypesFacetsObjectsCurrentClasses.update_forward_refs()
