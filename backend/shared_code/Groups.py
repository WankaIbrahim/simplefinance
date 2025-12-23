import json
import uuid

class Item:
    def __init__(
        self,
        id: int | None = 0,
        name: str | None= None,
        price: int | None = 0,
        url: str | None=None,
        purchased: bool | None = False, # Not purchased = 0        
        ):
        self.id = id
        self.name = name
        self.price = price
        self.url = url
        self.purchased = purchased
    
    def to_dict(self):
        return{
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "url": self.url,
            "purchased": self.purchased,
        }


class Groups:
    def __init__(
        self,
        groupId: str | None = None,
        name: str | None = None,
        guests: list[str] | None = None,
        users: list[str] | None = None,
        admins: list[str] | None = None,
        budget: int | None = 0,
        items: list[Item] | None= None,
        ): 
        self.groupId = groupId or str(uuid.uuid4())
        self.name = name
        self.guests = guests or []
        self.users = users or []
        self.admins = admins or []
        self.budget = budget
        self.items = items or []

    def to_json(self):
        return json.dumps({
          "groupId" : self.groupId,
          "name" : self.name,
          "guests" : self.guests,
          "users" : self.users,
          "admins" : self.admins,
          "budget" : self.budget,
          "items" : [item.to_dict() for item in self.items]  
        })
    def to_dict(self):
        return {
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
            "groupId",
            "name",
            "guests",
            "users",
            "admins",
            "budget",
            "items"
        }:
            raise ValueError("Input Keys for this dict is wrong")

        return cls(
            groupId = data['groupId'],
            name = data['name'],
            guests = data['guests'],
            users = data['users'],
            admins = data['admins'],
            budget = data['budget'],
            items = [Item(**d) for d in data['items']]
        )
        