import azure.functions as func
import json
import logging
import os 
from shared_code.User import User
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError#, more to import
app = func.FunctionApp()


# Accesses for the Cosmos DB for users
my_cosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
quiplash_db_proxy = my_cosmos.get_database_client(os.environ['DatabaseName'])
user_container_proxy = quiplash_db_proxy.get_container_client(os.environ['UserContainerName'])

#Accesses for the Cosmos DB for another container : To DO
#...

def user_register():
    pass

def user_login():
    pass

def delete_user():
    pass


def forgot_password():
    pass
