import asyncio
from core.scenarios.services import send_to_websocket

# Registr pro Python akce
PYTHON_ACTION_REGISTRY = {}

def register_python_action(name):
    """
    Dekorátor pro registraci Python akcí.
    Použij ho, když definuješ novou akci, aby se automaticky přidala do registru.
    """
    def decorator(func):
        PYTHON_ACTION_REGISTRY[name] = func
        return func
    return decorator

async def execute_python_action(action, parameters, context, group_name):
    """
    Spustí Python funkci definovanou v akci typu 'python'.
    Očekává se, že v konfiguraci akce bude uveden klíč 'python_function',
    který obsahuje název funkce registrované v PYTHON_ACTION_REGISTRY.
    
    Funkce se volá s předanými parametry a aktuálním kontextem.
    """
    python_function_name = action.get("python_function")
    if not python_function_name:
        await send_to_websocket(group_name, "Chybí specifikace python_function v akci.")
        return False, "Missing python_function specification."

    func = PYTHON_ACTION_REGISTRY.get(python_function_name)
    if not func:
        await send_to_websocket(group_name, f"Python funkce '{python_function_name}' nebyla nalezena.")
        return False, f"Python function '{python_function_name}' not found."

    try:
        # Podpora asynchroních i synchroních funkcí
        if asyncio.iscoroutinefunction(func):
            result = await func(parameters, context)
        else:
            result = func(parameters, context)
            
        await send_to_websocket(group_name, f"Výstup python funkce: {result}")
        return True, result
    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při spuštění python funkce '{python_function_name}': {str(e)}")
        return False, str(e)