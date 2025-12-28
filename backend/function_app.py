import azure.functions as func
import json
import logging
import os 
from shared_code.User import User
from shared_code.Group import Group
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

app = func.FunctionApp()

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
DBProxy = MyCosmos.get_database_client(os.environ['DatabaseName'])
UserContainerProxy = DBProxy.get_container_client(os.environ['UserContainerName'])
GroupContainerProxy = DBProxy.get_container_client(os.environ['GroupContainerName'])

# TODO
# Create function to allow items to be added to groups
# Create function to allow item to be removed from groups
# Create function to allow item details to be updated

@app.route(route="user/register", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def register_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()        
        user = User.from_dict(data)
        logging.info(f"Register attempt for username={user.username}")    
        
        UserContainerProxy.create_item(body=user.to_dict())
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK", "userId": user.id}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="user/login", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def login_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        
        username = data["username"]
        password = data["password"]
        
        logging.info(f"Login attempt for username={username}")

        items = list(UserContainerProxy.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.username = @username AND c.password = @password",
            parameters=[
                {"name": "@username", "value": username},
                {"name": "@password", "value": password}
            ],
            partition_key=username
        ))
        user = items[0] if items else None
        
        if not user:        
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Incorrect username or password"}),
                status_code=200,
                mimetype="application/json"
            )
            
        return func.HttpResponse(
            json.dumps({
                "result": True, 
                "msg": "OK",
                "userId": user["id"],       
                "username": user["username"] 
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="user/delete", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def delete_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to delete user: {data}")
        
        userId = data["userId"]
        
        items = list(UserContainerProxy.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": userId}],
            enable_cross_partition_query=True
        ))
        user_doc = items[0] if items else None
        
        if not user_doc:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
            
        username = user_doc["username"]
        groups = list(GroupContainerProxy.query_items(
            query="""
            SELECT * FROM c
            WHERE ARRAY_CONTAINS(c.admins, {"username": @username}, true)
               OR ARRAY_CONTAINS(c.users,  {"username": @username}, true)
               OR ARRAY_CONTAINS(c.guests, {"username": @username}, true)
            """,
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        ))
        
        blocked = []
        for g in groups:
            admins = g.get("admins", [])
            is_admin = any(a.get("username") == username for a in admins if isinstance(a, dict))
            if is_admin and len(admins) == 1:
                blocked.append({"groupId": g.get("groupId"), "name": g.get("name")})

        if blocked:
            return func.HttpResponse(
                json.dumps({
                    "result": False,
                    "msg": "Cannot delete user: they are the only admin in one or more groups.",
                    "blockedGroups": blocked
                }),
                status_code=400,
                mimetype="application/json"
            )

        def remove_from_role(arr):
            return [o for o in (arr or []) if o.get("username") != username]

        for g in groups:
            g["admins"] = remove_from_role(g.get("admins"))
            g["users"]  = remove_from_role(g.get("users"))
            g["guests"] = remove_from_role(g.get("guests"))

            GroupContainerProxy.replace_item(item=g["id"], body=g)

        
        UserContainerProxy.delete_item(item=userId, partition_key=username)
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
        
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="user/get", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)    
def get_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        userId = req.params.get("userId")
        logging.info(f"Request to get user: {userId}")

        if not userId:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        items = list(UserContainerProxy.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": userId}],
            enable_cross_partition_query=True
        ))
        user = items[0] if items else None

        if not user:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"result": True, "user": user}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/create", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def create_group(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to create group: {data}")
        
        group = Group.from_dict(data)   
        
        if not group.admins:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "admins must contain at least one username"}),
                status_code=400,
                mimetype="application/json"
            )     
        
        admin = group.admins[0]
        userId = admin["id"]
        username = admin["username"]
        
        try:
            UserContainerProxy.read_item(item=userId, partition_key=username)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Admin user does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        GroupContainerProxy.create_item(body=group.to_dict())
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK", "groupId": group.groupId}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/user/add", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def add_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to add user to group: {data}")
        
        groupId = data["groupId"]
        user = data["user"]
        userId = user["id"]
        username = user["username"]
        role = data["role"]
        
        if role not in ("users", "admins", "guests"):
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Invalid role"}),
                status_code=400,
                mimetype="application/json"
            )
        
        try:
            UserContainerProxy.read_item(item=userId, partition_key=username)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        for r in ("users", "admins", "guests"):
            if any(isinstance(u, dict) and u.get("id") == userId for u in group.get(r, [])):
                return func.HttpResponse(
                json.dumps({"result": False, "msg": "User already in group"}),
                status_code=404,
                mimetype="application/json"
                )
                
        group[role].append({"id": userId, "username": username})
        GroupContainerProxy.replace_item(item=groupId, body=group)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/user/remove", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def remove_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to remove user from group: {data}")
        
        groupId = data["groupId"]
        user = data["user"]
        userId = user["id"]
        username = user["username"]
        
        try:
            UserContainerProxy.read_item(item=userId, partition_key=username)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
                
        for r in ("users", "admins", "guests"):
            group[r] = [
                u for u in group.get(r, [])
                if not (isinstance(u, dict) and u.get("id") == userId)
            ]
        GroupContainerProxy.replace_item(item=groupId, body=group)
                
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
        
