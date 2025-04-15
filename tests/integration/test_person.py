# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from uuid import UUID
from uuid import uuid4

import pytest
from httpx import AsyncClient
from more_itertools import one
from respx import MockRouter

from sdtoolplus.autogenerated_graphql_client import EmployeeCreateInput
from sdtoolplus.autogenerated_graphql_client.input_types import EmployeeFilter
from sdtoolplus.depends import GraphQLClient

CPR = "0101011234"

EMP_ID = "12345"
TODAY_SD_FORMAT = date.strftime(date.today(), "%Y-%m-%d")
TODAY_URL_FORMAT = date.strftime(date.today(), "%d.%m.%Y")
GETPERSON_URL = f"https://service.sd.dk/sdws/GetPerson20111201?InstitutionIdentifier=II&EffectiveDate={TODAY_URL_FORMAT}&PersonCivilRegistrationIdentifier={CPR}&StatusActiveIndicator=True&StatusPassiveIndicator=False&ContactInformationIndicator=True&PostalAddressIndicator=True"

SD_RESP = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <GetPerson20111201 creationDateTime="2025-04-09T09:47:55">
        <RequestStructure>
            <InstitutionIdentifier>II</InstitutionIdentifier>
            <PersonCivilRegistrationIdentifier>0101011234</PersonCivilRegistrationIdentifier>
            <EffectiveDate>{TODAY_SD_FORMAT}</EffectiveDate>
            <StatusActiveIndicator>true</StatusActiveIndicator>
            <StatusPassiveIndicator>false</StatusPassiveIndicator>
            <ContactInformationIndicator>false</ContactInformationIndicator>
            <PostalAddressIndicator>false</PostalAddressIndicator>
        </RequestStructure>
        <Person>
            <PersonCivilRegistrationIdentifier>0101011234</PersonCivilRegistrationIdentifier>
            <PersonGivenName>Chuck</PersonGivenName>
            <PersonSurnameName>Norris</PersonSurnameName>
            <Employment>
                <EmploymentIdentifier>{EMP_ID}</EmploymentIdentifier>
            </Employment>
        </Person>
    </GetPerson20111201>
"""


@pytest.mark.integration_test
async def test_person_not_in_sd(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    """
    We are testing the case where the person is not found in SD. We should return
    HTTP 404. Note: if the person actually exists in MO, we will not terminate the
    person in MO.
    """
    # Arrange

    cpr = "0101010101"
    get_person_url = f"https://service.sd.dk/sdws/GetPerson20111201?InstitutionIdentifier=II&EffectiveDate={TODAY_URL_FORMAT}&PersonCivilRegistrationIdentifier={cpr}&StatusActiveIndicator=True&StatusPassiveIndicator=False&ContactInformationIndicator=True&PostalAddressIndicator=True"

    respx_mock.get(get_person_url).respond(
        content_type="text/xml;charset=UTF-8",
        content="""
        <Envelope>
            <Body>
                <Fault>
                    <faultcode>soapenv:soapenvClient.ParameterError</faultcode>
                    <faultstring>
                        The stated PersonCivilRegistrationIdentifier '0101010101' does not exist.
                    </faultstring>
                    <faultactor>
                        dk.eg.sd.loen.webservices.web.sdws.BusinessHandler.qm.GetPerson20111201BO
                    </faultactor>
                    <detail>
                        <string>
                            Missing or invalid parameter from client: "The stated PersonCivilRegistrationIdentifier '0101010101' does not exist."
                        </string>
                    </detail>
                </Fault>
            </Body>
        </Envelope>
        """,
    )

    # Act
    r = await test_client.post(
        "/timeline/sync/person",
        json={
            "institution_identifier": "II",
            "cpr": cpr,
        },
    )

    # Assert
    assert r.status_code == 404


@pytest.mark.integration_test
async def test_person_timeline_create_new(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:
    A person dosnt exist in MO and is created


    MO (givenname)
    SD (givenname)              |-----------------Chuck--------------------------------------

    """
    # Arrange
    # Ensure the person doesn't exist yet
    mo_person_before = await graphql_client.get_person(cpr=CPR)

    assert mo_person_before.objects == []
    respx_mock.get(GETPERSON_URL).respond(
        content_type="text/xml;charset=UTF-8",
        content=SD_RESP,
    )

    # Act
    r = await test_client.post(
        "/timeline/sync/person",
        json={
            "institution_identifier": "II",
            "cpr": CPR,
        },
    )

    # Assert
    assert r.status_code == 200
    mo_person = await graphql_client.get_person(cpr=CPR)
    assert isinstance(one(mo_person.objects).uuid, UUID)


@pytest.mark.integration_test
async def test_person_timeline_update(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:
    A person exists in MO but with the wrong name. Test that the name is updated in MO.


    MO (givenname)   |-------------------Buck-----------------------------------------------------
    SD (givenname)              |-----------------Chuck-------------------------------------------

    "Assert"         |----1----||--2--------------------------------------------------------------
    intervals
    """
    # Arrange

    # Create person
    person_uuid = uuid4()

    mo_person = await graphql_client.create_person(
        EmployeeCreateInput(
            uuid=person_uuid,
            cpr_number=CPR,
            given_name="Buck",
            surname="Lorris",
        )
    )
    respx_mock.get(GETPERSON_URL).respond(
        content_type="text/xml;charset=UTF-8",
        content=SD_RESP,
    )

    # Act
    r = await test_client.post(
        "/timeline/sync/person",
        json={
            "institution_identifier": "II",
            "cpr": CPR,
        },
    )

    # Assert
    assert r.status_code == 200

    # Check that there are only one validity from now to infinity with the correct data
    mo_timeline = await graphql_client.get_person_timeline(
        filter=EmployeeFilter(
            uuids=[mo_person.uuid], from_date=datetime.today(), to_date=None
        )
    )
    validities = one(mo_timeline.objects).validities

    assert len(validities) == 1
    assert one(validities).given_name == "Chuck"
    assert one(validities).surname == "Norris"
    assert one(validities).cpr_number == CPR

    # Check that there are another validity before today with the old data
    mo_timeline = await graphql_client.get_person_timeline(
        filter=EmployeeFilter(uuids=[mo_person.uuid], from_date=None, to_date=None)
    )
    validities = one(mo_timeline.objects).validities

    assert len(validities) == 2

    assert validities[0].given_name == "Buck"
    assert validities[1].given_name == "Chuck"
