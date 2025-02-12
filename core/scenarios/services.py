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
    
def replace_placeholders(text, replacements):
    """Nahradí zástupné hodnoty v textu."""
    for key, value in replacements.items():
        placeholder = f"{{{{{key}}}}}"
        text = text.replace(placeholder, str(value))
    return text

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