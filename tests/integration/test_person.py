# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from more_itertools import one
from respx import MockRouter

from sdtoolplus.autogenerated_graphql_client import EmployeeCreateInput
from sdtoolplus.autogenerated_graphql_client.input_types import EmployeeFilter
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo.timeline import _mo_end_to_timeline_end
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.types import CPRNumber

CPR = CPRNumber("0101011234")

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
async def test_person_create_new(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:
    A person dosnt exist in MO and is created

    Time  -----------------------t1--------------------------------------------------->

    MO (person does not exist)

    SD (given_name)              |-----------------Chuck-------------------------------
    SD (surname)                 |-----------------Norris------------------------------
    SD (cpr)                     |-----------------0101011234--------------------------

    "Assert"                     |------------------------1----------------------------
    intervals

    NOTE: we do not actually have temporal person data in SD!
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(1901, 1, 1, tzinfo=tz)

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

    mo_person = await graphql_client.get_person_timeline(
        EmployeeFilter(cpr_numbers=[CPR], from_date=None, to_date=None)
    )
    validity = one(one(mo_person.objects).validities)

    assert validity.validity.from_ == t1
    assert validity.validity.to is None
    assert validity.cpr_number == CPR
    assert validity.given_name == "Chuck"
    assert validity.surname == "Norris"


@pytest.mark.integration_test
async def test_person_timeline_update(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:
    A person exists in MO but with the wrong name. Test that the name is updated in MO.

    Time  ------------t1--------t2---------------------------------------------------->

    MO (given_name)   |-------------------Buck-----------------------------------------
    MO (surname)      |-------------------Lorris---------------------------------------
    MO (cpr)          |-------------------0101011234-----------------------------------

    "Arrange"         |---------------------------1------------------------------------
    intervals

    SD (givenname)    |---Buck--|-----------------Chuck--------------------------------
    MO (surname)      |--Lorris-|-----------------Norris-------------------------------
    MO (cpr)          |-------------------0101011234-----------------------------------

    "Assert"          |----1----|------------------------2-----------------------------
    intervals

    NOTE: we do not actually have temporal person data in SD! So t2 just indicates the
          point in time where the person data is changed in SD.
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(1901, 1, 1, tzinfo=tz)
    t2 = datetime.now(tz=tz)

    # Create person
    person_uuid = uuid4()
    await graphql_client.create_person(
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

    mo_person = await graphql_client.get_person_timeline(
        EmployeeFilter(uuids=[person_uuid], from_date=None, to_date=None)
    )
    validities = one(mo_person.objects).validities

    interval_1 = validities[0]
    assert interval_1.validity.from_ == t1
    assert _mo_end_to_timeline_end(interval_1.validity.to).date() == t2.date()
    assert interval_1.cpr_number == CPR
    assert interval_1.given_name == "Buck"
    assert interval_1.surname == "Lorris"

    interval_2 = validities[1]
    assert interval_2.validity.from_ is not None
    assert interval_2.validity.from_.date() == t2.date()
    assert _mo_end_to_timeline_end(interval_2.validity.to) == POSITIVE_INFINITY
    assert interval_2.cpr_number == CPR
    assert interval_2.given_name == "Chuck"
    assert interval_2.surname == "Norris"

    assert len(validities) == 2


# TODO: add test where MO-person validity should be extended
