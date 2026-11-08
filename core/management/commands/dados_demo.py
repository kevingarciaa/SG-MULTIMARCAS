import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Perfil
from clientes.models import Cliente
from produtos.models import Produto
from promissorias.models import Pagamento, Promissoria
from vendas.models import ItemVenda, Venda

VENDEDORES = [("joao", "João"), ("maria", "Maria"), ("carlos", "Carlos")]

CLIENTES = [
    {
        "nome": "Ana Souza",
        "telefone": "11987654321",
        "email": "ana.souza@email.com",
        "data_nascimento": date(1990, 3, 12),
        "endereco": "Rua das Flores, 120",
        "bairro": "Centro",
        "cidade": "São Paulo",
    },
    {
        "nome": "Bruno Lima",
        "telefone": "11976543210",
        "email": "bruno.lima@email.com",
        "data_nascimento": date(1985, 7, 22),
        "endereco": "Av. Paulista, 1500",
        "bairro": "Bela Vista",
        "cidade": "São Paulo",
    },
    {
        "nome": "Carla Mendes",
        "telefone": "11965432109",
        "email": "carla.mendes@email.com",
        "data_nascimento": date(1995, 11, 5),
        "endereco": "Rua Augusta, 890",
        "bairro": "Consolação",
        "cidade": "São Paulo",
    },
    {
        "nome": "Diego Rocha",
        "telefone": "11954321098",
        "email": "diego.rocha@email.com",
        "data_nascimento": date(1988, 1, 30),
        "endereco": "Rua Vergueiro, 450",
        "bairro": "Liberdade",
        "cidade": "São Paulo",
    },
    {
        "nome": "Elaine Costa",
        "telefone": "11943210987",
        "email": "elaine.costa@email.com",
        "data_nascimento": date(1992, 9, 18),
        "endereco": "Rua da Consolação, 200",
        "bairro": "Consolação",
        "cidade": "São Paulo",
    },
    {
        "nome": "Fábio Alves",
        "telefone": "11932109876",
        "email": "fabio.alves@email.com",
        "data_nascimento": date(1980, 5, 8),
        "endereco": "Av. Brigadeiro Faria Lima, 3000",
        "bairro": "Itaim Bibi",
        "cidade": "São Paulo",
    },
    {
        "nome": "Gabriela Nunes",
        "telefone": "11921098765",
        "email": "gabriela.nunes@email.com",
        "data_nascimento": date(1998, 12, 1),
        "endereco": "Rua Haddock Lobo, 595",
        "bairro": "Cerqueira César",
        "cidade": "São Paulo",
    },
    {
        "nome": "Henrique Dias",
        "telefone": "11910987654",
        "email": "henrique.dias@email.com",
        "data_nascimento": date(1975, 4, 15),
        "endereco": "Rua Oscar Freire, 700",
        "bairro": "Jardins",
        "cidade": "São Paulo",
        "observacoes": "Cliente preferencial — descontos eventuais.",
    },
]

PRODUTOS = [
    ("Calça Jeans Slim", "Levis", "189.90", "CJ-LEV-001", 40, "Calça jeans slim fit azul"),
    ("Camiseta Básica", "Hering", "49.90", "CM-HER-001", 80, "Camiseta 100% algodão"),
    ("Tênis Casual", "Olympikus", "259.90", "TN-OLY-001", 25, "Tênis casual para o dia a dia"),
    ("Vestido Floral", "Farm", "219.90", "VS-FRM-001", 18, "Vestido midi estampa floral"),
    ("Jaqueta Jeans", "Colcci", "329.90", "JK-COL-001", 15, "Jaqueta jeans oversized"),
    ("Boné Esportivo", "Nike", "89.90", "BN-NIK-001", 50, "Boné aba curva"),
    ("Shorts Moletom", "Adidas", "129.90", "SH-ADI-001", 35, "Shorts confortável"),
    ("Blusa Tricot", "Zara", "159.90", "BL-ZAR-001", 22, "Blusa de tricot manga longa"),
    ("Sandália Rasteira", "Arezzo", "179.90", "SD-ARE-001", 30, "Sandália rasteira couro"),
    ("Mochila Urbana", "Fila", "199.90", "MC-FIL-001", 20, "Mochila com compartimento para notebook"),
]


def gerar_cpf():
    """CPF fictício com dígitos verificadores válidos."""
    while True:
        digitos = [random.randint(0, 9) for _ in range(9)]
        if len(set(digitos)) == 1:
            continue
        for tamanho in (9, 10):
            soma = sum(d * (tamanho + 1 - i) for i, d in enumerate(digitos))
            digitos.append((soma * 10) % 11 % 10)
        return "".join(map(str, digitos))


