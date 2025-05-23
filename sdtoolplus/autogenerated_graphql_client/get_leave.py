from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetLeave(BaseModel):
    leaves: "GetLeaveLeaves"


class GetLeaveLeaves(BaseModel):
    objects: List["GetLeaveLeavesObjects"]


class GetLeaveLeavesObjects(BaseModel):
    uuid: UUID
    validities: List["GetLeaveLeavesObjectsValidities"]


class GetLeaveLeavesObjectsValidities(BaseModel):
    user_key: str
    person: List["GetLeaveLeavesObjectsValiditiesPerson"]
    engagement: "GetLeaveLeavesObjectsValiditiesEngagement"
    leave_type: "GetLeaveLeavesObjectsValiditiesLeaveType"
    validity: "GetLeaveLeavesObjectsValiditiesValidity"


class GetLeaveLeavesObjectsValiditiesPerson(BaseModel):
    uuid: UUID


class GetLeaveLeavesObjectsValiditiesEngagement(BaseModel):
    uuid: UUID


class GetLeaveLeavesObjectsValiditiesLeaveType(BaseModel):
    uuid: UUID


class GetLeaveLeavesObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetLeave.update_forward_refs()
GetLeaveLeaves.update_forward_refs()
GetLeaveLeavesObjects.update_forward_refs()
GetLeaveLeavesObjectsValidities.update_forward_refs()
GetLeaveLeavesObjectsValiditiesPerson.update_forward_refs()
GetLeaveLeavesObjectsValiditiesEngagement.update_forward_refs()
GetLeaveLeavesObjectsValiditiesLeaveType.update_forward_refs()
GetLeaveLeavesObjectsValiditiesValidity.update_forward_refs()
