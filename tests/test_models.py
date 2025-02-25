# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import time
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from sdtoolplus.models import Active
from sdtoolplus.models import Interval
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.models import combine_intervals

TZ = ZoneInfo("Europe/London")
TODAY_START = datetime.combine(datetime.now(), time.min, tzinfo=TZ)
YESTERDAY_START = TODAY_START - timedelta(days=1)
TOMORROW_START = TODAY_START + timedelta(days=1)
DAY_AFTER_TOMORROW_START = TODAY_START + timedelta(days=2)

MINUS_INFINITY = datetime.min.replace(tzinfo=TZ)
INFINITY = datetime.max.replace(tzinfo=TZ)


def test_entity_eq():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=TODAY_START, end=TOMORROW_START, value=True)
    active4 = Active(start=TOMORROW_START, end=TOMORROW_START, value=True)
    active5 = Active(start=TOMORROW_START, end=TOMORROW_START, value=True)

    # Act + Assert
    assert active1 == active1
    assert active1 != "Wrong object"
    assert active1 != active2
    assert active2 != active3
    assert active3 != active4
    assert active4 == active5


def test_timeline_eq():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=TODAY_START, end=TOMORROW_START, value=True)
    active4 = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=False)

    timeline1 = Timeline(intervals=(active1, active2))
    timeline2 = Timeline(intervals=(active3, active4))
    timeline3 = Timeline(intervals=(active3, active4))

    # Act + Assert
    assert timeline1 == timeline1
    assert timeline1 != "Wrong object"
    assert timeline1 != timeline2
    assert timeline2 == timeline3


def test_interval_must_have_identical_timezones():
    # Arrange
    datetime_with_timezone = datetime.now(tz=TZ)
    datetime_with_another_timezone = datetime.now(tz=ZoneInfo("Europe/Copenhagen"))
    datetime_without_timezone = datetime.now()

    # Act + Assert
    with pytest.raises(ValueError):
        Interval(start=datetime_without_timezone, end=datetime_with_timezone)

    with pytest.raises(ValueError):
        Interval(start=datetime_with_timezone, end=datetime_without_timezone)

    with pytest.raises(ValueError):
        Interval(start=datetime_with_timezone, end=datetime_with_another_timezone)


