import azure.functions as func
import logging
import json
import os
import uuid
import requests
from shared_code.Player import Player
from shared_code.Prompt import Prompt
from azure.cosmos import CosmosClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient


app = func.FunctionApp()

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
DBProxy = MyCosmos.get_database_client(os.environ['DatabaseName'])
Translator = TextTranslationClient(endpoint=os.environ['TranslationEndpoint'], credential=AzureKeyCredential(os.environ['TranslationKey']))
PlayerContainerProxy = DBProxy.get_container_client(os.environ['PlayerContainerName'])
PromptContainerProxy = DBProxy.get_container_client(os.environ['PromptContainerName'])

@app.route(route="player/register", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def player_register(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        player = Player.from_dict(data)
        logging.info(f"Request to register player: {data}")
        
        existing = list(PlayerContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username=@username",
            parameters=[{"name": "@username", "value": player.username}],
            enable_cross_partition_query=True
        ))
        
        if existing:
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Username already exists"}),
                mimetype="application/json",
                status_code=200
            )
        
        created_doc = PlayerContainerProxy.create_item(body=player.to_dict())
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            mimetype="application/json",
            status_code=200

        )
    
    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.route(route="player/login", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def player_login(req: func.HttpRequest) -> func.HttpResponse:
    try:  
        data = req.get_json()
        logging.info(f"Attempting to login player: {data}")
        username = data["username"]
        password = data["password"]
        
        
        existing = list(PlayerContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username=@username AND c.password=@password",
            parameters=[{"name": "@username", "value": username}, {"name": "@password", "value": password}],
            enable_cross_partition_query=True
        ))
        
        if(existing):
            return func.HttpResponse(
                json.dumps({"result": True, "msg": "OK"}),
                mimetype="application/json",
                status_code=200
            )
        
        return func.HttpResponse(
            json.dumps({"result": False, "msg": "Username or password incorrect"}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )
        
@app.route(route="player/update", methods=[func.HttpMethod.PUT], auth_level=func.AuthLevel.FUNCTION)
def player_update(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Updating player: {data}")
        username = data["username"]
        add_to_games_played = int(data.get("add_to_games_played", 0))
        add_to_score = int(data.get("add_to_score", 0))
        
        existing = list(PlayerContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username=@username",
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        ))
        
        if(existing):
            data = existing[0]
            data["games_played"] = int(data.get("games_played", 0)) + add_to_games_played
            data["total_score"] = int(data.get("total_score", 0)) + add_to_score
            
            PlayerContainerProxy.replace_item(
                item=data,
                body=data
            )
            
            return func.HttpResponse(
                json.dumps({"result": True, "msg": "OK"}),
                mimetype="application/json",
                status_code=200
            )
        
        return func.HttpResponse(
            json.dumps({"result": False, "msg": "Player does not exist"}),
            mimetype="application/json",
            status_code=200
        ) 
              
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code= 500    
        )

