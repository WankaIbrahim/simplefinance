import json
import uuid
import os
import logging
import requests

class Item:
    def __init__(
        self,
        id: int | None = None,
        name: str | None= None,
        price: float | None = 0.0,
        quantity: int | None = 1,
        buyer: dict | None= None,
        url: str | None=None,
        purchased: bool | None = False, # Not purchased = 0
        voted: list[str] | None= None
        ):
        self.id = id if id is not None else uuid.uuid4().int
        self.name = name
        self.price = price
        self.quantity = quantity
        self.buyer = buyer
        self.url = url
        self.purchased = purchased
        self.voted = voted
    
    def to_dict(self):
        return{
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "buyer": self.buyer,
            "url": self.url,
            "purchased": self.purchased,
            "voted": self.voted
        }

class Group:
    def __init__(
        self,
        admins: list[dict],
        name: str,
        groupId: str | None = None,
        guests: list[dict] | None = None,
        users: list[dict] | None = None,
        budget: int | None = 0,
        items: list[Item] | None= None,
        ):
        
        self.groupId = str(groupId) if groupId is not None else str(uuid.uuid4())
        self.id = self.groupId
        self.name = name
        self.admins = admins
        self.guests = guests or []
        self.users = users or []
        self.budget = budget
        self.items = items or []

    def to_json(self):
        return json.dumps(self.to_dict())
    
    def to_dict(self):
        return {
            "id": self.id,
            "groupId" : self.groupId,
            "name" : self.name,
            "guests" : self.guests,
            "users" : self.users,
            "admins" : self.admins,
            "budget" : self.budget,
            "items" : [item.to_dict() for item in self.items]  
        }
    
    @classmethod    
    def from_dict(cls, data):
        if set(data.keys()) != {
            "name",
            "guests",
            "users",
            "admins",
            "budget",
            "items"
        }:
            raise ValueError("Input Keys for this dict is wrong")
        
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        
        admins = data["admins"]
        if not isinstance(admins, list) or len(admins) == 0:
            raise ValueError("admins must be a non-empty list")

        return cls(
            name=data["name"],
            guests=data.get("guests", []),
            users=data.get("users", []),
            admins=data.get("admins"),
            budget=data.get("budget", 0),
            items=[Item(**d) for d in data.get("items", [])],
        )
    

def ai_item_suggest_helper(idea: str | None = "", people: int | None = 0, budget: float | None = 0.0, additional_notes: str | None = "") ->list[dict]:
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_key = os.getenv("AZURE_OPENAI_KEY", "")
    deployment_model = "gpt-4o-mini"
    model_version = "2024-10-21"

    if not azure_endpoint or not azure_key or not deployment_model or not model_version:
        raise ValueError("Missing Key infromation for the OPEN AI env")
    url = f"{azure_endpoint}/openai/deployments/{deployment_model}/chat/completions?api-version={model_version}"
    headers = {"api-key" : azure_key, "Content-Type" : "application/json"}
    ai_system_prompt_guide = (
        "You need to generate a shopping list of items for a group .\n"
        "Return ONLY valid JSON .\n"
        "Schema:\n"
        "{\n"
        '   "items": [\n'
        '    {"name" : Roast Chicken, "quantity" :  2 , "price" : 22.99, "url" : null | string}'
        "    ]\n"
        "}\n"
        "rules are as follows : \n"
        "1. Keep items relevant to the scenario\n"
        "2. The price is per unit in GBP\n"
        "3. Try to keep budget total close to or less than budget\n"
        "4. a range of 4-12 items ideally, but this is a soft margin, if more are needed add more\n"
        "5. additional_notes are important, consider these equally to the other inputs\n"
        "6. Do not include extra fields other than item name, quantity, price, url \n"
    )
    user_input_payload = {
        "idea" : idea,
        "people" : people,
        "budget" : budget,
        "additional_notes" : additional_notes
    }
    # Valid roles system, user and assistant
    body = {
        "messages" : [
            {"role" : "system", "content": ai_system_prompt_guide},
            {"role" : "user", "content" : json.dumps(user_input_payload)}
        ],
        "max_tokens" : 1000, 
        #Randomly set ^^
        "response_format": {"type" : "json_object"}
    }

    r = requests.post(url, headers=headers, json=body, timeout= 25)
    if r.status_code >= 400: 
        raise RuntimeError(f"Azure Open AI error, code : {r.status_code}: {r.text}")
    data = r.json()
    try:    
        gpt_response_content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"unexpected model shape response : {data}")
    try:
        parsed = json.loads(gpt_response_content)
    except json.JSONDecodeError:
        raise RuntimeError(f" Model did not return a JSON same as specified format")
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Model returned an invalid JSON format")
    cleaned: list[dict] = []
    for i in items[: 30]: # first 30 0-29
        if not isinstance(i, dict):
            continue
        item_name = (i.get("name") or "").strip() # get the name of the items
        if not item_name:
            continue
        try:
            item_quantity = int(i.get("quantity", 1)) # get quantity of items
        except Exception:
            item_quantity = 1
        item_quantity = max(1, item_quantity) # take the max quant either 1 or the get amount
        try: 
            item_price = float(i.get("price", 0.0))
        except Exception:
            item_price = 0.0
        item_price = max(0.0, item_price) # get the max item price either 0 or the get amt
        url_item = i.get("url")
        if url_item is not None and not isinstance(url_item, str):
            # if something and not a string set it to Nothing because it is wrong
            url_item = None
        #after cleaning everything append the proper json
        cleaned.append({"name" : item_name, "quantity" : item_quantity, "price" : item_price, "url":  url_item})
    if not cleaned: 
        raise ValueError("No items were generated from the AI response")
    return cleaned