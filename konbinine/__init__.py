__version__ = "0.1.3"

import calendar
import datetime
import logging
import os
from typing import List, Optional, Set, Union

import shotgun_api3
from urllib3.exceptions import ProtocolError

from konbinine.enums import SgEntity, SgHumanUserStatus
from konbinine.exceptions import MissingValueError
from konbinine.logs import KonbiniAdapter
from konbinine.models import SgBooking, SgHumanUser, SgTimeLog
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
        list
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

        fields = [
            "name",
            "projects",
            "groups",
        ]
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

        fields = [
            "name",
            "groups",
        ]
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

    def create_sg_humanuser(self, data: SgHumanUser) -> dict:
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

        create_data = data.to_dict()
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

    def update_sg_humanuser(self, data: SgHumanUser) -> bool:
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

        is_updated = True

        try:
            self.sg.update(
                entity_type=SgEntity.HUMANUSER,
                entity_id=data.id,
                data=data.to_dict(),
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

        fields = [
            "start_date",
            "end_date",
            "vacation",
            "user",
        ]
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

        fields = [
            "start_date",
            "end_date",
            "vacation",
            "user",
            "note",
        ]
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

        fields = [
            "start_date",
            "end_date",
            "vacation",
            "user",
            "note",
        ]
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

    def create_sg_booking(self, data: SgBooking) -> dict:
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

        create_data = data.to_dict()
        create_data.update(
            {
                "user": {
                    "id": data.user.id,
                    "type": SgEntity.HUMANUSER,
                }
            }
        )

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

    def get_sg_notes(self, project_id: int) -> List[dict]:
        """Get SG Notes
        
        Parameters
        ----------
        project_id : int
            ShotGrid Project ID.
        
        Returns
        -------
        list[dict]
            List of dict or empty list if no results from ShotGrid
        
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
        fields = [
            "subject",
            "content",
            "note_links",
        ]

        notes = self.sg.find(SgEntity.NOTE, filters, fields)
        return notes

    def get_sg_shots(
            self,
            project_id: int,
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Shots
        
        Parameters
        ----------
        project_id : int
            ShotGrid Project ID.
        custom_fields: list[str]
            List of custom fields
        
        Returns
        -------
        list[dict]
            List of dict or empty list if no results from ShotGrid
            
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
        fields = [
            "code",
            "description",
        ]
        if custom_fields:
            fields = custom_fields

        notes = self.sg.find(SgEntity.SHOT, filters, fields)
        return notes

    def get_sg_tasks(
            self,
            tasks_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Tasks

        Parameters
        ----------
        custom_fields: list[str]
        tasks_id : int | set[int] | list[int]
            ShotGrid Task ID.

        Returns
        -------
        list
            List of dict or empty list if no results from ShotGrid

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
        fields = [
            "content",
            "entity",
            "project",
        ]
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        tasks = self.sg.find(SgEntity.TASK, filters, fields)
        return tasks

    def bulk_update_sg_task_status(self, task_ids: List[int], status: str) -> bool:
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
        fields = [
            "date",
            "description",
            "duration",
            "project",
            "user",
        ]
        if custom_fields:
            fields = custom_fields

        timelogs = self.sg.find(SgEntity.TIMELOG, filters, fields)
        return timelogs

    def create_sg_timelog(self, data: SgTimeLog) -> dict:
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
        is_created = True
        response_data = {}

        try:
            response_data = self.sg.create("TimeLog", data.to_dict())
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

    def update_sg_timelog(self, data: SgTimeLog) -> bool:
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

    def create_sg_task(self, data: dict) -> bool:
        """Create SG Task

        Create SG Task entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Task entity.

        Parameters
        ----------
        data : dict
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

        try:
            self.sg.create("Task", data)
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
