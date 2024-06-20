from datetime import timezone, datetime, timedelta


TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def timestamp_now(timefmt: str = TIMESTAMP_FORMAT):
    return (datetime.now(timezone.utc) + timedelta(hours=-5)).strftime(timefmt)


def timestamp_from(time: str, timefmt: str = TIMESTAMP_FORMAT):
    return datetime.strptime(time, timefmt).replace(tzinfo=timezone.utc)
