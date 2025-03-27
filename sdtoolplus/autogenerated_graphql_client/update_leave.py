# Generated by ariadne-codegen on 2025-03-27 10:22
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class UpdateLeave(BaseModel):
    leave_update: "UpdateLeaveLeaveUpdate"


class UpdateLeaveLeaveUpdate(BaseModel):
    uuid: UUID


UpdateLeave.update_forward_refs()
UpdateLeaveLeaveUpdate.update_forward_refs()
