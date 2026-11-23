from datetime import datetime, time, timedelta


WORKDAY_START = time(9, 30)
WORKDAY_END = time(18, 30)
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)
CLEANING_BUFFER = timedelta(minutes=15)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Return whether two half-open time ranges overlap.

    A booking ending when another starts is allowed: [10:00, 11:00) and
    [11:00, 12:00) share an endpoint but no time.
    """
    return a_start < b_end and b_start < a_end


def needs_cleaning_buffer(start: datetime, end: datetime) -> bool:
    return end - start > timedelta(minutes=60)


def room_intervals_conflict(
    existing_start: datetime,
    existing_end: datetime,
    candidate_start: datetime,
    candidate_end: datetime,
) -> bool:
    """Check room use, including the required post-meeting cleaning buffer."""
    if needs_cleaning_buffer(existing_start, existing_end):
        existing_end += CLEANING_BUFFER
    if needs_cleaning_buffer(candidate_start, candidate_end):
        candidate_end += CLEANING_BUFFER
    return overlaps(existing_start, existing_end, candidate_start, candidate_end)


def overlaps_lunch(start: datetime, end: datetime) -> bool:
    lunch_start = datetime.combine(start.date(), LUNCH_START)
    lunch_end = datetime.combine(start.date(), LUNCH_END)
    return overlaps(start, end, lunch_start, lunch_end)
