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
})();
