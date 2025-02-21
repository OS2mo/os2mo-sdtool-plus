# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

def test__get_termination_intervals():
    """
    --------------t1--------t2---------t3------t4-----t5-------------------t6---------
    Diff:         |---True--|          |-----None-----|                    |---None---
    Term                    |---------------------------------------------------------
    Us:           |-------- v1 --------|              |-------- v2 --------|
    Them:                    |------- v1 ------|--------------- v2 -------------------
    Diff:         |--- v1 ---|         |---- None ----|                    |-- None --
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2002, 1, 1, tzinfo=timezone.utc)
    t3 = datetime(2003, 1, 1, tzinfo=timezone.utc)
    t4 = datetime(2004, 1, 1, tzinfo=timezone.utc)
    t5 = datetime(2005, 1, 1, tzinfo=timezone.utc)
    t6 = datetime(2006, 1, 1, tzinfo=timezone.utc)

    diff_timeline:     |--- None ---|
    """