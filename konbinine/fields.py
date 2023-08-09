"""
Opinionated SG entities default fields.

Modify this or use the custom_fields to pass in your preferred
fields. The models are set up with the default fields in mind.

"""

HUMANUSER_FIELDS = [
    "login",
    "name",
    "firstname",
    "lastname",
    "email",
    "file_access",
    "image",
    "sg_status_list",
    "projects",
    "groups",
]

PROJECT_FIELDS = [
    "name",
    "type",
    "archived",
    "code",
    "sg_description",
    "sg_status",
    "sg_type",
    "start_date",
    "end_date",
    "updated_at",
    "image",
    "duration",
]

TASK_FIELDS = [
    "content",
    "entity",
    "project",
    "sg_status_list",
]

ASSET_FIELDS = [
    "code",
    "tasks",
    "notes",
    "image",
    "filmstrip_image",
    "sg_asset_type",
    "sg_status_list",
]

SHOT_FIELDS = [
    "code",
    "image",
    "filmstrip_image",
    "sg_cut_in",
    "sg_cut_out",
    "sg_cut_duration",
    "sg_status_list",
    "sg_shot_type",
]

VERSION_FIELDS = [
    "code",
    "description",
    "flagged",
    "image",
    "filmstrip_image",
    "entity",
    "sg_task",
    "sg_uploaded_movie",
    "sg_path_to_frames",
    "sg_path_to_movie",
    "sg_status_list",
    "uploaded_movie_duration",
    "sg_uploaded_movie_frame_rate",
    "notes",
]

NOTE_FIELDS = [
    "subject",
    "content",
    "sg_status_list",
    "note_links",
]

BOOKING_FIELDS = [
    "start_date",
    "end_date",
    "vacation",
    "user",
    "note",
    "sg_status_list",
]

TIMELOG_FIELDS = [
    "date",
    "description",
    "duration",
    "entity",
    "project",
    "user",
]
