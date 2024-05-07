# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import unittest
from datetime import date
from datetime import datetime
from time import sleep
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from fastramqpi.pytest_util import retry
from freezegun import freeze_time
from httpx import Response
from more_itertools import one
from respx import MockRouter
from sdclient.requests import GetDepartmentParentRequest
from sdclient.responses import Department
from sdclient.responses import DepartmentReference
from sdclient.responses import GetDepartmentParentResponse
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.autogenerated_graphql_client import GraphQLClient
from sdtoolplus.autogenerated_graphql_client import TestingCreateOrgUnitOrgUnitCreate
from sdtoolplus.mo_org_unit_importer import OrgUnitLevelUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitTypeUUID
from sdtoolplus.tests.conftest import mock_get_department_parent
from sdtoolplus.tests.conftest import SharedIdentifier


class MockSDClient:
    def get_department_parent(
        self,
        query_params: GetDepartmentParentRequest,
    ) -> GetDepartmentParentResponse:
        return mock_get_department_parent(query_params)


@pytest.mark.integration_test
@patch("sdtoolplus.main.get_engine")
@patch("sdtoolplus.sd.importer.get_sd_departments")
@patch("sdtoolplus.sd.importer.get_sd_organization")
@patch("sdtoolplus.main.run_db_end_operations")
@patch("sdtoolplus.main.run_db_start_operations", return_value=None)
async def test_two_new_departments_in_sd(
    mock_run_db_start_operations: MagicMock,
    mock_run_db_end_operations: MagicMock,
    mock_get_sd_organization: MagicMock,
    mock_get_sd_departments: MagicMock,
    mock_get_engine: MagicMock,
    test_client: TestClient,
    graphql_client: GraphQLClient,
    base_tree_builder: TestingCreateOrgUnitOrgUnitCreate,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    respx_mock: MockRouter,
) -> None:
    """
    Two new units, Department 7 and Department 8, are added to the root of the
    SD tree
    """

    # Arrange
    org_uuid = (await graphql_client.get_organization()).uuid
    mock_sd_get_organization_response.InstitutionUUIDIdentifier = org_uuid

    get_org_dep7_and_dep8 = {
        "DepartmentIdentifier": "Afd",
        "DepartmentUUIDIdentifier": "80000000-0000-0000-0000-000000000000",
        "DepartmentLevelIdentifier": "Afdelings-niveau",
        "DepartmentReference": [
            {
                "DepartmentIdentifier": "NY0",
                "DepartmentUUIDIdentifier": "70000000-0000-0000-0000-000000000000",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "NY1",
                        "DepartmentUUIDIdentifier": str(
                            SharedIdentifier.child_org_unit_uuid
                        ),
                        "DepartmentLevelIdentifier": "NY1-niveau",
                    }
                ],
            }
        ],
    }
    mock_sd_get_organization_response.Organization[0].DepartmentReference.append(
        DepartmentReference.parse_obj(get_org_dep7_and_dep8)
    )

    get_dep_dep7_and_dep8 = [
        {
            "ActivationDate": "1999-01-01",
            "DeactivationDate": "9999-12-31",
            "DepartmentIdentifier": "dep7",
            "DepartmentLevelIdentifier": "NY0-niveau",
            "DepartmentName": "Department 7",
            "DepartmentUUIDIdentifier": "70000000-0000-0000-0000-000000000000",
        },
        {
            "ActivationDate": "1999-01-01",
            "DeactivationDate": "9999-12-31",
            "DepartmentIdentifier": "dep8",
            "DepartmentLevelIdentifier": "Afdelings-niveau",
            "DepartmentName": "Department 8",
            "DepartmentUUIDIdentifier": "80000000-0000-0000-0000-000000000000",
        },
    ]
    mock_sd_get_department_response.Department.extend(
        [Department.parse_obj(dep) for dep in get_dep_dep7_and_dep8]
    )

    mock_get_sd_organization.return_value = mock_sd_get_organization_response
    mock_get_sd_departments.return_value = mock_sd_get_department_response

    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/70000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))
    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/80000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))

    # Act
    test_client.post("/trigger")

    # Assert
    @retry()
    async def verify() -> None:
        # Verify Department 7 is correct
        dep7 = await graphql_client._testing__get_org_unit(
            UUID("70000000-0000-0000-0000-000000000000")
        )
        current = one(dep7.objects).current
        assert current is not None
        assert current.uuid == UUID("70000000-0000-0000-0000-000000000000")
        assert current.user_key == "dep7"
        assert current.name == "Department 7"
        assert current.validity.from_ == datetime(
            1999, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen")
        )
        assert current.validity.to is None
        assert current.org_unit_level.name == "NY0-niveau"  # type: ignore
        assert current.parent.uuid == UUID("10000000-0000-0000-0000-000000000000")  # type: ignore

        # Verify Department 8 is correct
        dep7 = await graphql_client._testing__get_org_unit(
            UUID("80000000-0000-0000-0000-000000000000")
        )
        current = one(dep7.objects).current
        assert current is not None
        assert current.uuid == UUID("80000000-0000-0000-0000-000000000000")
        assert current.user_key == "dep8"
        assert current.name == "Department 8"
        assert current.validity.from_ == datetime(
            1999, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen")
        )
        assert current.validity.to is None
        assert current.org_unit_level.name == "Afdelings-niveau"  # type: ignore
        assert current.parent.uuid == UUID("70000000-0000-0000-0000-000000000000")  # type: ignore

    await verify()


