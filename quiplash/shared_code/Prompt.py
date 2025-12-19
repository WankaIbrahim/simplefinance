import json
import uuid

LANGUAGES = ["en", "cy", "es", "ta", "zh-Hans", "ar"]

class Prompt:
    def __init__(self,username,text,tags,id=None):
        self.id = id or str(uuid.uuid4()) 
        self.username = username
        self.text = text
        self.tags = self.tags = self._deduplicate_tags(tags)
        self.texts = []
    
    @staticmethod    
    def _deduplicate_tags(tags):
        return list({tag.lower(): tag for tag in tags}.values())
    
    def validate_length(self):
        if not (20 <= len(self.text) <= 120):
            raise ValueError("Prompt less than 20 characters or more than 120 characters")

    def add_translations(self, translate_fn):
        detected_lang, confidence, _ = translate_fn(self.text, target_lang="en")
        if confidence < 0.2:
            raise ValueError("Unsupported language")

        self.texts.append({"language": detected_lang, "text": self.text})

        for lang in LANGUAGES:
            if lang == detected_lang:
                continue

            _, _, translated = translate_fn(self.text, target_lang=lang)
            self.texts.append({"language": lang, "text": translated})

    @classmethod
    def from_dict(cls, data):
        return cls(
            id = data.get("id"),
            username = data["username"],
            text = data["text"],
            tags = data["tags"]
        )
        
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "texts": self.texts,
            "tags": self.tags
        }    
        
    def to_json(self):
        return json.dumps(self.to_dict())

    