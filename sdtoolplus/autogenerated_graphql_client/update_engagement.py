# Generated by ariadne-codegen on 2025-04-11 09:35
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class UpdateEngagement(BaseModel):
    engagement_update: "UpdateEngagementEngagementUpdate"


class UpdateEngagementEngagementUpdate(BaseModel):
    uuid: UUID


UpdateEngagement.update_forward_refs()
UpdateEngagementEngagementUpdate.update_forward_refs()
