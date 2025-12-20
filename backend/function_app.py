import azure.functions as func
import json
import logging
import os 
from shared_code.User import User
import uuid
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError#, more to import
app = func.FunctionApp()


# Accesses for the Cosmos DB for users
my_cosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
quiplash_db_proxy = my_cosmos.get_database_client(os.environ['DatabaseName'])
user_container_proxy = quiplash_db_proxy.get_container_client(os.environ['UserContainerName'])

#Accesses for the Cosmos DB for another container : To DO
#...

#Decorators Sorry
@app.route(route="user/register", methods=[func.HttpMethod.POST] ,auth_level=func.AuthLevel.FUNCTION)
@app.cosmos_db_output( arg_name="usercontainerbinding",
        	        database_name=os.environ['DatabaseName'],
                      container_name=os.environ['UserContainerName'],
                      create_if_not_exists=True,
                      connection='AzureCosmosDBConnectionString')
def user_register(req: func.HttpRequest, usercontainerbinding: func.Out[func.Document]) -> func.HttpResponse:
    #POST
    req_body = req.get_json()
    logging.info("User Register Request")

    if len(req_body['username'])  < 6 or len(req_body['username']) > 20:
        username_response_body = json.dumps({'result': False, 'msg': "Username less than 6 characters or more than 20 "})
        return func.HttpResponse(body=username_response_body, mimetype="application/json")

    if len(req_body['password']) < 6 or len(req_body['password']) > 20:
        password_response_body = json.dumps({'result': False, 'msg' : "Password is less than 6 characters or more than 20, try a new one!"})
        return func.HttpResponse(body=password_response_body, mimetype="application/json")


    SQL = """
        SELECT TOP 1 c.id
        FROM c
        Where c.username = @username
        """

    parameters  = [{"name" : "@username", "value" : req_body['username']}]
    rows = list(user_container_proxy.query_items(
        query=SQL, parameters=parameters, enable_cross_partition_query=True,
    ))
    if rows:
        #Already exists if a pull works
        pre_existing_user_response_body = json.dumps({"result": False, "msg": "A user with these details already exists, try again!"})  
        return func.HttpResponse(body=pre_existing_user_response_body, mimetype="application/json")

    try:
        user_register_document = {"id" : str(uuid.uuid64()),
                                  "username" : req_body['username'],
                                  "password" : req_body['password']
                                  #, if more to do then do the more should be initialised to 0
                                  }

    except:
        return func.HttpResponse("Something went wrong")

    try:
        #Try to create an object
        user_register_document_for_cosmos = func.Document.from_dict(user_register_document)
        usercontainerbinding.set(user_register_document_for_cosmos)
        logging.info("Out Bind has been successful")
        true_object_response_body = json.dumps({"result": True, "msg": "OK"})
        return func.HttpResponse(body=true_object_response_body, mimetype="application/json")
    except Exception as error:
        logging.error(error)
        return func.HttpResponse("There was an error when registering") 

@app.route(route="user/login",)
def user_login(req: func.HttpRequest) -> func.HttpResponse:
    #POST

    username = req.params.get("username")
    password = req.params.get("password")
    if not username or not password:
        no_user_or_password_response_body = json.dumps({"result" : False, "msg": "Username or password is incorrect !"})
        return func.HttpResponse(body = no_user_or_password_response_body, mimetype="application/json")
    SQL = """
        SELETC TOP c.id
        from c
        WHERE c.username = @username
        AND c.password = @password
    """
    parameters = [{"name" :  "@username", "value" : username},
                  {"name" : "@password", "value" : password},]
    password_and_username_rows = list(user_container_proxy.query_items(
        query=SQL, parameters=parameters, enable_cross_partition = True
    ))
    if not password_and_username_rows:
        no_username_or_password_response_body = json.dumps({"result" : False, "msg" : "Incorrect Username or Password"})
        return func.HttpResponse(body=no_user_or_password_response_body, mimetype="application/json")
    else:
        is_password_and_username_body = json.dumps({"result": True, "msg" : "You Have sucessfully logged in"})
        return func.HttpResponse(body=is_password_and_username_body, mimetype="application/json")

@app.route(route="user/delete", methods=[func.HttpMethod.DELETE], auth_level=func.AuthLevel.FUNCTION)
def delete_user(req: func.HttpRequest)-> func.HttpResponse:
    #DELETE
    username = req.params.get("username") # Passwords will be in the url but it doesn't matter too much
    password = req.params.get("password") # ^^^, we don't care too much right? Can always be changed to a json
    SQL = """
            SELECT TOP 1 * 
            FROM c
            WHERE c.username = @username
            AND c.password = @password
    """
    parameters  = [{"name" : "@username", "value" : username},
                   {"name" : "@password", "value" : password},]
    
    username_and_password_rows = list(user_container_proxy.query_items(
        query = SQL, parameters = parameters, enable_corss_partition_query=True
    ))
    if not username_and_password_rows:
        wrong_details_response_body = json.dumps({"result" : False, "msg": "Username or password inccorect"})
        return func.HttpResponse(body=wrong_details_response_body, mimetype="application/json")
    
    user_document = username_and_password_rows[0] # first thing returned from doc (1), id (2), username password (3)
    user_id = user_document["id"] 
    user_container_proxy.delete_item(item=user_id, partition_key =username)

    true_delete_user_response_body = json.dumps({"result" : True, "msg" : "This user has been deleted"})
    return func.HttpResponse(body=true_delete_user_response_body, mimetype="application/json")

@app.route(route="user/passforgot")
def forgot_password()-> func.HttpResponse:
    #POST
    pass
