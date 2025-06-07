"""
homismart_client/enums.py

Defines enumerations for constants used in the Homismart client,
including command prefixes, server message prefixes, device types, and error codes.
"""
from enum import Enum, IntEnum

class RequestPrefix(Enum):
    """
    Prefixes for messages sent TO the Homismart server.
    Derived from CommandsService.js and observations.
    """
    # Core & Connection
    CLIENT_READY = "0000"            # cr: Likely "Client Ready" or initial handshake
    LOGIN = "0002"                   # lr: Login Request
    LIST_DEVICES = "0004"            # ld: Load Devices / List Devices
    HEARTBEAT = "0072"               # cmo: Client Main Online (likely a heartbeat or keep-alive)
                                     # Note: 'cmo' was "0072", 'cad' for controlAllDevices was "0138"

    # Device Control & Management
    TOGGLE_PROPERTY = "0006"         # tp: Toggle Power / Transmit Property (general device update)
    ADD_DEVICE = "0012"              # ad: Add Device
    DELETE_DEVICE = "0014"           # dd: Delete Device
    MODIFY_DEVICE = "0016"           # mde: Modify Device (used for name, lock, icon)
    CONTROL_ALL_DEVICES_BY_TYPE = "0138" # cad: Control All Devices (by type)

    # Timers
    ADD_NEW_TIMER = "0018"           # ant: Add New Timer
    EDIT_TIMER = "0020"              # et: Edit Timer
    DELETE_TIMER = "0022"            # dt: Delete Timer
    DELETE_ALL_TIMERS = "0024"       # dat: Delete All Timers (for a device)
    QUERY_TIMERS = "0028"            # qt: Query Timers (for a specific device)
    GET_ALL_TIMERS = "0044"          # ct: Get All Timers (for the account)

    # LED Control
    MODIFY_LED = "0030"              # ml: Modify LED

    # User Management & Settings
    REQUEST_USER_DETAILS = "0042"    # ru: Request User details
    CHANGE_PASSWORD = "0040"         # cp: Change Password
    FORGOT_PASSWORD_EMAIL = "0153"   # fp: Forgot Password (send email)
    FORGOT_PASSWORD_CODE = "0151"    # fpc: Forgot Password (submit code and new password)
    CHECK_USERNAME_AVAILABILITY = "0145" # cua: Check Username Availability
    CREATE_NEW_ACCOUNT = "0149"      # cnac: Create New Account
    ACCEPT_TERMS_CONDITIONS = "0222" # atc: Accept Terms & Conditions

    # Main Unit (Hub) Management
    REQUEST_EDIT_MASTER_USER = "0032" # remu: Request Edit Master User (MAC/Hub related)
    REQUEST_MASTER_USER_RESET = "0034" # rmu: Request Master User Reset (MAC/Hub related)
    REQUEST_MAIN_UNIT_CONSUMPTION = "0046" # muc: Main Unit Consumption

    # Scenes
    GET_ALL_SCENARIOS = "0112"       # gasc: Get All Scenarios/Scenes
    MODIFY_SCENARIO = "0114"         # msc: Modify Scenario/Scene
    DELETE_SCENARIO = "0116"         # dsc: Delete Scenario/Scene
    CONTROL_SCENARIO = "0118"        # csc: Control/Execute Scenario/Scene
    CREATE_SCENARIO_DEVICE_MODE = "0120" # cdm: Create Device Mode for Scenario?

    # Scenario Timers
    ADD_SCENARIO_TIMER = "0130"      # ast: Add Scenario Timer
    EDIT_SCENARIO_TIMER = "0132"     # est: Edit Scenario Timer
    DELETE_SCENARIO_TIMER = "0134"   # dst: Delete Scenario Timer
    DELETE_ALL_SCENARIO_TIMERS = "0136" # dast: Delete All Scenario Timers (for a scenario)
    GET_SCENARIO_TIMERS = "0140"     # gst: Get Scenario Timers (for a specific scenario)
    GET_ALL_SCENARIO_TIMERS = "0142" # gast: Get All Scenario Timers (for the account)

    # Curtain Specific
    SET_CURTAIN_CLOSED_POS = "0144"  # cuc: Curtain User Configuration (Closed Position)

    # Cameras
    GET_CAMERA_LIST = "0146"         # gcl: Get Camera List
    SAVE_CAMERA_DETAILS = "0148"     # scd: Save Camera Details
    DELETE_CAMERA = "0150"           # dac: Delete Camera
    SAVE_CAMERA_ACCESS = "0152"      # sac: Save Camera Access? (User related)
    UPDATE_CAMERA_ACCESS = "0154"    # uac: Update Camera Access?

    # Device Operation Time (e.g., for door locks)
    SET_DEVICE_OPERATION_TIME = "0156" # dto: Device Time Operation

    # Intercom
    GET_INTERCOM_LIST = "0176"       # gil: Get Intercom List
    SAVE_INTERCOM_DETAILS = "0178"   # sid: Save Intercom Details
    DELETE_INTERCOM_USER = "0182"    # diu: Delete Intercom User
    GET_RESIDENTS_LIST = "0184"      # grl: Get Residents List
    GET_INTERCOM_ACCESS_CODES = "0210" # gac: Get Access Codes
    SAVE_INTERCOM_ACCESS_CODE = "0212" # noe: New Or Edit access code
    DELETE_INTERCOM_ACCESS_CODE = "0214" # rac: Remove Access Code
    GET_QR_CODES = "0224"            # gqc: Get QR Codes
    SAVE_QR_CODE = "0226"            # sqc: Save QR Code
    DELETE_QR_CODE = "0228"          # dqc: Delete QR Code

    # Sharing
    SEND_SHARING_REQUEST = "0216"    # msa: Manage Sharing Add
    EDIT_SHARED_USERS = "0218"       # mse: Manage Sharing Edit
    DELETE_SHARED_USERS = "0220"     # msd: Manage Sharing Delete
    GET_SHARED_BY_TYPE = "0202"      # sbt: Share By Type (get list of users shared with)
    SHARE_WITH_USER = "0204"         # swu: Share With User
    UNSHARE_USER = "0206"            # unu: Unshare User
    UPDATE_SHARED_USER_PERMS = "0208" # usu: Update Shared User

    # Notifications
    GET_NOTIFICATIONS = "0186"       # gnl: Get Notification List
    ADD_NOTIFICATION_CONFIG = "0188" # enl: Edit Notification List (Add/Modify)
    DELETE_NOTIFICATION_CONFIG = "0190" # dan: Delete A Notification

    # Working Hours (likely for shared users or schedules)
    SEND_WORKING_HOURS = "0200"      # swh

    # Favorites
    GET_FAVORITES = "0230"           # gf: Get Favorites
    SAVE_FAVORITES = "0232"          # sf: Save Favorites
    DELETE_FAVORITE = "0234"         # df: Delete Favorite

    # PIMA Systems (Alarm Systems)
    GET_PIMA_SYSTEMS = "0254"        # gps: Get Pima Systems
    SET_NEW_PIMA_SYSTEM = "0256"     # sns: Set New System
    GET_PIMA_CHANNELS = "0258"       # gpc: Get Pima Channels
    SET_NEW_PIMA_CHANNEL = "0260"    # snc: Set New Channel
    DELETE_PIMA_CHANNEL = "0262"     # dtc: Delete The Channel

    # Building Management (likely for multi-tenant or large installations)
    GET_BUILDINGS = "0380"           # gb: Get Buildings
    GET_BUILDING_QR_CODES = "0388"   # gbQr: Get Building QR Codes
    EDIT_BUILDING_QR_CODE = "0390"   # ebQr: Edit Building QR Code
    DELETE_BUILDING_QR_CODE = "0392" # dbQr: Delete Building QR Code
    GET_BUILDING_RF_CARDS = "0394"   # gbRf: Get Building RF Cards
    EDIT_BUILDING_RF_CARD = "0396"   # ebRf: Edit Building RF Card
    DELETE_BUILDING_RF_CARD = "0398" # rbRf: Remove Building RF Card

    # Technician Mode
    GET_TECHNICIAN_PERMISSION = "0128" # tpm: Technician Permission Mode

    # Error/Fallback
    ERROR = "9999"                   # e: General error prefix (though server usually sends 9999 on receive)

