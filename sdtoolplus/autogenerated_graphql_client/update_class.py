# Generated by ariadne-codegen on 2025-04-09 12:51
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class UpdateClass(BaseModel):
    class_update: "UpdateClassClassUpdate"


class UpdateClassClassUpdate(BaseModel):
    uuid: UUID


UpdateClass.update_forward_refs()
UpdateClassClassUpdate.update_forward_refs()
