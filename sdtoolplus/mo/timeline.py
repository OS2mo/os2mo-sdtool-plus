# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import timedelta
from uuid import UUID

import structlog
from more_itertools import first
from more_itertools import one

from sdtoolplus.autogenerated_graphql_client import EngagementCreateInput
from sdtoolplus.autogenerated_graphql_client import EngagementTerminateInput
from sdtoolplus.autogenerated_graphql_client import EngagementUpdateInput
from sdtoolplus.autogenerated_graphql_client import OrganisationUnitCreateInput
from sdtoolplus.autogenerated_graphql_client import OrganisationUnitTerminateInput
from sdtoolplus.autogenerated_graphql_client import OrganisationUnitUpdateInput
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.log import anonymize_cpr
from sdtoolplus.mo_org_unit_importer import OrgUnitLevelUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitTypeUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals

logger = structlog.stdlib.get_logger()


def _mo_end_datetime(d: datetime | None) -> datetime:
    return d + timedelta(days=1) if d is not None else POSITIVE_INFINITY


def _get_mo_validity(start: datetime, end: datetime) -> RAValidityInput:
    mo_end: datetime | None = end
    assert mo_end is not None
    mo_end = (
        # Subtract one day due to MO
        None if mo_end == POSITIVE_INFINITY else mo_end - timedelta(days=1)
    )
    return RAValidityInput(from_=start, to=mo_end)


async def _get_ou_type(
    gql_client: GraphQLClient,
    org_unit_type_user_key: str,
) -> OrgUnitTypeUUID:
    ou_type_classes = await gql_client.get_facet_class(
        "org_unit_type", org_unit_type_user_key
    )

    current = one(ou_type_classes.objects).current
    assert current is not None
    return current.uuid


async def _get_ou_level(
    gql_client: GraphQLClient,
    org_unit_level_user_key: str,
) -> OrgUnitLevelUUID:
    ou_level_classes = await gql_client.get_facet_class(
        "org_unit_level", org_unit_level_user_key
    )

    current = one(ou_level_classes.objects).current
    assert current is not None
    return current.uuid


async def get_ou_timeline(
    gql_client: GraphQLClient,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    logger.info("Get MO org unit timeline", unit_uuid=str(unit_uuid))

    gql_timelime = await gql_client.get_org_unit_timeline(
        unit_uuid=unit_uuid, from_date=None, to_date=None
    )
    objects = gql_timelime.objects

    if not objects:
        return UnitTimeline(
            active=Timeline[Active](),
            name=Timeline[UnitName](),
            unit_id=Timeline[UnitId](),
            unit_level=Timeline[UnitLevel](),
            parent=Timeline[UnitParent](),
        )

    validities = one(objects).validities

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    id_intervals = tuple(
        UnitId(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.user_key,
        )
        for obj in validities
    )

    level_intervals = tuple(
        UnitLevel(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.org_unit_level.name if obj.org_unit_level is not None else None,
        )
        for obj in validities
    )

    name_intervals = tuple(
        UnitName(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.name,
        )
        for obj in validities
    )

    parent_intervals = tuple(
        UnitParent(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.parent.uuid if obj.parent is not None else None,
        )
        for obj in validities
    )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
        parent=Timeline[UnitParent](intervals=combine_intervals(parent_intervals)),
    )
    logger.debug("MO OU timeline", timeline=timeline)

    return timeline


