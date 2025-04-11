# Generated by ariadne-codegen on 2025-04-10 13:57
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class CreateClass(BaseModel):
    class_create: "CreateClassClassCreate"


class CreateClassClassCreate(BaseModel):
    uuid: UUID


CreateClass.update_forward_refs()
CreateClassClassCreate.update_forward_refs()