@pytest.mark.integration_test
@patch("sdtoolplus.main.get_engine")
@patch("sdtoolplus.app.SDClient", return_value=MockSDClient())
@patch("sdtoolplus.sd.importer.get_sd_departments")
@patch("sdtoolplus.sd.importer.get_sd_organization")
@patch("sdtoolplus.main.run_db_end_operations")
@patch("sdtoolplus.main.run_db_start_operations", return_value=None)
async def test_build_tree_extra_units_are_added(
    mock_run_db_start_operations: MagicMock,
    mock_run_db_end_operations: MagicMock,
    mock_get_sd_organization: MagicMock,
    mock_get_sd_departments: MagicMock,
    MockSDClient: MagicMock,
    mock_get_engine: MagicMock,
    test_client: TestClient,
    graphql_client: GraphQLClient,
    obsolete_unit_tree_builder: None,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response_extra_units: GetDepartmentResponse,
    respx_mock: MockRouter,
    org_unit_type: OrgUnitTypeUUID,
    org_unit_levels: dict[str, OrgUnitLevelUUID],
) -> None:
    """
    Test that the sdtoolplus.sd.tree.build_tree_extra functionality is working,
    i.e. that the SD departments missing in the GetOrganization response are
    added to the final SD tree.
    """

    # Arrange
    org_uuid = (await graphql_client.get_organization()).uuid
    mock_sd_get_organization_response.InstitutionUUIDIdentifier = org_uuid

    mock_get_sd_organization.return_value = mock_sd_get_organization_response
    mock_get_sd_departments.return_value = mock_sd_get_department_response_extra_units

    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/95000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))
    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/96000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))
    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/97000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))

    # Act
    test_client.post("/trigger")

    # Assert
    @retry()
    async def verify() -> None:
        # Verify that Departments have the correct parents
        dep7 = await graphql_client._testing__get_org_unit(
            UUID("95000000-0000-0000-0000-000000000000")
        )
        assert one(dep7.objects).current.parent.uuid == UUID("10000000-0000-0000-0000-000000000000")  # type: ignore

        dep8 = await graphql_client._testing__get_org_unit(
            UUID("96000000-0000-0000-0000-000000000000")
        )
        assert one(dep8.objects).current.parent.uuid == UUID("95000000-0000-0000-0000-000000000000")  # type: ignore

        dep9 = await graphql_client._testing__get_org_unit(
            UUID("97000000-0000-0000-0000-000000000000")
        )
        assert one(dep9.objects).current.parent.uuid == UUID("96000000-0000-0000-0000-000000000000")  # type: ignore

    await verify()

    # Act again - no operations should be performed
    r = test_client.post("/trigger")
    assert r.json() == []