def test_combine_intervals():
    """
    --------------t1---------t2---------t3-------t4-------t5-----t6---------
    Input:        |----v1----|          |---v1---|---v1---|--v1--|---v2-----
    Output:       |----v1----|          |-----------v1-----------|---v2-----
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=TZ)
    t2 = datetime(2002, 1, 1, tzinfo=TZ)
    t3 = datetime(2003, 1, 1, tzinfo=TZ)
    t4 = datetime(2004, 1, 1, tzinfo=TZ)
    t5 = datetime(2005, 1, 1, tzinfo=TZ)
    t6 = datetime(2006, 1, 1, tzinfo=TZ)

    # Arrange
    intervals = (
        Active(start=t1, end=t2, value=True),
        Active(start=t3, end=t4, value=True),
        Active(start=t4, end=t5, value=True),
        Active(start=t5, end=t6, value=True),
        Active(start=t6, end=INFINITY, value=False),
    )

    # Act
    condensed = combine_intervals(intervals)

    # Assert
    assert condensed == (
        Active(start=t1, end=t2, value=True),
        Active(start=t3, end=t6, value=True),
        Active(start=t6, end=INFINITY, value=False),
    )


def test_combine_intervals_empty_input():
    # Act
    condensed = combine_intervals(tuple())

    # Assert
    assert condensed == tuple()


def test_combine_intervals_single_input():
    # Arrange
    intervals = (Active(start=MINUS_INFINITY, end=INFINITY, value=True),)

    # Act
    condensed = combine_intervals(intervals)

    # Assert
    assert condensed == intervals


def test_timeline_can_be_instantiated_correctly():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    # Act + Assert
    assert Timeline[Active](intervals=(active1, active2))


def test_timeline_entities_must_be_same_type():
    # Arrange
    active = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    unit_uuid = UnitName(start=TODAY_START, end=TOMORROW_START, value="name")

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active, unit_uuid))


def test_timeline_entities_must_be_intervals():
    with pytest.raises(ValueError):
        Timeline[str](intervals=("Not interval", "Not interval"))


def test_timeline_elements_must_be_sorted():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active2, active1))


def test_timeline_intervals_cannot_overlap():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TOMORROW_START, value=True)
    active2 = Active(start=TODAY_START, end=DAY_AFTER_TOMORROW_START, value=True)
    active3 = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active1, active2, active3))


def test_timeline_successively_repeated_interval_values_not_allowed():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active1, active2))


def test_timeline_successively_repeated_interval_allowed_when_holes_in_timeline():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=DAY_AFTER_TOMORROW_START, end=INFINITY, value=True)

    # Act + Assert
    assert Timeline[Active](intervals=(active1, active2))


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        (
            YESTERDAY_START + timedelta(hours=12),
            Active(start=YESTERDAY_START, end=TODAY_START, value=True),
        ),
        (
            TODAY_START + timedelta(hours=12),
            Active(start=TODAY_START, end=TOMORROW_START, value=False),
        ),
        (YESTERDAY_START - timedelta(hours=12), None),
    ],
)
def test_timeline_entity_at(timestamp: datetime, expected: Active | None):
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    timeline = Timeline[Active](intervals=(active1, active2))

    # Act
    actual = timeline.entity_at(timestamp)

    # Assert
    assert actual == expected


def test_timeline_diff0():
    """
    Us:          (empty)
    Them:        (empty)
    Diff:        (empty)
    """

    # Arrange
    timeline = Timeline[Active]()

    # Act
    diff = timeline.diff(timeline)

    # Assert
    assert diff == Timeline[Active]()


def test_timeline_diff1():
    """
    Us:          |---------- v ------------|
    Them:        |---------- v ------------|
    Diff:                 (empty)
    """
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True)

    timeline = Timeline[Active](intervals=(active1, active2, active3))

    # Act
    diff = timeline.diff(timeline)

    # Assert
    assert diff == Timeline[Active]()


def test_timeline_diff2():
    """
    Us:          ------------------ v ------------|
    Them:               |---------- v ------------|
    Diff:        -- v --|
    """

    # Arrange
    active_us = Active(start=MINUS_INFINITY, end=DAY_AFTER_TOMORROW_START, value=True)
    active_them = Active(start=TODAY_START, end=DAY_AFTER_TOMORROW_START, value=True)

    us = Timeline[Active](intervals=(active_us,))
    them = Timeline[Active](intervals=(active_them,))

    # Act
    diff = us.diff(them)

    # Assert
    assert diff == Timeline[Active](
        intervals=(Active(start=MINUS_INFINITY, end=TODAY_START, value=True),)
    )


def test_timeline_diff3():
    """
    Us:                    |---------- v ------------|
    Them:        --------------------- v ------------|
    Diff:        -- None --|
    """

    # Arrange
    active_us = Active(start=TODAY_START, end=DAY_AFTER_TOMORROW_START, value=True)
    active_them = Active(start=MINUS_INFINITY, end=DAY_AFTER_TOMORROW_START, value=True)

    us = Timeline[Active](intervals=(active_us,))
    them = Timeline[Active](intervals=(active_them,))

    # Act
    diff = us.diff(them)

    # Assert
    assert diff == Timeline[Active](
        intervals=(Active(start=MINUS_INFINITY, end=TODAY_START, value=None),)
    )


def test_timeline_diff4():
    """
    Us:                          |------- v -------|
    Them:             |------- v --------|
    Diff:             |-- None --|       |--- v ---|
    """

    # Arrange
    active_us = Active(start=TODAY_START, end=DAY_AFTER_TOMORROW_START, value=True)
    active_them = Active(start=YESTERDAY_START, end=TOMORROW_START, value=True)

    us = Timeline[Active](intervals=(active_us,))
    them = Timeline[Active](intervals=(active_them,))

    # Act
    diff = us.diff(them)

    # Assert
    assert diff == Timeline[Active](
        intervals=(
            Active(start=YESTERDAY_START, end=TODAY_START, value=None),
            Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True),
        )
    )


def test_timeline_diff5():
    """
    Us:                                       |------- v -------|
    Them:             |------- v --------|
    Diff:             |------ None ------|    |------- v -------|
    """

    # Arrange
    active_us = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True)
    active_them = Active(start=YESTERDAY_START, end=TODAY_START, value=True)

    us = Timeline[Active](intervals=(active_us,))
    them = Timeline[Active](intervals=(active_them,))

    # Act
    diff = us.diff(them)

    # Assert
    assert diff == Timeline[Active](
        intervals=(
            Active(start=YESTERDAY_START, end=TODAY_START, value=None),
            Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True),
        )
    )


def test_timeline_diff6():
    """
    --------------t1--------t2---------t3------t4-----t5-------------------t6---------
    Us:           |-------- v1 --------|              |-------- v2 --------|
    Them:                    |------- v1 ------|--------------- v2 -------------------
    Diff:         |--- v1 ---|         |---- None ----|                    |-- None --
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=TZ)
    t2 = datetime(2002, 1, 1, tzinfo=TZ)
    t3 = datetime(2003, 1, 1, tzinfo=TZ)
    t4 = datetime(2004, 1, 1, tzinfo=TZ)
    t5 = datetime(2005, 1, 1, tzinfo=TZ)
    t6 = datetime(2006, 1, 1, tzinfo=TZ)

    us = Timeline[Active](
        intervals=(
            Active(start=t1, end=t3, value=True),
            Active(start=t5, end=t6, value=False),
        )
    )
    them = Timeline[Active](
        intervals=(
            Active(start=t2, end=t4, value=True),
            Active(start=t4, end=INFINITY, value=False),
        )
    )

    # Act
    diff = us.diff(them)

    # Assert
    assert diff == Timeline[Active](
        intervals=(
            Active(start=t1, end=t2, value=True),
            Active(start=t3, end=t5, value=None),
            Active(start=t6, end=INFINITY, value=None),
        )
    )
