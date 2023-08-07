import datetime
import re
from typing import Optional

SG_DATE_FORMAT = "%Y-%m-%d"  # E.g: 2022-02-22
SG_DT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # 2023-08-07T06:29:35Z where Z indicates UTC
UTC = datetime.timezone.utc
LOCAL_TZ = datetime.datetime.utcnow().astimezone().tzinfo


def validate_sg_date_format(date: str) -> bool:
    """Validate SG Date Format

    Date must be YYYY-MM-DD value. E.g: 2022-02-22

    Parameters
    ----------
    date : str
        The date string in SG Date format

    Returns
    -------
    bool
        True if valid SG Date format

    """
    result = re.match(
        r"^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$",
        date,
    )
    return bool(result)


def try_strptime(dt_str: str, use_local_tz=False) -> Optional[datetime.datetime]:
    """Try strptime

    Take note that SG datetime string format is in UTC timezone

    Parameters
    ----------
    dt_str : str
        The datetime string
    use_local_tz : bool
        Set True to return datetime object with local timezone attached and
        adjusted. Default False will return UTC datetime object

    Returns
    -------
    datetime.datetime or None

    """
    if not dt_str:
        return None

    # TODO: Simplify this logic as there should only one... string format unless
    #  Autodesk decided to return a completely new datetime string format
    dt_fmts = [
        SG_DT_FORMAT,
    ]

    for dt_fmt in dt_fmts:
        try:
            dt = datetime.datetime.strptime(dt_str, dt_fmt)
            dt = dt.replace(tzinfo=UTC)
            if not use_local_tz:
                return dt

            dt = dt.astimezone(LOCAL_TZ)
            return dt

        except ValueError:
            continue

    return None


def get_current_utc_dt() -> datetime.datetime:
    return datetime.datetime.now(UTC)
