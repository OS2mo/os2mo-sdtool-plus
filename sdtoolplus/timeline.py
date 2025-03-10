# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from itertools import chain
from itertools import pairwise
from typing import cast

import structlog
from more_itertools import collapse

from sdtoolplus.depends import GraphQLClient
from sdtoolplus.log import anonymize_cpr
from sdtoolplus.mo.timeline import create_or_update_engagement
from sdtoolplus.mo.timeline import create_or_update_ou
from sdtoolplus.mo.timeline import terminate_engagement
from sdtoolplus.mo.timeline import terminate_ou
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import Interval
from sdtoolplus.models import UnitTimeline

logger = structlog.stdlib.get_logger()


def _get_ou_interval_endpoints(ou_timeline: UnitTimeline) -> set[datetime]:
    return set(
        collapse(
            set(
                (i.start, i.end)
                for i in chain(
                    cast(tuple[Interval, ...], ou_timeline.active.intervals),
                    cast(tuple[Interval, ...], ou_timeline.name.intervals),
                    cast(tuple[Interval, ...], ou_timeline.unit_id.intervals),
                    cast(tuple[Interval, ...], ou_timeline.unit_level.intervals),
                )
            )
        )
    )


def _get_eng_interval_endpoints(eng_timeline: EngagementTimeline) -> set[datetime]:
    return set(
        collapse(
            set(
                (i.start, i.end)
                for i in chain(
                    cast(tuple[Interval, ...], eng_timeline.eng_active.intervals),
                    cast(tuple[Interval, ...], eng_timeline.eng_key.intervals),
                    cast(tuple[Interval, ...], eng_timeline.eng_name.intervals),
                    cast(tuple[Interval, ...], eng_timeline.eng_unit.intervals),
                )
            )
        )
    )


async def sync_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    org_unit_type_user_key: str,
    sd_unit_timeline: UnitTimeline,
    mo_unit_timeline: UnitTimeline,
    dry_run: bool,
) -> None:
    logger.info("Create, update or terminate OU in MO", org_unit=str(org_unit))

    sd_interval_endpoints = _get_ou_interval_endpoints(sd_unit_timeline)
    mo_interval_endpoints = _get_ou_interval_endpoints(mo_unit_timeline)

    endpoints = list(sd_interval_endpoints.union(mo_interval_endpoints))
    endpoints.sort()
    logger.debug("List of endpoints", endpoints=endpoints)

    for endpoint1, endpoint2 in pairwise(endpoints):
        logger.debug(
            "Processing endpoint pair", endpoint1=endpoint1, endpoint2=endpoint2
        )
        if sd_unit_timeline.equal_at(endpoint1, mo_unit_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_unit_timeline.has_value(endpoint1):
            await create_or_update_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=endpoint1,
                end=endpoint2,
                sd_unit_timeline=sd_unit_timeline,
                org_unit_type_user_key=org_unit_type_user_key,
            )
        else:
            await terminate_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=endpoint1,
                end=endpoint2,
            )


async def sync_eng(
    gql_client: GraphQLClient,
    cpr: str,
    emp_id: str,
    sd_eng_timeline: EngagementTimeline,
    mo_eng_timeline: EngagementTimeline,
    dry_run: bool,
) -> None:
    logger.info(
        "Create, update or terminate engagement in MO",
        cpr=anonymize_cpr(cpr),
        emp_id=emp_id,
    )

    sd_interval_endpoints = _get_eng_interval_endpoints(sd_eng_timeline)
    mo_interval_endpoints = _get_eng_interval_endpoints(mo_eng_timeline)

    endpoints = list(sd_interval_endpoints.union(mo_interval_endpoints))
    endpoints.sort()
    logger.debug("List of endpoints", endpoints=endpoints)

    for endpoint1, endpoint2 in pairwise(endpoints):
        logger.debug(
            "Processing endpoint pair", endpoint1=endpoint1, endpoint2=endpoint2
        )
        if sd_eng_timeline.equal_at(endpoint1, mo_eng_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_eng_timeline.has_value(endpoint1):
            await create_or_update_engagement(
                gql_client=gql_client,
                cpr=cpr,
                user_key=emp_id,
                start=endpoint1,
                end=endpoint2,
                sd_eng_timeline=sd_eng_timeline,
            )
        else:
            await terminate_engagement(
                gql_client=gql_client,
                cpr=cpr,
                user_key=emp_id,
                start=endpoint1,
                end=endpoint2,
            )
