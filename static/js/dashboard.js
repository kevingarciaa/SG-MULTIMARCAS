(function () {
  const dados = JSON.parse(document.getElementById("dados-graficos").textContent);

  const formatarMoeda = (valor) =>
    valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const CORES = ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#20c997", "#fd7e14"];

  const opcoesMoeda = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatarMoeda(ctx.parsed.y ?? ctx.parsed)}` } },
    },
    scales: { y: { beginAtZero: true, ticks: { callback: (v) => formatarMoeda(v) } } },
  };

  const opcoesPizza = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom" },
      tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${formatarMoeda(ctx.parsed)}` } },
    },
  };

  // Cada página envia só os dados dos gráficos que exibe
  function criarGrafico(id, chave, montar) {
    const canvas = document.getElementById(id);
    if (canvas && dados[chave]) new Chart(canvas, montar(dados[chave]));
  }

  criarGrafico("graficoVendasDia", "vendasDia", (d) => ({
    type: "line",
    data: {
      labels: d.rotulos,
      datasets: [{
        label: "Vendido", data: d.valores, borderColor: CORES[1],
        backgroundColor: "rgba(25, 135, 84, 0.15)", fill: true, tension: 0.3,
      }],
    },
    options: opcoesMoeda,
  }));

  criarGrafico("graficoEvolucao", "evolucao", (d) => ({
    type: "line",
    data: {
      labels: d.rotulos,
      datasets: [
        {
          label: "Período atual", data: d.valores, borderColor: CORES[0],
          backgroundColor: "rgba(13, 110, 253, 0.12)", fill: true, tension: 0.3,
        },
        {
          label: "Período anterior", data: d.anterior, borderColor: "#adb5bd",
          borderDash: [6, 4], fill: false, tension: 0.3,
        },
      ],
    },
    options: { ...opcoesMoeda, plugins: { ...opcoesMoeda.plugins, legend: { position: "bottom" } } },
  }));

  criarGrafico("graficoFormaPagamento", "formaPagamento", (d) => ({
    type: "doughnut",
    data: { labels: d.rotulos, datasets: [{ data: d.valores, backgroundColor: d.cores }] },
    options: opcoesPizza,
  }));

  criarGrafico("graficoPromissorias", "promissorias", (d) => ({
    type: "pie",
    data: { labels: d.rotulos, datasets: [{ data: d.valores, backgroundColor: ["#198754", "#ffc107", "#dc3545"] }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
  }));
})();
