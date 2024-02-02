# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from ramodels.mo import Validity

from sdtoolplus.autogenerated_graphql_client import AddressCreateInput
from sdtoolplus.autogenerated_graphql_client import AddressTypesFacets
from sdtoolplus.autogenerated_graphql_client import AddressTypesFacetsObjects
from sdtoolplus.autogenerated_graphql_client import AddressTypesFacetsObjectsCurrent
from sdtoolplus.autogenerated_graphql_client import (
    AddressTypesFacetsObjectsCurrentClasses,
)
from sdtoolplus.autogenerated_graphql_client import AddressUpdateInput
from sdtoolplus.autogenerated_graphql_client import CreateAddressAddressCreate
from sdtoolplus.autogenerated_graphql_client import CreateAddressAddressCreateCurrent
from sdtoolplus.autogenerated_graphql_client import (
    CreateAddressAddressCreateCurrentAddressType,
)
from sdtoolplus.autogenerated_graphql_client import (
    CreateAddressAddressCreateCurrentValidity,
)
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.graphql import add_address
from sdtoolplus.graphql import get_address_type_uuid
from sdtoolplus.graphql import update_address
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import OrgUnitNode

addr_uuid = uuid4()
addr_type_uuid = uuid4()
ou_uuid = uuid4()

address = Address(
    name="Paradisæblevej 13, 1000 Andeby",
    address_type=AddressType(
        uuid=addr_type_uuid,
        user_key="AddressMailUnit",
    ),
)

org_unit_node = OrgUnitNode(
    uuid=ou_uuid,
    parent_uuid=uuid4(),
    user_key="dep1",
    parent=None,
    name="Department 1",
    org_unit_level_uuid=uuid4(),
    addresses=[address],
    validity=Validity(from_date=datetime(2000, 1, 1, 12, 0, 0), to_date=None),
)


@pytest.mark.asyncio
async def test_get_address_type_uuid():
    # Arrange
    postal_addr_uuid = uuid4()
    pnumber_addr_uuid = uuid4()

    mock_gql_client = AsyncMock()
    mock_gql_client.address_types.return_value = AddressTypesFacets(
        objects=[
            AddressTypesFacetsObjects(
                current=AddressTypesFacetsObjectsCurrent(
                    user_key="org_unit_address_type",
                    uuid=uuid4(),
                    classes=[
                        AddressTypesFacetsObjectsCurrentClasses(
                            uuid=postal_addr_uuid,
                            user_key="AddressMailUnit",
                            name="Postadresse",
                        ),
                        AddressTypesFacetsObjectsCurrentClasses(
                            uuid=pnumber_addr_uuid,
                            user_key="Pnummer",
                            name="P-nummer",
                        ),
                    ],
                )
            )
        ]
    )

    # Act
    addr_type_uuid = await get_address_type_uuid(mock_gql_client, "Pnummer")

    # Arrange
    assert addr_type_uuid == pnumber_addr_uuid


@pytest.mark.asyncio
async def test_add_address():
    # Arrange
    mock_gql_client = AsyncMock()
    mock_gql_client.create_address.return_value = CreateAddressAddressCreate(
        current=CreateAddressAddressCreateCurrent(
            validity=CreateAddressAddressCreateCurrentValidity(
                from_=datetime(2000, 1, 1, 12, 0, 0), to=None
            ),
            uuid=addr_uuid,
            name="address",
            address_type=CreateAddressAddressCreateCurrentAddressType(
                user_key="AddressMailUnit"
            ),
        )
    )

    # Act
    created_addr = await add_address(mock_gql_client, org_unit_node, address)

    # Assert
    assert created_addr.uuid == addr_uuid
    assert created_addr.name == "Paradisæblevej 13, 1000 Andeby"
    assert created_addr.address_type.user_key == "AddressMailUnit"
    assert created_addr.address_type.uuid == addr_type_uuid

    mock_gql_client.create_address.assert_awaited_once_with(
        AddressCreateInput(
            org_unit=ou_uuid,
            value="Paradisæblevej 13, 1000 Andeby",
            address_type=addr_type_uuid,
            validity=RAValidityInput(
                from_=datetime(
                    2000, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen")
                ),
                to=None,
            ),
        )
    )


@pytest.mark.asyncio
async def test_update_address():
    # Arrange
    mock_gql_client = AsyncMock()
    addr = Address(
        uuid=addr_uuid,
        name="Paradisæblevej 13, 1000 Andeby",
        address_type=AddressType(
            uuid=addr_type_uuid,
            user_key="AddressMailUnit",
        ),
    )

    # Act
    await update_address(mock_gql_client, org_unit_node, addr)

    # Assert
    mock_gql_client.update_address.assert_awaited_once_with(
        AddressUpdateInput(
            uuid=addr_uuid,
            value="Paradisæblevej 13, 1000 Andeby",
            address_type=addr_type_uuid,
            validity=RAValidityInput(
                from_=datetime(
                    2000, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen")
                ),
                to=None,
            ),
        )
    )
