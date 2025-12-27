from shared_code.Group import Group
from shared_code.User import User
import uuid
import requests
import os
import json

#python -m pytest -q -s

BASE_URL = "http://localhost:7071" if os.getenv("USE_LOCAL") else "https://simplefinance.azurewebsites.net"
TIMEOUT = 20

K = {
    "user_register": "ucOHyFIFJ9tZsTJQMfCAwPgdhBMqfS3NFs5oFMNzyUDUAzFujb187g==",
    "user_login": "JuikdiX0WVLbGFLYMIJt66eUE7PYOMvBX9OiK9scEuRWAzFuwxNc3w==",
    "user_delete": "I4TfHBKBgitKNlDv9LvWvaFEbVJtH6YARqS_VAjVpkStAzFu4ETj-w==",
    "user_get": "9_IMEyHplOts3SdViERB0XaArBk5VZbbs5DV_5dVlUCPAzFu7Sd53A==",
    "group_create": "vlrGUpSX0M66XC4zxTbzAlUyQphE3gMFhDrKzvwVMSqtAzFuHFDZCQ==",
    "group_get": "IJe1WWPvJCPSCONYAx1STKfhTFH0mt5rwImcTxyXaXX4AzFuJ1CsLw==",
    "group_delete": "gLWZ6fmQJR4jDCka5SvSUFGqpECwME5d32NViYHan_VLAzFucmQsGg==",
    "group_user_add": "xGd1hmpK0Dr1QRlRMxsiF2NmawmdAhVj6MWuXIyeD3KaAzFu632QDA==",
    "group_user_remove": "sthFQaI_uSDK8T66qymAbNlKFZt3nOXKRn1kSat5eAlwAzFuYXnOQw==",
    "group_user_role_change": "dGst2DxbPun3HBc7sACmmYRlH-BH38jFAuBhPJWpJ-YhAzFumogylw==",
    "group_budget_set": "ErZe7mWprUXR9fTxaz39gicERXFeFjfxno7856M731D-AzFu23R4eA==",
    "group_name_set": "z2iy-teCedFOMW33P1PTFmGt3Cg3oVrAdx8Q4JbniB09AzFunpfr0A==",
}

def post(path, key, payload):
    r = requests.post(f"{BASE_URL}{path}?code={K[key]}", json=payload, timeout=TIMEOUT)
    try:
        print(f"Function: {key}, Response: {r.text}")
        return r.json()
    except Exception:
        raise AssertionError(f"POST {path} returned non-JSON: {r.status_code} {r.text!r}")

def get(path_qs, key):
    r = requests.get(f"{BASE_URL}{path_qs}&code={K[key]}", timeout=TIMEOUT)
    try:
        return r.json()
    except Exception:
        raise AssertionError(f"GET {path_qs} returned non-JSON: {r.status_code} {r.text!r}")

def _has_username(group: dict, section: str, username: str) -> bool:
    return any(u.get("username") == username for u in group.get(section, []))

def test_workflow():
    suffix = uuid.uuid4().hex[:6]

    #Create Test Users
    lewis = {"username" : f"lewis_{suffix}", "password": "Password123"}
    ibrahim = {"username": f"ibrahim_{suffix}", "password": "Password123"}
    
    # Register Test Users
    lewis_id = post("/user/register", "user_register", {"username": lewis["username"], "password": lewis["password"]})["userId"]
    ibrahim_id = post("/user/register", "user_register", {"username": ibrahim["username"], "password": ibrahim["password"]})["userId"]
    
    #Update Test Users
    lewis["id"] = lewis_id
    ibrahim["id"] = ibrahim_id
    
    # Login Test Users
    post("/user/login", "user_login", {"username": lewis["username"], "password": lewis["password"]})
    post("/user/login", "user_login", {"username": ibrahim["username"], "password": ibrahim["password"]})
    
    # Get Test Users
    lewis_got = get(f"/user/get?userId={lewis['id']}", "user_get")["user"]
    assert lewis_got.get("username") == lewis["username"], lewis_got

    ibrahim_got = get(f"/user/get?userId={ibrahim['id']}", "user_get")["user"]
    assert ibrahim_got.get("username") == ibrahim["username"], ibrahim_got
    
    # Create group with ibrahim as admin
    group = {
        "name": f"Group_{suffix}",
        "guests": [],
        "users": [],
        "admins": [{"id": ibrahim["id"], "username": ibrahim["username"]}],
        "budget": 0,
        "items": []
    }
    
    group_create_response = post("/group/create", "group_create", group)
    assert group_create_response.get("result") is True, group_create_response
    group_id = group_create_response["groupId"]
    
    # Assert Group Created
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert g.get("groupId") == group_id
    assert g.get("name") == group["name"]
    assert _has_username(g, "admins", ibrahim["username"])
    
    #Try to delete the only admin
    r = post("/user/delete", "user_delete", {"userId": ibrahim["id"]})
    assert r.get("result") is False
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert _has_username(g, "admins", ibrahim["username"])
    
    # Add Lewis to group as user
    post("/group/user/add", "group_user_add", {
        "groupId": group_id,
        "user": {"id": lewis["id"], "username": lewis["username"]},
        "role": "users"
    })
    
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert _has_username(g, "users", lewis["username"])
    
    # Demote Lewis to guest
    post("/group/user/role/change", "group_user_role_change", {
        "groupId": group_id,
        "user": {"id": lewis["id"], "username": lewis["username"]},
        "role": "guests"
    })
    
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert _has_username(g, "guests", lewis["username"])
    assert not _has_username(g, "users", lewis["username"])
    
    # Set new budget
    post("/group/budget/set", "group_budget_set", {"groupId": group_id, "budget": 1337})
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert g["budget"] == 1337
    
    # Rename group
    new_name = f"Group_Renamed_{suffix}"
    post("/group/name/set", "group_name_set", {"groupId": group_id, "name": new_name})
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert g["name"] == new_name
    
    # TODO
    # Add tests regarding items
    
    # Remove Lewis
    post("/group/user/remove", "group_user_remove", {
        "groupId": group_id,
        "user": {"id": lewis["id"], "username": lewis["username"]}
    })
    
    g = get(f"/group/get?groupId={group_id}", "group_get")["group"]
    assert not _has_username(g, "users", lewis["username"])
    assert not _has_username(g, "guests", lewis["username"])
    assert not _has_username(g, "admins", lewis["username"])
    
    # Delete group
    post("/group/delete", "group_delete", {"groupId": group_id})
    
    # Delete Test Users
    post("/user/delete", "user_delete", {"userId": lewis["id"]})
    post("/user/delete", "user_delete", {"userId": ibrahim["id"]})

