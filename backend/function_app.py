import azure.functions as func
import json
import logging
import os

from shared_code.User import User
from shared_code.User import hash_password, verify_password
from shared_code.Group import Group, ai_item_suggest_helper
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from passlib.hash import bcrypt

app = func.FunctionApp()

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
DBProxy = MyCosmos.get_database_client(os.environ['DatabaseName'])
UserContainerProxy = DBProxy.get_container_client(os.environ['UserContainerName'])
GroupContainerProxy = DBProxy.get_container_client(os.environ['GroupContainerName'])


@app.route(route="user/register", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def register_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()        
        user = User.from_dict(data)
        logging.info(f"Register attempt for username={user.username}")    
        if not bcrypt.identify(user.password):
            user.password = hash_password(user.password) # now saves the hashed password instead
        logging.warning(f"DEBUG stored password: {user.password}")
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
            query="SELECT TOP 1 * FROM c WHERE c.username = @username",
            parameters=[
                {"name": "@username", "value": username}
            ],
            partition_key=username
        ))
        user = items[0] if items else None
        
        if not user or not verify_password(password, user["password"]):        
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
    
@app.route(route="group/item/add", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def add_item(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to add item to group: {data}")
        
        groupId = data["groupId"]
        item_data = data["item"]
        
        if not item_data.get("name"):
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Item name is required"}),
                status_code=400,
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
        
        if item_data.get("buyer"):
            buyer = item_data["buyer"]
            try:
                UserContainerProxy.read_item(item=buyer["id"], partition_key=buyer["username"])
            except CosmosResourceNotFoundError:
                return func.HttpResponse(
                    json.dumps({"result": False, "msg": "Buyer user does not exist"}),
                    status_code=404,
                    mimetype="application/json"
                )
        
        from shared_code.Group import Item
        new_item = Item(
            name=item_data["name"],
            price=item_data.get("price", 0.0),
            quantity=item_data.get("quantity", 1),
            buyer=item_data.get("buyer"),
            url=item_data.get("url"),
            purchased=item_data.get("purchased", False),
            voted=item_data.get("voted", [])
        )
        
        group["items"].append(new_item.to_dict())
        GroupContainerProxy.replace_item(item=groupId, body=group)
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK", "itemId": new_item.id}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            status_code=400,
            mimetype="application/json"
        )

@app.route(route="group/item/remove", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def remove_item(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to remove item from group: {data}")
        
        groupId = data["groupId"]
        itemId = data["itemId"]
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        original_length = len(group["items"])
        group["items"] = [item for item in group["items"] if item.get("id") != itemId]
        
        if len(group["items"]) == original_length:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Item not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
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

@app.route(route="group/item/update", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def update_item(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to update item: {data}")
        
        groupId = data["groupId"]
        itemId = data["itemId"]
        updates = data["updates"]
        
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )
        
        item_found = False
        for item in group["items"]:
            if item.get("id") == itemId:
                item_found = True
                if "name" in updates:
                    item["name"] = updates["name"]
                if "price" in updates:
                    item["price"] = updates["price"]
                if "quantity" in updates:
                    item["quantity"] = updates["quantity"]
                if "buyer" in updates:
                    buyer = updates["buyer"]
                    if buyer:
                        try:
                            UserContainerProxy.read_item(item=buyer["id"], partition_key=buyer["username"])
                        except CosmosResourceNotFoundError:
                            return func.HttpResponse(
                                json.dumps({"result": False, "msg": "Buyer user does not exist"}),
                                status_code=404,
                                mimetype="application/json"
                            )
                    item["buyer"] = buyer
                if "url" in updates:
                    item["url"] = updates["url"]
                if "purchased" in updates:
                    item["purchased"] = updates["purchased"]
                if "voted" in updates:
                    item["voted"] = updates["voted"]
                break
        
        if not item_found:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Item not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
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

@app.route(route="group/item/vote", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def vote_item(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to vote on item: {data}")
        
        groupId = data["groupId"]
        itemId = data["itemId"]
        username = data["username"]
        vote_action = data.get("action", "toggle") 
        try:
            group = GroupContainerProxy.read_item(item=groupId, partition_key=groupId)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Group does not exist"}),
                status_code=404,
                mimetype="application/json"
            )        
        item_found = False
        for item in group["items"]:
            if item.get("id") == itemId:
                item_found = True
                voted = item.get("voted", [])
                
                if vote_action == "upvote" or (vote_action == "toggle" and username not in voted):
                    if username not in voted:
                        voted.append(username)
                elif vote_action == "downvote" or (vote_action == "toggle" and username in voted):
                    if username in voted:
                        voted.remove(username)
                
                item["voted"] = voted
                break
        if not item_found:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Item not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
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
    
@app.route(route="user/friend/request", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def send_friend_request(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        user_sending_req_id = data["id_from_username_request"]
        user_sending_req = data["from_username_request"] # current logged in user
        user_receiving_req = data["to_username_request"] # the inputted username of the person wanting to be added
        if not isinstance(user_sending_req, str) or not user_sending_req.strip():
            no_request_response = func.HttpResponse(json.dumps({"result": False, "msg": "No username found for this friend request"}),status_code=400, mimetype="application/json") 
            return no_request_response
        if not isinstance(user_receiving_req, str) or not user_receiving_req.strip():
            no_user_to_send_request_response = func.HttpResponse(json.dumps({"result": False, "msg": "No user/username found to send request from"}),status_code=400, mimetype="application/json")
            return no_user_to_send_request_response
        if user_receiving_req == user_sending_req:
            adding_self_response = func.HttpResponse(json.dumps({"result" : False, "msg":  "You cannot add yourself"}), status_code=400, mimetype="application/json")
            return adding_self_response
        try:
            #sending req user
            user_sender = UserContainerProxy.read_item(item= user_sending_req_id, partition_key=user_sending_req)
            #receiving req user
            SQL = """ SELECT TOP 1 * FROM c WHERE c.username = @username"""
            parameters =  [{"name" : "@username", "value": user_receiving_req}]
            items = list(UserContainerProxy.query_items(query=SQL, parameters=parameters, enable_cross_partition_query=True))
            user_receiver = items[0] if items else None
            if user_receiver is None:
                return func.HttpResponse(
                    json.dumps({"result": False, "msg": "Reciever Not found"}), status_code=404, mimetype="application/json"
                )
        except CosmosResourceNotFoundError:
            return func.HttpResponse(json.dumps({"result" : False, "msg": "Sender or Reciever not Found"}), status_code=404, mimetype="application/json")
        for user in (user_receiver, user_sender):
            user.setdefault("friends", [])
            user.setdefault("incoming_requests", [])
            user.setdefault("outgoing_requests", [])
        if user_receiving_req in user_sender["friends"]:
            return func.HttpResponse(json.dumps({"result": False, "msg":  "You are already friends with this user"}), status_code=409, mimetype="application/json")
        if user_receiving_req in user_sender["outgoing_requests"] or user_sending_req in user_receiver["incoming_requests"]:
            return func.HttpResponse(json.dumps({"result": True, "msg": "Request already sent"}), status_code=200, mimetype="application/json")
        user_sender["outgoing_requests"].append(user_receiving_req)
        user_receiver["incoming_requests"].append(user_sending_req)
        UserContainerProxy.replace_item(user_sender["id"], user_sender, user_sender["username"])
        UserContainerProxy.replace_item(user_receiver["id"], user_receiver, user_receiver["username"])
        return func.HttpResponse(
            json.dumps({"result" : True, "msg" : "Friend Request Sent"}), status_code=200, mimetype="application/json"
        )
    except Exception as err:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(err)}), status_code=400, mimetype="application/json"
        )
@app.route(route="user/friend/response", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def respond_friend_request(req : func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        req_to_user_id, req_to_user_username = data["to_id"], data["to_username"]
        req_from_user_username, request_response = data["from_username"], data["accepted"]

        if not isinstance(req_to_user_username, str) or not req_to_user_username.strip():
            no_username_response = func.HttpResponse(json.dumps({"result": False, "msg" : "No username for the user request sent to"}), status_code= 400, mimetype="application/json")
            return no_username_response
        if not isinstance(req_from_user_username, str) or not req_from_user_username.strip():
            no_username_from_response = func.HttpResponse(json.dumps({"result": False, "msg": "No username for the request from User found"}), status_code=400, mimetype="application/json")
            return no_username_from_response
        if not isinstance(request_response, bool):
            non_boolean_req_response = func.HttpResponse(json.dumps({"result": False, "msg": "Not a Boolean response when responding to friend req"}),status_code=400, mimetype="application/json")
            return non_boolean_req_response
        if req_from_user_username == req_to_user_username:
            req_to_self_response = func.HttpResponse(json.dumps({"result" : False, "msg": "Cannot have a freind request to self"}), status_code=200, mimetype="application/json")
            return req_to_self_response
        try:
            user_receiver = UserContainerProxy.read_item(item=req_to_user_id, partition_key=req_to_user_username)
        except CosmosResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "No user reciver" }), status_code=404, mimetype="application/json")
        SQL = """SELECT TOP 1 * FROM c WHERE c.username = @username"""
        parameters = [{"name": "@username", "value": req_from_user_username}]
        items = list(UserContainerProxy.query_items(
            query= SQL, parameters=parameters, enable_cross_partition_query=True
        ))
        user_sender = items[0] if items else None # first item basically aka first query/read
        if user_sender is None:
            return func.HttpResponse(
                json.dumps({"result":  False, "msg": "No sender to found who sent a req"}), status_code=404, mimetype="application/json" # Could happen if someone deletes account
            )
        for user in (user_receiver, user_sender):
            user.setdefault("friends", [])
            user.setdefault("incoming_requests", [])
            user.setdefault("outgoing_requests", [])
        if (req_from_user_username not in user_receiver["incoming_requests"]) or (req_to_user_username not in user_sender["outgoing_requests"]):
            return func.HttpResponse(
                json.dumps({"result" : False, "msg": "Friend request not found"}), status_code=404, mimetype="application/json"
            )
        user_sender["outgoing_requests"] = [x for x in user_sender["outgoing_requests"] if x != req_to_user_username]
        user_receiver["incoming_requests"] = [x for x in user_receiver["incoming_requests"] if x != req_from_user_username]
        if request_response:
            if req_from_user_username not in user_receiver["friends"]:
                user_receiver["friends"].append(req_from_user_username)
            if req_to_user_username not in user_sender["friends"]:
                user_sender["friends"].append(req_to_user_username)
        UserContainerProxy.replace_item(user_receiver["id"], user_receiver, user_receiver["username"])
        UserContainerProxy.replace_item(user_sender["id"], user_sender, user_sender["username"])
        return func.HttpResponse(
            json.dumps({"result" : True,  "msg":  "Accepted" if request_response else "Rejected"}), status_code= 200, mimetype="application/json"
        )
    except Exception as err:
        return func.HttpResponse(json.dumps({"result" : False, "msg" : str(err)}), status_code=400, mimetype="application/json")


@app.route(route="user/update", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def update_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to update user: {data}")

        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": data["userId"]}],
            enable_cross_partition_query=True
        ))


        user_doc = items[0]
        if "password" in data:
            user_doc["password"] = data["password"]
        # if "email" in data:
        #     user_doc["email"] = data["email"]

        UserContainerProxy.replace_item(item=user_doc["id"], body=user_doc)        

        return func.HttpResponse(
            json.dumps({
                "result": True, 
                "msg": "OK",
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
    
@app.route(route="group/items/suggest", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def group_items_ai_suggestion(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()


