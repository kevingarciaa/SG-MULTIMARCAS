from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_do_usuario(sender, instance, created, raw=False, **kwargs):
    """Todo usuário novo ganha um perfil (superusuário = Administrador; demais = Vendedor)."""
    if created and not raw:
        Perfil.objects.create(usuario=instance, papel=Perfil.papel_inicial(instance))