class ReceivePrefix(Enum):
    """
    Prefixes for messages received FROM the Homismart server.
    Derived from CommandsService.js and observations.
    """
    # Core & Connection
    LOGIN_RESPONSE = "0003"          # lre: Login Response
    DEVICE_LIST = "0005"             # gd: Get Devices (full list)
    DEVICE_UPDATE_PUSH = "0009"      # pd: Push Device (single device update)
    SERVER_REDIRECT = "0039"         # jts: Jump To Server (redirect instruction with new IP/port)
                                     # Note: The payload for 0039 was {"ip":"...", "port":"..."}
    SERVER_ERROR = "9999"            # ff: Fatal Failure / General Server Error

    # Device Management Responses
    ADD_DEVICE_RESPONSE = "0013"     # ad: Add Device response
    DELETE_DEVICE_RESPONSE = "0015"  # dd: Delete Device response
    BIND_DEVICE_RESPONSE = "0011"    # ab: Add Bind response (related to adding devices)

    # Timer Responses
    TIMER_LIST_FOR_DEVICE = "0029"   # gdl: Get Device List (of timers)
    ALL_TIMERS_LIST = "0045"         # gtl: Get Timers List (all timers for account)
    ADD_TIMER_RESPONSE = "0019"      # at: Add Timer response
    EDIT_TIMER_RESPONSE = "0021"     # et: Edit Timer response
    DELETE_TIMER_RESPONSE = "0023"   # dt: Delete Timer response
    DELETE_ALL_TIMERS_RESPONSE = "0025" # dat: Delete All Timers response

    # User Management & Settings Responses
    USER_DETAILS_RESPONSE = "0043"   # Not in JS, but logical pair to ru "0042"
    CHANGE_PASSWORD_RESPONSE = "0041"# cp: Change Password response
    FORGOT_PASSWORD_EMAIL_SENT = "0152" # rp: Response for Password forgot (email sent)
    FORGOT_PASSWORD_CODE_ACCEPTED = "0150" # rps: Response for Password Set (code accepted)
    USERNAME_AVAILABILITY_RESPONSE = "0144" # ce: Check Email/Username response
    CREATE_ACCOUNT_SUCCESS = "0146"  # cas: Create Account Success
    ACCEPT_TERMS_RESPONSE = "0223"   # atc: Accept Terms & Conditions response

    # Main Unit (Hub) Responses
    MAIN_UNIT_ONLINE_STATUS = "0049" # muo: Main Unit Online status
    MAIN_UNIT_CONSUMPTION_RESPONSE = "0047" # muc: Main Unit Consumption response
    EDIT_MASTER_USER_RESPONSE = "0033" # remu: Response for Edit Master User
    MASTER_USER_RESET_RESPONSE = "0035" # rmu: Response for Master User Reset

    # Scene Responses
    ALL_SCENARIOS_LIST = "0113"      # gasc: Get All Scenarios list
    MODIFY_SCENARIO_RESPONSE = "0115"# msc: Modify Scenario response
    DELETE_SCENARIO_RESPONSE = "0117"# dsc: Delete Scenario response
    CONTROL_SCENARIO_RESPONSE = "0119" # csc: Control Scenario response
    CREATE_SCENARIO_DEVICE_MODE_RESPONSE = "0121" # cdm

    # Scenario Timer Responses
    ADD_SCENARIO_TIMER_RESPONSE = "0131" # ast
    EDIT_SCENARIO_TIMER_RESPONSE = "0133" # est
    DELETE_SCENARIO_TIMER_RESPONSE = "0135" # dst
    DELETE_ALL_SCENARIO_TIMERS_RESPONSE = "0137" # dast
    SCENARIO_TIMERS_LIST = "0141"    # gst
    ALL_SCENARIO_TIMERS_LIST = "0143"# gast

    # Curtain Specific Responses
    # No specific response prefix for SET_CURTAIN_CLOSED_POS ("0144"), likely updates via "0009"

    # Camera Responses
    CAMERA_LIST_RESPONSE = "0147"    # rcl: Receive Camera List
    SAVE_CAMERA_RESPONSE = "0149"    # ucr: Update Camera Response (likely for save/edit)
    DELETE_CAMERA_RESPONSE = "0151"  # dcr: Delete Camera Response

    # Intercom Responses
    INTERCOM_LIST_RESPONSE = "0177"  # ril: Receive Intercom List
    SAVE_INTERCOM_RESPONSE = "0179"  # rid: Response Intercom Details (save/edit)
    DELETE_INTERCOM_USER_RESPONSE = "0183" # diu
    RESIDENTS_LIST_RESPONSE = "0185" # rrl: Receive Residents List
    INTERCOM_ACCESS_CODES_LIST = "0211" # gac
    SAVE_INTERCOM_ACCESS_CODE_RESPONSE = "0213" # noe
    DELETE_INTERCOM_ACCESS_CODE_RESPONSE = "0215" # rac
    QR_CODES_LIST_RESPONSE = "0225"  # gqc
    SAVE_QR_CODE_RESPONSE = "0227"   # sqc
    DELETE_QR_CODE_RESPONSE = "0229" # dqc

    # Sharing Responses
    SHARING_REQUEST_RESPONSE = "0217" # msa
    EDIT_SHARED_USERS_RESPONSE = "0219" # mse
    DELETE_SHARED_USERS_RESPONSE = "0221" # msd
    SHARED_BY_TYPE_RESPONSE = "0203" # sbt
    SHARE_WITH_USER_RESPONSE = "0205" # swu
    UNSHARE_USER_RESPONSE = "0207"   # unu
    UPDATE_SHARED_USER_RESPONSE = "0209" # usu
    SET_MANY_USERS_RESPONSE = "0239" # smu (related to intercom user setup)

    # Notification Responses
    NOTIFICATIONS_LIST = "0187"      # rnl: Receive Notification List
    ADD_NOTIFICATION_RESPONSE = "0189" # ren: Response Edit Notification
    DELETE_NOTIFICATION_RESPONSE = "0191" # rdn: Response Delete Notification

    # Working Hours Response
    WORKING_HOURS_RESPONSE = "0201"  # rwh

    # Favorites Responses
    FAVORITES_LIST = "0231"          # gf
    SAVE_FAVORITES_RESPONSE = "0233" # sf
    DELETE_FAVORITE_RESPONSE = "0235"# df

    # PIMA System Responses
    PIMA_SYSTEMS_LIST = "0255"       # gps
    SET_NEW_PIMA_SYSTEM_RESPONSE = "0257" # sns
    PIMA_CHANNELS_LIST = "0259"      # gpc
    SET_NEW_PIMA_CHANNEL_RESPONSE = "0261" # snc
    DELETE_PIMA_CHANNEL_RESPONSE = "0263" # dtc

    # Building Management Responses
    BUILDINGS_LIST = "0381"          # gb
    BUILDING_QR_CODES_LIST = "0389"  # gbQr
    EDIT_BUILDING_QR_CODE_RESPONSE = "0391" # ebQr
    DELETE_BUILDING_QR_CODE_RESPONSE = "0393" # dbQr
    BUILDING_RF_CARDS_LIST = "0395"  # gbRf
    EDIT_BUILDING_RF_CARD_RESPONSE = "0397" # ebRf
    # DELETE_BUILDING_RF_CARD_RESPONSE not explicitly in JS, but logical pair to rbRf "0398"

    # Technician Mode Response
    TECHNICIAN_PERMISSION_RESPONSE = "0129" # tpm

