from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetPerson(BaseModel):
    employees: "GetPersonEmployees"


class GetPersonEmployees(BaseModel):
    objects: List["GetPersonEmployeesObjects"]


class GetPersonEmployeesObjects(BaseModel):
    uuid: UUID


GetPerson.update_forward_refs()
GetPersonEmployees.update_forward_refs()
GetPersonEmployeesObjects.update_forward_refs()
