import azure.functions as func
import json
import logging
import os

from shared_code.User import User
from shared_code.User import hash_password, verify_password
from shared_code.Group import Group, ai_item_suggest_helper, Item
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
        logging.info(f"Request to update group name: {data}")
        
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
        logging.info(f"Request to delete group: {data}")
        
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

        current_user_id = data.get("userId") 
        originator_username = data.get("friendUsername")
        response_accepted = data.get("accepted")

        if not current_user_id or not originator_username or response_accepted is None:
             return func.HttpResponse(json.dumps({"result": False, "msg": "Missing parameters"}), status_code=400, mimetype="application/json")

        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": current_user_id}],
            enable_cross_partition_query=True
        ))
        
        if not items:
             return func.HttpResponse(json.dumps({"result": False, "msg": "Current user not found"}), status_code=404, mimetype="application/json")
        
        user_receiver = items[0]
        receiver_username = user_receiver["username"]

        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username = @username",
            parameters=[{"name": "@username", "value": originator_username}],
            partition_key=originator_username
        ))
        
        if not items:
             return func.HttpResponse(json.dumps({"result": False, "msg": "Friend user not found"}), status_code=404, mimetype="application/json")
        
        user_sender = items[0]

        if originator_username not in user_receiver.get("incoming_requests", []):
             return func.HttpResponse(json.dumps({"result": False, "msg": "No incoming request from this user"}), status_code=400, mimetype="application/json")

        user_receiver["incoming_requests"] = [u for u in user_receiver.get("incoming_requests", []) if u != originator_username]
        user_sender["outgoing_requests"] = [u for u in user_sender.get("outgoing_requests", []) if u != receiver_username]

        if response_accepted:
            user_receiver.setdefault("friends", [])
            user_sender.setdefault("friends", [])
            
            if originator_username not in user_receiver["friends"]:
                user_receiver["friends"].append(originator_username)
            
            if receiver_username not in user_sender["friends"]:
                user_sender["friends"].append(receiver_username)

        UserContainerProxy.replace_item(item=user_receiver["id"], body=user_receiver)
        UserContainerProxy.replace_item(item=user_sender["id"], body=user_sender)

        return func.HttpResponse(
            json.dumps({"result" : True,  "msg":  "Accepted" if response_accepted else "Rejected"}), status_code= 200, mimetype="application/json"
        )
    except Exception as err:
        return func.HttpResponse(json.dumps({"result" : False, "msg" : str(err)}), status_code=400, mimetype="application/json")

@app.route(route="user/friend/remove", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)    
def remove_friend(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        current_user_id = data.get("userId")
        friend_username = data.get("friendUsername")

        if not current_user_id or not friend_username:
            return func.HttpResponse(json.dumps({"result": False, "msg": "Missing parameters"}), status_code=400, mimetype="application/json")

        # Get the current user
        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": current_user_id}],
            enable_cross_partition_query=True
        ))
        if not items: return func.HttpResponse(json.dumps({"result": False, "msg": "User not found"}), status_code=404)
        user_current = items[0]
        current_username = user_current["username"]

        # Get the friend
        items = list(UserContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username = @username",
            parameters=[{"name": "@username", "value": friend_username}],
            partition_key=friend_username
        ))
        if not items: return func.HttpResponse(json.dumps({"result": False, "msg": "Friend not found"}), status_code=404)
        user_friend = items[0]

        # Remove from friends lists
        if "friends" in user_current:
            user_current["friends"] = [f for f in user_current["friends"] if f != friend_username]
        
        if "friends" in user_friend:
            user_friend["friends"] = [f for f in user_friend["friends"] if f != current_username]

        UserContainerProxy.replace_item(item=user_current["id"], body=user_current)
        UserContainerProxy.replace_item(item=user_friend["id"], body=user_friend)

        return func.HttpResponse(json.dumps({"result": True, "msg": "Friend removed"}), status_code=200, mimetype="application/json")

    except Exception as e:
        return func.HttpResponse(json.dumps({"result": False, "msg": str(e)}), status_code=400, mimetype="application/json")

