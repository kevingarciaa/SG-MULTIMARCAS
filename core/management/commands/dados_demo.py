import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Perfil
from clientes.models import Cliente
from produtos.models import Produto
from promissorias.models import Pagamento, Promissoria
from vendas.models import ItemVenda, Venda

VENDEDORES = [("joao", "João"), ("maria", "Maria"), ("carlos", "Carlos")]
CLIENTES = ["Ana Souza", "Bruno Lima", "Carla Mendes", "Diego Rocha", "Elaine Costa", "Fábio Alves"]
PRODUTOS = [
    ("Calça Jeans", "Levis", "189.90"), ("Camiseta Básica", "Hering", "49.90"),
    ("Tênis Casual", "Olympikus", "259.90"), ("Vestido Floral", "Farm", "219.90"),
    ("Jaqueta", "Colcci", "329.90"), ("Boné", "Nike", "89.90"),
]


class Command(BaseCommand):
    help = "Cria dados fictícios para testar o dashboard. Use apenas em ambiente de testes."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        hoje = timezone.localdate()
        agora = timezone.now()

        vendedores = self.obter_vendedores()
        clientes = [
            Cliente.objects.create(nome=n, telefone=f"119{i:08d}", cadastrado_por=random.choice(vendedores))
            for i, n in enumerate(CLIENTES)
        ]
        produtos = [
            Produto.objects.create(nome=n, marca=m, preco=Decimal(p), estoque=50) for n, m, p in PRODUTOS
        ]

        for _ in range(90):
            forma = random.choice(Venda.FormaPagamento.values)
            cliente = random.choice(clientes)
            venda = Venda.objects.create(
                cliente=cliente, forma_pagamento=forma, vendedor=random.choice(vendedores),
                data_venda=agora - timedelta(days=random.choice([random.randint(0, 40), random.randint(0, 330)])),
            )
            for produto in random.sample(produtos, random.randint(1, 3)):
                ItemVenda.objects.create(venda=venda, produto=produto, quantidade=random.randint(1, 3))
            venda.refresh_from_db()

            if forma == Venda.FormaPagamento.PROMISSORIA:
                emissao = venda.data_venda.date()
                promissoria = Promissoria.objects.create(
                    cliente=cliente, venda=venda, valor=venda.valor_total,
                    data_emissao=emissao, data_vencimento=emissao + timedelta(days=30),
                )
                if promissoria.data_vencimento < hoje - timedelta(days=20):
                    Pagamento.objects.create(
                        promissoria=promissoria, valor=promissoria.valor, forma_pagamento="pix",
                        data_pagamento=promissoria.data_vencimento,
                    )

        for i, dias in enumerate((2, 5, -3)):
            Promissoria.objects.create(
                cliente=clientes[i], valor=Decimal("150.00"),
                data_emissao=hoje - timedelta(days=30), data_vencimento=hoje + timedelta(days=dias),
            )

        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados."))

    def obter_vendedores(self):
        """Usa os vendedores cadastrados; se não houver, cria João, Maria e Carlos (sem senha)."""
        Usuario = get_user_model()
        vendedores = list(Usuario.objects.filter(perfil__papel=Perfil.Papel.VENDEDOR, is_active=True))
        if vendedores:
            return vendedores
        for login, nome in VENDEDORES:
            usuario = Usuario(username=login, first_name=nome)
            usuario.set_unusable_password()
            usuario.save()
            vendedores.append(usuario)
        self.stdout.write("Vendedores de demonstração criados sem senha: defina a senha em /admin para usá-los.")
        return vendedores
