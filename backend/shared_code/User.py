import json
import uuid



class User:
    def __init__(
            self, 
            username : str, 
            password : str,
            id:str | None = None 
        ):
        
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.password = password
        
    def to_json(self):
        return json.dumps(self.to_dict())
    
    def to_dict(self):
        return {
            "id" : self.id,
            "username" : self.username,
            "password" : self.password
        }
    
    @classmethod
    def from_dict(cls, data):
        if set(data.keys()) != {
            "username",
            "password"
        }:
            raise ValueError("The input keys do not match the ones respective to a user")

        return cls(
            username = data["username"],
            password = data["password"]
        )