@app.route(route="user/update", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def update_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to update user: {data}")

        user_id = data.get("userId")
        if not user_id:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "userId is required"}),
                status_code=400,
                mimetype="application/json"
            )

        items = list(UserContainerProxy.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": user_id}],
            enable_cross_partition_query=True
        ))

        if not items:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "User does not exist"}),
                status_code=404,
                mimetype="application/json"
            )

        user_doc = items[0]
        old_username = user_doc.get("username")

        if "password" in data and data["password"]:
            user_doc["password"] = data["password"]

        if "pfpUrl" in data:
            user_doc["pfpUrl"] = data["pfpUrl"]

        if "email" in data:
            user_doc["email"] = data["email"]

        if "bio" in data:
            user_doc["bio"] = data["bio"]

        new_username = data.get("username")
        if new_username:
            new_username = new_username.strip()

        if new_username and new_username != old_username:
            existing = list(UserContainerProxy.query_items(
                query="SELECT TOP 1 * FROM c WHERE c.username = @username",
                parameters=[{"name": "@username", "value": new_username}],
                enable_cross_partition_query=True
            ))
            if existing:
                return func.HttpResponse(
                    json.dumps({"result": False, "msg": "Username already taken"}),
                    status_code=409,
                    mimetype="application/json"
                )
            new_doc = dict(user_doc)
            new_doc["username"] = new_username

            UserContainerProxy.create_item(body=new_doc)

            UserContainerProxy.delete_item(item=user_doc["id"], partition_key=old_username)

            groups = list(GroupContainerProxy.query_items(
                query="""
                SELECT * FROM c
                WHERE ARRAY_CONTAINS(c.admins, {"username": @username}, true)
                   OR ARRAY_CONTAINS(c.users,  {"username": @username}, true)
                   OR ARRAY_CONTAINS(c.guests, {"username": @username}, true)
                """,
                parameters=[{"name": "@username", "value": old_username}],
                enable_cross_partition_query=True
            ))

            def replace_username(arr):
                out = []
                for u in (arr or []):
                    if isinstance(u, dict) and u.get("id") == user_id:
                        out.append({"id": u.get("id"), "username": new_username})
                    else:
                        out.append(u)
                return out

            for g in groups:
                g["admins"] = replace_username(g.get("admins"))
                g["users"]  = replace_username(g.get("users"))
                g["guests"] = replace_username(g.get("guests"))
                GroupContainerProxy.replace_item(item=g["id"], body=g)

            return func.HttpResponse(
                json.dumps({"result": True, "msg": "OK", "username": new_username}),
                status_code=200,
                mimetype="application/json"
            )

        UserContainerProxy.replace_item(item=user_doc["id"], body=user_doc)

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

    
@app.route(route="group/items/suggest", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def group_items_ai_suggestion(req: func.HttpRequest) -> func.HttpResponse:
    try: 
        data = req.get_json()
        groupId = data.get("groupId")
        idea = (data.get("idea") or "").strip() # remove trailing whitespace etc
        people = data.get("people")
        budget = data.get("budget")
        additional_notes = data.get("additional_notes")
        add_items_to_group = data.get("addToGroup", False)
        if isinstance(add_items_to_group, str):
            add_items_to_group = add_items_to_group.lower() in ("1", "true", "yes")
        else:
            add_items_to_group = bool(add_items_to_group)
        if not idea or not isinstance(idea, str):
            no_idea_response_body = json.dumps({"result" : False, "msg" : "No idea or improper format"})
            return func.HttpResponse(no_idea_response_body, status_code=400, mimetype="application/json") 
        if not groupId or not isinstance(groupId, str):
            no_groupId_response_body = json.dumps({"result" : False, "msg" : "No group id Found or improper format"})
            return func.HttpResponse(no_groupId_response_body, status_code=400, mimetype="application/json")
        try:
            if people is not None: 
                people =  int(people)
            else : 
                people = None
        except Exception:
            people = None
        if people is not None:
            #Dinner part for 1000 people maybe ?  or just keep it locked at like 50 ? 
            people = max(1, min(1000, people))
        try:
            if budget is not None:
                budget = float(budget)
            else:
                budget = None
        except Exception:
            budget = None
        if budget is not None:
            budget = max(0.0, budget)
        suggested_items = ai_item_suggest_helper(idea, people, budget, additional_notes)
        item_dictionary = []
        new_item_ids = []
        for i in suggested_items:
            # Create the proper shape for every item in the dictionary then append to a list of items
            # Alongside appropriate ids
            new_item = Item(
                name=i["name"],
                price = i.get("price", 0.0),
                quantity = i.get("quantity", 1),
                url = i.get("url"),
                purchased = False,
                voted = []
            )
            item_dictionary.append(new_item.to_dict())
            new_item_ids.append(new_item.id)
        if add_items_to_group:
            try:
                group = GroupContainerProxy.read_item(item = groupId, partition_key=groupId)
            except CosmosResourceNotFoundError:
                unable_load_group_response_body = json.dumps({"result" : False, "msg" : "Unable to load a group, no group found"})
                return func.HttpResponse(unable_load_group_response_body, status_code=404, mimetype="application/json")
            group.setdefault("items" , [])
            group["items"].extend(item_dictionary)
            GroupContainerProxy.replace_item(item=groupId, body=group)
            
        correct_output_response_body = json.dumps({
            "result" : True, "msg" : "OK" , "added" : add_items_to_group, "itemIds" : new_item_ids if add_items_to_group else [], "items" : item_dictionary
        })
        return func.HttpResponse(correct_output_response_body, status_code=200, mimetype="application/json")
    except Exception as err:
        logging.exception("AI RESPONSE FAILED")
        failed_AI_response_body = json.dumps({"result" : False, "msg" : str(err)})
        return func.HttpResponse(failed_AI_response_body, status_code=400, mimetype="application/json")