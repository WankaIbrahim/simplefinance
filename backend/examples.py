import requests

USE_LOCAL = False
BASE_URL = "http://localhost:7071" if USE_LOCAL else "https://simplefinance.azurewebsites.net"


def example_register_user():
    FUNCTION_KEY = "ucOHyFIFJ9tZsTJQMfCAwPgdhBMqfS3NFs5oFMNzyUDUAzFujb187g=="
    REGISTER_USER_URL = f"{BASE_URL}/user/register?code={FUNCTION_KEY}"

    payload = {
        "username": "Lewis",
        "password": "Password123"
    }

    r = requests.post(REGISTER_USER_URL, json=payload)

    print("Example Register User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_login_user():
    FUNCTION_KEY = "JuikdiX0WVLbGFLYMIJt66eUE7PYOMvBX9OiK9scEuRWAzFuwxNc3w=="
    LOGIN_USER_URL = f"{BASE_URL}/user/login?code={FUNCTION_KEY}"

    payload = {
        "username": "Lewis",
        "password": "Password123"
    }

    r = requests.post(LOGIN_USER_URL, json=payload)

    print("Example Login User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))#

def example_delete_user():
    FUNCTION_KEY = "I4TfHBKBgitKNlDv9LvWvaFEbVJtH6YARqS_VAjVpkStAzFu4ETj-w=="
    DELETE_USER_URL = f"{BASE_URL}/user/delete?code={FUNCTION_KEY}"

    payload = {
        "userId": "596fbc1c-18bd-4752-899b-22582e9c35b8"
    }

    r = requests.post(DELETE_USER_URL, json=payload)

    print("Example Delete User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_get_user():
    FUNCTION_KEY = "9_IMEyHplOts3SdViERB0XaArBk5VZbbs5DV_5dVlUCPAzFu7Sd53A=="
    userId = "713380a1-7c60-433a-b295-aa04ea32c031"

    GET_USER_URL = f"{BASE_URL}/user/get?userId={userId}&code={FUNCTION_KEY}"

    r = requests.get(GET_USER_URL)

    print("Example Get User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_create_group():
    FUNCTION_KEY = "vlrGUpSX0M66XC4zxTbzAlUyQphE3gMFhDrKzvwVMSqtAzFuHFDZCQ=="
    CREATE_GROUP_URL = f"{BASE_URL}/group/create?code={FUNCTION_KEY}"

    payload = {
        "name": "Group J",
        "guests": [],
        "users": [],
        "admins": [{"id": "76aabf43-3a61-4772-96f4-6156df534dd8", "username": "ibrahim"}],
        "budget": 500,
        "items": [],
        "description": 'Description adad',
    }

    r = requests.post(CREATE_GROUP_URL, json=payload)

    print("Example Create Group")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_add_user():
    FUNCTION_KEY = "xGd1hmpK0Dr1QRlRMxsiF2NmawmdAhVj6MWuXIyeD3KaAzFu632QDA=="
    ADD_USER_URL = f"{BASE_URL}/group/user/add?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031",
        "user": {"id": "f7609661-b382-487d-9482-0f019c0d342d", "username": "lewis"},
        "role": "users"
    }

    r = requests.post(ADD_USER_URL, json=payload)

    print("Example Add User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_remove_user():
    FUNCTION_KEY = "sthFQaI_uSDK8T66qymAbNlKFZt3nOXKRn1kSat5eAlwAzFuYXnOQw=="
    REMOVE_USER_URL = f"{BASE_URL}/group/user/remove?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031",
        "user": {"id": "f7609661-b382-487d-9482-0f019c0d342d", "username": "lewis"}
    }

    r = requests.post(REMOVE_USER_URL, json=payload)

    print("Example Remove User")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_change_role():
    FUNCTION_KEY = "dGst2DxbPun3HBc7sACmmYRlH-BH38jFAuBhPJWpJ-YhAzFumogylw=="
    CHANGE_ROLE_URL = f"{BASE_URL}/group/user/role/change?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031",
        "user": {"id": "f7609661-b382-487d-9482-0f019c0d342d", "username": "lewis"},
        "role": "guests"
    }

    r = requests.post(CHANGE_ROLE_URL, json=payload)

    print("Example Change Role")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_update_budget():
    FUNCTION_KEY = "ErZe7mWprUXR9fTxaz39gicERXFeFjfxno7856M731D-AzFu23R4eA=="
    UPDATE_BUDGET_URL = f"{BASE_URL}/group/budget/set?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031",
        "budget": 500
    }

    r = requests.post(UPDATE_BUDGET_URL, json=payload)

    print("Example Update Budget")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_update_name():
    FUNCTION_KEY = "z2iy-teCedFOMW33P1PTFmGt3Cg3oVrAdx8Q4JbniB09AzFunpfr0A=="
    UPDATE_NAME_URL = f"{BASE_URL}/group/name/set?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031",
        "name": "Group New"
    }

    r = requests.post(UPDATE_NAME_URL, json=payload)

    print("Example Update Name")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))

def example_delete_group():
    FUNCTION_KEY = "gLWZ6fmQJR4jDCka5SvSUFGqpECwME5d32NViYHan_VLAzFucmQsGg=="
    DELETE_GROUP_URL = f"{BASE_URL}/group/delete?code={FUNCTION_KEY}"

    payload = {
        "groupId": "713380a1-7c60-433a-b295-aa04ea32c031"
    }

    r = requests.post(DELETE_GROUP_URL, json=payload)

    print("Example Delete Group")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))
    print("HASH:", r.json().get("password"))


def example_group_get():
    FUNCTION_KEY = "IJe1WWPvJCPSCONYAx1STKfhTFH0mt5rwImcTxyXaXX4AzFuJ1CsLw=="
    groupId = "713380a1-7c60-433a-b295-aa04ea32c031"

    GROUP_GET_URL = f"{BASE_URL}/group/get?groupId={groupId}&code={FUNCTION_KEY}"

    r = requests.get(GROUP_GET_URL)

    print("Example Group Get")
    print("STATUS:", r.status_code)
    print("BODY:", repr(r.text))


if __name__ == "__main__":
    example_create_group()
    