from __future__ import annotations

import datetime
import inspect
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Type

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

    @staticmethod
    def _get_model(
        field_name: str,
        value: None | dict | list[dict],
        model_lookup: dict[str, Type[SgBaseModel]],
    ) -> None | dict | list[dict] | list[SgBaseModel] | SgBaseModel:
        if value is None:
            return None

        model = model_lookup[field_name]
        if isinstance(value, list):
            value_: list[dict] = value
            return [model.from_dict(_v) for _v in value_]
        else:
            value_: dict = value
            return model.from_dict(value_)

    def to_dict(self, include_extra_fields=False) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        dict_.pop("id", None)
        dict_.pop("type", None)
        extra_fields = dict_.pop("_extra_fields", {})
        if include_extra_fields:
            dict_.update(extra_fields)

        return dict_

    def to_full_dict(self, include_extra_fields=False) -> Dict[str, Any]:
        dict_ = {
            k: v for k, v in asdict(self).items() if v
        }
        extra_fields = dict_.pop("_extra_fields", {})
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
    project: Optional[SgProject] = None
    user: Optional[SgHumanUser] = None
    addressings_cc: list[SgGenericEntity] = field(default_factory=list)
    addressings_to: list[SgGenericEntity] = field(default_factory=list)
    note_links: list[SgGenericEntity] = field(default_factory=list)
    attachments: list[SgGenericEntity] = field(default_factory=list)
    sg_status_list: str = ""
    type: str = SgEntity.NOTE

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "project": SgProject,
            "user": SgHumanUser,
            "addressings_cc": SgGenericEntity,
            "addressings_to": SgGenericEntity,
            "note_links": SgGenericEntity,
            "attachments": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    is_template: bool = False
    is_demo: bool = False
    archived: bool = False
    code: Optional[str] = None
    sg_description: Optional[str] = None
    sg_status: Optional[str] = None
    sg_type: Optional[str] = None
    start_date: Optional[str] = None  # Date uses YYYY-MM-DD format
    end_date: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None  # Example 2023-08-07T06:29:35Z
    image: Optional[str] = None  # When retrieve from SG API, should be the URL path
    image_upload: Optional[str] = None  # For uploading to SG (str, bytes or os.PathLike object)
    filmstrip_image: Optional[str] = None
    duration: Optional[int] = None  # Number of days
    users: list[SgHumanUser] = field(default_factory=list)
    type: str = SgEntity.PROJECT

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "users": SgHumanUser,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )

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
    project: Optional[SgProject] = None
    user: Optional[SgHumanUser] = None
    tasks: List[SgGenericEntity] = field(default_factory=list)
    playlists: List[SgGenericEntity] = field(default_factory=list)
    notes: List[SgGenericEntity] = field(default_factory=list)
    open_notes: List[SgGenericEntity] = field(default_factory=list)
    otio_playable: Optional[str] = None
    cuts: List[SgGenericEntity] = field(default_factory=list)
    uploaded_movie_duration: Optional[str] = None
    sg_task: Optional[SgGenericEntity] = None
    sg_uploaded_movie: Optional[TSgUploadedMovie] = None
    sg_uploaded_movie_mp4: Optional[TSgUploadedMovie] = None
    sg_uploaded_movie_webm: Optional[TSgUploadedMovie] = None
    sg_uploaded_movie_transcoding_status: Optional[int] = None
    sg_uploaded_movie_frame_rate: Optional[str] = None
    sg_path_to_frames: Optional[str] = None
    sg_path_to_movie: Optional[str] = None
    sg_status_list: str = ""
    sg_version_type: str = ""
    type: str = SgEntity.VERSION

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "project": SgProject,
            "entity": SgGenericEntity,
            "user": SgHumanUser,
            "cuts": SgGenericEntity,
            "sg_task": SgGenericEntity,
            "tasks": SgGenericEntity,
            "playlists": SgGenericEntity,
            "notes": SgGenericEntity,
            "open_notes": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    project: Optional[SgProject] = None
    notes: list[SgGenericEntity] = field(default_factory=list)
    open_notes: list[SgGenericEntity] = field(default_factory=list)
    assets: list[SgGenericEntity] = field(default_factory=list)
    tasks: list[SgGenericEntity] = field(default_factory=list)
    parent_shots: list[SgGenericEntity] = field(default_factory=list)
    shots: list[SgGenericEntity] = field(default_factory=list)
    head_in: Optional[int] = None
    head_duration: Optional[int] = None
    head_out: Optional[int] = None
    tail_in: Optional[int] = None
    tail_out: Optional[int] = None
    sg_head_in: Optional[int] = None
    sg_head_out: Optional[int] = None
    sg_cut_in: Optional[int] = None
    sg_cut_out: Optional[int] = None
    sg_cut_duration: Optional[int] = None
    sg_working_duration: Optional[int] = None
    sg_status_list: str = ""
    sg_shot_type: str = ""
    sg_published_files: list[SgGenericEntity] = field(default_factory=list)
    sg_versions: list[SgGenericEntity] = field(default_factory=list)
    type: str = SgEntity.SHOT

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "project": SgProject,
            "notes": SgGenericEntity,
            "open_notes": SgGenericEntity,
            "assets": SgGenericEntity,
            "tasks": SgGenericEntity,
            "parent_shots": SgGenericEntity,
            "shots": SgGenericEntity,
            "sg_published_files": SgGenericEntity,
            "sg_versions": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    duration: int = 0
    milestone: bool = False
    est_in_mins: Optional[int] = None  # Bid on SG Web
    time_logs_sum: Optional[int] = None  # Time Logged on SG Web
    time_percent_of_est: Optional[int] = None  # Time Logged - % of Bid on SG Web
    time_vs_est: Optional[int] = None
    implicit: bool = False
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    workload: int = 0  # calculated field type that defaults on using Duration field on SG Web
    task_reviewers: list[SgHumanUser] = field(default_factory=list)
    task_assignees: list[SgHumanUser] = field(default_factory=list)
    entity: Optional[SgGenericEntity] = None
    project: Optional[SgProject] = None
    sg_versions: list[SgGenericEntity] = field(default_factory=list)
    step: Optional[SgGenericEntity] = None
    notes: list[SgGenericEntity] = field(default_factory=list)
    open_notes: list[SgGenericEntity] = field(default_factory=list)
    sg_status_list: str = ""
    type: str = SgEntity.TASK

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "task_reviewers": SgHumanUser,
            "task_assignees": SgHumanUser,
            "entity": SgGenericEntity,
            "project": SgProject,
            "sg_versions": SgGenericEntity,
            "step": SgGenericEntity,
            "notes": SgGenericEntity,
            "open_notes": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    open_notes: list[SgGenericEntity] = field(default_factory=list)
    project: Optional[SgProject] = None
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    sg_asset_type: str = ""
    sg_status_list: str = ""
    sg_published_files: list[SgGenericEntity] = field(default_factory=list)
    sg_versions: list[SgGenericEntity] = field(default_factory=list)
    type: str = SgEntity.ASSET

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "tasks": SgTask,
            "notes": SgGenericEntity,
            "open_notes": SgGenericEntity,
            "project": SgProject,
            "sg_published_files": SgGenericEntity,
            "sg_versions": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    locked: bool = False
    locked_by: Optional[SgHumanUser] = None
    project: Optional[SgProject] = None
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    sg_date_and_time: Optional[str] = None
    notes: list[SgGenericEntity] = field(default_factory=list)
    open_notes: list[SgGenericEntity] = field(default_factory=list)
    versions: List[SgVersion] = field(default_factory=list)
    type: str = SgEntity.PLAYLIST

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "locked_by": SgHumanUser,
            "project": SgProject,
            "notes": SgGenericEntity,
            "open_notes": SgGenericEntity,
            "versions": SgVersion,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    file_access: bool = False
    image: Optional[str] = None
    filmstrip_image: Optional[str] = None
    groups: List[SgGenericEntity] = field(default_factory=list)
    bookings: List[SgGenericEntity] = field(default_factory=list)
    department: Optional[SgGenericEntity] = None
    projects: List[SgProject] = field(default_factory=list)
    contracts: List[SgGenericEntity] = field(default_factory=list)
    language: str = "en"
    sg_status_list: str = ""
    type: str = SgEntity.HUMANUSER

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "groups": SgGenericEntity,
            "bookings": SgGenericEntity,
            "department": SgGenericEntity,
            "projects": SgProject,
            "contracts": SgGenericEntity,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )

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
    note: str = ""
    vacation: bool = True
    project: Optional[SgProject] = None
    percent_allocation: int = 100
    sg_status_list: str = ""
    type: str = SgEntity.BOOKING

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "user": SgHumanUser,
            "project": SgProject,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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
    project: Optional[SgProject] = None
    user: Optional[SgHumanUser] = None
    type: str = SgEntity.TIMELOG

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "entity": SgGenericEntity,
            "project": SgProject,
            "user": SgHumanUser,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
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