async def create_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
) -> None:
    logger.info("Creating OU", uuid=str(org_unit))
    logger.debug("Creating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline)

    # Get the OU type UUID
    ou_type_uuid = await _get_ou_type(gql_client, org_unit_type_user_key)

    # Get the OU level UUID
    unit_level = sd_unit_timeline.unit_level.entity_at(start)
    ou_level_uuid = await _get_ou_level(gql_client, unit_level.value)  # type: ignore

    await gql_client.create_org_unit(
        OrganisationUnitCreateInput(
            uuid=org_unit,
            validity=_get_mo_validity(start, end),
            name=sd_unit_timeline.name.entity_at(start).value,
            user_key=sd_unit_timeline.unit_id.entity_at(start).value,
            parent=sd_unit_timeline.parent.entity_at(start).value,
            org_unit_type=ou_type_uuid,
            org_unit_level=ou_level_uuid,
        )
    )


async def update_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
) -> None:
    logger.info("Updating OU", uuid=str(org_unit))
    logger.debug("Updating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline)

    mo_validity = _get_mo_validity(start, end)
    # TODO: refactor get_org_unit_timeline to take a RAValidityInput object instead of
    # start and end dates
    ou = await gql_client.get_org_unit_timeline(
        org_unit, mo_validity.from_, mo_validity.to
    )

    # Get the OU type UUID
    ou_type_uuid = await _get_ou_type(gql_client, org_unit_type_user_key)

    # Get the OU level UUID
    unit_level = sd_unit_timeline.unit_level.entity_at(start)
    ou_level_uuid = await _get_ou_level(gql_client, unit_level.value)  # type: ignore

    if ou.objects:
        # The OU may not exist in this validity period
        for validity in one(ou.objects).validities:
            org_unit_hierarchy = (
                validity.org_unit_hierarchy_model.uuid
                if validity.org_unit_hierarchy_model is not None
                else None
            )
            time_planning = (
                validity.time_planning.uuid
                if validity.time_planning is not None
                else None
            )

            await gql_client.update_org_unit(
                OrganisationUnitUpdateInput(
                    uuid=org_unit,
                    validity=_get_mo_validity(start, end),
                    name=sd_unit_timeline.name.entity_at(start).value,
                    user_key=sd_unit_timeline.unit_id.entity_at(start).value,
                    parent=sd_unit_timeline.parent.entity_at(start).value,
                    org_unit_type=ou_type_uuid,
                    org_unit_level=ou_level_uuid,
                    org_unit_hierarchy=org_unit_hierarchy,
                    time_planning=time_planning,
                )
            )
        return

    await gql_client.update_org_unit(
        OrganisationUnitUpdateInput(
            uuid=org_unit,
            validity=_get_mo_validity(start, end),
            name=sd_unit_timeline.name.entity_at(start).value,
            user_key=sd_unit_timeline.unit_id.entity_at(start).value,
            parent=sd_unit_timeline.parent.entity_at(start).value,
            org_unit_type=ou_type_uuid,
            org_unit_level=ou_level_uuid,
        )
    )


async def terminate_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
) -> None:
    logger.info("(Re-)terminate OU", org_unit=str(org_unit))

    mo_validity = _get_mo_validity(start, end)

    if mo_validity.to is not None:
        payload = OrganisationUnitTerminateInput(
            uuid=org_unit,
            from_=mo_validity.from_,
            to=mo_validity.to,
        )
    else:
        payload = OrganisationUnitTerminateInput(
            uuid=org_unit,
            # Converting from "from" to "to" due to the wierd way terminations in MO work
            to=mo_validity.from_ - timedelta(days=1),
        )

    await gql_client.terminate_org_unit(payload)


async def get_engagement_timeline(
    gql_client: GraphQLClient,
    cpr: str,
    user_key: str,
) -> EngagementTimeline:
    logger.info("Get MO engagement timeline", cpr=anonymize_cpr(cpr), emp_id=user_key)

    gql_timeline = await gql_client.get_engagement_timeline(
        cpr=cpr, user_key=user_key, from_date=None, to_date=None
    )
    objects = gql_timeline.objects

    if not objects:
        return EngagementTimeline(
            eng_active=Timeline[Active](),
            eng_key=Timeline[EngagementKey](),
            eng_name=Timeline[EngagementName](),
            eng_unit=Timeline[EngagementUnit](),
        )

    validities = one(objects).validities

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    key_intervals = tuple(
        EngagementKey(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.job_function.user_key,
        )
        for obj in validities
    )

    name_intervals = tuple(
        EngagementName(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            # TODO: introduce name strategy here
            value=obj.extension_1,
        )
        for obj in validities
    )

    unit_intervals = tuple(
        EngagementUnit(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=one(obj.org_unit).uuid,
        )
        for obj in validities
    )

    timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        eng_key=Timeline[EngagementKey](intervals=combine_intervals(key_intervals)),
        eng_name=Timeline[EngagementName](intervals=combine_intervals(name_intervals)),
        eng_unit=Timeline[EngagementUnit](intervals=combine_intervals(unit_intervals)),
    )
    logger.debug("MO engagement timeline", timeline=timeline)

    return timeline


async def create_engagement(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    sd_eng_timeline: EngagementTimeline,
) -> None:
    logger.info("Creating engagement", person=str(person), emp_id=user_key)
    logger.debug(
        "Creating engagement", start=start, end=end, sd_unit_timeline=sd_eng_timeline
    )

    # Get the engagement type
    # TODO: we need to find out how (if possible) to get the engagement type from SD
    r_eng_type = await gql_client.get_facet_class(
        "engagement_type", "SDbe3edd69-16c1-4dcb-a8c1-16b4db611b9b"
    )
    current_eng_type = one(r_eng_type.objects).current
    assert current_eng_type is not None
    eng_type_uuid = current_eng_type.uuid

    # Get the job_function
    r_job_function = await gql_client.get_facet_class(
        "engagement_job_function",
        str(sd_eng_timeline.eng_key.entity_at(start).value),
    )
    current_job_function = one(r_job_function.objects).current
    assert current_job_function is not None
    job_function_uuid = current_job_function.uuid

    await gql_client.create_engagement(
        EngagementCreateInput(
            user_key=user_key,
            validity=_get_mo_validity(start, end),
            # TODO: introduce extension_1 strategy
            extension_1=sd_eng_timeline.eng_name.entity_at(start),
            person=person,
            # TODO: introduce org_unit strategy
            org_unit=sd_eng_timeline.eng_unit.entity_at(start),
            engagement_type=eng_type_uuid,
            # TODO: introduce job_function strategy
            job_function=job_function_uuid,
        )
    )


