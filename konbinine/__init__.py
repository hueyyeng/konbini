__version__ = "0.3.2"

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
    ATTACHMENT_FIELDS,
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
    SgAttachment,
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
            #  Forgot to include this link https://status.shotgridsoftware.com/
            self.sg = shotgun_api3.Shotgun
            logger.error(e, exc_info=True)
            logger.error(
                "Highly advisable to verify SG service outages! "
                "https://status.shotgridsoftware.com/"
            )

    def get_sg_entity_schema_fields(self, entity: str) -> List[str]:
        """Get SG Entity Schema Fields

        Parameters
        ----------
        entity : str
            The entity type (e.g. Asset, Shot, Timelog, etc.)

        Returns
        -------
        list[str]
            The list of fields belonging to the entity type

        """
        fields = self.sg.schema_field_read(entity_type=entity)
        return list(fields.keys())

    def get_valid_values(self, entity: str, field_name: str) -> List[str]:
        """Get Valid Values

        Parameters
        ----------
        entity : str
            The entity type (e.g. Asset, Shot, Timelog, etc.)
        field_name : str
            The field name (e.g. sg_status, sg_status_list, etc.)

        Returns
        -------
        list[str]
            The list of valid values

        """
        response_data = self.sg.schema_field_read(entity, field_name)
        try:
            valid_values: List[str] = response_data[field_name]["properties"]["valid_values"]["value"]
        except (KeyError, Exception) as e:
            raise e

        return valid_values

    def get_sg_projects(
            self,
            project_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgProject]:
        """Get SG Projects

        Parameters
        ----------
        project_id : int | set[int] | list[int]
            ShotGrid Project ID. Default None which retrieve all Projects
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgProject]
            List of SgProject or empty list if no results from ShotGrid

        """
        filters = []
        if project_id:
            if isinstance(project_id, int):
                project_id = [project_id]

            if isinstance(project_id, set):
                project_id = list(project_id)

            filters = [
                [
                    "id",
                    "in",
                    project_id
                ]
            ]

        fields = PROJECT_FIELDS
        if custom_fields:
            fields = custom_fields

        projects_: List[dict] = self.sg.find(SgEntity.PROJECT, filters, fields)
        projects = [SgProject.from_dict(_) for _ in projects_]
        return projects

    def create_sg_project(self, data: SgProject, **kwargs) -> int:
        """Create SG Project

        Create SG Project entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Project entity.

        Parameters
        ----------
        data : SgProject
            The SgProject data for create

        Returns
        -------
        int
            The created Project ID if successful or 0 if failed

        """
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

        # Note for devs, this is unique to Konbini, take care if you have a custom fields
        # on SG for Project entity that happen to have the same field name as "image_upload"
        if data.image_upload:
            # Make sure it is str, bytes or os.PathLike object
            create_data["image"] = data.image_upload,

        create_data.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(
                entity_type=SgEntity.PROJECT,
                data=create_data,
            )
            created_id = response_data["id"]
            logger.info(f"SgProject {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError, KeyError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Project",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgProject {data.name}: {e}")

        return created_id

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

        is_updated = False
        try:
            self.sg.update(
                entity_type=SgEntity.PROJECT,
                entity_id=data.id,
                data=data_,
            )
            is_updated = True
            logger.info(f"Update SgProject {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating SgProject {data.id}: {e}")
        except Exception as e:
            logger.error(f"Unhandled exception when updating SgProject {data.id}: {e}")

        return is_updated

    def get_sg_humanusers(
            self,
            humanuser_id: Optional[Union[int, Set[int], List[int]]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgHumanUser]:
        """Get SG HumanUsers

        Parameters
        ----------
        humanuser_id : int | Set[int] | List[int]
            ShotGrid HumanUser ID. Default None which retrieve all valid HumanUser
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgHumanUser]
            List of SgHumanUser or empty list if no results from ShotGrid

        """
        filters = []
        if isinstance(humanuser_id, int):
            humanuser_id = [humanuser_id]

        if isinstance(humanuser_id, set):
            humanuser_id = list(humanuser_id)

        if humanuser_id:
            filters = [
                [
                    "id",
                    "in",
                    humanuser_id
                ]
            ]

        fields = HUMANUSER_FIELDS
        if custom_fields:
            fields = custom_fields

        users_: List[dict] = self.sg.find(SgEntity.HUMANUSER, filters, fields)
        users = [SgHumanUser.from_dict(_) for _ in users_]
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

    def create_sg_humanuser(self, data: SgHumanUser, **kwargs) -> int:
        """Create SG HumanUser

        Create SG HumanUser entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a HumanUser entity.

        Parameters
        ----------
        data : SgHumanUser
            The SgHumanUser data for create

        Returns
        -------
        int
            The HumanUser ID if successful or 0 if failed

        Examples
        --------
        {
            "name": "Kepci Bin Mekdi",
        }

        """
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.HUMANUSER, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        create_data = data.to_dict()
        create_data.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.HUMANUSER, create_data)
            created_id = response_data["id"]
            logger.info(f"SgHumanUser {response_data['id']} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError, KeyError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG HumanUser",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgHumanUser {data.name}: {e}")

        return created_id

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

    # TODO: Maybe can consider delete_sg_humanuser but better to have an
    #  actual person to manually delete the HumanUser from SG Web admin page

    def get_sg_bookings(
        self,
        booking_id: Union[int, Set[int], List[int]] = None,
        custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings

        Parameters
        ----------
        booking_id : int | Set[int] | List[int]
            ShotGrid Booking ID. Default None which retrieve all Bookings
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgBooking]
            List of SgBooking or empty list if no results from ShotGrid

        """
        filters = []
        if booking_id:
            if isinstance(booking_id, int):
                booking_id = [booking_id]

            if isinstance(booking_id, set):
                booking_id = list(booking_id)

            filters = [
                [
                    "id",
                    "in",
                    booking_id,
                ]
            ]

        fields = BOOKING_FIELDS
        if custom_fields:
            fields = custom_fields

        bookings_: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields)
        bookings = [SgBooking.from_dict(_) for _ in bookings_]
        return bookings

    def get_sg_bookings_by_user(
            self,
            humanuser_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings

        Parameters
        ----------
        humanuser_id : int | Set[int] | List[int]
            ShotGrid HumanUser ID
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgBooking]
            List of SgBooking or empty list if no results from ShotGrid

        """
        if isinstance(humanuser_id, int):
            humanuser_id = [humanuser_id]

        if isinstance(humanuser_id, set):
            humanuser_id = list(humanuser_id)

        users = [
            {"id": _, "type": SgEntity.HUMANUSER}
            for _ in humanuser_id
        ]
        filters = [
            [
                "user",
                "in",
                users,
            ]
        ]

        fields = BOOKING_FIELDS
        if custom_fields:
            fields = custom_fields

        bookings_: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields)
        bookings = [SgBooking.from_dict(_) for _ in bookings_]
        return bookings

    def get_sg_bookings_by_year(
            self,
            year: int,
            humanuser_id: Optional[int | Set[int] | List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings by Year
        
        Parameters
        ----------
        year : int
            Calendar year
        humanuser_id : int | Set[int] | List[int]
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
            if isinstance(humanuser_id, int):
                humanuser_id = [humanuser_id]

            if isinstance(humanuser_id, set):
                humanuser_id = list(humanuser_id)

            users = [
                {"id": _, "type": SgEntity.HUMANUSER}
                for _ in humanuser_id
            ]
            filters.append(
                [
                    "user",
                    "in",
                    users,
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

        bookings_: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields, order=order)
        bookings = [SgBooking.from_dict(_) for _ in bookings_]
        return bookings

    def get_sg_bookings_by_month_year(
            self,
            month: int,
            year: int,
            humanuser_id: Optional[Union[int, Set[int], List[int]]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgBooking]:
        """Get SG Bookings by Month Year

        Parameters
        ----------
        month : int
            Calendar month
        year : int
            Calendar year
        humanuser_id : int | Set[int] | List[int]
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
            if isinstance(humanuser_id, int):
                humanuser_id = [humanuser_id]

            if isinstance(humanuser_id, set):
                humanuser_id = list(humanuser_id)

            users = [
                {"id": _, "type": SgEntity.HUMANUSER}
                for _ in humanuser_id
            ]
            filters.append(
                [
                    "user",
                    "in",
                    users,
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

        bookings_: List[dict] = self.sg.find(SgEntity.BOOKING, filters, fields, order=order)
        if not bookings_:
            return []

        bookings = []
        for booking in bookings_:
            sg_booking = SgBooking.from_dict(booking)
            booking_dt = datetime.datetime.strptime(sg_booking.start_date, SG_DATE_FORMAT)
            if booking_dt.month != month or booking_dt.year != year:
                continue

            bookings.append(sg_booking)

        return bookings

    def create_sg_booking(self, data: SgBooking, **kwargs) -> int:
        """Create SG Booking
        
        Create SG Booking entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Booking entity.
        
        Parameters
        ----------
        data : SgBooking
            The SgBooking data for create
        
        Returns
        -------
        int
            The Booking ID if successful or 0 if failed

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

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.BOOKING, create_data)
            created_id = response_data["id"]
            logger.info(f"SgBooking {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError, KeyError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Booking",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgBooking: {e}")

        return created_id

    def update_sg_booking(self, data: SgBooking, **kwargs) -> bool:
        """Update SG Booking

        Parameters
        ----------
        data : SgBooking
            The SgBooking data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgBooking):
            raise Exception("Data must be instance of SgBooking!")

        if not data.id:
            raise Exception("No SgBooking ID found!")

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.BOOKING, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.BOOKING,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update Booking {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating Booking {data.id}: {e}")
            is_updated = False

        return is_updated

    def delete_sg_booking(self, booking_id: int) -> bool:
        """Delete SG Booking

        Delete SG Booking entity.

        Parameters
        ----------
        booking_id : int
            The SG Booking ID for delete

        Returns
        -------
        bool
            True if deleted successfully

        """
        is_deleted = False
        try:
            is_deleted = self.sg.delete(SgEntity.BOOKING, booking_id)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": f"Fail to delete SG Booking ID {booking_id}",
                    "error": e,
                }
            )

        return is_deleted

    def create_sg_note(self, data: SgNote, **kwargs) -> int:
        """Create SG Note

        Create SG Note entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Note entity.

        For devs, the "note_links" is the field that you want to specify to
        ensure the created note is link to whatever entities you want the notes
        to appear

        Parameters
        ----------
        data : SgNote
            The SgNote data for create

        Returns
        -------
        int
            The Note ID if successful or 0 if failed

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

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.NOTE, create_data)
            created_id = response_data["id"]
            logger.info(f"SgNote {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError, KeyError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Note",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgNote: {e}")

        return created_id

    def get_sg_notes(
            self,
            note_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgVersion]:
        """Get SG Versions

        Parameters
        ----------
        note_id : int | set[int] | list[int]
            ShotGrid Note ID. Default None which retrieves all notes
        custom_fields: list[str]
            Optional. List of valid fields for SG Note.

        Returns
        -------
        list[SgNote]
            List of SgNote or empty list if no results from ShotGrid

        """
        filters = []
        if note_id:
            if isinstance(note_id, int):
                note_id = [note_id]

            if isinstance(note_id, set):
                note_id = list(note_id)

            filters = [
                [
                    "id",
                    "in",
                    note_id
                ]
            ]

        fields = NOTE_FIELDS
        if custom_fields:
            fields = custom_fields

        notes_: List[dict] = self.sg.find(SgEntity.NOTE, filters, fields)
        notes = [SgNote.from_dict(t) for t in notes_]
        return notes

    def get_sg_notes_by_entity(self, entity_id: int, entity_type: str) -> List[SgNote]:
        """Get SG Notes by entity

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

    def update_sg_note(self, data: SgNote, **kwargs) -> bool:
        """Update SG Note

        Parameters
        ----------
        data : SgNote
            The SgNote data for update

        Returns
        -------
        bool
            True if updated successfully

        """
        if not isinstance(data, SgNote):
            raise Exception("Data must be instance of SgNote!")

        if not data.id:
            raise Exception("No SgNote ID found!")

        is_successful_update = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.NOTE,
                entity_id=data.id,
                data=data.to_dict(),
            )
            logger.info(f"Update Note {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.warning(f"Error updating Note {data.id}: {e}")
            is_successful_update = False
        except Exception as e:
            logger.error(f"Unhandled exception when updating Note {data.id}: {e}")
            is_successful_update = False

        return is_successful_update

    def get_sg_assets(
            self,
            asset_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgAsset]:
        """Get SG Assets

        Parameters
        ----------
        asset_id : int | set[int] | list[int]
            ShotGrid Asset ID. Default None which retrieve all Assets
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgAsset]
            List of SgAsset or empty list if no results from ShotGrid

        """
        filters = []
        if asset_id:
            if isinstance(asset_id, int):
                asset_id = [asset_id]

            if isinstance(asset_id, set):
                asset_id = list(asset_id)

            filters = [
                [
                    "id",
                    "in",
                    asset_id
                ]
            ]

        fields = ASSET_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        assets_: List[dict] = self.sg.find(SgEntity.ASSET, filters, fields)
        assets = [SgAsset.from_dict(t) for t in assets_]
        return assets

    def create_sg_asset(self, data: SgAsset, **kwargs) -> int:
        """Create SG Asset

        Create SG Asset entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create Asset entity.

        Parameters
        ----------
        data : SgTask
            The SG Asset data for create

        Returns
        -------
        int
            The created Asset ID if successful or 0 if failed

        Examples
        --------
        Content: Valid string format
            {
                "project": {
                    "id": 551,
                    "type": "Project"
                },
                "code": "BentoA",
            }

        """
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.ASSET, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        data_ = data.to_dict()
        data_.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.ASSET, data_)
            created_id = response_data["id"]
            logger.info(f"SgAsset {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Asset",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgAsset {data.code}: {e}")

        return created_id

    def update_sg_asset(self, data: SgAsset, **kwargs) -> bool:
        """Update SG Asset

        Parameters
        ----------
        data : SgAsset
            The SgAsset data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgAsset):
            raise Exception("Data must be instance of SgBooking!")

        if not data.id:
            raise Exception("No SgAsset ID found!")

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.ASSET, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.ASSET,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update Asset {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating Asset {data.id}: {e}")
            is_updated = False

        return is_updated

    def get_sg_shots(
            self,
            shot_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgShot]:
        """Get SG Shots

        Parameters
        ----------
        shot_id : int | set[int] | list[int]
            ShotGrid Project ID. Default None which retrieve all Shots
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgTask]
            List of SgShot or empty list if no results from ShotGrid

        """
        filters = []
        if shot_id:
            if isinstance(shot_id, int):
                shot_id = [shot_id]

            if isinstance(shot_id, set):
                shot_id = list(shot_id)

            filters = [
                [
                    "id",
                    "in",
                    shot_id
                ]
            ]

        fields = SHOT_FIELDS
        if custom_fields:
            fields = custom_fields

        shots_: List[dict] = self.sg.find(SgEntity.SHOT, filters, fields)
        shots = [SgProject.from_dict(_) for _ in shots_]
        return shots

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

    def create_sg_shot(self, data: SgShot, **kwargs) -> int:
        """Create SG Shot

        Create SG Shot entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create Shot entity.

        Parameters
        ----------
        data : SgShot
            The SG Shot data for create

        Returns
        -------
        int
            The created Shot ID if successful or 0 if failed

        Examples
        --------
        Content: Valid string format
            {
                "project": {
                    "id": 551,
                    "type": "Project"
                },
                "code": "014_003",
            }
        """
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.SHOT, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        data_ = data.to_dict()
        data_.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.SHOT, data_)
            created_id = response_data["id"]
            logger.info(f"SgShot {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Shot",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgShot {data.code}: {e}")

        return created_id

    def update_sg_shot(self, data: SgShot, **kwargs) -> bool:
        """Update SG Shot

        Parameters
        ----------
        data : SgShot
            The SgShot data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgShot):
            raise Exception("Data must be instance of SgShot!")

        if not data.id:
            raise Exception("No SgShot ID found!")

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.SHOT, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.SHOT,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update Shot {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating Shot {data.id}: {e}")
            is_updated = False

        return is_updated

    def get_sg_tasks(
            self,
            task_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgTask]:
        """Get SG Tasks

        Parameters
        ----------
        task_id : int | set[int] | list[int]
            ShotGrid Task ID. Default None which retrieve all Tasks
        custom_fields: list[str]
            List of custom fields

        Returns
        -------
        list[SgTask]
            List of SgTask or empty list if no results from ShotGrid

        Notes
        -----
        If content is 'Idle' or 'Report', the entity value will be None

        """
        filters = []
        if task_id:
            if isinstance(task_id, int):
                task_id = [task_id]

            if isinstance(task_id, set):
                task_id = list(task_id)

            filters = [
                [
                    "id",
                    "in",
                    task_id
                ]
            ]

        fields = TASK_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        tasks_: List[dict] = self.sg.find(SgEntity.TASK, filters, fields)
        tasks = [SgTask.from_dict(t) for t in tasks_]
        return tasks

    def create_sg_task(self, data: SgTask, **kwargs) -> int:
        """Create SG Task

        Create SG Task entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Task entity.

        Parameters
        ----------
        data : SgTask
            The SG Task data for create

        Returns
        -------
        int
            The created Task ID if successful or 0 if failed

        Examples
        --------
        Content: Valid string format
            {
                "project": {
                    "id": 551,
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
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.TASK, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        data_ = data.to_dict()
        data_.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.TASK, data_)
            created_id = response_data["id"]
            logger.info(f"SgTask {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG task",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgTask {data.name}: {e}")

        return created_id

    def update_sg_task(self, data: SgTask, **kwargs) -> bool:
        """Update SG Task

        Parameters
        ----------
        data : SgTask
            The SgTask data for update

        Returns
        -------
        bool
            True if update successfully

        """
        if not isinstance(data, SgTask):
            raise Exception("Data must be instance of SgBooking!")

        if not data.id:
            raise Exception("No SgTask ID found!")

        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.TASK, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        is_updated = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.TASK,
                entity_id=data.id,
                data=data_,
            )
            logger.info(f"Update Task {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.error(f"Error updating Task {data.id}: {e}")
            is_updated = False

        return is_updated

    def bulk_update_sg_task_status(
            self,
            task_id: List[int],
            status: str,
    ) -> bool:
        """Bulk Update SG Task Status

        Parameters
        ----------
        task_id : list[int]
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
        for _id in task_id:
            request_data = {
                "request_type": "update",
                "entity_id": _id,
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
                    "task_id": task_id,
                }
            )
            is_bulk_updated = False

        return is_bulk_updated

    def get_sg_versions(
            self,
            version_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgVersion]:
        """Get SG Versions

        Parameters
        ----------
        version_id : int | set[int] | list[int]
            ShotGrid Version ID. Default None which retrieve all Versions
        custom_fields: list[str]
            Optional. List of valid fields for SG Version.

        Returns
        -------
        list[SgVersion]
            List of SgVersion or empty list if no results from ShotGrid

        """
        filters = []
        if version_id:
            if isinstance(version_id, int):
                version_id = [version_id]

            if isinstance(version_id, set):
                version_id = list(version_id)

            filters = [
                [
                    "id",
                    "in",
                    version_id
                ]
            ]

        fields = VERSION_FIELDS
        if custom_fields:
            fields = custom_fields

        # If content is 'Idle', the entity value will be None
        versions_: List[dict] = self.sg.find(SgEntity.VERSION, filters, fields)
        versions = [SgVersion.from_dict(t) for t in versions_]
        return versions

    def create_sg_version(self, data: SgVersion, **kwargs) -> int:
        """Create SG Version

        Create SG Version entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a Version entity.

        Parameters
        ----------
        data : SgVersion
            The SG Task data for create

        Returns
        -------
        int
            The created Version ID if successful or 0 if failed

        Examples
        --------
        Content: Valid string format
            {
                "project": {
                    "id": 551,
                    "type": "Project"
                },
                "code": "Report",
                "entity": [
                    {
                        "id": 2042,
                        "type": SgEntity.ASSET
                    }
                ],
            }

        """
        if data.sg_status_list:
            valid_values = self.get_valid_values(SgEntity.VERSION, "sg_status_list")
            if data.sg_status_list not in valid_values:
                raise Exception(f"Invalid {data.sg_status_list} value! Valid values: {valid_values}")

        data_ = data.to_dict()
        data_.update(**kwargs)

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.VERSION, data_)
            created_id = response_data["id"]
            logger.info(f"SgVersion {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Version",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgVersion {data.code}: {e}")

        return created_id

    def update_sg_version(self, data: SgVersion, **kwargs) -> bool:
        """Update SG Version

        Parameters
        ----------
        data : SgVersion
            The SgVersion data for update

        Returns
        -------
        bool
            True if updated successfully

        """
        if not isinstance(data, SgVersion):
            raise Exception("Data must be instance of SgVersion!")

        if not data.id:
            raise Exception("No SgVersion ID found!")

        is_successful_update = True
        data_ = data.to_dict()
        data_.update(**kwargs)

        try:
            self.sg.update(
                entity_type=SgEntity.VERSION,
                entity_id=data.id,
                data=data.to_dict(),
            )
            logger.info(f"Update SG Version {data.id} successful")
        except shotgun_api3.ShotgunError as e:
            logger.warning(f"Error updating SG Version {data.id}: {e}")
            is_successful_update = False

        return is_successful_update

    def get_sg_timelogs(
            self,
            timelog_id: Union[int, Set[int], List[int]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Timelogs

        Parameters
        ----------
        timelog_id : int | set[int] | list[int]
            The SG Timelog ID. Default None which retrieve all TimeLogs
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgTimeLog]
            List of SgTimeLog or empty list if no results from ShotGrid

        """
        filters = []
        if timelog_id:
            if isinstance(timelog_id, int):
                timelog_id = [timelog_id]

            if isinstance(timelog_id, set):
                timelog_id = list(timelog_id)

            filters = [
                [
                    "id",
                    "in",
                    timelog_id,
                ]
            ]

        fields = TIMELOG_FIELDS
        if custom_fields:
            fields = custom_fields

        timelogs_ = self.sg.find(SgEntity.TIMELOG, filters, fields)
        timelogs = [SgTimeLog.from_dict(t) for t in timelogs_]
        return timelogs

    def get_sg_timelogs_by_user(
            self,
            humanuser_id: Union[int, Set[int], List[int]],
            custom_fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """Get SG Timelogs

        Parameters
        ----------
        humanuser_id : int | set[int] | list[int]
            The SG HumanUser ID
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgTimeLog]
            List of SgTimeLog or empty list if no results from ShotGrid

        """
        if isinstance(humanuser_id, int):
            humanuser_id = [humanuser_id]

        if isinstance(humanuser_id, set):
            humanuser_id = list(humanuser_id)

        users = [
            {"id": _, "type": SgEntity.HUMANUSER}
            for _ in humanuser_id
        ]
        filters = [
            [
                "user",
                "in",
                users,
            ]
        ]
        fields = TIMELOG_FIELDS
        if custom_fields:
            fields = custom_fields

        timelogs_ = self.sg.find(SgEntity.TIMELOG, filters, fields)
        timelogs = [SgTimeLog.from_dict(t) for t in timelogs_]
        return timelogs

    def create_sg_timelog(self, data: SgTimeLog, **kwargs) -> int:
        """Create SG TimeLog

        Create SG TimeLog entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create a TimeLog entity.

        Parameters
        ----------
        data : SgTimeLog
            The SgTimeLog data for create

        Returns
        -------
        int
            The created Timelog ID if successful or 0 if failed

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

        created_id = 0
        try:
            response_data = self.sg.create(SgEntity.TIMELOG, data_)
            created_id = response_data["id"]
            logger.info(f"SgTimeLog {created_id} successfully created")
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Timelog",
                    "error": e,
                    "data": data,
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception when creating SgTimeLog: {e}")

        return created_id

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

    def delete_sg_timelog(self, timelog_id: int) -> bool:
        """Delete SG TimeLog

        Delete SG TimeLog entity.

        Parameters
        ----------
        timelog_id : int
            The SG TimeLog ID for delete

        Returns
        -------
        bool
            True if updated successfully

        """
        try:
            is_deleted = self.sg.delete(SgEntity.TIMELOG, timelog_id)
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.warning(f"Error deleting Timelog {timelog_id}: {e}")
            is_deleted = False

        return is_deleted

    def bulk_delete_sg_timelog(self, timelog_id: Union[int, List[int]]) -> bool:
        """Bulk Delete Timelog

        Bulk delete SG TimeLog entities.

        Parameters
        ----------
        timelog_id : int | list[int]
            List of SG TimeLog ID for bulk delete

        Returns
        -------
        bool
            True if bulk delete successfully

        """
        timelog_ids = list(timelog_id)
        batch_data = []
        for _id in timelog_ids:
            request_data = {
                "request_type": "delete",
                "entity_id": _id,
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
                    "timelog_ids": timelog_ids,
                }
            )
            is_bulk_delete_timelog_successful = False

        return is_bulk_delete_timelog_successful

    def get_sg_attachments(
            self,
            attachment_id: Optional[Union[int, Set[int], List[int]]] = None,
            custom_fields: Optional[List[str]] = None,
    ) -> List[SgAttachment]:
        """Get SG Attachments

        Parameters
        ----------
        attachment_id : int | set[int] | list[int]
            ShotGrid Attachment ID. Default None which retrieve all Attachments
        custom_fields : list[str]
            List of custom fields

        Returns
        -------
        list[SgAttachment]
            List of SgAttachment or empty list if no results from ShotGrid

        """
        filters = []
        if attachment_id:
            if isinstance(attachment_id, int):
                attachment_id = [attachment_id]

            if isinstance(attachment_id, set):
                attachment_id = list(attachment_id)

            filters = [
                [
                    "id",
                    "in",
                    attachment_id
                ]
            ]

        fields = ATTACHMENT_FIELDS
        if custom_fields:
            fields = custom_fields

        attachments_: List[dict] = self.sg.find(SgEntity.ATTACHMENT, filters, fields)
        attachments = [SgAttachment.from_dict(_) for _ in attachments_]
        return attachments

    def upload_attachment(
            self,
            entity_id: int,
            entity_type: str,
            attachment_file: str,
            **kwargs,
    ) -> int:
        """Upload attachment

        Upload file as SG Attachment entity. Refer to the data structure in Examples for
        the bare minimum key values to successfully create the Attachment entity.

        CAUTION FOR DEVS: USE THE UPLOAD_MOVIE WRAPPER FUNCTION IF YOU NEED TO DISPLAY
         PLAYBLAST/MOVIE/PICTURE IN SHOTGRID SCREENING ROOM

        Parameters
        ----------
        entity_id : int
            The entity ID
        entity_type : str
            The entity type (e.g. 'Shot', 'Asset', etc.)
        attachment_file : str
            The attachment file path

        Returns
        -------
        int
            The created attachment ID. If error, the return value will be 0

        """
        attachment_id = 0
        try:
            attachment_id = self.sg.upload(
                entity_id=entity_id,
                entity_type=entity_type,
                path=attachment_file,
                **kwargs,
            )
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to create SG Attachment",
                    "error": e,
                    "attachment_file": attachment_file,
                }
            )

        return attachment_id

    def upload_movie(
        self,
        entity_id: int,
        entity_type: str,
        attachment_file: str,
        **kwargs,
    ) -> int:
        """Upload movie

        Same as upload_attachment but opinionated for uploading... movie/picture for
        Version entity? The reason is typically for Screening Room, it checks for the
        sg_uploaded_movie field instead of image field. Correct me if I'm wrong by
        creating a GitHub issue!

        Parameters
        ----------
        entity_id : int
            The entity ID
        entity_type : str
            The entity type (e.g. 'Shot', 'Asset', etc.)
        attachment_file : str
            The attachment file path

        Returns
        -------
        int
            The created attachment ID. If error, the return value will be 0

        """
        attachment_id = 0
        try:
            attachment_id = self.sg.upload(
                entity_id=entity_id,
                entity_type=entity_type,
                path=attachment_file,
                field_name="sg_uploaded_movie",
                **kwargs,
            )
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to upload movie",
                    "error": e,
                    "attachment_file": attachment_file,
                }
            )

        return attachment_id

    def upload_thumbnail(
        self,
        entity_id: int,
        entity_type: str,
        attachment_file: str,
        **kwargs,
    ) -> int:
        """Upload thumbnail

        Similar to upload_attachment but for thumbnail. DON'T USE THIS IF YOU'RE PLANNING
        TO UPLOAD SOMETHING TO SHOW UP IN THE SCREENING ROOM!

        Parameters
        ----------
        entity_id : int
         The entity ID
        entity_type : str
         The entity type (e.g. 'Shot', 'Asset', etc.)
        attachment_file : str
         The attachment file path

        Returns
        -------
        int
         The created attachment ID. If error, the return value will be 0

        """
        attachment_id = 0
        try:
            attachment_id = self.sg.upload_thumbnail(
                entity_id=entity_id,
                entity_type=entity_type,
                path=attachment_file,
                **kwargs,
            )
        except (shotgun_api3.Fault, shotgun_api3.ShotgunError) as e:
            logger.error(
                {
                    "msg": "Fail to upload thumbnail",
                    "error": e,
                    "attachment_file": attachment_file,
                }
            )

        return attachment_id
