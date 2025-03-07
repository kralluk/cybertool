from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from core.models import NetworkInfo
        # NetworkInfo.objects.delete() # Smazání starých dat o dostupných sítích
        # print("Stará data o sítích byla smazána.")   
