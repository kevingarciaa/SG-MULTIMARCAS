"""Regras de acesso de cada papel (perfil) de usuário.

O Gerente recebe todas as permissões dos apps da loja e enxerga os dados de
todos os vendedores; o Vendedor recebe apenas as listadas em
PERMISSOES_VENDEDOR e enxerga somente as próprias vendas. Para mudar o que
cada papel pode fazer, altere este arquivo e rode: python manage.py criar_grupos
"""

from django.contrib.auth.models import Group, Permission

GRUPO_GERENTE = "Gerente"
GRUPO_VENDEDOR = "Vendedor"
GRUPOS_DE_PAPEL = (GRUPO_GERENTE, GRUPO_VENDEDOR)

APPS_DA_LOJA = ["clientes", "produtos", "vendas", "promissorias"]

PERMISSOES_VENDEDOR = [
    "clientes.view_cliente",
    "clientes.add_cliente",
    "clientes.change_cliente",
    "produtos.view_produto",
    "produtos.add_produto",
    "produtos.change_produto",
    "vendas.view_venda",
    "vendas.add_venda",
    "vendas.view_itemvenda",
    "vendas.add_itemvenda",
    "promissorias.view_promissoria",
    "promissorias.add_promissoria",
    "promissorias.view_pagamento",
    "promissorias.add_pagamento",
    "promissorias.view_historicopromissoria",
]


def eh_gerente(usuario):
    """Gerente (ou superusuário): enxerga os dados de toda a loja."""
    if not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    perfil = getattr(usuario, "perfil", None)
    return perfil is not None and perfil.papel == "gerente"


def _permissoes_do_grupo(nome):
    if nome == GRUPO_GERENTE:
        return list(Permission.objects.filter(content_type__app_label__in=APPS_DA_LOJA))
    permissoes = []
    for codigo in PERMISSOES_VENDEDOR:
        app_label, codename = codigo.split(".")
        permissoes.extend(Permission.objects.filter(content_type__app_label=app_label, codename=codename))
    return permissoes


def configurar_grupos():
    """Cria/atualiza os grupos de papel com suas permissões. Retorna {nome: Group}."""
    grupos = {}
    for nome in GRUPOS_DE_PAPEL:
        grupo, _ = Group.objects.get_or_create(name=nome)
        grupo.permissions.set(_permissoes_do_grupo(nome))
        grupos[nome] = grupo
    return grupos


def obter_grupos():
    """Retorna os grupos de papel, criando e configurando os que ainda não existirem."""
    grupos = {g.name: g for g in Group.objects.filter(name__in=GRUPOS_DE_PAPEL)}
    if len(grupos) < len(GRUPOS_DE_PAPEL):
        grupos = configurar_grupos()
    return grupos
