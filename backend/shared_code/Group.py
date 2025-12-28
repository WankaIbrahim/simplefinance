import json
import uuid

class Item:
    def __init__(
        self,
        id: int | None = uuid.uuid4().int,
        name: str | None= None,
        price: float | None = 0.0,
        quantity: int | None = 1,
        buyer: dict | None= None,
        url: str | None=None,
        purchased: bool | None = False, # Not purchased = 0
        voted: list[str] | None= None
        ):
        self.id = id
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