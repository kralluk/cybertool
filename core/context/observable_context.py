import asyncio

class ObservableContext(dict):
    """
    Rozšířená verze dictionary, která umožňuje registrovat callbacky pro změny hodnot.
    Když se nastaví nová hodnota pro daný klíč, všechny registrované callbacky (asynchronní funkce)
    se spustí.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callbacks = {}

    def register_callback(self, key, callback):
        """
        Registruje callback, který bude zavolán, když se změní hodnota daného klíče.
        callback musí být asynchronní funkce, která přijímá (key, value).
        """
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                # Spustíme callback jako samostatný task, aby nedošlo k blokaci
                asyncio.create_task(callback(key, value))