class DeviceType(IntEnum):
    """
    Numeric codes for different device types.
    Derived from MainDeviceModel.js and GlobalData.js.
    """
    UNKNOWN = 0
    SOCKET = 1
    SWITCH = 2
    # Type 3 is undefined in provided JS
    SHUTTER = 4
    CURTAIN = 5
    SWITCH_MULTI_GANG_A = 6 # Assumption: another switch type
    DOUBLE_SWITCH_OR_SOCKET = 7 # MainDeviceModel.doubleType
    SOCKET_ALT = 8          # Assumption: another socket type
    DOOR_LOCK = 9
    # Type 10 mentioned in TableModel.controlAllDevices for 'all', not a specific device type
    # Types like 45 for 'curtain' in controlAllDevices are group types, not individual device types.

class ErrorCode(IntEnum):
    """
    Error codes received from the server (typically in "9999" messages).
    Derived from MainModel.setErrorArr.
    """
    UNKNOWN_ERROR = 0
    GENERAL_FAILURE = 1 # Also used for code 12
    USERNAME_PASSWORD_ERROR = 2
    NOT_REGISTERED_EMAIL = 3 # Also used for code 54
    USER_ALREADY_EXISTS = 4 # Also used for code 28
    MAIN_UNIT_NOT_ONLINE = 5
    MAC_NOT_FOUND = 7
    WRONG_EMAIL_FORMAT = 9 # Assuming based on "wrong_email"
    USER_FORBIDDEN = 11
    # CODE 12 maps to GENERAL_FAILURE
    MAIN_UNIT_ALREADY_BOUND = 15
    PARAMETER_ERROR = 17 # Also for 19, 22, 26
    CONNECTION_FAILED = 18 # "connect_failed"
    # CODE 19 maps to PARAMETER_ERROR
    # CODE 22 maps to PARAMETER_ERROR
    ENTER_VCODE = 24 # Also for 30, 31, 41, 47 (Verification Code)
    # CODE 26 maps to PARAMETER_ERROR
    # CODE 28 maps to USER_ALREADY_EXISTS
    # CODE 30 maps to ENTER_VCODE
    # CODE 31 maps to ENTER_VCODE
    DEVICE_ALREADY_EXISTS = 33 # Also for 36
    PASSWORD_DEVICE_NOT_MATCH = 34
    # CODE 36 maps to DEVICE_ALREADY_EXISTS
    NO_RESPONSE_FROM_DEVICE = 40 # "no_response"
    # CODE 41 maps to ENTER_VCODE
    # CODE 47 maps to ENTER_VCODE
    # CODE 54 maps to NOT_REGISTERED_EMAIL
    PERMISSION_DENIED = 72
    ADD_DEVICE_FAILED = 76
    OUTSIDE_OF_ACTIVITY_HOURS = 94
    NOT_PRO_USER = 96
    CHANNEL_ALREADY_EXISTS = 109

    # Codes from SocketMsgContainer.errorHandler not in MainModel.setErrorArr
    # These are client-side interpretations rather than server codes.
    # MAC_OFF = client-side interpretation, maps to MAIN_UNIT_NOT_ONLINE (5)
    # NO_MAIN_UNIT = client-side interpretation, maps to MAC_NOT_FOUND (7)
    # EMPTY_INPUT = client-side validation
    # WRONG_PASS = client-side validation, potentially maps to PARAMETER_ERROR or USERNAME_PASSWORD_ERROR
    # LOGIN_TIMEOUT = client-side timeout
    # RELOAD_PAGE = client-side instruction
    # CONNECTION_CLOSE = client-side interpretation of WebSocket close
    # NO_CONNECTION = client-side network status check
    # USERNAME_REQUIRED = client-side validation
    # PASSWORD_REQUIRED = client-side validation

    # Add more as discovered or if the server sends codes not in this initial list.

if __name__ == '__main__':
    # Example usage (can be removed or kept for simple testing)
    print(f"Login Request Prefix: {RequestPrefix.LOGIN.value}")
    print(f"Device List Receive Prefix: {ReceivePrefix.DEVICE_LIST.name} -> {ReceivePrefix.DEVICE_LIST.value}")
    print(f"Curtain Device Type Code: {DeviceType.CURTAIN.value}")
    print(f"Error Code for Permission Denied: {ErrorCode.PERMISSION_DENIED.value}")

    try:
        print(ReceivePrefix('0005').name)
    except ValueError:
        print("Prefix '0005' not found directly by value in ReceivePrefix, use .DEVICE_LIST")

    # Accessing by value (if needed, though direct attribute access is preferred)
    for prefix_enum in ReceivePrefix:
        if prefix_enum.value == "0005":
            print(f"Found by value: {prefix_enum.name}")
            break
