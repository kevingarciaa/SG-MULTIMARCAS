"""Cálculo dos indicadores e dados dos gráficos dos dashboards.

As funções de vendas recebem um queryset base: o dashboard do gerente passa
todas as vendas da loja e o do vendedor passa apenas as vendas dele.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from clientes.models import Cliente
from produtos.models import Produto
from promissorias.models import Promissoria
from vendas.models import ItemVenda, Venda

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _soma(queryset, campo):
    return queryset.aggregate(total=Sum(campo))["total"] or Decimal("0")


def _inicio_do_mes(data, meses_atras=0):
    ano, mes = data.year, data.month - meses_atras
    while mes <= 0:
        mes += 12
        ano -= 1
    return data.replace(year=ano, month=mes, day=1)


def resumo(vendas):
    """Quantidade, valor e ticket médio de um conjunto de vendas concluídas."""
    totais = vendas.aggregate(quantidade=Count("id"), valor=Sum("valor_total"))
    quantidade, valor = totais["quantidade"], totais["valor"] or Decimal("0")
    return {
        "quantidade": quantidade,
        "valor": valor,
        "ticket_medio": (valor / quantidade).quantize(Decimal("0.01")) if quantidade else Decimal("0"),
    }


def resumo_por_prazo(vendas):
    """Resumo geral, do dia e do mês corrente."""
    hoje = timezone.localdate()
    return {
        "geral": resumo(vendas),
        "dia": resumo(vendas.filter(data_venda__date=hoje)),
        "mes": resumo(vendas.filter(data_venda__date__gte=hoje.replace(day=1))),
    }


def ranking_vendedores(vendas, limite=None):
    """Valor e quantidade vendidos por vendedor, do maior para o menor."""
    dados = (
        vendas.values("vendedor", "vendedor__first_name", "vendedor__last_name", "vendedor__username")
        .annotate(quantidade=Count("id"), valor=Sum("valor_total"))
        .order_by("-valor")
    )
    total = sum((d["valor"] or Decimal("0") for d in dados), Decimal("0"))
    linhas = []
    for d in dados[:limite] if limite else dados:
        nome = f"{d['vendedor__first_name'] or ''} {d['vendedor__last_name'] or ''}".strip()
        valor = d["valor"] or Decimal("0")
        linhas.append({
            "vendedor_id": d["vendedor"],
            "nome": nome or d["vendedor__username"] or "Sem vendedor",
            "quantidade": d["quantidade"],
            "valor": valor,
            "ticket_medio": (valor / d["quantidade"]).quantize(Decimal("0.01")) if d["quantidade"] else Decimal("0"),
            "participacao": float(valor / total * 100) if total else 0.0,
        })
    return {"linhas": linhas, "total": total}


def indicadores_loja():
    vendas = Venda.objects.concluidas()
    em_aberto = Promissoria.objects.em_aberto()
    inicio_mes = timezone.localdate().replace(day=1)
    melhores = ranking_vendedores(vendas.filter(data_venda__date__gte=inicio_mes, vendedor__isnull=False), limite=1)
    return {
        **resumo_por_prazo(vendas),
        "melhor_vendedor": melhores["linhas"][0] if melhores["linhas"] else None,
        "promissorias_abertas": em_aberto.count(),
        "promissorias_vencidas": Promissoria.objects.vencidas().count(),
        "promissorias_pagas": Promissoria.objects.pagas().count(),
        "total_a_receber": _soma(em_aberto, "valor") - _soma(em_aberto, "valor_pago"),
        "total_clientes": Cliente.objects.ativos().count(),
        "total_produtos": Produto.objects.ativos().count(),
    }


def vendas_por_mes(vendas, meses=12):
    """Valor vendido em cada um dos últimos `meses` meses (inclui meses sem venda)."""
    hoje = timezone.localdate()
    inicio = _inicio_do_mes(hoje, meses - 1)
    dados = {
        item["mes"].date() if hasattr(item["mes"], "date") else item["mes"]: item["total"]
        for item in vendas.filter(data_venda__date__gte=inicio)
        .annotate(mes=TruncMonth("data_venda"))
        .values("mes")
        .annotate(total=Sum("valor_total"))
    }
    rotulos, valores = [], []
    for i in range(meses - 1, -1, -1):
        mes = _inicio_do_mes(hoje, i)
        rotulos.append(f"{MESES[mes.month - 1]}/{mes:%y}")
        valores.append(float(dados.get(mes, 0) or 0))
    return {"rotulos": rotulos, "valores": valores}


def vendas_por_dia(vendas, inicio, fim):
    """Valor vendido em cada dia entre `inicio` e `fim` (inclui dias sem venda)."""
    dados = {
        item["dia"]: item["total"]
        for item in vendas.filter(data_venda__date__range=(inicio, fim))
        .annotate(dia=TruncDate("data_venda"))
        .values("dia")
        .annotate(total=Sum("valor_total"))
    }
    rotulos, valores = [], []
    for i in range((fim - inicio).days + 1):
        dia = inicio + timedelta(days=i)
        rotulos.append(f"{dia:%d/%m}")
        valores.append(float(dados.get(dia, 0) or 0))
    return {"rotulos": rotulos, "valores": valores}


def vendas_ultimos_dias(vendas, dias=30):
    hoje = timezone.localdate()
    return vendas_por_dia(vendas, hoje - timedelta(days=dias - 1), hoje)


def formas_pagamento(vendas):
    """Quantidade, valor e participação de cada forma de pagamento."""
    nomes = dict(Venda.FormaPagamento.choices)
    dados = (
        vendas.values("forma_pagamento")
        .annotate(quantidade=Count("id"), valor=Sum("valor_total"))
        .order_by("-valor")
    )
    total = sum((d["valor"] or Decimal("0") for d in dados), Decimal("0"))
    return [
        {
            "nome": nomes.get(d["forma_pagamento"], d["forma_pagamento"]),
            "quantidade": d["quantidade"],
            "valor": d["valor"] or Decimal("0"),
            "participacao": float((d["valor"] or 0) / total * 100) if total else 0.0,
        }
        for d in dados
    ]


def grafico_formas_pagamento(vendas):
    linhas = formas_pagamento(vendas)
    return {"rotulos": [l["nome"] for l in linhas], "valores": [float(l["valor"]) for l in linhas]}


def promissorias_por_situacao():
    vencidas = Promissoria.objects.vencidas().count()
    abertas_em_dia = Promissoria.objects.em_aberto().count() - vencidas
    return {
        "rotulos": ["Pagas", "Abertas (em dia)", "Vencidas"],
        "valores": [Promissoria.objects.pagas().count(), abertas_em_dia, vencidas],
    }


def produtos_mais_vendidos(vendas, limite=5):
    """Produtos ordenados pela quantidade vendida, com o faturamento bruto (antes de descontos)."""
    subtotal = ExpressionWrapper(F("quantidade") * F("preco_unitario"), output_field=DecimalField())
    dados = (
        ItemVenda.objects.filter(venda__in=vendas)
        .values("produto", "produto__nome", "produto__marca")
        .annotate(quantidade_vendida=Sum("quantidade"), faturamento=Sum(subtotal))
        .order_by("-quantidade_vendida", "-faturamento")
    )
    return [
        {
            "nome": f"{d['produto__nome']} ({d['produto__marca']})" if d["produto__marca"] else d["produto__nome"],
            "quantidade": d["quantidade_vendida"],
            "faturamento": d["faturamento"] or Decimal("0"),
        }
        for d in (dados[:limite] if limite else dados)
    ]


def grafico_produtos(vendas, limite=5):
    linhas = produtos_mais_vendidos(vendas, limite)
    return {"rotulos": [l["nome"] for l in linhas], "valores": [l["quantidade"] for l in linhas]}


def variacao(atual, anterior):
    """Variação percentual entre dois valores; None quando não há base de comparação."""
    if not anterior:
        return None
    return float((Decimal(atual) - Decimal(anterior)) / Decimal(anterior) * 100)


def dias_maior_volume(vendas, limite=5):
    return (
        vendas.annotate(dia=TruncDate("data_venda"))
        .values("dia")
        .annotate(quantidade=Count("id"), valor=Sum("valor_total"))
        .order_by("-valor")[:limite]
    )


def analise_periodo(periodo):
    """Todos os dados da página de análises do gerente para o período escolhido."""
    vendas = periodo.filtrar(Venda.objects.concluidas())
    anterior = periodo.anterior()
    vendas_anterior = anterior.filtrar(Venda.objects.concluidas())

    atual, passado = resumo(vendas), resumo(vendas_anterior)
    comparacao = {
        campo: {"atual": atual[campo], "anterior": passado[campo], "variacao": variacao(atual[campo], passado[campo])}
        for campo in ("valor", "quantidade", "ticket_medio")
    }
    evolucao_atual = vendas_por_dia(vendas, periodo.inicio, periodo.fim)
    evolucao_anterior = vendas_por_dia(vendas_anterior, anterior.inicio, anterior.fim)
    vendedores = ranking_vendedores(vendas)
    formas = formas_pagamento(vendas)
    produtos = produtos_mais_vendidos(vendas, limite=10)

    return {
        "anterior": anterior,
        "comparacao": comparacao,
        "vendedores": vendedores,
        "formas": formas,
        "produtos": produtos,
        "dias_top": dias_maior_volume(vendas),
        "graficos": {
            "evolucao": {
                "rotulos": evolucao_atual["rotulos"],
                "valores": evolucao_atual["valores"],
                "anterior": evolucao_anterior["valores"],
            },
            "vendedores": {
                "rotulos": [l["nome"] for l in vendedores["linhas"]],
                "valores": [float(l["valor"]) for l in vendedores["linhas"]],
            },
            "formaPagamento": {"rotulos": [f["nome"] for f in formas], "valores": [float(f["valor"]) for f in formas]},
            "maisVendidos": {"rotulos": [p["nome"] for p in produtos], "valores": [p["quantidade"] for p in produtos]},
        },
    }


def alertas_promissorias(limite=10):
    relacionados = ("cliente",)
    return {
        "vencidas": Promissoria.objects.vencidas().select_related(*relacionados)[:limite],
        "a_vencer": Promissoria.objects.a_vencer().select_related(*relacionados)[:limite],
    }
