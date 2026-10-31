"""
Señales de PetCare.

Reglas de negocio automáticas:
1. Al registrar una vacuna con próxima dosis se crea (o actualiza) un
   recordatorio de vacunación para la mascota.
2. Al registrar una ficha clínica con próxima revisión se crea (o actualiza)
   un recordatorio de control periódico.

Estas señales permiten que el personal de la clínica no tenga que crear los
recordatorios manualmente y garantizan que la agenda de avisos esté siempre
sincronizada con la atención clínica.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FichaClinica, Recordatorio, Vacuna


@receiver(post_save, sender=Vacuna)
def sincronizar_recordatorio_vacuna(sender, instance, **kwargs):
    """Crea o actualiza el recordatorio de la próxima dosis de una vacuna."""
    if not instance.proxima_dosis:
        # Si la vacuna ya no tiene próxima dosis, se eliminan los avisos
        # pendientes asociados para no mostrar recordatorios obsoletos.
        Recordatorio.objects.filter(
            vacuna=instance,
            estado=Recordatorio.EstadoChoices.PENDIENTE,
        ).delete()
        return

    recordatorio = Recordatorio.objects.filter(vacuna=instance).first()
    if recordatorio is None:
        Recordatorio.objects.create(
            mascota=instance.mascota,
            tipo=Recordatorio.TipoChoices.VACUNA,
            titulo=f'Próxima dosis de {instance.nombre}',
            descripcion=(
                f'Se aplicó {instance.nombre} el '
                f'{instance.fecha_aplicacion:%d/%m/%Y}. '
                f'Corresponde la próxima dosis.'
            ),
            fecha_programada=instance.proxima_dosis,
            vacuna=instance,
        )
        return

    # Si cambió la fecha de la próxima dosis se reactiva el aviso.
    cambio_fecha = recordatorio.fecha_programada != instance.proxima_dosis
    recordatorio.mascota = instance.mascota
    recordatorio.titulo = f'Próxima dosis de {instance.nombre}'
    recordatorio.fecha_programada = instance.proxima_dosis
    if cambio_fecha:
        recordatorio.estado = Recordatorio.EstadoChoices.PENDIENTE
        recordatorio.fecha_envio = None
    recordatorio.save()


@receiver(post_save, sender=FichaClinica)
def sincronizar_recordatorio_control(sender, instance, **kwargs):
    """Crea o actualiza el recordatorio de la próxima revisión clínica."""
    if not instance.proxima_revision:
        Recordatorio.objects.filter(
            ficha=instance,
            estado=Recordatorio.EstadoChoices.PENDIENTE,
        ).delete()
        return

    recordatorio = Recordatorio.objects.filter(ficha=instance).first()
    if recordatorio is None:
        Recordatorio.objects.create(
            mascota=instance.mascota,
            tipo=Recordatorio.TipoChoices.CONTROL,
            titulo=f'Control de {instance.mascota.nombre}',
            descripcion=(
                f'Control posterior a la atención del '
                f'{instance.fecha:%d/%m/%Y}. Diagnóstico: {instance.diagnostico[:150]}'
            ),
            fecha_programada=instance.proxima_revision,
            ficha=instance,
        )
        return

    cambio_fecha = recordatorio.fecha_programada != instance.proxima_revision
    recordatorio.mascota = instance.mascota
    recordatorio.fecha_programada = instance.proxima_revision
    if cambio_fecha:
        recordatorio.estado = Recordatorio.EstadoChoices.PENDIENTE
        recordatorio.fecha_envio = None
    recordatorio.save()
