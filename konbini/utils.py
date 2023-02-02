import re

SG_DATE_FORMAT = "%Y-%m-%d"  # E.g: 2022-02-22


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
