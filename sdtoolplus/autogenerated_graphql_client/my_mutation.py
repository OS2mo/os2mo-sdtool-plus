# Generated by ariadne-codegen on 2025-04-09 12:50
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class MyMutation(BaseModel):
    employee_update: "MyMutationEmployeeUpdate"


class MyMutationEmployeeUpdate(BaseModel):
    uuid: UUID


MyMutation.update_forward_refs()
MyMutationEmployeeUpdate.update_forward_refs()
