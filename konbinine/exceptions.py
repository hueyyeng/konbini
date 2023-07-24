class InvalidSgDateFormatException(Exception):
    pass


class MissingValueError(ValueError):
    def __init__(self, missing_param_name: str, *args):
        _message = (
            f"Missing {missing_param_name} value. Use either KONBINI_{missing_param_name.upper()} "
            f"environment variables or {missing_param_name} param."
        )
        super().__init__(_message, *args)