@app.route(route="prompt/create", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_create(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        logging.info(f"Request to create prompt: {data}")
        prompt = Prompt.from_dict(data)
        prompt.validate_length()
        prompt.add_translations(translator_fn)
        
        existing = list(PlayerContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username=@username",
            parameters=[{"name": "@username", "value": prompt.username}],
            enable_cross_partition_query=True
        ))
        
        if not existing:      
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Player does not exist"}),
                mimetype="application/json",
                status_code=200
            )
            
        created_doc = PromptContainerProxy.create_item(body=prompt.to_dict())
        return func.HttpResponse(
            json.dumps({"result": True, "msg": "OK"}),
            mimetype="application/json",
            status_code=200
        )
    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.route(route="prompt/moderate", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_moderate(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        prompt_ids = data.get("prompt-ids", [])
        
        if not prompt_ids or not isinstance(prompt_ids, list):
            return func.HttpResponse(
                json.dumps({"result": False, "msg": "Missing or invalid prompt-ids"}),
                mimetype="application/json",
                status_code=400
            )
        
        endpoint = os.environ["ContentSafetyEndpoint"]
        key = os.environ["ContentSafetyKey"]
        api_version = "2024-09-01"
        url = f"{endpoint}contentsafety/text:analyze?api-version={api_version}"

        
        url = f"{endpoint}contentsafety/text:analyze?api-version={api_version}"
        
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/json"
        }
        
        results = []
        
        for pid in prompt_ids:
            existing = list(PromptContainerProxy.query_items(
                query="SELECT * FROM c WHERE c.id=@id",
                parameters=[{"name": "@id", "value": pid}],
                enable_cross_partition_query=True
            ))

            if not existing:
                logging.info(f"Prompt {pid} does not exist")
                continue

            prompt_doc = existing[0]

            english_text = ""
            for t in prompt_doc.get("texts", []):
                if t.get("language") == "en":
                    english_text = t.get("text", "")
                    break

            if not english_text:
                continue

            body = {"text": english_text}
            response = requests.post(url, headers=headers, json=body)
            result_json = response.json()

            if response.status_code != 200:
                logging.warning(f"Content Safety API error for {pid}: {result_json}")
                continue

            try:
                categories = result_json["categoriesAnalysis"]
                severities = [c["severity"] for c in categories]
                avg_severity = sum(severities) / len(severities)
                outcome = avg_severity > 2
            except Exception as parse_err:
                logging.error(f"Error parsing moderation result for {pid}: {parse_err}")
                continue

            results.append({
                "prompt-id": pid,
                "outcome": outcome,
                "average_severity": round(avg_severity, 2)
            })

        return func.HttpResponse(
            json.dumps(results),
            mimetype="application/json",
            status_code=200
        )

        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.route(route="prompt/delete", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_delete(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        username = data["player"]
        
        existing = list(PromptContainerProxy.query_items(
            query="SELECT * FROM c WHERE c.username=@username",
            parameters=[{"name": "@username", "value": username}],
            enable_cross_partition_query=True
        ))
        
        
        delete_count = 0
        for item in existing:
            try:
                PromptContainerProxy.delete_item(item=item["id"], partition_key=item["username"])
                delete_count+=1
            except Exception as e:
                logging.info(f"Deletion of prompt {item['id']} failed. {str(e)}")
                continue
        
        return func.HttpResponse(
            json.dumps({"result": True, "msg": f"{delete_count} prompts deleted"}),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.route(route="utils/get", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def utils_get(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        usernames = data.get("players", [])
        tag_list = data.get("tag_list", [])
        
        prompts = []
        for username in usernames:
            existing = list(PromptContainerProxy.query_items(
                query="SELECT * FROM c WHERE c.username=@username",
                parameters=[{"name": "@username", "value": username}],
                enable_cross_partition_query=True
            ))
            
            for prompt in existing:
                tags = prompt.get("tags", [])
                if any(tag.lower() in [t.lower() for t in tags] for tag in tag_list):
                    prompts.append({
                        k: v for k, v in prompt.items()
                        if not k.startswith("_")
                    })
                    
        return func.HttpResponse(
            json.dumps(prompts),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"result": False, "msg": str(e)}),
            mimetype="application/json",
            status_code=500
        )

@app.function_name(name="utils_welcome")
@app.cosmos_db_trigger(
    arg_name="documents",
    connection= "AzureCosmosDBConnectionString",
    database_name= os.environ["DatabaseName"],
    container_name=os.environ["PlayerContainerName"],
    lease_container_name="leases",
    create_lease_container_if_not_exists=True
)
def utils_welcome(documents: func.DocumentList) -> None:
    if not documents:
        return
    
    for doc in documents:
        player_data = doc.to_dict()
        username = player_data.get("username")

        if not username:
            logging.warning("Triggered document missing 'username' field.")
            continue

        if player_data.get("games_played", 0) != 0 or player_data.get("total_score", 0) != 0:
            logging.info(f"Skipping update for existing player: {username}")
            continue
        logging.info(f"New player detected: {username}")
        
        prompt = Prompt(username,
                        f"Welcome to COMP3207, {username}",
                        [])
        prompt.add_translations(translator_fn)
        created_doc = PromptContainerProxy.create_item(body=prompt.to_dict())
    return
        


def translator_fn(text, target_lang):
    key = os.environ['TranslationKey']
    endpoint = os.environ['TranslationEndpoint']
    region = os.environ['TranslationRegion']
    path = 'translate'

    constructed_url = endpoint + path

    params = {
        'api-version': '3.0',
        'to': [target_lang],
    }

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        "Ocp-Apim-Subscription-Region": region,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{'text': text}]

    response = requests.post(constructed_url, params=params, headers=headers, json=body)
    response.raise_for_status()
    result = response.json()[0]

    detected_lang = result["detectedLanguage"]["language"]
    confidence = result["detectedLanguage"]["score"]
    translated_text = result["translations"][0]["text"]

    return detected_lang, confidence, translated_text