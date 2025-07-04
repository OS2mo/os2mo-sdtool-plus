from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from ..types import CPRNumber
from .base_model import BaseModel


class GetPersonTimeline(BaseModel):
    employees: "GetPersonTimelineEmployees"


class GetPersonTimelineEmployees(BaseModel):
    objects: List["GetPersonTimelineEmployeesObjects"]


class GetPersonTimelineEmployeesObjects(BaseModel):
    uuid: UUID
    validities: List["GetPersonTimelineEmployeesObjectsValidities"]


class GetPersonTimelineEmployeesObjectsValidities(BaseModel):
    addresses: List["GetPersonTimelineEmployeesObjectsValiditiesAddresses"]
    cpr_number: Optional[CPRNumber]
    given_name: str
    surname: str
    validity: "GetPersonTimelineEmployeesObjectsValiditiesValidity"


class GetPersonTimelineEmployeesObjectsValiditiesAddresses(BaseModel):
    address_type: "GetPersonTimelineEmployeesObjectsValiditiesAddressesAddressType"
    name: Optional[str]


class GetPersonTimelineEmployeesObjectsValiditiesAddressesAddressType(BaseModel):
    user_key: str
    scope: Optional[str]


class GetPersonTimelineEmployeesObjectsValiditiesValidity(BaseModel):
    from_: Optional[datetime] = Field(alias="from")
    to: Optional[datetime]


GetPersonTimeline.update_forward_refs()
GetPersonTimelineEmployees.update_forward_refs()
GetPersonTimelineEmployeesObjects.update_forward_refs()
GetPersonTimelineEmployeesObjectsValidities.update_forward_refs()
GetPersonTimelineEmployeesObjectsValiditiesAddresses.update_forward_refs()
GetPersonTimelineEmployeesObjectsValiditiesAddressesAddressType.update_forward_refs()
GetPersonTimelineEmployeesObjectsValiditiesValidity.update_forward_refs()
