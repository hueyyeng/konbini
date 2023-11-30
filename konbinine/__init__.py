__version__ = "0.2.0"

import calendar
import datetime
import logging
import os
from typing import List, Optional, Set, Tuple, Union

import shotgun_api3
from urllib3.exceptions import ProtocolError

from konbinine.enums import SgEntity, SgHumanUserStatus
from konbinine.exceptions import MissingValueError
from konbinine.fields import (
    ASSET_FIELDS,
    BOOKING_FIELDS,
    HUMANUSER_FIELDS,
    NOTE_FIELDS,
    PROJECT_FIELDS,
    SHOT_FIELDS,
    TASK_FIELDS,
    TIMELOG_FIELDS,
    VERSION_FIELDS,
)
from konbinine.logs import KonbiniAdapter
from konbinine.models import (
    SgAsset,
    SgBooking,
    SgHumanUser,
    SgNote,
    SgProject,
    SgShot,
    SgTask,
    SgTimeLog,
    SgVersion,
)
from konbinine.utils import SG_DATE_FORMAT

logger = KonbiniAdapter(logging.getLogger(__name__), {})
logger.setLevel(logging.ERROR)


class Konbini:
    NO_SSL_VALIDATION = False

    def __init__(
        self,
        base_url: Optional[str] = None,
        script_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # Higher precedence for params value
        if not base_url:
            base_url = os.environ.get("KONBINI_BASE_URL", default="")

        if not script_name:
            script_name = os.environ.get("KONBINI_SCRIPT_NAME", default="")

        if not api_key:
            api_key = os.environ.get("KONBINI_API_KEY", default="")

        # Verify values exists from either params or env
        if not base_url:
            raise MissingValueError("base_url")

        if not script_name:
            raise MissingValueError("script_name")

        if not api_key:
            raise MissingValueError("api_key")
        
        # Override shotgun NO_SSL_VALIDATION value
        shotgun_api3.shotgun.NO_SSL_VALIDATION = self.NO_SSL_VALIDATION

        self.connect(
            base_url,
            script_name,
            api_key,
        )

    def connect(
        self,
        base_url: str,
        script_name: str,
        api_key: str,
    ):
        try:
            self.sg = shotgun_api3.Shotgun(
                base_url,
                script_name,
                api_key,
            )
        except (ProtocolError, Exception) as e:
            # TODO: Handle this gracefully? The SG outage back in 2023-01-04 (UTC) breaks BADLY and
            #  resulted in this weird exception handling. Refer to https://health.autodesk.com/incidents/d3tbvtvrmq1y
            self.sg = shotgun_api3.Shotgun
            logger.error(e, exc_info=True)
            logger.error("Highly advisable to verify SG service outages!")

    def get_sg_entity_schema_fields(self, entity: str) -> List[str]:
        """Get SG Entity Schema Fields

        Parameters
        ----------
        entity : str
            The entity type (e.g. Asset, Shot, Timelog, etc)

        Returns
        -------
        list
            The list of fields belonging to the entity type

        """
        fields = self.sg.schema_field_read(entity_type=entity)
        return list(fields.keys())

    def get_valid_values(self, entity: str, field_name: str) -> List[str]:
        """Get Valid Values

        Parameters
        ----------
        entity : str
            The entity type (e.g. Asset, Shot, Timelog, etc)
        field_name : str
            The field name (e.g. sg_status, sg_status_list, etc)

        Returns
        -------
        list of str

        """
        response_data = self.sg.schema_field_read(entity, field_name)
        try:
            valid_values: List[str] = response_data[field_name]["properties"]["valid_values"]["value"]
        except (KeyError, Exception) as e:
            raise e

        return valid_values

    def get_sg_projects(
            self,
            project_id: Optional[int] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgProject]:
        """Get SG Projects

        Parameters
        ----------
        project_id : int
            ShotGrid Project ID. Default None which retrieve all Projects
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list of SgProject
            List of SgProject or empty list if no results from ShotGrid

        """
        filters = []
        if project_id:
            filters = [
                [
                    "id",
                    "is",
                    project_id
                ]
            ]

        fields = PROJECT_FIELDS
        if custom_fields:
            fields = custom_fields

        _projects: List[dict] = self.sg.find(SgEntity.PROJECT, filters, fields)
        if not _projects:
            return []

        projects = []
        for project in _projects:
            sg_project = SgProject.from_dict(project)
            projects.append(sg_project)

        return projects

    def create_sg_project(self, data: SgProject, **kwargs) -> Tuple[int, bool]:
        if not isinstance(data, SgProject):
            raise Exception("Data must be instance of SgProject!")

        create_data = {
            "name": data.name,
            "sg_description": data.sg_description,
        }
        if data.sg_status:
            valid_values = self.get_valid_values(SgEntity.PROJECT, "sg_status")
            if data.sg_status not in valid_values:
                raise Exception(f"Invalid {data.sg_status} value! Valid values: {valid_values}")

            create_data["sg_status"] = data.sg_status

        # Make sure it is str, bytes or os.PathLike object
        if data.image_upload:
            create_data["image"] = data.image_upload,

        create_data.update(**kwargs)
        is_created = True
        sg_id = 0

        try:
            response_data = self.sg.create(
                entity_type=SgEntity.PROJECT,
                data=create_data,
            )
            sg_id = response_data["id"]
            logger.info(f"SgProject {response_data['id']} successfully created")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error creating SgProject for Project {data.name}: {e}")
            is_created = False
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgProject {data.name}: {e}")
            is_created = False

        return sg_id, is_created

    def update_sg_project(self, data: SgProject, **kwargs) -> bool:
        """Update SG Project

        Parameters
        ----------
        data : SgProject
            The SgProject data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgProject):
            raise Exception("Data must be instance of SgProject!")

        if not data.id:
            raise Exception("No SgProject ID found!")

        if data.sg_status:
            valid_values = self.get_valid_values(SgEntity.PROJECT, "sg_status")
            if data.sg_status not in valid_values:
                raise Exception(f"Invalid {data.sg_status} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()

        # Project start and end date is read only (only can be modified using Project Planning app on SG Web)
        data_.pop("start_date", None)
        data_.pop("end_date", None)
        data_.pop("duration", None)
        data_.pop("updated_at", None)
        data_.pop("image", None)

        # Make sure it is str, bytes or os.PathLike object
        is_image_upload = data_.pop("image_upload", None)
        if is_image_upload:
            data_["image"] = is_image_upload

        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.PROJECT,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update SgProject {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating SgProject {data.id}: {e}")
            is_updated = False
        except Exception as e:
            logger.error(f"Unhandled exception when updating SgProject {data.id}: {e}")
            is_updated = False

        return is_updated

    def get_sg_humanusers(
            self,
            humanuser_id: Optional[int] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgHumanUser]:
        """Get SG HumanUsers

        Parameters
        ----------
        humanuser_id : int
            ShotGrid HumanUser ID. Default None which retrieve all valid HumanUser
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgHumanUser]
            List of SgHumanUser or empty list if no results from ShotGrid

        """
        filters = []
        if humanuser_id:
            filters = [
                [
                    "id",
                    "is",
                    humanuser_id
                ]
            ]

        fields = HUMANUSER_FIELDS
        if custom_fields:
            fields = custom_fields

        _users: List[dict] = self.sg.find(SgEntity.HUMANUSER, filters, fields)
        if not _users:
            return []

        users = []
        for user in _users:
            sg_humanuser = SgHumanUser.from_dict(user)
            users.append(sg_humanuser)

        return users

    def get_active_sg_humanusers(
            self,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgHumanUser]:
        """Get Active SG HumanUsers

        Parameters
        ----------
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgHumanUser]
            List of SgHumanUser or empty list if no results from ShotGrid

        """
        filters = [
            [
                "sg_status_list",
                "is",
                SgHumanUserStatus.ACTIVE,
            ]
        ]

        fields = HUMANUSER_FIELDS
        if custom_fields:
            fields = custom_fields

        _users: List[dict] = self.sg.find(SgEntity.HUMANUSER, filters, fields)
        if not _users:
            return []

        users = []
        for user in _users:
            sg_humanuser = SgHumanUser.from_dict(user)
            users.append(sg_humanuser)

        return users

    def create_sg_humanuser(self, data: SgHumanUser, **kwargs) -> dict:
        """Create SG HumanUser

        Create SG HumanUser entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a HumanUser entity.

        Parameters
        ----------
        data : SgHumanUser
            The SgHumanUser data for create

        Returns
        -------
        dict
            Dict of is_created and the HumanUser data if created successfully

        Examples
        --------
        {
            "name": "Kepci Bin Mekdi",
        }

        """
        is_created = True
        response_data = {}

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.HUMANUSER, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        create_data = data.to_dict()
        create_data.update(**kwargs)

        try:
            response_data = self.sg.create(SgEntity.HUMANUSER, create_data)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG HumanUser",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        data = {
            "is_created": is_created,
        }
        data.update(response_data)

        return data

    def update_sg_humanuser(self, data: SgHumanUser, **kwargs) -> bool:
        """Update SG HumanUser

        Parameters
        ----------
        data : SgHumanUser
            The SgHumanUser data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgHumanUser):
            raise Exception("Data must be instance of SgHumanUser!")

        if not data.id:
            raise Exception("No SgHumanUser ID found!")

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.HUMANUSER, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()

        # Requires Autodesk Account Portal to update the following fields
        data_.pop("email", None)
        data_.pop("firstname", None)
        data_.pop("lastname", None)

        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.HUMANUSER,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update HumanUser {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating HumanUser {data.id}: {e}")
            is_updated = False

        return is_updated

    def get_sg_bookings(
            self,
            humanuser_id: int = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings

        Parameters
        ----------
        humanuser_id : int
            ShotGrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgBooking]
            List of SgBooking or empty list if no results from ShotGrid

        """
        filters = []
        if humanuser_id:
            filters = [
                [
                    "user",
                    "is",
                    [
                        {
                            "id": humanuser_id,
                            "type": SgEntity.HUMANUSER,
                        }
                    ]
                ]
            ]

        fields = BOOKING_FIELDS
        if custom_fields:
            fields = custom_fields

        _bookings: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields)
        if not _bookings:
            return []

        bookings = []
        for booking in _bookings:
            sg_booking = SgBooking.from_dict(booking)
            bookings.append(sg_booking)

        return bookings

    def get_sg_bookings_by_year(
            self,
            year: int,
            humanuser_id: int = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings by Year
        
        Parameters
        ----------
        year : int
            Calendar year
        humanuser_id : int
            ShotGrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser
        custom_fields: list[str]
            List of custom fields
                  
        Returns
        -------
        list[SgBooking]
            List of SgBooking or empty list if no results from ShotGrid
        
        """
        current_dt = datetime.datetime.now()
        current_year = current_dt.year
        sg_year_offset = 0
        if not year == current_year:
            sg_year_offset = year - current_year

        filters = [
            [
                "start_date",
                "in_calendar_year",
                sg_year_offset,
            ]
        ]
        if humanuser_id:
            filters.append(
                [
                    "user",
                    "is",
                    [
                        {
                            "id": humanuser_id,
                            "type": SgEntity.HUMANUSER,
                        }
                    ]
                ]
            )

        fields = BOOKING_FIELDS
        if custom_fields:
            fields = custom_fields

        order = [
            {
                "field_name": "start_date",
                "direction": "asc",
            }
        ]

        _bookings: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields, order=order)
        if not _bookings:
            return []

        bookings = []
        for booking in _bookings:
            sg_booking = SgBooking.from_dict(booking)
            bookings.append(sg_booking)

        return bookings

    def get_sg_bookings_by_month_year(
            self,
            month: int,
            year: int,
            humanuser_id: int = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings by Month Year

        Parameters
        ----------
        month : int
            Calendar month
        year : int
            Calendar year
        humanuser_id : int
            ShotGrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgBooking]
            List of SgBooking or empty list if no results from ShotGrid

        """
        current_dt = datetime.datetime.now()
        current_month = current_dt.month
        current_year = current_dt.year

        sg_month_offset = 0
        if not month == current_month:
            sg_month_offset = month - current_month

        filters = [
            [
                "start_date",
                "in_calendar_month",
                sg_month_offset,
            ],
        ]

        sg_year_offset = 0
        if not year == current_year:
            sg_year_offset = year - current_year

        if sg_year_offset:
            last_day_of_month = calendar.monthrange(year, month)[1]
            filters = [
                [
                    "start_date",
                    "is",
                    f"{year}-{month:02}-01",
                ],
                [
                    "end_date",
                    "is",
                    f"{year}-{month:02}-{last_day_of_month}",
                ],
            ]

        if humanuser_id:
            filters.append(
                [
                    "user",
                    "is",
                    [
                        {
                            "id": humanuser_id,
                            "type": SgEntity.HUMANUSER,
                        }
                    ]
                ]
            )

        fields = BOOKING_FIELDS
        if custom_fields:
            fields = custom_fields

        order = [
            {
                "field_name": "start_date",
                "direction": "asc",
            }
        ]

        _bookings: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields, order=order)
        if not _bookings:
            return []

        bookings = []
        for booking in _bookings:
            sg_booking = SgBooking.from_dict(booking)
            _booking_dt = datetime.datetime.strptime(sg_booking.start_date, SG_DATE_FORMAT)
            if _booking_dt.month != month or _booking_dt.year != year:
                continue

            bookings.append(sg_booking)

        return bookings

    def create_sg_booking(self, data: SgBooking, **kwargs) -> dict:
        """Create SG Booking
        
        Create SG Booking entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Booking entity.
        
        Parameters
        ----------
        data : SgBooking
            The SgBooking data for create
        
        Returns
        -------
        dict
        
        Examples
        --------
        start_date/end_date : YYYY-MM-DD in string format
        sg_duration: Day in float format
            {
                "start_date": "2022-02-22",
                "end_date": "2022-02-22",
                "vacation": True,
                "note": "Blah Blah Blah",
                "user": {
                    "id": 1984,
                    "type": SgEntity.HUMANUSER
                },
            }
            
        """
        is_created = True
        response_data = {}

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.BOOKING, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        create_data = data.to_dict()
        create_data.update(
            {
                "user": {
                    "id": data.user.id,
                    "type": SgEntity.HUMANUSER,
                }
            }
        )
        create_data.update(**kwargs)

        try:
            response_data = self.sg.create(SgEntity.BOOKING, create_data)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Booking",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        data = {
            "is_created": is_created,
        }
        data.update(response_data)

        return data

    def delete_sg_booking(self, sg_booking_id: int) -> bool:
        """Delete SG Booking

        Delete SG Booking entity.

        Parameters
        ----------
        sg_booking_id : int
            The SG Booking ID for delete

        Returns
        -------
        bool
            True if deleted successfully

        """
        is_deleted = False
        try:
            is_deleted = self.sg.delete(SgEntity.BOOKING, sg_booking_id)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": f"Fail to delete SG Booking ID {sg_booking_id}",
                    "error": e,
                }
            )

        return is_deleted

    def create_sg_note(self, data: SgNote, **kwargs) -> dict:
        """Create SG Note

        Create SG Note entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Note entity.

        Parameters
        ----------
        data : SgNote
            The SgNote data for create

        Returns
        -------
        dict

        Examples
        --------
        {
            "subject": "Note Subject",
            "content": "Body message (column name is Body in SG Web)",
            "project": {
                "id": 666,
                "type": "Project"
            },
            "user": {
                "id": 16,
                "type": "HumanUser"
            },
            "addressings_to": [
                {
                    "id": 256,
                    "type": "HumanUser"
                }
            ],
            "note_links": [
                {
                    "id": 2048,
                    "type": "Version"
                }
            ]
        }

        """
        is_created = True
        response_data = {}

        if data.project is None:
            raise Exception(f"Project is required!")

        if data.user is None:
            raise Exception(
                f"User is required! If no explicit user is provided, the note's author "
                f"will default to the API Key when viewed on SG Web."
            )

        if not data.addressings_to:
            raise Exception(
                f"Include at least one HumanUser for addressings_to field!"
            )

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.NOTE, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        create_data = data.to_dict()
        create_data.update(
            {
                "user": {
                    "id": data.user.id,
                    "type": SgEntity.HUMANUSER,
                }
            }
        )
        create_data.update(**kwargs)

        try:
            response_data = self.sg.create(SgEntity.NOTE, create_data)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Note",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        data = {
            "is_created": is_created,
        }
        data.update(response_data)

        return data

    def get_sg_notes(self, entity_id: int, entity_type: str) -> List[SgNote]:
        """Get SG Notes

        Parameters
        ----------
        entity_id : int
            The SG Entity ID.
        entity_type: str
            The SG Entity Type (refer to SgEntity)

        Returns
        -------
        list[SgNote]
            List of SgNote or empty list if no results from ShotGrid

        """
        filters = [
            [
                "note_links",
                "is",
                {
                    "id": entity_id,
                    "type": entity_type,
                }
            ],
        ]
        fields = NOTE_FIELDS

        notes_ = self.sg.find(SgEntity.NOTE, filters, fields)
        notes = [SgNote.from_dict(n) for n in notes_]
        return notes

    def get_sg_notes_by_project(self, project_id: int) -> List[SgNote]:
        """Get SG Notes by Project
        
        Parameters
        ----------
        project_id : int
            ShotGrid Project ID.
        
        Returns
        -------
        list[SgNote]
            List of SgNote or empty list if no results from ShotGrid
        
        """
        filters = [
            [
                "project",
                "is",
                [
                    {
                        "id": project_id,
                        "type": SgEntity.PROJECT,
                    }
                ]
            ]
        ]
        fields = NOTE_FIELDS

        notes_ = self.sg.find(SgEntity.NOTE, filters, fields)
        notes = [SgNote.from_dict(n) for n in notes_]
        return notes

    def get_sg_assets(
            self,
            assets_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgAsset]:
        """Get SG Assets

        Parameters
        ----------
        custom_fields: list[str]
        assets_id : int | set[int] | list[int]
            ShotGrid Asset ID.

        Returns
        -------
        list of SgAsset
            List of SgAsset or empty list if no results from ShotGrid

        Notes
        -----
        If content is 'Idle' or 'Report', the entity value will be None

        """
        if isinstance(assets_id, int):
            assets_id = [assets_id]

        if isinstance(assets_id, set):
            assets_id = list(assets_id)

        filters = [
            [
                "id",
                "in",
                assets_id
            ]
        ]
        fields = ASSET_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        assets_: List[dict] = self.sg.find(SgEntity.ASSET, filters, fields)
        assets = [SgAsset.from_dict(t) for t in assets_]
        return assets

    def get_sg_shots_by_project(
            self,
            project_id: int,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgShot]:
        """Get SG Shots
        
        Parameters
        ----------
        project_id : int
            ShotGrid Project ID.
        custom_fields: list[str]
            List of custom fields
        
        Returns
        -------
        list[SgShot]
            List of SgShot or empty list if no results from ShotGrid
            
        """
        filters = [
            [
                "project",
                "is",
                [
                    {
                        "id": project_id,
                        "type": SgEntity.PROJECT,
                    }
                ]
            ]
        ]
        fields = SHOT_FIELDS
        if custom_fields:
            fields = custom_fields

        shots_ = self.sg.find(SgEntity.SHOT, filters, fields)
        shots = [SgShot.from_dict(s) for s in shots_]
        return shots

    def get_sg_tasks(
            self,
            tasks_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgTask]:
        """Get SG Tasks

        Parameters
        ----------
        custom_fields: list[str]
        tasks_id : int | set[int] | list[int]
            ShotGrid Task ID.

        Returns
        -------
        list of SgTask
            List of SgTask or empty list if no results from ShotGrid

        Notes
        -----
        If content is 'Idle' or 'Report', the entity value will be None

        """
        if isinstance(tasks_id, int):
            tasks_id = [tasks_id]

        if isinstance(tasks_id, set):
            tasks_id = list(tasks_id)

        filters = [
            [
                "id",
                "in",
                tasks_id
            ]
        ]
        fields = TASK_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        tasks_: List[dict] = self.sg.find(SgEntity.TASK, filters, fields)
        tasks = [SgTask.from_dict(t) for t in tasks_]
        return tasks

    def create_sg_task(self, data: SgTask, **kwargs) -> bool:
        """Create SG Task

        Create SG Task entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Task entity.

        Parameters
        ----------
        data : SgTask
            The SG Task data for create

        Returns
        -------
        bool
            True if created successfully

        Examples
        --------
        Content: Valid string format
            {
                "project": {
                    "id": 280,
                    "type": "Project"
                },
                "content": "Report",
                "task_assignees": [
                    {
                        "id": 970,
                        "type": SgEntity.HUMANUSER
                    }
                ],
            }

        """
        is_created = True
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.TASK, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.create("Task", data_)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG task",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        return is_created

    def bulk_update_sg_task_status(
            self,
            task_ids: List[int],
            status: str,
    ) -> bool:
        """Bulk Update SG Task Status

        Parameters
        ----------
        task_ids : list[int]
            List of Task IDs for bulk update
        status : str
            The status name

        Returns
        -------
        bool
            True if bulk update successfully

        """
        valid_values = self.get_valid_values(SgEntity.TASK, "sg_status_list")
        if status not in valid_values:
            raise Exception(f"Invalid {status} value! Valid values: {valid_values}")

        batch_data = []
        for task_id in task_ids:
            request_data = {
                "request_type": "update",
                "entity_id": task_id,
                "entity_type": SgEntity.TASK,
                "data": {
                    "sg_status_list": status
                },
            }
            batch_data.append(request_data)

        is_bulk_updated = True

        try:
            self.sg.batch(batch_data)
        except Exception as e:
            logger.error(
                {
                    "msg": "Unexpected error in bulk updating tasks status",
                    "error": e,
                    "task ids": task_ids,
                }
            )
            is_bulk_updated = False

        return is_bulk_updated

    def get_sg_versions(
            self,
            versions_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgVersion]:
        """Get SG Versions

        Parameters
        ----------
        custom_fields: list[str]
            Optional. List of valid fields for SG Version.
        versions_id : int | set[int] | list[int]
            ShotGrid Version ID.

        Returns
        -------
        list of SgVersion
            List of SgVersion or empty list if no results from ShotGrid

        Notes
        -----
        If content is 'Idle' or 'Report', the entity value will be None

        """
        if isinstance(versions_id, int):
            versions_id = [versions_id]

        if isinstance(versions_id, set):
            versions_id = list(versions_id)

        filters = [
            [
                "id",
                "in",
                versions_id
            ]
        ]
        fields = VERSION_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        versions_: List[dict] = self.sg.find(SgEntity.VERSION, filters, fields)
        versions = [SgVersion.from_dict(t) for t in versions_]
        return versions

    def get_sg_timelogs(
            self,
            sg_humanuser_id: int,
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Timelogs

        Parameters
        ----------
        sg_humanuser_id : int
            The SG Humanuser ID
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[dict]
            List of Timelog dict

        """
        filters = [
            [
                "user",
                "is",
                [
                    {
                        "id": sg_humanuser_id,
                        "type": SgEntity.HUMANUSER,
                    }
                ]
            ]
        ]
        fields = TIMELOG_FIELDS
        if custom_fields:
            fields = custom_fields

        timelogs = self.sg.find(SgEntity.TIMELOG, filters, fields)
        return timelogs

    def create_sg_timelog(self, data: SgTimeLog, **kwargs) -> dict:
        """Create SG TimeLog

        Create SG TimeLog entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a TimeLog entity.

        Parameters
        ----------
        data : SgTimeLog
            The SgTimeLog data for create

        Returns
        -------
        dict

        Examples
        --------
        Date: YYYY-MM-DD in string format
        Duration: Minutes in integer format
            {
                "project": {
                    "id": 410,
                    "type": "Project"
                },
                "date": "2021-08-31",
                "duration": 117,
                "entity": {
                    "id": 152698,
                    "type": "Task"
                },
                "user": {
                    "id": 970,
                    "type": SgEntity.HUMANUSER
                },
                "description": "Golden Week 2023"
            }

        """
        data_ = data.to_dict()
        data_.update(**kwargs)
        is_created = True
        response_data = {}

        try:
            response_data = self.sg.create("TimeLog", data_)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG timelog",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        data = {
            "is_created": is_created,
        }
        data.update(response_data)

        return data

    def bulk_create_sg_timelog(self, batch_data: List[dict]) -> List[dict]:
        """Bulk Create Timelog

        Parameters
        ----------
        batch_data : list[dict]
            list of Timelog dict for bulk create

        Returns
        -------
        list[dict]
            List of Timelog dict

        Raises
        ------
        shotgun_api3.ShotgunError

        """
        try:
            batch_response = self.sg.batch(batch_data)
        except shotgun_api3.ShotgunError as e:
            logger.error(
                {
                    "msg": "Unexpected error in bulk create timelogs",
                    "error": e,
                }
            )
            raise e

        return batch_response

    def update_sg_timelog(self, data: SgTimeLog, **kwargs) -> bool:
        """Update SG Timelog

        Parameters
        ----------
        data : SgTimeLog
            The SgTimeLog data for update

        Returns
        -------
        bool
            True if updated successfully

        """
        if not isinstance(data, SgTimeLog):
            raise Exception("Data must be instance of SgTimeLog!")

        if not data.id:
            raise Exception("No SgTimeLog ID found!")

        is_successful_update = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.TIMELOG,
                entity_id=data.id,
                data=data.to_dict(),
            )
            logger.info(f"Update Timelog {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.warning(f"Error updating Timelog {data.id}: {e}")
            is_successful_update = False

        return is_successful_update

    def delete_sg_timelog(self, sg_timelog_id: int) -> bool:
        """Delete SG TimeLog

        Delete SG TimeLog entity.

        Parameters
        ----------
        sg_timelog_id : int
            The SG TimeLog ID for delete

        Returns
        -------
        bool
            True if updated successfully

        """
        try:
            is_deleted = self.sg.delete(SgEntity.TIMELOG, sg_timelog_id)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.warning(f"Error deleting Timelog {sg_timelog_id}: {e}")
            is_deleted = False

        return is_deleted

    def bulk_delete_sg_timelog(self, sg_timelog_ids: List[int]) -> bool:
        """Bulk Delete Timelog

        Bulk delete SG TimeLog entities.

        Parameters
        ----------
        sg_timelog_ids : list[int]
            List of SG TimeLog ID for bulk delete

        Returns
        -------
        bool
            True if bulk delete successfully

        """
        batch_data = []
        for sg_timelog_id in sg_timelog_ids:
            request_data = {
                "request_type": "delete",
                "entity_id": sg_timelog_id,
                "entity_type": SgEntity.TIMELOG,
            }
            batch_data.append(request_data)

        is_bulk_delete_timelog_successful = True

        try:
            self.sg.batch(batch_data)
        except Exception as e:
            logger.error(
                {
                    "msg": " Unexpected error in bulk deleting timelog",
                    "error": e,
                    "task ids": sg_timelog_ids,
                }
            )
            is_bulk_delete_timelog_successful = False

        return is_bulk_delete_timelog_successful
