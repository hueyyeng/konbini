import datetime
import inspect
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from konbinine.enums import SgEntity
from konbinine.exceptions import InvalidSgDateFormatException
from konbinine.utils import SG_DATE_FORMAT, validate_sg_date_format

# TODO: Use Python 3.10+ kw_only but that is another headache for maintenance...


@dataclass
class SgIdMixin:
    id: int = 0


@dataclass
class SgBaseModel:
    def to_dict(self) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        dict_.pop("id", None)
        dict_.pop("type", None)
        return dict_

    def to_full_dict(self) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        return dict_

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")
            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgGenericEntity(SgIdMixin, SgBaseModel):
    name: str = ""
    type: str = ""


@dataclass
class SgNote(SgIdMixin, SgBaseModel):
    name: str = ""
    type: str = SgEntity.NOTE


@dataclass
class SgProject(SgIdMixin, SgBaseModel):
    name: str = ""
    type: str = SgEntity.PROJECT


@dataclass
class _SgPipelineStep(SgBaseModel):
    code: str  # The nice name (e.g. Model)
    short_name: str  # Self explanatory (e.g. MOD)
    type: str = SgEntity.STEP


@dataclass
class SgPipelineStep(SgIdMixin, _SgPipelineStep):
    pass


@dataclass
class _SgVersion(SgBaseModel):
    code: str  # Version Name
    entity: Optional[dict] = None  # Link
    notes: List[SgNote] = field(default_factory=list)
    type: str = SgEntity.VERSION

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")
            if k == "notes" and v:
                v = [SgNote.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgVersion(SgIdMixin, _SgVersion):
    pass


@dataclass
class _SgShot(SgBaseModel):
    code: str  # Shot Code
    type: str = SgEntity.SHOT


@dataclass
class SgShot(SgIdMixin, _SgShot):
    pass


@dataclass
class _SgTask(SgBaseModel):
    name: str
    short_name: str = ""
    content: str = ""
    entity: Optional[SgGenericEntity] = None
    project: Optional[SgProject] = None
    type: str = SgEntity.TASK


@dataclass
class SgTask(SgIdMixin, _SgTask):
    pass


@dataclass
class _SgAsset(SgBaseModel):
    code: str  # Shot Code
    tasks: List[SgTask] = field(default_factory=list)
    type: str = SgEntity.ASSET

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            if k == "tasks" and v:
                v = [SgTask.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgAsset(SgIdMixin, _SgAsset):
    pass


@dataclass
class _SgPlaylist(SgBaseModel):
    code: str  # Playlist name
    description: str = ""
    versions: List[SgVersion] = field(default_factory=list)
    type: str = SgEntity.PLAYLIST

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "versions" and v:
                v = [SgVersion.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgPlaylist(SgIdMixin, _SgPlaylist):
    pass


@dataclass
class _SgHumanUser(SgBaseModel):
    name: str = ""
    type: str = SgEntity.HUMANUSER
    projects: Optional[List[dict]] = None
    groups: Optional[List[dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        dict_.pop("id", None)
        dict_.pop("type", None)

        return dict_


@dataclass
class SgHumanUser(SgIdMixin, _SgHumanUser):
    pass


@dataclass
class _SgBooking(SgBaseModel):
    user: SgHumanUser
    start_date: str
    end_date: str
    vacation: bool = True
    note: str = ""
    type: str = SgEntity.BOOKING

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "user" and v:
                v = SgHumanUser.from_dict(v)

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )

    def __post_init__(self):
        valid_start_date = validate_sg_date_format(self.start_date)
        valid_end_date = validate_sg_date_format(self.end_date)

        if not valid_start_date or not valid_end_date:
            raise InvalidSgDateFormatException("Date format must be YYYY-MM-DD")


@dataclass
class SgBooking(SgIdMixin, _SgBooking):
    pass


@dataclass
class _SgTimeLog(SgBaseModel):
    date: str
    description: str = ""
    duration: float = 0.0
    entity: Optional[SgGenericEntity] = None
    project: Optional[SgProject] = None
    user: Optional[SgHumanUser] = None
    type: str = SgEntity.TIMELOG

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "entity" and v:
                v = SgGenericEntity.from_dict(v)

            if k == "project" and v:
                v = SgProject.from_dict(v)

            if k == "user" and v:
                v = SgHumanUser.from_dict(v)

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )

    def __post_init__(self):
        valid_date = validate_sg_date_format(self.date)

        if not valid_date:
            raise InvalidSgDateFormatException("Date format must be YYYY-MM-DD")

    def get_date(self) -> datetime.date:
        timelog_date = datetime.datetime.strptime(self.date, SG_DATE_FORMAT).date()
        return timelog_date


@dataclass
class SgTimeLog(SgIdMixin, _SgTimeLog):
    pass
