from django.apps import AppConfig


class PetcareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'petcare'
    verbose_name = 'Clínica Veterinaria PetCare'

    def ready(self):
        # Registra las señales que generan recordatorios automáticos.
        import petcare.signals  # noqa: F401
