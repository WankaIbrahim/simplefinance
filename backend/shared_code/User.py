import json
import uuid
from passlib.hash import bcrypt


class User:
    def __init__(
            self, 
            username : str, 
            password : str,
            id:str | None = None,
            friends : list[str] | None = None,
            incoming_requests : list[str] | None= None, #storing user ids
            outgoing_requests : list[str] | None = None, # ^^
            bio : str | None = None,     
            email : str | None = None
        ):
        
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.password = password
        self.friends = friends or []
        self.incoming_requests = incoming_requests or []
        self.outgoing_requests = outgoing_requests or []
        self.bio = bio
        self.email = email
        
    def to_json(self):
        return json.dumps(self.to_dict())
    
    def to_dict(self):
        return {
            "id" : self.id,
            "username" : self.username,
            "password" : self.password,
            "friends" : self.friends,
            "incoming_requests" : self.incoming_requests,
            "outgoing_requests" : self.outgoing_requests,
            "bio": self.bio,
            "email": self.email
        }
    
    @classmethod
    def from_dict(cls, data):
        if "username" not in data or "password" not in data:
            raise ValueError("The input keys do not match the ones respective to a user")

        return cls(
            username = data["username"],
            password = data["password"],
            friends =  data.get("friends", []),
            incoming_requests = data.get("incoming_requests", []),
            outgoing_requests = data.get("outgoing_requests", []),
            id=data.get("id"),
            bio=data.get("bio"),
            email=data.get("email")
        )
    
def hash_password(password: str | str = "") -> str:
    return bcrypt.hash(password)

def verify_password(password: str | str = "", stored_hashed_password:  str | str = "") -> bool:
    return bcrypt.verify(password, stored_hashed_password)
#Password Hashing helper ^