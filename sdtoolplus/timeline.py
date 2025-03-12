# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from itertools import chain
from itertools import pairwise
from typing import cast

import structlog
from more_itertools import collapse

from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo.timeline import create_ou
from sdtoolplus.mo.timeline import terminate_ou
from sdtoolplus.mo.timeline import update_ou
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
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

    for start, end in pairwise(endpoints):
        logger.debug("Processing endpoint pair", start=start, end=end)
        if sd_unit_timeline.equal_at(start, mo_unit_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_unit_timeline.has_value(start):
            ou = await gql_client.get_org_unit_timeline(
                unit_uuid=org_unit, from_date=None, to_date=None
            )
            if ou.objects:
                await update_ou(
                    gql_client=gql_client,
                    org_unit=org_unit,
                    start=start,
                    end=end,
                    sd_unit_timeline=sd_unit_timeline,
                    org_unit_type_user_key=org_unit_type_user_key,
                )
                continue
            await create_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
                sd_unit_timeline=sd_unit_timeline,
                org_unit_type_user_key=org_unit_type_user_key,
            )
        else:
            await terminate_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
            )
