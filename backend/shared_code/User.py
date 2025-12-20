import json
import uuid



class User:
    def __init__(
            self, 
            ident:str | None = None, 
            username : str | None = "", 
            password : str | None = "" 
            #, to do whatever other things we need
        ):
        self.id = ident or str(uuid.uuid4())
        self.username = username
        self.password = password
        #, to do whatever other things we need
    def to_json(self):
        return json.dumps({
            "id": self.id,
            "username" : self.username,
            "password" : self.password
            #, to do whatever other things we need
        })
    def to_dict(self):
        return {
            "id" : self.id,
            "username" : self.username,
            "password" : self.password
            #, to do whatever other things we need
        }
    def from_dict(self, dictionary_tree):
            #Check the pull from dict is the same as expected keys
        if set(dictionary_tree.keys()) != {
            "id",
            "username",
            "password"
            #, to do whatever other things we need
        }:
            raise ValueError("The input keys do not match the ones respective to a user")

        self.id = dictionary_tree['id']
        self.username = dictionary_tree['username']
        self.password = dictionary_tree['password']
        #self. to do whatever other things we need