@app.route(route="group/user/role/change", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def change_role(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to change user role: {data}")
        
        groupId = data["groupId"]
        user = data["user"]
        userId = user["id"]
        username = user["username"]
        role = data["role"]
        
        if role not in ("users", "admins", "guests"):
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Invalid role"}),
                status_code=400,
                mimetype="application/json"
            )
        
        try:
            UserContainerProxy.read_item(item=userId, partition_key=username)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        if any(isinstance(u, dict) and u.get("id") == userId for u in group.get(role, [])):
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User already has this role"}),
                status_code=409,
                mimetype="application/json"
            )
        
        for r in ("users", "admins", "guests"):
            group[r] = [
                u for u in group.get(r, [])
                if not (isinstance(u, dict) and u.get("id") == userId)
            ]
                
        group[role].append({"id": userId, "username": username})
        GroupContainerProxy.replace_item(item=groupId, body=group)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/budget/set", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def update_budget(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to update group budget: {data}")
        
        groupId = data["groupId"]
        change = data["budget"]
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        current = int(group.get("budget", 0))
        new_value = current + change

        if new_value < 0:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Budget cannot go below 0"}),
                status_code=400,
                mimetype="application/json"
            )

        group["budget"] = new_value
        GroupContainerProxy.replace_item(item=groupId, body=group)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/name/set", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def update_name(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to delete group: {data}")
        
        groupId = data["groupId"]
        name = data["name"]
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )        

        group["name"] = name
        GroupContainerProxy.replace_item(item=groupId, body=group)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/delete", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def delete_group(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to update group name: {data}")
        
        groupId = data["groupId"]
        
        try:
            GroupContainerProxy.read_item(item=groupId, partition_key=groupId)    
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
            
        GroupContainerProxy.delete_item(item=groupId, partition_key=groupId)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
        
@app.route(route="group/get", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)    
def get_group(req: func.HttpRequest) -> func.HttpResponse:
    try:
        groupId = req.params.get("groupId")
        logging.info(f"Request to update group name: {groupId}")

        if not groupId:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)

        return func.HttpResponse(
            json.dumps({"result": True, "group": group}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
    

# helper function to get all groups where a user is an admin
# from Nikola
@app.route(route="group/list/admin", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def get_groups_by_admin(req: func.HttpRequest) -> func.HttpResponse:
    try:
        username = req.params.get("username")
        
        if not username:
             return func.HttpResponse(
                json.dumps({"result": False, "msg": "username is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"Searching for groups where admin is: {username}")

        items = list(GroupContainerProxy.query_items(
            query="SELECT * FROM c WHERE ARRAY_CONTAINS(c.admins, {'username': @username}, true)",
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        ))

        return func.HttpResponse(
            json.dumps({"result": True, "groups": items}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
    
    # some helper functions
    # from Nikola
@app.route(route="group/list/member", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def get_groups_by_member(req: func.HttpRequest) -> func.HttpResponse:
    username = req.params.get("username")
    if not username: return func.HttpResponse(json.dumps({"result": False}), status_code=400)

    items = list(GroupContainerProxy.query_items(
        query="SELECT * FROM c WHERE ARRAY_CONTAINS(c.users, {'username': @username}, true)",
        parameters=[{"name": "@username", "value": username}],
        enable_cross_partition_query=True
    ))

    return func.HttpResponse(json.dumps({"result": True, "groups": items}), status_code=200, mimetype="application/json")

@app.route(route="group/list/guest", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def get_groups_by_guest(req: func.HttpRequest) -> func.HttpResponse:
    username = req.params.get("username")
    if not username: return func.HttpResponse(json.dumps({"result": False}), status_code=400)

    items = list(GroupContainerProxy.query_items(
        query="SELECT * FROM c WHERE ARRAY_CONTAINS(c.guests, {'username': @username}, true)",
        parameters=[{"name": "@username", "value": username}],
        enable_cross_partition_query=True
    ))

    return func.HttpResponse(json.dumps({"result": True, "groups": items}), status_code=200, mimetype="application/json")
    
@app.route(route="user/get/username", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)    
def get_user_by_name(req: func.HttpRequest) -> func.HttpResponse:
    try:
        username = req.params.get("username")
        logging.info(f"Request to get user by name: {username}")

        if not username:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Username is required"}),
                status_code=400,
                mimetype="application/json"
            )

        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username = @username",
            parameters=[{"name": "@username", "value": username}],
            partition_key=username 
        ))
        
        user = items[0] if items else None

        if not user:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"result": True, "user": user}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )