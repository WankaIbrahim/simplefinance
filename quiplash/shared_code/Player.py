import json
import uuid

class Player:
    def __init__(self,username,password,id=None):
        if not 5 <= len(username) <= 12: 
            raise ValueError("Username less than 5 characters or more than 12 characters")
        if not 8 <= len(password) <= 12:
            raise ValueError("Password less than 8 characters or more than 12 characters")
        
        self.id = id or str(uuid.uuid4()) 
        self.username = username
        self.password = password
        self.games_played = 0
        self.total_score = 0

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "games_played": self.games_played,
            "total_score": self.total_score,
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(
            id = data.get("id"),
            username = data["username"],
            password = data["password"]
        )
        
    def to_json(self):
        return json.dumps(self.to_dict())

    