@unittest.skip("Awaiting Redmine case #60582...")
@pytest.mark.integration_test
@freeze_time("2024-04-22")
@patch("sdtoolplus.main.get_engine")
@patch("sdtoolplus.app.SDClient", return_value=MockSDClient())
@patch("sdtoolplus.sd.importer.get_sd_departments")
@patch("sdtoolplus.sd.importer.get_sd_organization")
@patch("sdtoolplus.main.run_db_end_operations")
@patch("sdtoolplus.main.run_db_start_operations", return_value=None)
async def test_build_tree_date_range_errors(
    mock_run_db_start_operations: MagicMock,
    mock_run_db_end_operations: MagicMock,
    mock_get_sd_organization: MagicMock,
    mock_get_sd_departments: MagicMock,
    MockSDClient: MagicMock,
    mock_get_engine: MagicMock,
    test_client: TestClient,
    graphql_client: GraphQLClient,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response_date_range_errors: GetDepartmentResponse,
    respx_mock: MockRouter,
    org_unit_type: OrgUnitTypeUUID,
    org_unit_levels: dict[str, OrgUnitLevelUUID],
) -> None:
    # TODO: add docstring

    # Arrange
    org_uuid = (await graphql_client.get_organization()).uuid
    mock_sd_get_organization_response.InstitutionUUIDIdentifier = org_uuid

    mock_get_sd_organization.return_value = mock_sd_get_organization_response
    mock_get_sd_departments.return_value = (
        mock_sd_get_department_response_date_range_errors
    )

    default_start_time = datetime(1999, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen"))

    root = await graphql_client._testing__create_org_unit(
        uuid=UUID("12121212-1212-1212-1212-121212121212"),
        name="Root",
        user_key="root",
        org_unit_type=org_unit_type,
        from_date=datetime(1950, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen")),
    )

    dep1 = await graphql_client._testing__create_org_unit(
        UUID("10000000-0000-0000-0000-000000000000"),
        name="Department 1",
        user_key="dep1",
        org_unit_type=org_unit_type,
        org_unit_level=org_unit_levels["NY1-niveau"],
        from_date=default_start_time,
        parent=root.uuid,
    )

    dep2 = await graphql_client._testing__create_org_unit(
        UUID("20000000-0000-0000-0000-000000000000"),
        name="Department 2",
        user_key="dep2",
        org_unit_type=org_unit_type,
        org_unit_level=org_unit_levels["NY0-niveau"],
        from_date=default_start_time,
        parent=dep1.uuid,
    )

    dep3 = await graphql_client._testing__create_org_unit(
        UUID("30000000-0000-0000-0000-000000000000"),
        name="Department 3",
        user_key="dep3",
        org_unit_type=org_unit_type,
        org_unit_level=org_unit_levels["Afdelings-niveau"],
        from_date=default_start_time,
        parent=dep2.uuid,
    )

    dep4 = await graphql_client._testing__create_org_unit(
        UUID("40000000-0000-0000-0000-000000000000"),
        name="Department 4",
        user_key="dep4",
        org_unit_type=org_unit_type,
        org_unit_level=org_unit_levels["Afdelings-niveau"],
        from_date=default_start_time,
        parent=dep2.uuid,
    )

    dep5 = await graphql_client._testing__create_org_unit(
        UUID("50000000-0000-0000-0000-000000000000"),
        name="Department 5",
        user_key="dep5",
        org_unit_type=org_unit_type,
        org_unit_level=org_unit_levels["NY0-niveau"],
        from_date=default_start_time,
        parent=dep1.uuid,
    )

    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/60000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))

    # TODO: refactor into separate function
    respx_mock.get(
        "https://service.sd.dk/sdws/GetDepartment20111201?InstitutionIdentifier=XY&DepartmentUUIDIdentifier=50000000-0000-0000-0000-000000000000&ActivationDate=01.01.1930&DeactivationDate=22.04.2024&DepartmentNameIndicator=True&PostalAddressIndicator=False&UUIDIndicator=True"
    ).mock(
        return_value=Response(
            200,
            text='<?xml version="1.0" encoding="UTF-8" ?>'
            '<GetDepartment20111201 creationDateTime="2024-04-22T10:05:14" >'
            "  <RequestStructure>"
            "    <InstitutionIdentifier>XY</InstitutionIdentifier>"
            "    <DepartmentUUIDIdentifier>50000000-0000-0000-0000-000000000000</DepartmentUUIDIdentifier>"
            "    <ActivationDate>1930-01-01</ActivationDate>"
            "    <DeactivationDate>2024-04-22</DeactivationDate>"
            "    <ContactInformationIndicator>false</ContactInformationIndicator>"
            "    <DepartmentNameIndicator>true</DepartmentNameIndicator>"
            "    <EmploymentDepartmentIndicator>false</EmploymentDepartmentIndicator>"
            "    <PostalAddressIndicator>false</PostalAddressIndicator>"
            "    <ProductionUnitIndicator>false</ProductionUnitIndicator>"
            "    <UUIDIndicator>true</UUIDIndicator>"
            "  </RequestStructure>"
            "  <RegionIdentifier>RI</RegionIdentifier>"
            "  <RegionUUIDIdentifier>4b80fcea-c23f-4d3c-82fd-69c0b180c62d</RegionUUIDIdentifier>"
            "  <InstitutionIdentifier>II</InstitutionIdentifier>"
            "  <InstitutionUUIDIdentifier>3db34422-91bd-4580-975c-ea240adb5dd9</InstitutionUUIDIdentifier>"
            "  <Department>"
            "    <ActivationDate>1998-01-01</ActivationDate>"
            "    <DeactivationDate>1998-05-31</DeactivationDate>"
            "    <DepartmentIdentifier>dep5</DepartmentIdentifier>"
            "    <DepartmentUUIDIdentifier>50000000-0000-0000-0000-000000000000</DepartmentUUIDIdentifier>"
            "    <DepartmentLevelIdentifier>NY0-niveau</DepartmentLevelIdentifier>"
            "    <DepartmentName>Department5</DepartmentName>"
            "  </Department>"
            "  <Department>"
            "    <ActivationDate>1998-06-01</ActivationDate>"
            "    <DeactivationDate>9999-12-31</DeactivationDate>"
            "    <DepartmentIdentifier>dep5</DepartmentIdentifier>"
            "    <DepartmentUUIDIdentifier>50000000-0000-0000-0000-000000000000</DepartmentUUIDIdentifier>"
            "    <DepartmentLevelIdentifier>NY0-niveau</DepartmentLevelIdentifier>"
            "    <DepartmentName>Department 5</DepartmentName>"
            "  </Department>"
            "</GetDepartment20111201>",
        )
    )

    # Act
    test_client.post("/trigger")

    # Assert
    @retry()
    async def verify() -> None:
        # Verify that Departments have the correct parents and that their
        # validities have been updated
        dep6 = await graphql_client._testing__get_org_unit(
            UUID("60000000-0000-0000-0000-000000000000")
        )
        current = one(dep6.objects).current
        assert current.parent.uuid == UUID("50000000-0000-0000-0000-000000000000")  # type: ignore
        assert current.validity.from_.date() == date(1997, 1, 1)  # type: ignore

        dep5 = await graphql_client._testing__get_org_unit(
            UUID("50000000-0000-0000-0000-000000000000")
        )
        current = one(dep5.objects).current
        assert current.parent.uuid == UUID("10000000-0000-0000-0000-000000000000")  # type: ignore
        assert current.validity.from_.date() == date(1997, 1, 1)  # type: ignore

        dep1 = await graphql_client._testing__get_org_unit(
            UUID("10000000-0000-0000-0000-000000000000")
        )
        current = one(dep1.objects).current
        assert current.parent.uuid == UUID("12121212-1212-1212-1212-121212121212")  # type: ignore
        assert current.validity.from_.date() == date(1997, 1, 1)  # type: ignore

    await verify()

    # Act again - no operations should be performed
    r = test_client.post("/trigger")
    assert r.json() == []
