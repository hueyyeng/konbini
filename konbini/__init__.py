__version__ = "0.1.0"

import calendar
import datetime
import logging
from typing import List, Optional, Union, Set

import shotgun_api3
from shotgun_api3 import ShotgunError

from konbini.enums import SgEntity, SgHumanUserStatus
from konbini.models import SgHumanUser, SgBooking
from urllib3.exceptions import ProtocolError

from konbini.utils import SG_DATE_FORMAT

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)



class Konbini:
    DISABLE_SSL_VALIDATION = False

    def __init__(self, base_url: str, script_name: str, api_key: str):
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
            self.sg = shotgun_api3.Shotgun
            logger.error(e, exc_info=True)

    def get_sg_entity_schema_fields(self, entity: str):
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
            Shotgun/Shotgrid HumanUser ID. Default None which retrieve all valid HumanUser
        custom_fields : list of str

        Returns
        -------
        list of SgHumanUser
            List of SgHumanUser or empty list if no results from Shotgun/Shotgrid

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
        custom_fields : list of str

        Returns
        -------
        list of SgHumanUser
            List of SgHumanUser or empty list if no results from Shotgun/Shotgrid

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

        Returns
        -------
        dict

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
        if not isinstance(data, SgHumanUser):
            raise Exception("[SG] Data must be instance of SgHumanUser!")

        if not data.id:
            raise Exception("[SG] No SgHumanUser ID found!")

        is_updated = True
        try:
            self.sg.update(
                entity_type=SgEntity.HUMANUSER,
                entity_id=data.id,
                data=data.to_dict(),
            )
            logger.info(f"[SG] Update HumanUser {data.id} successful")
        except ShotgunError as e:
            logger.error(f"[SG] Error updating HumanUser {data.id}: {e}")
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
        custom_fields
        humanuser_id : int
            Shotgun/Shotgrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser

        Returns
        -------
        list of SgBooking
            List of SgBooking or empty list if no results from Shotgun/Shotgrid

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
        custom_fields
        year : int
        humanuser_id : int
            Shotgun/Shotgrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser
        
        Returns
        -------
        list of SgBooking
            List of SgBooking or empty list if no results from Shotgun/Shotgrid
        
        """
        current_dt = datetime.datetime.now()
        current_year = current_dt.year
        sg_year_offset = 0
        if year != current_year:
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
        custom_fields
        month : int
        year : int
        humanuser_id : int
            Shotgun/Shotgrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser

        Returns
        -------
        list of SgBooking
            List of SgBooking or empty list if no results from Shotgun/Shotgrid

        """
        current_dt = datetime.datetime.now()
        current_month = current_dt.month
        current_year = current_dt.year

        sg_month_offset = 0
        if month != current_month:
            sg_month_offset = month - current_month

        filters = [
            [
                "start_date",
                "in_calendar_month",
                sg_month_offset,
            ],
        ]

        sg_year_offset = 0
        if year != current_year:
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

        Returns
        -------
        bool

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
            Shotgun/Shotgrid Project ID.
        
        Returns
        -------
        list
            List of dict or empty list if no results from Shotgun/Shotgrid
        
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

    def get_sg_shot_notes(
            self,
            project_id: int,
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Shot Notes
        
        Parameters
        ----------
        custom_fields
        project_id : int
            Shotgun/Shotgrid Project ID.
        
        Returns
        -------
        list
            List of dict or empty list if no results from Shotgun/Shotgrid
            
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
        custom_fields
        tasks_id : int or set of int or list of int
            Shotgun/Shotgrid Task ID.

        Returns
        -------
        list
            List of dict or empty list if no results from Shotgun/Shotgrid

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


    def get_leave_sg_timelogs_by_month_year(
            self,
            month: int,
            year: int,
            humanuser_id: int = None,
    ) -> List[SgTimeLog]:
        """Get SG Timelogs by Month Year
        Parameters
        ----------
        month : int
        year : int
        humanuser_id : int
            Shotgun/Shotgrid HumanUser ID. Default None which retrieve all
            bookings for every valid HumanUser
        Returns
        -------
        list of SgTimeLog
            List of SgTimeLog or empty list if no results from Shotgun/Shotgrid
        """

        end_month = month + 1
        end_year = year

        # Set end date to January next year if current month is December
        if end_month > 12:
            end_month = 1
            end_year = year + 1

        last_day_of_month = calendar.monthrange(end_year, end_month)[1]
        filters = [
            [
                "date",
                "between",
                [f"{year}-{month:02}-01", f"{end_year}-{end_month:02}-{last_day_of_month}"],
            ],
            [
                "entity",
                "is",
                [
                    {
                        "id": SgTaskId.MASTER_SCHEDULE_LEAVE,
                        "type": "Task",
                    }
                ]
            ],
            [
                "sg_leave_id",
                "is_not",
                None

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
            "date",
            "entity",
            "description",
            "sg_leave_id",
            "user",
        ]

        order = [
            {
                "field_name": "date",
                "direction": "asc",
            }
        ]
        _timelogs: List[dict] = sg.find(SgEntity.TIMELOG, filters, fields, order=order)
        if not _timelogs:
            return []

        timelogs = []
        for timelog in _timelogs:
            sg_timelog = SgTimeLog.from_dict(timelog)
            _timelog_dt = datetime.datetime.strptime(sg_timelog.date, SG_DATE_FORMAT)
            timelogs.append(sg_timelog)

        return timelogs


    def create_sg_timelog(data: SgTimeLog) -> dict:
        """Create SG TimeLog
        Create SG TimeLog entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a TimeLog entity.
        Parameters
        ----------
        data : SgTimeLog
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
                "description": "Merdeka 2021"
            }
        """
        is_created = True
        response_data = {}

        try:
            response_data = sg.create("TimeLog", data.to_dict())
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG timelog",
                    "error": e,
                    "data": data,
                }
            )
            is_created = False

        # LW-59 UPDATE SG HUMANUSER PROJECTS LIST ON TIMELOG SUCCESSFULLY CREATED
        if is_created:
            timelog_project_id = data.project.id
            timelog_project = data.project
            # Should have one result for the user. If not, let it error out
            _sg_humanuser = get_sg_humanusers(data.user.id)[0]
            sg_user_project_list = _sg_humanuser.projects
            sg_user_project_id_list = []
            for project in sg_user_project_list:
                sg_user_project_id_list.append(project["id"])

            # Exclude "Master Schedule" project from being add
            excluded_project_list = [MASTER_SCHEDULE_PROJECT_ID]
            is_not_in_user_project = timelog_project_id not in sg_user_project_id_list
            is_not_in_excluded = timelog_project_id not in excluded_project_list

            if is_not_in_user_project and is_not_in_excluded:
                _sg_humanuser.projects.append(timelog_project.to_full_dict())
                is_update_sg_humanuser_successful = update_sg_humanuser(_sg_humanuser)
                logger.info(is_update_sg_humanuser_successful)

        data = {
            "is_created": is_created,
        }
        data.update(response_data)

        return data


    def bulk_create_sg_timelog(batch_data: List[dict]) -> List[dict]:
        """Bulk Create Timelog
        Parameters
        ----------
        batch_data : List[dict]
        Returns
        -------
        list of dict
        Raises
        ------
        ShotgunError
        """
        try:
            batch_response = sg.batch(batch_data)
        except Exception as e:
            logger.error(
                {
                    "msg": "Unexpected error in bulk create timelogs",
                    "error": e,
                }
            )

        return batch_response


    def bulk_create_leave_sg_timelog(month: int = None, year: int = None) -> bool:
        """Bulk Create Employee Leaves SG Timelog
        Also handle update if existing leaves SG Timelog exists
        Parameters
        ----------
        month : int
        year : int
        Returns
        -------
        list
            List of dict or empty list if no results from Shotgun/Shotgrid
        Raises
        ------
        ShotgunError
        """
        current_dt = datetime.datetime.now()
        if not month or not int(month) in range(1, 12 + 1):
            month = current_dt.month

        if not year or int(year) < 2010:
            year = current_dt.year

        try:
            leaves: Leave = Leave.objects.filter(
                start_date__year=year,
                start_date__month=month,
                status=LeaveStatus.APPROVED,
            ).values(
                'id',
                'start_date',
                'end_date',
                'employee_id',
                'working_hour_duration',
                'sg_booking_metadata'
            ).annotate(
                employee_name=F('employee_id__official_name'),
                employee_sg_id=F('employee_id__sg_id'),
                employee_location_id=F('employee_id__employment_location__id'),
            ).order_by(
                'employee_id',
            )
        except Exception as e:
            logger.error(
                {
                    "msg": "Unexpected error in getting Leaves",
                    "error": e,
                }
            )

        timelog_leave_ids = []
        _sg_timelogs = get_leave_sg_timelogs_by_month_year(
            month,
            year,
        )
        for timelog in _sg_timelogs:
            timelog_leave_ids.append(timelog.sg_leave_id)

        timelog_leave_ids = list(set(timelog_leave_ids))
        if leaves:
            current_sg_id = int
            current_employee_location_id = int
            timelog_batch_data = []
            for leave in leaves:
                leave_id = leave["id"]
                if leave_id not in timelog_leave_ids:
                    # Get employee timelogs and holiday list [Only run the query if next employee on the loop is a different person]
                    if current_sg_id != leave["employee_sg_id"]:
                        current_sg_id = leave["employee_sg_id"]
                        if current_employee_location_id != leave["employee_location_id"]:
                            current_employee_location_id = leave["employee_location_id"]
                            if current_employee_location_id == EmploymentLocationId.KUALA_LUMPUR:
                                event_type_pk = [
                                    PublicHolidayEventTypeId.NATIONAL,
                                    PublicHolidayEventTypeId.KUALA_LUMPUR,
                                ]
                            if current_employee_location_id == EmploymentLocationId.PENANG:
                                event_type_pk = [
                                    PublicHolidayEventTypeId.NATIONAL,
                                    PublicHolidayEventTypeId.PENANG,
                                ]

                            holidays = Event.objects.filter(
                                event_type__in=event_type_pk,
                                event_date__year=year,
                                event_date__month=month,
                            ).values_list(
                                "event_date",
                                flat=True
                            )
                            holidays_list = list(holidays)

                    leave_start_date = leave["start_date"]
                    leave_end_date = leave["end_date"]
                    leave_days = leave_end_date - leave_start_date
                    working_hour_duration = 8
                    if leave["working_hour_duration"] != 'full_day':
                        working_hour_duration = 4

                    for leave_day in range(leave_days.days + 1):
                        current_leave_date = leave_start_date + timedelta(days=leave_day)
                        if current_leave_date not in holidays_list and current_leave_date.weekday() < 5:
                            request_data = {
                                "request_type": "create",
                                "entity_type": SgEntity.TIMELOG,
                                "data": {
                                    "date": current_leave_date.strftime('%Y-%m-%d'),
                                    "description": "Leave",
                                    "sg_leave_id": leave_id,
                                    "duration": round(float(working_hour_duration) * 60),
                                    "entity": {
                                        "id": SgTaskId.MASTER_SCHEDULE_LEAVE,
                                        "type": "Task",
                                    },
                                    "project": {
                                        "id": SgLemonSkyProject.MASTER_SCHEDULE,
                                        "type": "Project",
                                    },
                                    "user": {
                                        "id": current_sg_id,
                                        "type": SgEntity.HUMANUSER
                                    },
                                },
                            }
                            timelog_batch_data.append(request_data)

            try:
                bulk_create_sg_timelog_response = bulk_create_sg_timelog(timelog_batch_data)
            except ShotgunError as e:
                print(f"[Bulk Create SG Timelog API] ERROR:", e)

            # Update LC leave metadata on SG timelog creation
            if bulk_create_sg_timelog_response:
                total_response_index = len(bulk_create_sg_timelog_response)
                current_leave_id = int
                leave_metadata_list = []

                for index, metadata in enumerate(bulk_create_sg_timelog_response):
                    current_leave_id = metadata["sg_leave_id"]
                    next_metadata_index = index + 1
                    leave_metadata_list.append(metadata)

                    # Check if next metadata index is within range, if out of bound then save current leave metadata list created
                    if next_metadata_index < total_response_index:
                        next_leave_id = bulk_create_sg_timelog_response[next_metadata_index]["sg_leave_id"]
                        # Check if next leave on the loop have the same leave id as current index leave_id, if not save leave metadata list then reset it
                        if current_leave_id != next_leave_id:
                            leave: Leave = Leave.objects.get(pk=current_leave_id)
                            leave.sg_booking_metadata = leave_metadata_list
                            leave.save()
                            leave_metadata_list = []
                    else:
                        leave: Leave = Leave.objects.get(pk=current_leave_id)
                        leave.sg_booking_metadata = leave_metadata_list
                        leave.save()

        return bulk_create_sg_timelog_response


    def update_sg_timelog(data: SgTimeLog) -> bool:
        if not isinstance(data, SgTimeLog):
            raise Exception("[SG] Data must be instance of SgTimeLog!")

        if not data.id:
            raise Exception("[SG] No SgTimeLog ID found!")

        is_successful_update = True
        try:
            sg.update(
                entity_type=SgEntity.TIMELOG,
                entity_id=data.id,
                data=data.to_dict(),
            )
            print(f"[SG] Update Timelog {data.id} successful")
        except ShotgunError as e:
            print(f"[SG] Error updating Timelog {data.id}: {e}")
            is_successful_update = False

        return is_successful_update


    def delete_sg_timelog(sg_timelog_id: int) -> bool:
        """Delete SG TimeLog
        Delete SG Timelog entity.
        Parameters
        ----------
        sg_timelog_id : int
        Returns
        -------
        bool
        """
        is_deleted = True
        try:
            is_deleted = sg.delete(SgEntity.TIMELOG, sg_timelog_id)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": f"Fail to delete SG Timelog ID {sg_timelog_id}",
                    "error": e,
                },
                exc_info=True,
            )
            is_deleted = False

        return is_deleted


    def bulk_delete_sg_timelog(sg_timelog_ids: List[int]) -> bool:
        """Bulk Delete Timelog

        Parameters
        ----------
        sg_timelog_ids : List[int]

        Returns
        -------
        bool

        Raises
        ------
        ShotgunError

        """
        batch_data = []
        for sg_timelog_id in sg_timelog_ids:
            request_data = {
                "request_type": "delete",
                "entity_id": sg_timelog_id,
                "entity_type": SgEntity.TIMELOG,
            }
            batch_data.append(request_data)

        is_bulk_delete_successful = True
        try:
            sg.batch(batch_data)
        except Exception as e:
            logger.error(
                {
                    "msg": "Unexpected error in bulk deleting timelog",
                    "error": e,
                    "task ids": sg_timelog_ids,
                }
            )
            is_bulk_delete_successful = False

        return is_bulk_delete_successful


    def create_sg_task(data: dict) -> bool:
        """Create SG Task
        Create SG Task entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Task entity.
        Parameters
        ----------
        data : dict
        Returns
        -------
        bool
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
            sg.create("Task", data)
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
