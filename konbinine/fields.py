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
    "groups",
    "bookings",
    "department",
    "projects",
    "contracts",
    "language",
    "sg_status_list",
]

PROJECT_FIELDS = [
    "name",
    "is_template",
    "is_demo",
    "archived",
    "code",
    "sg_description",
    "sg_status",
    "sg_type",
    "start_date",
    "end_date",
    "updated_at",
    "image",
    "image_upload",
    "filmstrip_image",
    "duration",
    "users",
]

TASK_FIELDS = [
    "name",
    "short_name",
    "content",
    "duration",
    "milestone",
    "est_in_mins",
    "time_logs_sum",
    "time_percent_of_est",
    "time_vs_est",
    "implicit",
    "image",
    "filmstrip_image",
    "start_date",
    "due_date",
    "workload",
    "task_reviewers",
    "task_assignees",
    "entity",
    "project",
    "sg_versions",
    "step",
    "notes",
    "open_notes",
    "sg_status_list",
]

ASSET_FIELDS = [
    "code",
    "tasks",
    "notes",
    "open_notes",
    "project",
    "image",
    "filmstrip_image",
    "sg_asset_type",
    "sg_status_list",
    "sg_published_files",
    "sg_versions",
]

SHOT_FIELDS = [
    "code",
    "description",
    "image",
    "filmstrip_image",
    "project",
    "notes",
    "open_notes",
    "assets",
    "tasks",
    "parent_shots",
    "shots",
    "head_in",
    "head_duration",
    "head_out",
    "tail_in",
    "tail_out",
    "sg_head_in",
    "sg_head_out",
    "sg_cut_in",
    "sg_cut_out",
    "sg_cut_duration",
    "sg_working_duration",
    "sg_status_list",
    "sg_shot_type",
    "sg_published_files",
    "sg_versions",
]

VERSION_FIELDS = [
    "code",
    "description",
    "flagged",
    "image",
    "filmstrip_image",
    "entity",
    "project",
    "user",
    "tasks",
    "playlists",
    "notes",
    "open_notes",
    "otio_playable",
    "cuts",
    "uploaded_movie_duration",
    "sg_task",
    "sg_uploaded_movie",
    "sg_uploaded_movie_mp4",
    "sg_uploaded_movie_webm",
    "sg_uploaded_movie_transcoding_status",
    "sg_uploaded_movie_frame_rate",
    "sg_path_to_frames",
    "sg_path_to_movie",
    "sg_status_list",
    "sg_version_type",
]

PLAYLIST_FIELDS = [
    "code",
    "description",
    "locked",
    "locked_by",
    "project",
    "image",
    "filmstrip_image",
    "sg_date_and_time",
    "notes",
    "open_notes",
    "versions",
]

ATTACHMENT_FIELDS = [
    "this_file",
    "display_name",
    "description",
    "image",
    "filename",
    "file_extension",
    "file_size",
    "filmstrip_image",
    "processing_status",
    "original_fname",
    "open_notes_count",
    "sg_status_list",
]

NOTE_FIELDS = [
    "subject",
    "content",
    "project",
    "user",
    "addressings_cc",
    "addressings_to",
    "note_links",
    "attachments",
    "sg_status_list",
]

BOOKING_FIELDS = [
    "user",
    "start_date",
    "end_date",
    "note",
    "vacation",
    "project",
    "percent_allocation",
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
