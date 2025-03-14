# Generated by ariadne-codegen on 2025-03-14 11:43
# Source: queries.graphql

from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetPerson(BaseModel):
    employees: "GetPersonEmployees"


class GetPersonEmployees(BaseModel):
    objects: List["GetPersonEmployeesObjects"]


class GetPersonEmployeesObjects(BaseModel):
    validities: List["GetPersonEmployeesObjectsValidities"]


class GetPersonEmployeesObjectsValidities(BaseModel):
    uuid: UUID


GetPerson.update_forward_refs()
GetPersonEmployees.update_forward_refs()
GetPersonEmployeesObjects.update_forward_refs()
GetPersonEmployeesObjectsValidities.update_forward_refs()
