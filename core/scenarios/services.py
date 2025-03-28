from core.models import Scenario
from bson import ObjectId
from mongoengine.errors import DoesNotExist
from core.models import Action, Scenario

def get_all_scenarios():

    # Načtení všech scénářů s požadovanými poli
    return Scenario.objects.only("id", "name", "description")

def get_scenario_detail(scenario_id):
    try:
        # Nejprve zkusíme načíst scénář přímo se scenario_id (jako string)
        return Scenario.objects.get(id=scenario_id)
    except DoesNotExist:
        try:
            # Pokud to selže, pokusíme se scénář načíst pomocí konverze na ObjectId
            return Scenario.objects.get(id=ObjectId(scenario_id))
        except DoesNotExist:
            return None
        
def load_scenario_from_db(scenario_id):
    """Načte scénář podle ID z databáze."""
    try:
        # Ujistěte se, že ID je správného typu ObjectId
        if not ObjectId.is_valid(scenario_id):
            print(f"ID '{scenario_id}' není platné ObjectId.")
            return None

        # Načtení scénáře
        scenario = Scenario.objects.get(id=ObjectId(scenario_id))
        return scenario.to_mongo().to_dict()  # Převod na Python dict
    except DoesNotExist:
        print(f"Scénář s ID '{scenario_id}' nebyl nalezen.")
        return None
    
    


def load_action(action_id):
    """Načte akci z databáze podle jejího _id."""
    try:
        # Načtení akce podle vlastního ID (_id)
        action = Action.objects.get(_id=action_id)
        return action.to_mongo().to_dict()  # Převod na Python slovník
    except DoesNotExist:
        print(f"Akce s ID '{action_id}' nebyla nalezena.")
        return None
    
def replace_placeholders(value, context):
    """
    Nahrazuje {{key}} v různých typech (str, dict, list) 
    podle hodnot definovaných v `context`.
    
    - Pokud `value` je str, provede .replace() pro všechny klíče v `context`.
    - Pokud je `value` dict, rekurzivně zpracuje všechny položky.
    - Pokud je `value` list, rekurzivně zpracuje všechny prvky.
    - Jinak hodnotu vrátí beze změn.
    """
    if value is None:
        return None

    if isinstance(value, str):
        # Nahrazujeme v řetězci
        for k, v in context.items():
            placeholder = f"{{{{{k}}}}}"
            value = value.replace(placeholder, str(v))
        return value
    elif isinstance(value, dict):
        # Rekurzivně zpracujeme všechny položky slovníku
        new_dict = {}
        for dict_key, dict_val in value.items():
            new_dict[dict_key] = replace_placeholders(dict_val, context)
        return new_dict
    elif isinstance(value, list):
        # Rekurzivně zpracujeme všechny prvky seznamu
        return [replace_placeholders(item, context) for item in value]
    else:
        # int, float, bool, nebo jiný typ => nic neměníme
        return value

async def send_to_websocket(group_name, message):
    """
    Posílá zprávu přes WebSocket do skupiny.
    """
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        group_name,
        {"type": "send_message", "message": message}
    )