class Command(BaseCommand):
    help = "Cria dados fictícios para testar o sistema. Use apenas em ambiente de testes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove vendas, promissórias, clientes e produtos antes de criar os dados.",
        )
        parser.add_argument(
            "--vendas",
            type=int,
            default=90,
            help="Quantidade de vendas a criar (padrão: 90).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        hoje = timezone.localdate()
        agora = timezone.now()

        if options["limpar"]:
            self.limpar_dados()
        elif Cliente.objects.exists() or Produto.objects.exists() or Venda.objects.exists():
            raise CommandError(
                "Já existem dados cadastrados. Use --limpar para apagar e recriar, "
                "ou remova os registros manualmente."
            )

        vendedores = self.obter_vendedores()
        clientes = [
            Cliente.objects.create(
                cpf=gerar_cpf(),
                cadastrado_por=random.choice(vendedores),
                **dados,
            )
            for dados in CLIENTES
        ]
        produtos = [
            Produto.objects.create(
                nome=nome,
                marca=marca,
                preco=Decimal(preco),
                codigo=codigo,
                estoque=estoque,
                descricao=descricao,
            )
            for nome, marca, preco, codigo, estoque, descricao in PRODUTOS
        ]

        total_vendas = max(1, options["vendas"])
        for _ in range(total_vendas):
            forma = random.choice(Venda.FormaPagamento.values)
            cliente = random.choice(clientes) if forma == Venda.FormaPagamento.PROMISSORIA or random.random() < 0.7 else None
            venda = Venda.objects.create(
                cliente=cliente,
                forma_pagamento=forma,
                vendedor=random.choice(vendedores),
                data_venda=agora - timedelta(days=random.choice([random.randint(0, 40), random.randint(0, 330)])),
                desconto=Decimal("0") if random.random() < 0.85 else Decimal(random.choice(["10.00", "20.00", "30.00"])),
            )
            for produto in random.sample(produtos, random.randint(1, 3)):
                ItemVenda.objects.create(
                    venda=venda,
                    produto=produto,
                    quantidade=random.randint(1, 3),
                    preco_unitario=produto.preco,
                )
            venda.refresh_from_db()

            if forma == Venda.FormaPagamento.PROMISSORIA and cliente:
                emissao = venda.data_venda.date()
                promissoria = Promissoria.objects.create(
                    cliente=cliente,
                    venda=venda,
                    valor=venda.valor_total,
                    data_emissao=emissao,
                    data_vencimento=emissao + timedelta(days=30),
                    criado_por=venda.vendedor,
                )
                if promissoria.data_vencimento < hoje - timedelta(days=20):
                    Pagamento.objects.create(
                        promissoria=promissoria,
                        valor=promissoria.valor,
                        forma_pagamento="pix",
                        data_pagamento=promissoria.data_vencimento,
                        recebido_por=venda.vendedor,
                    )
                elif promissoria.data_vencimento < hoje and random.random() < 0.4:
                    parcial = (promissoria.valor / 2).quantize(Decimal("0.01"))
                    Pagamento.objects.create(
                        promissoria=promissoria,
                        valor=parcial,
                        forma_pagamento=random.choice(["dinheiro", "pix", "debito"]),
                        data_pagamento=promissoria.data_vencimento + timedelta(days=random.randint(1, 10)),
                        recebido_por=venda.vendedor,
                    )

        for i, dias in enumerate((2, 5, -3, -15)):
            Promissoria.objects.create(
                cliente=clientes[i],
                valor=Decimal(random.choice(["150.00", "220.00", "89.90", "350.00"])),
                data_emissao=hoje - timedelta(days=30),
                data_vencimento=hoje + timedelta(days=dias),
                criado_por=random.choice(vendedores),
                observacoes="Promissória avulsa de demonstração.",
            )

        self.stdout.write(self.style.SUCCESS(
            f"Dados de demonstração criados: {len(clientes)} clientes, "
            f"{len(produtos)} produtos, {total_vendas} vendas."
        ))

    def limpar_dados(self):
        """Remove dados de negócio (mantém usuários)."""
        Pagamento.objects.all().delete()
        Promissoria.objects.all().delete()
        ItemVenda.objects.all().delete()
        Venda.objects.all().delete()
        Cliente.objects.all().delete()
        Produto.objects.all().delete()
        self.stdout.write("Dados anteriores removidos.")

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
