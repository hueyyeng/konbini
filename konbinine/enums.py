# Inherit the enum class to extend custom status
class SgStatusList:
    # TODO: Sane default statuses? I got no idea what's the default statuses
    wtg = "Waiting to Start"
    hld = "On Hold"
    ip = "In Progress"
    na = "N/A"


# Inherit the enum class to extend custom entity
class SgEntity:
    APIUSER = "ApiUser"
    ASSET = "Asset"
    ATTACHMENT = "Attachment"
    BOOKING = "Booking"
    COMPOSITION = "Composition"
    DEPARTMENT = "Department"
    GROUP = "Group"
    HUMANUSER = "HumanUser"
    NOTE = "Note"
    PLAYLIST = "Playlist"
    PROJECT = "Project"
    PUBLISHEDFILE = "PublishedFile"
    PUBLISHEDFILETYPE = "PublishedFileType"
    SEQUENCE = "Sequence"
    SHOT = "Shot"
    STEP = "Step"
    STATUS = "Status"
    TASK = "Task"
    TIMELOG = "TimeLog"
    VERSION = "Version"


class SgHumanUserStatus:
    ACTIVE = "act"
    DISABLED = "dis"
