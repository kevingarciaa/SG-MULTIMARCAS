(function () {
  const lista = document.getElementById("itens");
  const modelo = document.getElementById("modelo-item");
  const totalForms = document.getElementById("id_itens-TOTAL_FORMS");

  // Novo item: copia o modelo trocando __prefix__ pelo próximo índice do formset
  document.getElementById("adicionar-item").addEventListener("click", () => {
    const indice = Number(totalForms.value);
    lista.insertAdjacentHTML("beforeend", modelo.innerHTML.replaceAll("__prefix__", indice));
    totalForms.value = indice + 1;
  });

  // Remover: marca o item como excluído (DELETE) e o esconde, mantendo a numeração do formset
  lista.addEventListener("click", (evento) => {
    const botao = evento.target.closest(".remover-item");
    if (!botao) return;
    const visiveis = lista.querySelectorAll(".item-venda:not(.d-none)");
    if (visiveis.length <= 1) return;
    const item = botao.closest(".item-venda");
    item.querySelector("input[name$='-DELETE']").checked = true;
    item.classList.add("d-none");
  });

  // Vencimento só faz sentido para pagamento em promissória
  const forma = document.getElementById("id_forma_pagamento");
  const vencimento = document.getElementById("campo-vencimento");
  const atualizarVencimento = () => vencimento.classList.toggle("d-none", forma.value !== "promissoria");
  forma.addEventListener("change", atualizarVencimento);
  atualizarVencimento();

  // ---------- Resumo e simulação do total ----------
  const formulario = document.getElementById("form-venda");
  const percentualDesconto = document.getElementById("id_desconto_percentual");
  const cliente = document.getElementById("id_cliente");
  const dataVencimento = document.getElementById("id_vencimento_promissoria");
  const modalElemento = document.getElementById("modal-confirmar-venda");
  const modal = new bootstrap.Modal(modalElemento);
  const botaoConfirmar = document.getElementById("confirmar-venda");
  const aviso = document.getElementById("simulacao-aviso");
  let confirmada = false;

  const moeda = (valor) => valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const textoSelecionado = (select) => select.options[select.selectedIndex]?.text || "";

  function itensSelecionados() {
    return [...lista.querySelectorAll(".item-venda:not(.d-none)")]
      .map((item) => {
        const opcao = item.querySelector("select[name$='-produto']").selectedOptions[0];
        const quantidade = parseInt(item.querySelector("input[name$='-quantidade']").value, 10);
        if (!opcao || !opcao.dataset.preco || !(quantidade > 0)) return null;
        const preco = parseFloat(opcao.dataset.preco);
        return { nome: opcao.dataset.nome, quantidade, preco, subtotal: preco * quantidade };
      })
      .filter(Boolean);
  }

  function calcular() {
    const itens = itensSelecionados();
    const subtotal = itens.reduce((soma, item) => soma + item.subtotal, 0);
    const percentual = parseFloat((percentualDesconto.value || "0").replace(",", ".")) || 0;
    const valorDesconto = Math.round(subtotal * Math.min(Math.max(percentual, 0), 100)) / 100;
    return {
      itens,
      subtotal,
      percentual,
      desconto: valorDesconto,
      total: Math.max(subtotal - valorDesconto, 0),
      quantidade: itens.reduce((soma, item) => soma + item.quantidade, 0),
    };
  }

  function preencher(alvo, resumo) {
    alvo.querySelectorAll("[data-resumo]").forEach((campo) => {
      const chave = campo.dataset.resumo;
      if (chave === "quantidade") campo.textContent = resumo.quantidade;
      else if (chave === "percentual") campo.textContent = `${resumo.percentual.toLocaleString("pt-BR")}%`;
      else if (chave === "desconto") campo.textContent = `- ${moeda(resumo.desconto)}`;
      else campo.textContent = moeda(resumo[chave]);
    });
  }

  const atualizarResumo = () => preencher(document.getElementById("resumo-venda"), calcular());
  formulario.addEventListener("input", atualizarResumo);
  formulario.addEventListener("change", atualizarResumo);
  lista.addEventListener("click", () => setTimeout(atualizarResumo));
  atualizarResumo();

  function problemas(resumo) {
    const promissoria = forma.value === "promissoria";
    if (!cliente.value) return "Selecione o cliente. Vendas só podem ser feitas para clientes cadastrados.";
    if (!resumo.itens.length) return "Selecione pelo menos um produto com quantidade válida.";
    if (!forma.value) return "Escolha a forma de pagamento.";
    if (resumo.percentual < 0 || resumo.percentual > 100) return "O desconto deve ficar entre 0% e 100%.";
    if (promissoria && resumo.total <= 0) return "Venda em promissória precisa ter valor maior que zero.";
    if (promissoria && !dataVencimento.value) return "Informe o vencimento da promissória.";
    return "";
  }

  function abrirSimulacao() {
    const resumo = calcular();
    const corpo = document.getElementById("simulacao-itens");
    corpo.replaceChildren(
      ...resumo.itens.map((item) => {
        const linha = document.createElement("tr");
        [
          [item.nome, ""],
          [item.quantidade, "text-center"],
          [moeda(item.preco), "text-end text-nowrap"],
          [moeda(item.subtotal), "text-end text-nowrap"],
        ].forEach(([texto, classe]) => {
          const celula = document.createElement("td");
          celula.textContent = texto;
          celula.className = classe;
          linha.appendChild(celula);
        });
        return linha;
      })
    );
    preencher(modalElemento, resumo);

    const promissoria = forma.value === "promissoria";
    document.getElementById("simulacao-cliente").textContent = cliente.value ? textoSelecionado(cliente) : "-";
    document.getElementById("simulacao-pagamento").textContent = forma.value ? textoSelecionado(forma) : "-";
    document.getElementById("simulacao-vencimento").textContent =
      dataVencimento.value ? dataVencimento.value.split("-").reverse().join("/") : "-";
    modalElemento.querySelectorAll(".simulacao-vencimento").forEach((el) => el.classList.toggle("d-none", !promissoria));

    const problema = problemas(resumo);
    aviso.textContent = problema;
    aviso.classList.toggle("d-none", !problema);
    botaoConfirmar.disabled = Boolean(problema);
    modal.show();
  }

  formulario.addEventListener("submit", (evento) => {
    if (confirmada) return;
    evento.preventDefault();
    abrirSimulacao();
  });

  botaoConfirmar.addEventListener("click", () => {
    confirmada = true;
    botaoConfirmar.disabled = true;
    formulario.requestSubmit();
  });
})();
