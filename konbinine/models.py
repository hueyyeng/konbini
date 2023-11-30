from __future__ import annotations

import datetime
import inspect
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from konbinine.enums import SgEntity
from konbinine.exceptions import (
    InvalidSgDateFormatException,
)
from konbinine.types import TSgUploadedMovie
from konbinine.utils import (
    get_current_utc_dt,
    SG_DATE_FORMAT,
    validate_sg_date_format,
)

# TODO: Use Python 3.10+ kw_only but that is another headache for maintenance...


@dataclass
class SgIdMixin:
    id: int = 0


@dataclass
class SgBaseModel:
    _extra_fields: dict = field(default_factory=dict)

    def to_dict(self, include_extra_fields=False) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        dict_.pop("id", None)
        dict_.pop("type", None)
        extra_fields = dict_.pop("_extra_fields", None)
        if include_extra_fields:
            dict_.update(extra_fields)

        return dict_

    def to_full_dict(self, include_extra_fields=False) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        extra_fields = dict_.pop("_extra_fields", None)
        if include_extra_fields:
            dict_.update(extra_fields)

        return dict_

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")
            sanitized_dict[k] = v

        _extra_fields = {}
        for k, v in dict_.items():
            if k not in params:
                _extra_fields[k] = v

        sanitized_dict["_extra_fields"] = _extra_fields

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
    subject: str = ""
    content: str = ""
    sg_status_list: str = ""
    project: Optional[SgProject] = None
    user: Optional[SgGenericEntity] = None
    addressings_to: list[SgGenericEntity] = field(default_factory=list)
    note_links: list[SgGenericEntity] = field(default_factory=list)
    type: str = SgEntity.NOTE

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "note_links" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgProject(SgIdMixin, SgBaseModel):
    name: str = ""
    type: str = SgEntity.PROJECT
    archived: bool = False
    code: Optional[str] = None
    sg_description: Optional[str] = None
    sg_status: Optional[str] = None
    sg_type: Optional[str] = None
    start_date: Optional[str] = None  # Date uses YYYY-MM-DD format
    end_date: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None  # Example 2023-08-07T06:29:35Z
    image: Optional[str] = None  # When retrieve from SG API, should be the URL path
    filmstrip_image: Optional[str] = None
    image_upload: Optional[str] = None  # For uploading to SG (str, bytes or os.PathLike object)
    duration: Optional[int] = None  # Number of days

    def validate_stale_data(self) -> bool:
        current_dt = get_current_utc_dt()
        return self.updated_at > current_dt


@dataclass
class _SgPipelineStep(SgBaseModel):
    code: str = ""  # The nice name (e.g. Model)
    short_name: str = ""  # Self-explanatory (e.g. MOD)
    type: str = SgEntity.STEP


@dataclass
class SgPipelineStep(SgIdMixin, _SgPipelineStep):
    pass


@dataclass
class _SgVersion(SgBaseModel):
    code: str = ""  # Version Name
    description: Optional[str] = None
    flagged: bool = False
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    entity: Optional[SgGenericEntity] = None  # Link
    sg_task: Optional[SgGenericEntity] = None
    sg_uploaded_movie: Optional[TSgUploadedMovie] = None
    sg_uploaded_movie_mp4: Optional[TSgUploadedMovie] = None
    sg_uploaded_movie_webm: Optional[TSgUploadedMovie] = None
    sg_path_to_frames: Optional[str] = None
    sg_path_to_movie: Optional[str] = None
    sg_status_list: str = ""
    uploaded_movie_duration: Optional[str] = None
    sg_uploaded_movie_frame_rate: Optional[str] = None
    notes: List[SgGenericEntity] = field(default_factory=list)
    type: str = SgEntity.VERSION

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            if k == "entity" and v:
                v = SgGenericEntity.from_dict(v)

            if k == "sg_task" and v:
                v = SgGenericEntity.from_dict(v)

            if k == "notes" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

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
    code: str = ""  # Shot Code
    description: Optional[str] = None
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    notes: list[SgGenericEntity] = field(default_factory=list)
    sg_cut_in: Optional[int] = None
    sg_cut_out: Optional[int] = None
    sg_cut_duration: Optional[int] = None
    sg_status_list: str = ""
    sg_shot_type: str = ""
    type: str = SgEntity.SHOT

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            if k == "notes" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgShot(SgIdMixin, _SgShot):
    pass


@dataclass
class _SgTask(SgBaseModel):
    name: str = ""
    short_name: str = ""
    content: str = ""
    notes: list[SgGenericEntity] = field(default_factory=list)
    sg_status_list: str = ""
    entity: Optional[SgGenericEntity] = None
    project: Optional[SgProject] = None
    type: str = SgEntity.TASK

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            if k == "notes" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )


@dataclass
class SgTask(SgIdMixin, _SgTask):
    pass


@dataclass
class _SgAsset(SgBaseModel):
    code: str = ""  # Shot Code
    tasks: List[SgTask] = field(default_factory=list)
    notes: list[SgGenericEntity] = field(default_factory=list)
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    sg_asset_type: str = ""
    sg_status_list: str = ""
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

            if k == "notes" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

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
    code: str = ""  # Playlist name
    description: str = ""
    notes: list[SgGenericEntity] = field(default_factory=list)
    versions: List[SgVersion] = field(default_factory=list)
    type: str = SgEntity.PLAYLIST

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "versions" and v:
                v = [SgVersion.from_dict(_v) for _v in v]

            if k == "notes" and v:
                v = [SgGenericEntity.from_dict(_v) for _v in v]

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
    login: str = ""
    name: str = ""
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    sg_status_list: str = ""
    file_access: bool = False
    type: str = SgEntity.HUMANUSER
    image: Optional[str] = None
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
    user: Optional[SgHumanUser] = None
    start_date: str = ""
    end_date: str = ""
    vacation: bool = True
    note: str = ""
    sg_status_list: str = ""
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
    date: str = ""
    description: str = ""
    duration: float = 0.0
    entity: Optional[SgGenericEntity] = None
    project: Optional[SgGenericEntity] = None
    user: Optional[SgGenericEntity] = None
    type: str = SgEntity.TIMELOG

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        sanitized_dict = {}
        for k, v in dict_.items():
            if k == "entity" and v:
                v = SgGenericEntity.from_dict(v)

            if k == "project" and v:
                v = SgGenericEntity.from_dict(v)

            if k == "user" and v:
                v = SgGenericEntity.from_dict(v)

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
