# Generated by ariadne-codegen on 2025-04-10 13:57
# Source: queries.graphql

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import Field

from .base_model import BaseModel


class GetAddresses(BaseModel):
    addresses: "GetAddressesAddresses"


class GetAddressesAddresses(BaseModel):
    objects: List["GetAddressesAddressesObjects"]


class GetAddressesAddressesObjects(BaseModel):
    validities: List["GetAddressesAddressesObjectsValidities"]


class GetAddressesAddressesObjectsValidities(BaseModel):
    validity: "GetAddressesAddressesObjectsValiditiesValidity"
    name: Optional[str]
    address_type: "GetAddressesAddressesObjectsValiditiesAddressType"


class GetAddressesAddressesObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetAddressesAddressesObjectsValiditiesAddressType(BaseModel):
    user_key: str


GetAddresses.update_forward_refs()
GetAddressesAddresses.update_forward_refs()
GetAddressesAddressesObjects.update_forward_refs()
GetAddressesAddressesObjectsValidities.update_forward_refs()
GetAddressesAddressesObjectsValiditiesValidity.update_forward_refs()
GetAddressesAddressesObjectsValiditiesAddressType.update_forward_refs()
