from django.db import models
from mongoengine import Document, StringField, ListField, DictField

class NetworkInfo(Document):
    interface = StringField(required=True, max_length=255)
    ip_address = StringField(required=True)
    network = StringField(required=True)

    meta = {
        'collection': 'network_info',  # Název kolekce v MongoDB
        'ordering': ['interface'],    # Třídění dle interface
    }

class Scenario(Document):
    name = StringField(required=True, max_length=255)
    description = StringField(required=True)
    steps = ListField(
        DictField(),  # Každý krok je slovník (dict)
        required=True,  # Pole `steps` je povinné
    )
    
    meta = {
        'collection': 'attack_scenarios',
        'ordering': ['name'],
    }


class Action(Document):
    meta = {'collection': 'actions'}  # Volitelné: Pokud kolekce v MongoDB má název "actions"

    _id = StringField(primary_key=True)  # Používáme vlastní ID jako primární klíč
    name = StringField(required=True, max_length=255)
    type = StringField(required=False, max_length=100, default="local") 
    command = StringField(required=True)
    description = StringField(required=False)  # Popis akce
    required_parameters = ListField(StringField(), default=[])  # Seznam povinných parametrů
    success_keywords = ListField(StringField(), default=[])  # Klíčová slova pro úspěch
    options = DictField()  # Další volitelné parametry (např. pro Metasploit)
    python_function = StringField()  # Název Python funkce pro akci typu 'python'
    category = StringField()  # Kategorie akce (např. "reconnaissance", "exploitation")
    mitre_tactic = StringField()  # MITRE ATT&CK taktika
    mitre_technique = StringField()  # MITRE ATT&CK technika


    def __str__(self):
        return f"{self.name} ({self._id})"