async def update_engagement(
    gql_client: GraphQLClient,
    person: UUID,
    cpr: str,  # TODO: to be removed in later commits
    user_key: str,
    start: datetime,
    end: datetime,
    sd_eng_timeline: EngagementTimeline,
) -> None:
    logger.info("Update engagement", cpr=anonymize_cpr(cpr), emp_id=user_key)
    logger.debug(
        "Update engagement", start=start, end=end, sd_unit_timeline=sd_eng_timeline
    )

    # Get the job_function
    r_job_function = await gql_client.get_facet_class(
        "engagement_job_function",
        str(sd_eng_timeline.eng_key.entity_at(start).value),
    )
    current_job_function = one(r_job_function.objects).current
    assert current_job_function is not None
    job_function_uuid = current_job_function.uuid

    # Get the engagement type
    # TODO: we need to find out how (if possible) to get the engagement type from SD
    r_eng_type = await gql_client.get_facet_class(
        "engagement_type", "SDbe3edd69-16c1-4dcb-a8c1-16b4db611b9b"
    )
    current_eng_type = one(r_eng_type.objects).current
    assert current_eng_type is not None
    eng_type_uuid = current_eng_type.uuid

    mo_validity = _get_mo_validity(start, end)

    eng = await gql_client.get_engagement_timeline(cpr, user_key, start, end)

    if eng.objects:
        # The engagement already exists in this validity period

        for validity in one(eng.objects).validities:
            await gql_client.update_engagement(
                EngagementUpdateInput(
                    uuid=validity.uuid,
                    user_key=user_key,
                    primary=validity.primary.uuid
                    if validity.primary is not None
                    else None,
                    validity=mo_validity,
                    # TODO: introduce extention_1 strategy
                    extension_1=sd_eng_timeline.eng_name.entity_at(start).value,
                    extension_2=validity.extension_2,
                    extension_3=validity.extension_3,
                    extension_4=validity.extension_4,
                    extension_5=validity.extension_5,
                    extension_6=validity.extension_6,
                    extension_7=validity.extension_7,
                    extension_8=validity.extension_8,
                    extension_9=validity.extension_9,
                    extension_10=validity.extension_10,
                    person=person,
                    org_unit=sd_eng_timeline.eng_unit.entity_at(start).value,
                    # TODO: we need to find out how (if possible) to get the engagement type from SD
                    engagement_type=validity.engagement_type.uuid,
                    job_function=job_function_uuid,
                )
            )
        return

    # The engagement does not already exist in this validity period
    eng = await gql_client.get_engagement_timeline(
        cpr=cpr, user_key=user_key, from_date=None, to_date=None
    )
    await gql_client.update_engagement(
        EngagementUpdateInput(
            uuid=first(one(eng.objects).validities).uuid,
            user_key=user_key,
            validity=mo_validity,
            # TODO: introduce extention_1 strategy
            extension_1=sd_eng_timeline.eng_name.entity_at(start).value,
            person=person,
            org_unit=sd_eng_timeline.eng_unit.entity_at(start).value,
            # TODO: we need to find out how (if possible) to get the engagement type from SD
            engagement_type=eng_type_uuid,
            job_function=job_function_uuid,
        )
    )


async def terminate_engagement(
    gql_client: GraphQLClient,
    cpr: str,
    user_key: str,
    start: datetime,
    end: datetime,
) -> None:
    logger.info(
        "(Re-)terminate engagement",
        cpr=anonymize_cpr(cpr),
        user_key=user_key,
        start=start,
        end=end,
    )

    mo_validity = _get_mo_validity(start, end)

    eng = await gql_client.get_engagement_timeline(
        cpr=cpr, user_key=user_key, from_date=None, to_date=None
    )
    eng_uuid = first(one(eng.objects).validities).uuid

    if mo_validity.to is not None:
        payload = EngagementTerminateInput(
            uuid=eng_uuid, from_=mo_validity.from_, to=mo_validity.to
        )
    else:
        payload = EngagementTerminateInput(
            uuid=eng_uuid,
            # Converting from "from" to "to" due to the wierd way terminations in MO work
            to=mo_validity.from_ - timedelta(days=1),
        )

    await gql_client.terminate_engagement(payload)
