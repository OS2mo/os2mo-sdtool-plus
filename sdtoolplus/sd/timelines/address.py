# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import cast
from uuid import UUID

import structlog
from aiohttp import ClientError
from fastramqpi.os2mo_dar_client import AsyncDARClient

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitPostalAddress
from sdtoolplus.models import combine_intervals

logger = structlog.stdlib.get_logger()


async def _get_dar_address(dar_client: AsyncDARClient, address: str) -> UUID | None:
    try:
        dar_uuid_address = await dar_client.search(address)
    except (ClientError, TimeoutError, ValueError, KeyError):
        # This will happen when DAR is occasionally down or returns an
        # unexpected response. In this case, the OU event fails and will be
        # retried later.
        logger.error("Failed to get DAR address", addr=address)
        raise

    if dar_uuid_address is None:
        logger.warning("No DAR address match", addr=address)
        return None

    logger.info("Found address in DAR", dar_uuid_address=dar_uuid_address)
    return dar_uuid_address


async def sd_postal_dar_address_strategy(
    sd_postal_address_timeline: Timeline[UnitPostalAddress],
) -> Timeline[UnitPostalAddress]:
    logger.info("Getting DAR address timeline")

    dar_client = AsyncDARClient()

    dar_uuid_intervals = []
    async with dar_client:
        for interval in sd_postal_address_timeline.intervals:
            logger.info("Processing postal address interval", interval=interval.dict())

            interval_value = cast(str, interval.value)  # To make mypy happy...
            # The SD postal address has the format "<street>, <postal code>, <town>",
            # but DAR requires the format "<street>, <postal code> <town>", so we
            # remove the last comma (the street may contain commas itself)
            dar_search_address = " ".join(interval_value.rsplit(", ", 1))
            dar_uuid_address = await _get_dar_address(dar_client, dar_search_address)

            if dar_uuid_address is None:
                continue

            dar_uuid_intervals.append(
                UnitPostalAddress(
                    start=interval.start,
                    end=interval.end,
                    value=str(dar_uuid_address),
                )
            )

    desired_address_timeline = Timeline[UnitPostalAddress](
        intervals=combine_intervals(tuple(dar_uuid_intervals)),
    )

    logger.info(
        "Desired DAR address timeline",
        desired_address_timeline=desired_address_timeline.dict(),
    )

    return desired_address_timeline


async def sd_postal_address_strategy(
    settings: SDToolPlusSettings,
    sd_postal_address_timeline: Timeline[UnitPostalAddress],
) -> Timeline[UnitPostalAddress]:
    """
    Strategy/state pattern for getting the SD postal address timeline based on
    the settings, i.e. whether to use text addresses or DAR (UUID) addresses or
    something else (the latter is not yet implemented).
    """
    if settings.use_dar_addresses:
        return await sd_postal_dar_address_strategy(sd_postal_address_timeline)
    return sd_postal_address_timeline
