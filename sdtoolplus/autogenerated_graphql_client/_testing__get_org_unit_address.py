from typing import List
from typing import Optional

from .base_model import BaseModel


class TestingGetOrgUnitAddress(BaseModel):
    org_units: "TestingGetOrgUnitAddressOrgUnits"


class TestingGetOrgUnitAddressOrgUnits(BaseModel):
    objects: List["TestingGetOrgUnitAddressOrgUnitsObjects"]


class TestingGetOrgUnitAddressOrgUnitsObjects(BaseModel):
    current: Optional["TestingGetOrgUnitAddressOrgUnitsObjectsCurrent"]


class TestingGetOrgUnitAddressOrgUnitsObjectsCurrent(BaseModel):
    addresses: List["TestingGetOrgUnitAddressOrgUnitsObjectsCurrentAddresses"]


class TestingGetOrgUnitAddressOrgUnitsObjectsCurrentAddresses(BaseModel):
    value: str
    user_key: str


TestingGetOrgUnitAddress.update_forward_refs()
TestingGetOrgUnitAddressOrgUnits.update_forward_refs()
TestingGetOrgUnitAddressOrgUnitsObjects.update_forward_refs()
TestingGetOrgUnitAddressOrgUnitsObjectsCurrent.update_forward_refs()
TestingGetOrgUnitAddressOrgUnitsObjectsCurrentAddresses.update_forward_refs()