@dataclass
class SgAttachmentFile(SgIdMixin, SgBaseModel):
    url: str = ""
    name: str = ""  # the filename
    content_type: Optional[str] = None
    link_type: str = ""
    type: str = SgEntity.ATTACHMENT


@dataclass
class SgAttachment(SgBaseModel):
    # NOTE: There is no ID attribute on Attachment entity, but it is stored
    #  in 'this_file' attribute where you can find the file at 'Files' page on SG
    this_file: Optional[SgAttachmentFile] = None
    display_name: str = ""  # filename
    description: Optional[str] = None
    image: Optional[str] = None
    filename: Optional[str] = None
    file_extension: Optional[str] = None
    file_size: Optional[int] = None
    filmstrip_image: Optional[str] = None
    processing_status: Optional[str] = None
    original_fname: Optional[str] = None
    open_notes_count: int = 0
    sg_status_list: str = ""

    @classmethod
    def from_dict(cls, dict_):
        params = inspect.signature(cls).parameters

        _map = {
            "this_file": SgAttachmentFile,
        }

        sanitized_dict = {}
        for k, v in dict_.items():
            if "." in k:
                k = k.replace(".", "__")

            v = cls._get_model(k, v, _map) if k in _map else v
            sanitized_dict[k] = v

        return cls(
            **{
                k: v for k, v in sanitized_dict.items()
                if k in params
            }
        )
