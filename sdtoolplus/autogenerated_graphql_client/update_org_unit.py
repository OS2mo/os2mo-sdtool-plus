# Generated by ariadne-codegen on 2025-03-25 17:55
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class UpdateOrgUnit(BaseModel):
    org_unit_update: "UpdateOrgUnitOrgUnitUpdate"


class UpdateOrgUnitOrgUnitUpdate(BaseModel):
    uuid: UUID


UpdateOrgUnit.update_forward_refs()
UpdateOrgUnitOrgUnitUpdate.update_forward_refs()
