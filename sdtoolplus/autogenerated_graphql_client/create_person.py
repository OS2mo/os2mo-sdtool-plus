# Generated by ariadne-codegen on 2025-04-10 13:21
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class CreatePerson(BaseModel):
    employee_create: "CreatePersonEmployeeCreate"


class CreatePersonEmployeeCreate(BaseModel):
    uuid: UUID


CreatePerson.update_forward_refs()
CreatePersonEmployeeCreate.update_forward_refs()
