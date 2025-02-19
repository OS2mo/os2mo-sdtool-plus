# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID
from uuid import uuid4

import pytest
from more_itertools import one

from sdtoolplus.autogenerated_graphql_client import GetFacetClassClasses
from sdtoolplus.autogenerated_graphql_client import GetFacetClassClassesObjects
from sdtoolplus.autogenerated_graphql_client import GetFacetClassClassesObjectsCurrent
from sdtoolplus.filters import filter_by_line_management
from sdtoolplus.filters import remove_by_name
from sdtoolplus.mo_org_unit_importer import OrgUnitHierarchyUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitNode

LINE_MGMT_CLASS_UUID = uuid4()


@pytest.fixture
def line_mgmt_class_uuid() -> OrgUnitHierarchyUUID:
    return cast(OrgUnitHierarchyUUID, LINE_MGMT_CLASS_UUID)


@pytest.fixture
def unit_with_hierarchy(
    line_mgmt_class_uuid: OrgUnitHierarchyUUID,
) -> list[OrgUnitNode]:
    return [
        OrgUnitNode(
            uuid=UUID("10000000-0000-0000-0000-000000000000"),
            user_key="dep1",
            name="Department 1",
            org_unit_hierarchy=cast(OrgUnitHierarchyUUID, line_mgmt_class_uuid),
        ),
        OrgUnitNode(
            uuid=UUID("20000000-0000-0000-0000-000000000000"),
            user_key="dep2",
            name="Department 2",
            org_unit_hierarchy=cast(OrgUnitHierarchyUUID, uuid4()),
        ),
    ]


def test_remove_by_name(expected_units_to_add):
    # Arrange
    regexs = ["^.*5$", "^.*6$"]  # Filter out units where the name ends in "5" or "6"

    # Act
    kept_units = remove_by_name(regexs, expected_units_to_add)

    # Assert
    assert expected_units_to_add[:2] == kept_units


def test_remove_by_name_special_characters(sd_expected_validity):
    # Arrange
    regexs = ["^%.*$"]
    org_unit_nodes = [
        OrgUnitNode(
            uuid=uuid4(),
            parent_uuid=uuid4(),
            user_key="dep3",
            name="% Department 3",
            org_unit_level_uuid=uuid4(),
            validity=sd_expected_validity,
        )
    ]

    # Act
    kept_units = remove_by_name(regexs, org_unit_nodes)

    # Assert
    assert kept_units == []


def test_remove_by_name_keep_all(expected_units_to_add):
    # Act
    kept_units = remove_by_name([], expected_units_to_add)

    # Assert
    assert expected_units_to_add == kept_units


async def test_filter_by_hierarchy_no_filtering(unit_with_hierarchy: list[OrgUnitNode]):
    # Act
    filtered_units = await filter_by_line_management(
        False, AsyncMock(), unit_with_hierarchy
    )

    # Assert
    assert filtered_units == unit_with_hierarchy


async def test_filter_by_hierarchy_line_mgmt_filtering(
    unit_with_hierarchy: list[OrgUnitNode],
):
    # Arrange
    mock_gql_client = AsyncMock()
    mock_gql_client.get_facet_class.return_value = GetFacetClassClasses(
        objects=[
            GetFacetClassClassesObjects(
                current=GetFacetClassClassesObjectsCurrent(
                    uuid=LINE_MGMT_CLASS_UUID,
                    user_key="linjeorg",
                    name="Linjeorganisation",
                )
            )
        ]
    )

    # Act
    filtered_units = await filter_by_line_management(
        True, mock_gql_client, unit_with_hierarchy
    )

    # Assert
    assert one(filtered_units).uuid == UUID("10000000-0000-0000-0000-000000000000")

    mock_gql_client.get_facet_class.assert_awaited_once_with(
        "org_unit_hierarchy", "linjeorg"
    )
