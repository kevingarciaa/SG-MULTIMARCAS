// Mostra as datas "De/Até" apenas quando o período personalizado está selecionado
document.querySelectorAll("select[name='periodo']").forEach((select) => {
  const form = select.closest("form");
  const atualizar = () => {
    const personalizado = select.value === "personalizado";
    form.querySelectorAll(".campo-personalizado").forEach((el) => el.classList.toggle("d-none", !personalizado));
  };
  select.addEventListener("change", () => {
    atualizar();
    if (select.value !== "personalizado") form.requestSubmit();
  });
  atualizar();
});
