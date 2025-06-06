# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import parse_obj_as

from sdtoolplus.autogenerated_graphql_client import GetRelatedUnitsRelatedUnitsObjects
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.mo.timeline import _get_related_unit_at
from sdtoolplus.mo.timeline import _get_related_units_endpoints
from sdtoolplus.mo.timeline import get_patch_validity
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID

TZ = ZoneInfo("Europe/Copenhagen")

RELATED_OBJECTS_RAW = [
    {
        "validities": [
            {
                "uuid": "caf9acd5-ae83-48ce-81c1-e2ba534f6f0f",
                "validity": {
                    "from": "2005-01-01T00:00:00+01:00",
                    "to": "2006-12-31T00:00:00+01:00",
                },
                "org_units": [
                    {"uuid": "30000000-0000-0000-0000-000000000000"},
                    {"uuid": "eeeeeeee-2a66-429e-8893-eeeeeeeeeeee"},
                ],
            }
        ]
    },
    {
        "validities": [
            {
                "uuid": "d2f48f24-0e06-4447-afbf-ac01e8ffd7a2",
                "validity": {
                    "from": "2004-01-01T00:00:00+01:00",
                    "to": "2005-12-31T00:00:00+01:00",
                },
                "org_units": [
                    {"uuid": "30000000-0000-0000-0000-000000000000"},
                    {"uuid": "dddddddd-2a66-429e-8893-dddddddddddd"},
                ],
            }
        ]
    },
    {
        "validities": [
            {
                "uuid": "e53dabdc-b9c8-4f7f-8257-7dfffc1c1531",
                "validity": {
                    "from": "2001-01-01T00:00:00+01:00",
                    "to": "2004-12-31T00:00:00+01:00",
                },
                "org_units": [
                    {"uuid": "30000000-0000-0000-0000-000000000000"},
                    {"uuid": "cccccccc-2a66-429e-8893-cccccccccccc"},
                ],
            }
        ]
    },
]


@pytest.mark.parametrize(
    "codegen_validity_from, codegen_validity_to, mo_validity_from, mo_validity_to, expected_from, expected_to",
    [
        (
            datetime(1900, 1, 1),
            None,
            datetime(2000, 1, 1),
            None,
            datetime(2000, 1, 1),
            None,
        ),
        (
            datetime(2000, 1, 1),
            None,
            datetime(1900, 1, 1),
            None,
            datetime(2000, 1, 1),
            None,
        ),
        (
            datetime(2000, 1, 1),
            datetime(2200, 1, 1),
            datetime(2000, 1, 1),
            datetime(2100, 1, 1),
            datetime(2000, 1, 1),
            datetime(2100, 1, 1),
        ),
        (
            datetime(2000, 1, 1),
            datetime(2100, 1, 1),
            datetime(2000, 1, 1),
            datetime(2200, 1, 1),
            datetime(2000, 1, 1),
            datetime(2100, 1, 1),
        ),
    ],
)
def test__get_update_validity(
    codegen_validity_from: datetime,
    codegen_validity_to: datetime | None,
    mo_validity_from: datetime,
    mo_validity_to: datetime | None,
    expected_from: datetime,
    expected_to: datetime | None,
):
    # Arrange
    mo_validity = RAValidityInput(from_=mo_validity_from, to=mo_validity_to)

    # Act
    actual_validity = get_patch_validity(
        codegen_validity_from, codegen_validity_to, mo_validity
    )

    # Assert
    assert actual_validity == RAValidityInput(from_=expected_from, to=expected_to)


def test__get_related_units_endpoints():
    """
    We are testing this scenario, i.e. we wnt to find the related units endpoints of the
    related units to dep3

    Time  --------t1--------t2----t3--t4--t5--t6--t7--t8-----t9--------------------->
    dep3          |-------------C---------|---E---|
                                      |---D---|
    """
    # Arrange
    objects = parse_obj_as(
        list[GetRelatedUnitsRelatedUnitsObjects], RELATED_OBJECTS_RAW
    )

    t3 = datetime(2003, 1, 1, tzinfo=TZ)
    t4 = datetime(2004, 1, 1, tzinfo=TZ)
    t5 = datetime(2005, 1, 1, tzinfo=TZ)
    t6 = datetime(2006, 1, 1, tzinfo=TZ)
    t7 = datetime(2007, 1, 1, tzinfo=TZ)
    t8 = datetime(2008, 1, 1, tzinfo=TZ)

    # Act
    endpoints = _get_related_units_endpoints(objects, start=t3, end=t8)

    # Assert
    assert endpoints == [t3, t4, t5, t6, t7, t8]


@pytest.mark.parametrize(
    "at, expected_related_unit",
    [
        (
            datetime(2002, 1, 1, tzinfo=TZ),
            OrgUnitUUID("cccccccc-2a66-429e-8893-cccccccccccc"),
        ),
        (
            datetime(2004, 1, 1, tzinfo=TZ),
            OrgUnitUUID("cccccccc-2a66-429e-8893-cccccccccccc"),
        ),
        (
            datetime(2004, 7, 1, tzinfo=TZ),
            OrgUnitUUID("cccccccc-2a66-429e-8893-cccccccccccc"),
        ),
        (
            datetime(2005, 1, 1, tzinfo=TZ),
            OrgUnitUUID("dddddddd-2a66-429e-8893-dddddddddddd"),
        ),
        (
            datetime(2005, 7, 1, tzinfo=TZ),
            OrgUnitUUID("dddddddd-2a66-429e-8893-dddddddddddd"),
        ),
        (
            datetime(2006, 1, 1, tzinfo=TZ),
            OrgUnitUUID("eeeeeeee-2a66-429e-8893-eeeeeeeeeeee"),
        ),
        (
            datetime(2006, 7, 1, tzinfo=TZ),
            OrgUnitUUID("eeeeeeee-2a66-429e-8893-eeeeeeeeeeee"),
        ),
        (datetime(2007, 1, 1, tzinfo=TZ), None),
        (datetime(2007, 7, 1, tzinfo=TZ), None),
    ],
)
def test__get_related_unit_at(
    at: datetime,
    expected_related_unit: OrgUnitUUID | None,
):
    """
    We are testing this scenario, i.e. we wnt to find the related units to dep3

    Time  --------t1--------t2----t3--t4--t5--t6--t7--t8-----t9--------------------->
    dep3          |-------------C---------|---E---|
                                      |---D---|
    """
    # Arrange
    objects = parse_obj_as(
        list[GetRelatedUnitsRelatedUnitsObjects], RELATED_OBJECTS_RAW
    )

    # UUID of dep3
    unit_uuid = OrgUnitUUID("30000000-0000-0000-0000-000000000000")

    # Act
    related_unit = _get_related_unit_at(objects=objects, unit_uuid=unit_uuid, at=at)

    # Arrange
    assert related_unit == expected_related_unit
