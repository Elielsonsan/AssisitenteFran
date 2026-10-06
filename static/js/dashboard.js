/**
 * Assistente Fran - dashboard.js
 * Inicialização dos gráficos com Chart.js e exportação de PDF com html2pdf.js
 */

// Variáveis globais dos dados do Dashboard (carregadas com segurança via application/json)
let STATUS_LABELS = [];
let STATUS_VALORES = [];
let TEMA_LABELS = [];
let TEMA_ACERTOS = [];
let TEMA_ERROS = [];
let TEMA_PARCIAIS = [];
let submissoesData = {};

// Instâncias ativas dos gráficos Chart.js para atualização dinâmica de tema
let chartStatusInstance = null;
let chartTemasInstance = null;

/**
 * Retorna as cores apropriadas para os gráficos de acordo com o tema atual
 */
function getChartThemeColors(tema) {
    const isLight = tema === "light";
    return {
        textColor: isLight ? "#0f172a" : "#cbd5e1",
        mutedTextColor: isLight ? "#334155" : "#94a3b8",
        gridColor: isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.05)",
        doughnutBorder: isLight ? "#ffffff" : "#162032"
    };
}

/**
 * Atualiza dinamicamente as cores dos gráficos Chart.js quando o usuário alterna o tema
 */
window.atualizarCoresGraficosTema = function(tema) {
    const temaAtivo = tema || document.documentElement.getAttribute("data-theme") || "dark";
    const colors = getChartThemeColors(temaAtivo);

    if (chartStatusInstance) {
        if (chartStatusInstance.options.plugins && chartStatusInstance.options.plugins.legend) {
            chartStatusInstance.options.plugins.legend.labels.color = colors.textColor;
        }
        if (chartStatusInstance.data.datasets && chartStatusInstance.data.datasets[0]) {
            chartStatusInstance.data.datasets[0].borderColor = colors.doughnutBorder;
        }
        chartStatusInstance.update();
    }

    if (chartTemasInstance) {
        if (chartTemasInstance.options.plugins && chartTemasInstance.options.plugins.legend) {
            chartTemasInstance.options.plugins.legend.labels.color = colors.textColor;
        }
        if (chartTemasInstance.options.scales) {
            if (chartTemasInstance.options.scales.x) {
                chartTemasInstance.options.scales.x.ticks.color = colors.mutedTextColor;
                chartTemasInstance.options.scales.x.grid.color = colors.gridColor;
            }
            if (chartTemasInstance.options.scales.y) {
                chartTemasInstance.options.scales.y.ticks.color = colors.mutedTextColor;
                chartTemasInstance.options.scales.y.grid.color = colors.gridColor;
            }
        }
        chartTemasInstance.update();
    }
};

function carregarDadosDashboard() {
    const dataScript = document.getElementById("dashboard-data");
    if (dataScript && dataScript.textContent) {
        try {
            const dados = JSON.parse(dataScript.textContent);
            STATUS_LABELS = dados.status_labels || [];
            STATUS_VALORES = dados.status_valores || [];
            TEMA_LABELS = dados.tema_labels || [];
            TEMA_ACERTOS = dados.tema_acertos || [];
            TEMA_ERROS = dados.tema_erros || [];
            TEMA_PARCIAIS = dados.tema_parciais || [];
            submissoesData = dados.submissoes || {};
        } catch (e) {
            console.error("Erro ao processar dados do dashboard:", e);
        }
    }
}

// Carrega imediatamente se o elemento já estiver no DOM
document.addEventListener("DOMContentLoaded", () => {
    carregarDadosDashboard();
    inicializarGraficos();
    atualizarDataEmissao();
    renderizarPaginacaoRisco();
    renderizarPaginacaoSubmissoes();
});

/**
 * Atualiza a data e hora de emissão no cabeçalho do relatório
 */
function atualizarDataEmissao() {
    const el = document.getElementById("dataRelatorio");
    if (el) {
        const hoje = new Date().toLocaleString("pt-BR", {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        el.textContent = `Data de Emissão: ${hoje}`;
    }
}

/**
 * Inicializa os gráficos Chart.js:
 * 1. Gráfico de Rosca (Doughnut): Visão Geral das Respostas
 * 2. Gráfico de Barras: Acertos vs. Erros por Tópico Gramatical
 */
function inicializarGraficos() {
    const temaAtual = document.documentElement.getAttribute("data-theme") || "dark";
    const themeColors = getChartThemeColors(temaAtual);

    // Destrói instâncias anteriores se houver reinicialização
    if (chartStatusInstance) {
        chartStatusInstance.destroy();
        chartStatusInstance = null;
    }
    if (chartTemasInstance) {
        chartTemasInstance.destroy();
        chartTemasInstance = null;
    }

    // -------------------------------------------------------------
    // GRÁFICO 1: Rosca (Doughnut) - Visão Geral por Status (Interativo)
    // -------------------------------------------------------------
    const ctxStatus = document.getElementById('graficoStatus');
    if (ctxStatus && typeof Chart !== "undefined") {
        chartStatusInstance = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: STATUS_LABELS || [],
                datasets: [{
                    data: STATUS_VALORES || [],
                    backgroundColor: getDoughnutStatusColors(filtroStatusAtivo),
                    borderColor: themeColors.doughnutBorder,
                    borderWidth: 3,
                    offset: getDoughnutStatusOffsets(filtroStatusAtivo),
                    hoverOffset: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements, chart) => {
                    if (!elements || elements.length === 0) {
                        // Clicou no centro ou fora dos anéis -> reseta para todos
                        alternarFiltroInterativoStatus("TODOS", "doughnut");
                        return;
                    }
                    const idx = elements[0].index;
                    const labelClicada = chart.data.labels[idx];
                    alternarFiltroInterativoStatus(labelClicada, "doughnut");
                },
                onHover: (event, elements) => {
                    if (event && event.native && event.native.target) {
                        event.native.target.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        onClick: (e, legendItem, legend) => {
                            const label = legendItem.text;
                            alternarFiltroInterativoStatus(label, "legend");
                        },
                        onHover: (event) => {
                            if (event && event.native && event.native.target) {
                                event.native.target.style.cursor = 'pointer';
                            }
                        },
                        labels: {
                            color: themeColors.textColor,
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 12,
                                weight: 600
                            },
                            padding: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} exercícios (${pct}%) — Clique para filtrar`;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }

    // -------------------------------------------------------------
    // GRÁFICO 2: Barras Comparativo - Acertos vs Erros por Tópico Gramatical
    // -------------------------------------------------------------
    const ctxTemas = document.getElementById('graficoTemas');
    if (ctxTemas && typeof Chart !== "undefined") {
        chartTemasInstance = new Chart(ctxTemas, {
            type: 'bar',
            data: {
                labels: TEMA_LABELS || [],
                datasets: [
                    {
                        label: 'Acertos (Corretos)',
                        data: TEMA_ACERTOS || [],
                        backgroundColor: '#10b981',
                        borderRadius: 6
                    },
                    {
                        label: 'Parciais (Desvios leves)',
                        data: TEMA_PARCIAIS || [],
                        backgroundColor: '#f59e0b',
                        borderRadius: 6
                    },
                    {
                        label: 'Erros (Incorretos)',
                        data: TEMA_ERROS || [],
                        backgroundColor: '#ef4444',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements, chart) => {
                    if (!elements || elements.length === 0) return;
                    const idx = elements[0].index;
                    const topico = chart.data.labels[idx];
                    filtrarTabelaPorTopico(topico);
                },
                onHover: (event, elements) => {
                    if (event && event.native && event.native.target) {
                        event.native.target.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: themeColors.gridColor
                        },
                        ticks: {
                            color: themeColors.mutedTextColor,
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 11
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: themeColors.mutedTextColor,
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 11
                            }
                        },
                        grid: {
                            color: themeColors.gridColor
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: themeColors.textColor,
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 12,
                                weight: 600
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function() {
                                return "Clique na barra para filtrar a tabela por este tema";
                            }
                        }
                    }
                }
            }
        });

        // Sincroniza a visibilidade das barras caso haja filtro de status ativo
        atualizarBarChartInterativo(filtroStatusAtivo);
    }
}

/**
 * Exportação em PDF usando html2pdf.js
 */
function exportarRelatorioPDF() {
    const elemento = document.getElementById('conteudo-relatorio');
    const botao = document.getElementById('btnExportarPdf');

    if (!elemento) {
        alert("Elemento de relatório não localizado.");
        return;
    }

    if (typeof html2pdf === "undefined") {
        alert("Biblioteca html2pdf.js não carregada. Verifique sua conexão com a internet.");
        return;
    }

    const textoOriginal = botao.innerHTML;
    botao.innerHTML = "<span>Génération du PDF...</span>";
    botao.disabled = true;

    const dataHoje = new Date().toISOString().slice(0, 10);
    const opcoes = {
        margin: [10, 10, 12, 10],
        filename: `relatorio_frances_fran_${dataHoje}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
            scale: 2,
            useCORS: true,
            logging: false,
            backgroundColor: (document.documentElement.getAttribute("data-theme") === "light") ? '#ffffff' : '#0a0e17'
        },
        jsPDF: {
            unit: 'mm',
            format: 'a4',
            orientation: 'portrait'
        }
    };

    html2pdf()
        .set(opcoes)
        .from(elemento)
        .save()
        .then(() => {
            botao.innerHTML = textoOriginal;
            botao.disabled = false;
        })
        .catch(err => {
            console.error("Erro na exportação para PDF:", err);
            alert("Ocorreu um erro ao gerar o PDF.");
            botao.innerHTML = textoOriginal;
            botao.disabled = false;
        });
}

/**
 * Funções de Controle do Modal de Detalhes com Análise do Professor
 */
function abrirModalFeedback(id) {
    if (typeof submissoesData === "undefined" || !submissoesData[id]) return;

    const sub = submissoesData[id];
    const modal = document.getElementById("feedbackModal");

    document.getElementById("modalTitle").textContent = `Submissão #${sub.id}`;
    document.getElementById("modalTopicBadge").textContent = sub.tema;
    document.getElementById("modalQuestion").textContent = sub.pergunta;
    document.getElementById("modalAnswer").textContent = sub.resposta;
    document.getElementById("modalTimestamp").textContent = `Enviado em: ${sub.data_hora}`;

    const cefrBadge = document.getElementById("modalCefrBadge");
    if (cefrBadge) {
        const lvl = (sub.nivel_cefr || "A2").toUpperCase();
        cefrBadge.textContent = `Niveau ${lvl}`;
        cefrBadge.className = `cefr-level-badge lvl-${lvl.toLowerCase()}`;
    }

    const tentativaBadge = document.getElementById("modalTentativaBadge");
    if (tentativaBadge) {
        if (sub.tentativa && sub.tentativa > 1) {
            tentativaBadge.textContent = `Tentativa ${sub.tentativa}`;
            tentativaBadge.classList.remove("hidden");
        } else {
            tentativaBadge.classList.add("hidden");
        }
    }

    const analiseBox = document.getElementById("modalAnaliseText");
    if (analiseBox) {
        analiseBox.textContent = sub.analise || "Análise gramatical registrada.";
    }

    const badge = document.getElementById("modalStatusBadge");
    badge.className = "status-badge";
    badge.textContent = sub.status;

    if (sub.status === "Correto") {
        badge.classList.add("status-correta");
    } else if (sub.status === "Parcialmente Correto") {
        badge.classList.add("status-parcial");
    } else {
        badge.classList.add("status-incorreta");
    }

    const feedbackBox = document.getElementById("modalFeedbackText");
    if (typeof marked !== "undefined" && marked.parse) {
        feedbackBox.innerHTML = marked.parse(sub.feedback || "");
    } else {
        feedbackBox.textContent = sub.feedback || "";
    }

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

let respostaAtualModal = "";

function ouvirRespostaModal() {
    const btn = document.getElementById("btnAudioModal");
    const modalAnswer = document.getElementById("modalAnswer");
    const texto = modalAnswer ? modalAnswer.textContent : "";
    if (!texto || !texto.trim()) {
        alert("Nenhuma resposta para reproduzir.");
        return;
    }
    falarTextoFrancesDashboard(texto, btn);
}

function falarTextoFrancesDashboard(texto, btnElement = null) {
    if (!('speechSynthesis' in window)) {
        alert("Seu navegador não possui suporte à síntese de voz nativa.");
        return;
    }

    window.speechSynthesis.cancel();
    const textoLimpo = texto.replace(/[*_#`~>«»]/g, "").trim();
    const utterance = new SpeechSynthesisUtterance(textoLimpo);
    utterance.lang = 'fr-FR';
    utterance.rate = 0.88;
    utterance.pitch = 1.0;

    const vozes = window.speechSynthesis.getVoices();
    const vozFrancesa = vozes.find(v => v.lang === 'fr-FR' || v.lang.startsWith('fr'));
    if (vozFrancesa) {
        utterance.voice = vozFrancesa;
    }

    if (btnElement) {
        const textoOriginal = btnElement.innerHTML;
        btnElement.classList.add("speaking");
        btnElement.innerHTML = '<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> <span>Écoute...</span>';

        utterance.onend = () => {
            btnElement.classList.remove("speaking");
            btnElement.innerHTML = textoOriginal;
        };
        utterance.onerror = () => {
            btnElement.classList.remove("speaking");
            btnElement.innerHTML = textoOriginal;
        };
    }

    window.speechSynthesis.speak(utterance);
}

function fecharModal() {
    const modal = document.getElementById("feedbackModal");
    if (modal) {
        modal.classList.add("hidden");
        document.body.style.overflow = "";
    }
}

function fecharModalSeClicarFora(event) {
    if (event.target.id === "feedbackModal") {
        fecharModal();
    }
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        fecharModal();
        if (typeof fecharModalAluno === "function") fecharModalAluno();
    }
});

/**
 * =====================================================================
 * SISTEMA DE FILTRAGEM CRUZADA INTERATIVA (CROSS-FILTERING)
 * Conecta Cards de Métricas, Gráfico de Rosca, Gráfico de Barras e Tabelas
 * =====================================================================
 */
let filtroCefrAtivo = "TODOS";
let filtroStatusAtivo = "TODOS";
let filtroTemaAtivo = "TODOS";

/**
 * Retorna paleta de cores para o gráfico de rosca destacando o status selecionado
 */
function getDoughnutStatusColors(filtroAtivo) {
    const statusColors = {
        "Correto": "#10b981",
        "Parcialmente Correto": "#f59e0b",
        "Incorreto": "#ef4444"
    };
    const statusColorsDimmed = {
        "Correto": "rgba(16, 185, 129, 0.22)",
        "Parcialmente Correto": "rgba(245, 158, 11, 0.22)",
        "Incorreto": "rgba(239, 68, 68, 0.22)"
    };
    return (STATUS_LABELS || []).map(label => {
        if (!filtroAtivo || filtroAtivo === "TODOS") {
            return statusColors[label] || "#6366f1";
        }
        return label === filtroAtivo ? (statusColors[label] || "#6366f1") : (statusColorsDimmed[label] || "rgba(148, 163, 184, 0.2)");
    });
}

/**
 * Retorna os offsets dos segmentos do gráfico de rosca (destaca a fatia clicada)
 */
function getDoughnutStatusOffsets(filtroAtivo) {
    return (STATUS_LABELS || []).map(label => {
        return (filtroAtivo && filtroAtivo !== "TODOS" && label === filtroAtivo) ? 14 : 0;
    });
}

/**
 * Alterna e sincroniza o filtro interativo entre Cards, Gráfico de Rosca, Gráfico de Barras e Tabelas
 * @param {string} status 'Correto' | 'Parcialmente Correto' | 'Incorreto' | 'TODOS'
 * @param {string} origem 'card' | 'doughnut' | 'legend' | 'pill' | 'banner' | 'code'
 */
function alternarFiltroInterativoStatus(status, origem = 'card') {
    // Se o usuário clicar no mesmo status já ativo, alterna para 'TODOS' (desfaz o filtro)
    if (filtroStatusAtivo === status && status !== "TODOS") {
        filtroStatusAtivo = "TODOS";
    } else {
        filtroStatusAtivo = status || "TODOS";
    }

    // 1. Atualiza visual dos 4 Cards de Métricas
    atualizarEstiloCardsInterativos(filtroStatusAtivo);

    // 2. Atualiza Gráfico de Rosca (Doughnut)
    atualizarDoughnutInterativo(filtroStatusAtivo);

    // 3. Atualiza Gráfico de Barras Comparativo
    atualizarBarChartInterativo(filtroStatusAtivo);

    // 4. Sincroniza Pílulas da Tabela de Submissões e Filtra Linhas
    atualizarTabelasComFiltro(filtroStatusAtivo);

    // 5. Atualiza Banner de Filtro Ativo
    atualizarBannerFiltroAtivo(filtroStatusAtivo);

    // 6. Notificação Toast suave
    const nomesStatus = {
        "Correto": "Domínio Pleno (Correto)",
        "Parcialmente Correto": "Parcialmente Correto",
        "Incorreto": "Respostas Incorretas",
        "TODOS": "Todos os Exercícios"
    };
    const nomeAmigavel = nomesStatus[filtroStatusAtivo] || filtroStatusAtivo;
    if (filtroStatusAtivo === "TODOS") {
        if (typeof mostrarToast === "function" && origem !== "code") {
            mostrarToast("Filtro interativo redefinido. Exibindo todos os dados.", "info");
        }
    } else {
        if (typeof mostrarToast === "function" && origem !== "code") {
            const origemMsg = origem === "doughnut" ? "pelo Gráfico de Pizza" :
                              origem === "card" ? "pelo Card de Métrica" :
                              origem === "legend" ? "pela Legenda do Gráfico" : "pelo Painel";
            mostrarToast(`Filtro ativado ${origemMsg}: ${nomeAmigavel}.`, "info");
        }
    }
}
window.alternarFiltroInterativoStatus = alternarFiltroInterativoStatus;

/**
 * Atualiza visualmente os cards de métricas (selecionado, opaco/dimmed, hints)
 */
function atualizarEstiloCardsInterativos(status) {
    const cardTotal = document.getElementById("cardMetricTotal");
    const cardCorretas = document.getElementById("cardMetricCorretas");
    const cardParciais = document.getElementById("cardMetricParciais");
    const cardIncorretas = document.getElementById("cardMetricIncorretas");

    const cards = [
        { el: cardCorretas, key: "Correto", hint: document.getElementById("hintMetricCorretas") },
        { el: cardParciais, key: "Parcialmente Correto", hint: document.getElementById("hintMetricParciais") },
        { el: cardIncorretas, key: "Incorreto", hint: document.getElementById("hintMetricIncorretas") }
    ];

    if (status === "TODOS") {
        if (cardTotal) {
            cardTotal.classList.remove("metric-card-selected", "has-filter-active");
            const hintTotal = document.getElementById("hintMetricTotal");
            if (hintTotal) hintTotal.textContent = "Visão Geral";
        }
        cards.forEach(c => {
            if (c.el) {
                c.el.classList.remove("metric-card-selected", "metric-card-dimmed");
            }
            if (c.hint) c.hint.textContent = "Filtrar";
        });
    } else {
        if (cardTotal) {
            cardTotal.classList.add("has-filter-active");
            const hintTotal = document.getElementById("hintMetricTotal");
            if (hintTotal) hintTotal.textContent = "↺ Resetar";
        }
        cards.forEach(c => {
            if (!c.el) return;
            if (c.key === status) {
                c.el.classList.add("metric-card-selected");
                c.el.classList.remove("metric-card-dimmed");
                if (c.hint) c.hint.textContent = "✓ Ativo";
            } else {
                c.el.classList.remove("metric-card-selected");
                c.el.classList.add("metric-card-dimmed");
                if (c.hint) c.hint.textContent = "Filtrar";
            }
        });
    }
}

/**
 * Atualiza cores e offset das fatias do gráfico de rosca
 */
function atualizarDoughnutInterativo(status) {
    if (!chartStatusInstance || !chartStatusInstance.data || !chartStatusInstance.data.datasets) return;
    const dataset = chartStatusInstance.data.datasets[0];
    if (!dataset) return;

    dataset.backgroundColor = getDoughnutStatusColors(status);
    dataset.offset = getDoughnutStatusOffsets(status);
    chartStatusInstance.update();
}

/**
 * Atualiza a visibilidade dos conjuntos de dados no gráfico de barras
 */
function atualizarBarChartInterativo(status) {
    if (!chartTemasInstance) return;

    // Dataset 0: Acertos (Corretos)
    // Dataset 1: Parciais (Desvios leves)
    // Dataset 2: Erros (Incorretos)
    if (status === "TODOS") {
        chartTemasInstance.setDatasetVisibility(0, true);
        chartTemasInstance.setDatasetVisibility(1, true);
        chartTemasInstance.setDatasetVisibility(2, true);
    } else if (status === "Correto") {
        chartTemasInstance.setDatasetVisibility(0, true);
        chartTemasInstance.setDatasetVisibility(1, false);
        chartTemasInstance.setDatasetVisibility(2, false);
    } else if (status === "Parcialmente Correto") {
        chartTemasInstance.setDatasetVisibility(0, false);
        chartTemasInstance.setDatasetVisibility(1, true);
        chartTemasInstance.setDatasetVisibility(2, false);
    } else if (status === "Incorreto") {
        chartTemasInstance.setDatasetVisibility(0, false);
        chartTemasInstance.setDatasetVisibility(1, false);
        chartTemasInstance.setDatasetVisibility(2, true);
    }
    chartTemasInstance.update();
}

/**
 * Sincroniza as pílulas de filtro da tabela e oculta/exibe a tabela de risco conforme o status
 */
function atualizarTabelasComFiltro(status) {
    const botoes = document.querySelectorAll("[data-filter-status]");
    botoes.forEach(b => {
        if (b.getAttribute("data-filter-status") === status) {
            b.classList.add("active");
        } else {
            b.classList.remove("active");
        }
    });

    aplicarFiltrosTabela();

    const cardRisco = document.getElementById("cardTabelaRisco");
    const riskOuter = document.getElementById("riskBoxOuter") || cardRisco;
    if (cardRisco) {
        if (status === "Correto" || status === "Parcialmente Correto") {
            cardRisco.style.display = "none";
            if (riskOuter) riskOuter.style.display = "none";
        } else {
            cardRisco.style.display = "";
            if (riskOuter) riskOuter.style.display = "";
            if (status === "Incorreto") {
                cardRisco.classList.add("risk-highlighted");
            } else {
                cardRisco.classList.remove("risk-highlighted");
            }
            if (typeof renderizarPaginacaoRisco === "function") {
                renderizarPaginacaoRisco();
            }
        }
    }
}

/**
 * Exibe ou oculta o banner informativo de filtro ativo acima dos gráficos
 */
function atualizarBannerFiltroAtivo(status) {
    const banner = document.getElementById("bannerFiltroInterativo");
    const texto = document.getElementById("textoFiltroAtivo");
    const badge = document.getElementById("badgeFiltroAtivoCount");
    if (!banner) return;

    if (!status || status === "TODOS") {
        banner.classList.remove("visible");
        return;
    }

    const nomes = {
        "Correto": "Domínio Pleno (Correto)",
        "Parcialmente Correto": "Parcialmente Correto",
        "Incorreto": "Respostas Incorretas"
    };

    let count = 0;
    const elVal = status === "Correto" ? document.getElementById("valMetricCorretas") :
                  status === "Parcialmente Correto" ? document.getElementById("valMetricParciais") :
                  document.getElementById("valMetricIncorretas");
    if (elVal) count = elVal.textContent.trim();

    if (texto) texto.textContent = nomes[status] || status;
    if (badge) badge.textContent = `${count} exercícios filtrados`;
    banner.classList.add("visible");
}

/**
 * Filtro por Nível CEFR na tabela
 */
function filtrarTabelaCefr(nivel) {
    filtroCefrAtivo = (nivel || "TODOS").toUpperCase();
    
    const botoes = document.querySelectorAll("[data-filter-cefr]");
    botoes.forEach(b => {
        if (b.getAttribute("data-filter-cefr") === filtroCefrAtivo) {
            b.classList.add("active");
        } else {
            b.classList.remove("active");
        }
    });

    aplicarFiltrosTabela();
}
window.filtrarTabelaCefr = filtrarTabelaCefr;

/**
 * Filtro por Status disparado pelas pílulas da tabela
 */
function filtrarTabelaStatus(status) {
    alternarFiltroInterativoStatus(status, 'pill');
}
window.filtrarTabelaStatus = filtrarTabelaStatus;

/**
 * Filtro rápido por clique no gráfico de barras temático
 */
function filtrarTabelaPorTopico(topico) {
    if (!topico) return;
    if (filtroTemaAtivo === topico) {
        filtroTemaAtivo = "TODOS";
        if (typeof mostrarToast === "function") {
            mostrarToast("Filtro por tema removido.", "info");
        }
    } else {
        filtroTemaAtivo = topico;
        if (typeof mostrarToast === "function") {
            mostrarToast(`Filtrando tabela por: ${topico}`, "info");
        }
    }
    aplicarFiltrosTabela();
    const tabEl = document.getElementById("tabelaSubmissoes");
    if (tabEl) {
        tabEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
window.filtrarTabelaPorTopico = filtrarTabelaPorTopico;

/**
 * Aplica os filtros combinados (CEFR, Status, Tema) sobre as linhas da tabela de submissões
 * e sincroniza com o sistema de paginação dinâmica (resetando para a página 1)
 */
function aplicarFiltrosTabela() {
    if (typeof renderizarPaginacaoSubmissoes === "function") {
        renderizarPaginacaoSubmissoes(true);
    }
}
window.aplicarFiltrosTabela = aplicarFiltrosTabela;

/**
 * Filtro rápido ativado pelo botão de opções (...) dos cards modernos de métricas
 */
function filtrarPorStatusRapido(status) {
    alternarFiltroInterativoStatus(status, 'dots');
    const tabEl = document.getElementById("tabelaSubmissoes");
    if (tabEl) {
        tabEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
window.filtrarPorStatusRapido = filtrarPorStatusRapido;

/* =====================================================================
   GESTAO PEDAGOGICA DE ALUNOS & NIVEIS CEFR (PROFESSOR)
   ===================================================================== */

/**
 * Atualiza instantaneamente o nível de proficiência CEFR de um aluno via API.
 */
async function alterarNivelAluno(alunoId, novoNivel, nomeAluno) {
    if (!alunoId || !novoNivel) return;

    try {
        const response = await fetch(`/api/alunos/${alunoId}/nivel`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ nivel_cefr: novoNivel })
        });

        const data = await response.json();

        if (response.ok && data.status === "sucesso") {
            // Atualiza visualmente o badge de nível na linha da tabela
            const badge = document.getElementById(`badge-nivel-aluno-${alunoId}`);
            if (badge) {
                badge.textContent = novoNivel;
                badge.className = `badge-level-student lvl-${novoNivel.toLowerCase()}`;
            }

            mostrarToast(data.mensagem, "sucesso");
        } else {
            mostrarToast(data.mensagem || "Erro ao atualizar nível.", "erro");
        }
    } catch (err) {
        console.error("Erro na requisição de alteração de nível:", err);
        mostrarToast("Falha de comunicação com o servidor.", "erro");
    }
}

/**
 * Abre o modal para cadastro de um novo aluno.
 */
function abrirModalCadastroAluno() {
    const modal = document.getElementById("modalAluno");
    const form = document.getElementById("formModalAluno");
    const titulo = document.getElementById("modalAlunoTitulo");
    const formId = document.getElementById("aluno_form_id");
    const hintSenha = document.getElementById("hintSenha");
    const labelSenha = document.getElementById("labelSenha");
    const senhaInput = document.getElementById("aluno_senha");
    const msgBox = document.getElementById("alunoFormMsg");

    if (form) form.reset();
    if (formId) formId.value = "";
    if (titulo) titulo.textContent = "Cadastrar Novo Aluno";
    if (hintSenha) hintSenha.style.display = "none";
    if (labelSenha) labelSenha.textContent = "Senha de Acesso:";
    if (senhaInput) {
        senhaInput.required = true;
        senhaInput.placeholder = "Ex: 123456";
    }
    if (msgBox) {
        msgBox.style.display = "none";
        msgBox.textContent = "";
    }

    if (modal) {
        modal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
        if (typeof alternarAbaAlunoModal === "function") alternarAbaAlunoModal("form");
        const labelTab = document.getElementById("labelTabFormAluno");
        if (labelTab) labelTab.textContent = "Cadastrar Novo Aluno";
    }
}

/**
 * Abre o modal preenchido com dados para edição de um aluno existente.
 */
function abrirModalEdicaoAluno(alunoId, nome, matricula, turmaId, nivelCefr) {
    const modal = document.getElementById("modalAluno");
    const titulo = document.getElementById("modalAlunoTitulo");
    const formId = document.getElementById("aluno_form_id");
    const nomeInput = document.getElementById("aluno_nome");
    const matInput = document.getElementById("aluno_matricula");
    const turmaSelect = document.getElementById("aluno_turma_id");
    const nivelSelect = document.getElementById("aluno_nivel_cefr");
    const hintSenha = document.getElementById("hintSenha");
    const labelSenha = document.getElementById("labelSenha");
    const senhaInput = document.getElementById("aluno_senha");
    const msgBox = document.getElementById("alunoFormMsg");

    if (formId) formId.value = alunoId;
    if (titulo) titulo.textContent = `Editar Aluno: ${nome}`;
    if (nomeInput) nomeInput.value = nome;
    if (matInput) matInput.value = matricula;
    if (turmaSelect) turmaSelect.value = turmaId;
    if (nivelSelect) nivelSelect.value = nivelCefr;

    if (hintSenha) hintSenha.style.display = "block";
    if (labelSenha) labelSenha.textContent = "Nova Senha (Opcional):";
    if (senhaInput) {
        senhaInput.required = false;
        senhaInput.value = "";
        senhaInput.placeholder = "Deixe em branco para manter a senha";
    }

    if (msgBox) {
        msgBox.style.display = "none";
        msgBox.textContent = "";
    }

    if (modal) {
        modal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
        if (typeof alternarAbaAlunoModal === "function") alternarAbaAlunoModal("form");
        const labelTab = document.getElementById("labelTabFormAluno");
        if (labelTab) labelTab.textContent = `Editar: ${nome}`;
    }
}

/**
 * Fecha o modal de cadastro/edição de aluno.
 */
function fecharModalAluno() {
    const modal = document.getElementById("modalAluno");
    if (modal) {
        modal.classList.add("hidden");
        document.body.style.overflow = "";
    }
}

function fecharModalAlunoSeClicarFora(event) {
    if (event.target.id === "modalAluno") {
        fecharModalAluno();
    }
}

/**
 * Processa o envio do formulário de aluno (novo ou edição).
 */
async function salvarAluno(event) {
    event.preventDefault();

    const formId = document.getElementById("aluno_form_id").value;
    const nome = document.getElementById("aluno_nome").value.trim();
    const matricula = document.getElementById("aluno_matricula").value.trim();
    const senha = document.getElementById("aluno_senha").value.trim();
    const turma_id = document.getElementById("aluno_turma_id").value;
    const nivel_cefr = document.getElementById("aluno_nivel_cefr").value;
    const msgBox = document.getElementById("alunoFormMsg");
    const btnSalvar = document.getElementById("btnSalvarAluno");

    if (!nome || !matricula || !turma_id || !nivel_cefr) {
        if (msgBox) {
            msgBox.className = "form-alert-msg error";
            msgBox.textContent = "Por favor, preencha todos os campos obrigatórios.";
            msgBox.style.display = "block";
        }
        return;
    }

    if (!formId && !senha) {
        if (msgBox) {
            msgBox.className = "form-alert-msg error";
            msgBox.textContent = "Por favor, defina uma senha inicial para o novo aluno.";
            msgBox.style.display = "block";
        }
        return;
    }

    const payload = {
        nome,
        matricula,
        senha,
        turma_id,
        nivel_cefr
    };

    const url = formId ? `/api/alunos/${formId}/editar` : "/api/alunos/cadastrar";

    try {
        if (btnSalvar) {
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = "<span>Salvando...</span>";
        }

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.status === "sucesso") {
            fecharModalAluno();
            mostrarToast(data.mensagem, "sucesso");
            // Recarrega a página para atualizar a tabela e os filtros
            setTimeout(() => {
                window.location.reload();
            }, 750);
        } else {
            if (msgBox) {
                msgBox.className = "form-alert-msg error";
                msgBox.textContent = data.mensagem || "Erro ao salvar aluno.";
                msgBox.style.display = "block";
            }
        }
    } catch (err) {
        console.error("Erro ao salvar aluno:", err);
        if (msgBox) {
            msgBox.className = "form-alert-msg error";
            msgBox.textContent = "Falha de conexão ao comunicar com o servidor.";
            msgBox.style.display = "block";
        }
    } finally {
        if (btnSalvar) {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = "<span>Salvar Aluno</span>";
        }
    }
}

/**
 * Exibe um toast notification elegante na tela.
 */
function mostrarToast(mensagem, tipo = "info") {
    const container = document.getElementById("toastNotification");
    if (!container) return;

    container.textContent = mensagem;
    container.className = `toast-notification visible ${tipo}`;

    if (window._toastTimer) clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => {
        container.className = "toast-notification";
    }, 3800);
}

/* =====================================================================
   CO-PILOTO PEDAGÓGICO: GERADOR DE EXERCÍCIOS & BANCO DE QUESTÕES (IA)
   ===================================================================== */

/**
 * Envia solicitação assíncrona ao Co-piloto de IA para gerar enunciados práticos.
 */
async function gerarExerciciosCopiloto(event) {
    if (event) event.preventDefault();

    const temaSelect = document.getElementById("copiloto_tema");
    const nivelSelect = document.getElementById("copiloto_nivel");
    const quantInput = document.getElementById("copiloto_quantidade");
    const btnGerar = document.getElementById("btnGerarCopiloto");
    const btnTexto = document.getElementById("btnGerarCopilotoTexto");
    const spinner = document.getElementById("spinnerCopiloto");
    const previewContainer = document.getElementById("preview-exercicios");
    const listaCards = document.getElementById("listaCardsExercicios");
    const btnSalvar = document.getElementById("btnSalvarExercicios");
    const countBadge = document.getElementById("previewCountBadge");

    const tema = temaSelect ? temaSelect.value : "Passé Composé"; // This is actually tema_id now
    const nivel = nivelSelect ? nivelSelect.value : "A2";
    const quantidade = quantInput ? parseInt(quantInput.value, 10) || 3 : 3;

    try {
        if (btnGerar) btnGerar.disabled = true;
        if (spinner) spinner.classList.remove("hidden");
        if (btnTexto) btnTexto.textContent = "Gerando sugestões com Gemini...";

        const response = await fetch("/api/copiloto/gerar_exercicio", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ tema_id: tema, nivel, quantidade })
        });

        const data = await response.json();

        if (response.ok && data.status === "sucesso" && Array.isArray(data.exercicios) && data.exercicios.length > 0) {
            if (listaCards) {
                listaCards.innerHTML = "";
                data.exercicios.forEach((enunciado, index) => {
                    const card = document.createElement("div");
                    card.className = "exercise-editable-item";
                    card.innerHTML = `
                        <div class="exercise-item-header">
                            <span class="exercise-num-badge">Item #${index + 1}</span>
                            <span class="exercise-item-meta">${escapeHtml(data.tema)} • Nível ${escapeHtml(data.nivel)}</span>
                            <button type="button" class="btn-remove-preview" onclick="removerExercicioPreview(this)" title="Remover este item">&times;</button>
                        </div>
                        <textarea class="form-textarea exercise-editable-textarea" rows="2" placeholder="Enunciado do exercício...">${escapeHtml(enunciado)}</textarea>
                    `;
                    listaCards.appendChild(card);
                });
            }

            if (countBadge) {
                countBadge.textContent = `${data.exercicios.length} sugestões prontas`;
            }

            if (previewContainer) {
                previewContainer.classList.remove("hidden");
                previewContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }

            if (btnSalvar) {
                btnSalvar.classList.remove("hidden");
                btnSalvar.disabled = false;
                btnSalvar.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                        <polyline points="17 21 17 13 7 13 7 21"></polyline>
                        <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    <span>Salvar no Banco de Questões</span>
                `;
            }

            mostrarToast(`${data.exercicios.length} exercícios gerados com sucesso pelo Gemini!`, "sucesso");
        } else {
            mostrarToast(data.mensagem || "Falha ao gerar exercícios com IA.", "erro");
        }
    } catch (err) {
        console.error("Erro ao gerar exercícios com Co-piloto:", err);
        mostrarToast("Falha de comunicação com o servidor.", "erro");
    } finally {
        if (btnGerar) btnGerar.disabled = false;
        if (spinner) spinner.classList.add("hidden");
        if (btnTexto) btnTexto.textContent = "Gerar Sugestões com IA";
    }
}

/**
 * Remove um exercício individual da área de pré-visualização.
 */
function removerExercicioPreview(btn) {
    const card = btn.closest(".exercise-editable-item");
    if (card) {
        card.remove();
        const listaCards = document.getElementById("listaCardsExercicios");
        const countBadge = document.getElementById("previewCountBadge");
        const btnSalvar = document.getElementById("btnSalvarExercicios");
        const items = listaCards ? listaCards.querySelectorAll(".exercise-editable-item") : [];

        if (countBadge) {
            countBadge.textContent = `${items.length} sugestões`;
        }

        if (items.length === 0 && btnSalvar) {
            btnSalvar.classList.add("hidden");
        }
    }
}

/**
 * Salva os exercícios revisados pelo professor no banco de dados SQLite.
 */
async function salvarExerciciosNoBanco() {
    const temaSelect = document.getElementById("copiloto_tema");
    const nivelSelect = document.getElementById("copiloto_nivel");
    const btnSalvar = document.getElementById("btnSalvarExercicios");
    const textareas = document.querySelectorAll(".exercise-editable-textarea");

    const tema = temaSelect ? temaSelect.value : "Geral"; // This is actually tema_id
    const nivel = nivelSelect ? nivelSelect.value : "A2";
    const exercicios = [];

    textareas.forEach(t => {
        const val = t.value.trim();
        if (val) exercicios.push(val);
    });

    if (exercicios.length === 0) {
        mostrarToast("Nenhum exercício válido na lista para salvar.", "erro");
        return;
    }

    try {
        if (btnSalvar) {
            btnSalvar.disabled = true;
            btnSalvar.innerHTML = `<span>Salvando no banco...</span>`;
        }

        const response = await fetch("/api/copiloto/salvar_exercicios", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ tema_id: tema, nivel, exercicios })
        });

        const data = await response.json();

        if (response.ok && data.status === "sucesso") {
            mostrarToast(data.mensagem, "sucesso");
            if (btnSalvar) {
                btnSalvar.innerHTML = `<span>Salvo no Banco!</span>`;
                setTimeout(() => {
                    btnSalvar.classList.add("hidden");
                }, 2200);
            }
        } else {
            mostrarToast(data.mensagem || "Erro ao salvar no banco de dados.", "erro");
            if (btnSalvar) {
                btnSalvar.disabled = false;
                btnSalvar.innerHTML = `<span>Tentar Novamente</span>`;
            }
        }
    } catch (err) {
        console.error("Erro ao salvar exercícios:", err);
        mostrarToast("Falha de comunicação com o servidor.", "erro");
        if (btnSalvar) {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = `<span>Tentar Novamente</span>`;
        }
    }
}

/**
 * Escapa strings contra XSS ao inserir no DOM.
 */
function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Intervenção Pedagógica: Radar
 */
async function gerarReforcoRadar(alunoId, temaId) {
    if (!alunoId || !temaId) return;

    try {
        mostrarToast("Gerando plano de reforço com IA...", "info");

        const response = await fetch("/api/radar/reforco", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ aluno_id: alunoId, tema_id: temaId })
        });

        const data = await response.json();

        if (response.ok && data.status === "sucesso") {
            mostrarToast(data.mensagem, "sucesso");
        } else {
            mostrarToast(data.mensagem || "Erro ao gerar reforço.", "erro");
        }
    } catch (err) {
        console.error("Erro na requisição do radar:", err);
        mostrarToast("Falha de comunicação com o servidor.", "erro");
    }
}



/* =====================================================================
   CÉREBRO ANALÍTICO - FILTROS CRUZADOS
   ===================================================================== */

async function carregarAlunosPorTurma() {
    const turmaId = document.getElementById("filtroTurma").value;
    const alunoSelect = document.getElementById("filtroAluno");
    
    // Reset aluno select
    alunoSelect.innerHTML = '<option value="todos">Visão Macro / Todos os Alunos</option>';
    
    if (turmaId === "todas") return;
    
    try {
        const response = await fetch(`/api/alunos_por_turma/${turmaId}`);
        const alunos = await response.json();
        
        alunos.forEach(a => {
            const opt = document.createElement("option");
            opt.value = a.id;
            opt.textContent = a.nome;
            alunoSelect.appendChild(opt);
        });
    } catch (e) {
        console.error("Erro ao carregar alunos:", e);
    }
}

async function gerarRelatorioVisual() {
    const btn = document.getElementById("btnRelatorioText");
    if (btn) btn.textContent = "Carregando...";
    
    const turmaId = document.getElementById("filtroTurma") ? document.getElementById("filtroTurma").value : "";
    const nivelCefr = document.getElementById("filtroNivel") ? document.getElementById("filtroNivel").value : "";
    const alunoId = document.getElementById("filtroAluno") ? document.getElementById("filtroAluno").value : "";
    
    try {
        const query = new URLSearchParams({
            turma_id: turmaId,
            nivel_cefr: nivelCefr,
            aluno_id: alunoId
        });
        
        const response = await fetch(`/api/dashboard/estatisticas?${query.toString()}`);
        const data = await response.json();
        
        if (data.status === "sucesso") {
            // Atualiza os cards modernos de métricas da primeira fileira
            if (data.metricas) {
                atualizarCardsMetricas(data.metricas);
            } else if (data.desempenho_geral && data.desempenho_geral.data) {
                const labels = data.desempenho_geral.labels || [];
                const vals = data.desempenho_geral.data || [];
                let c = 0, p = 0, i = 0;
                labels.forEach((lbl, idx) => {
                    if (lbl === 'Correto') c = vals[idx] || 0;
                    else if (lbl === 'Parcialmente Correto') p = vals[idx] || 0;
                    else if (lbl === 'Incorreto') i = vals[idx] || 0;
                });
                const total = c + p + i;
                atualizarCardsMetricas({
                    total: total,
                    corretos: c,
                    parciais: p,
                    incorretos: i,
                    pct_correto: total > 0 ? (c / total * 100).toFixed(1) : 0,
                    pct_parcial: total > 0 ? (p / total * 100).toFixed(1) : 0,
                    pct_incorreto: total > 0 ? (i / total * 100).toFixed(1) : 0
                });
            }

            // Atualiza as variáveis que o inicializarGraficos() consome
            STATUS_LABELS = window.STATUS_LABELS = data.desempenho_geral.labels || [];
            STATUS_VALORES = window.STATUS_VALORES = data.desempenho_geral.data || [];
            
            if (data.desempenho_tema) {
                TEMA_LABELS = window.TEMA_LABELS = data.desempenho_tema.labels || [];
                TEMA_ACERTOS = window.TEMA_ACERTOS = data.desempenho_tema.acertos || [];
                TEMA_PARCIAIS = window.TEMA_PARCIAIS = data.desempenho_tema.parciais || [];
                TEMA_ERROS = window.TEMA_ERROS = data.desempenho_tema.erros || [];
            } else if (data.dificuldade_tema) {
                TEMA_LABELS = window.TEMA_LABELS = data.dificuldade_tema.labels || [];
                TEMA_ERROS = window.TEMA_ERROS = data.dificuldade_tema.data || [];
                TEMA_ACERTOS = window.TEMA_ACERTOS = [];
                TEMA_PARCIAIS = window.TEMA_PARCIAIS = [];
            }
            
            // Recria graficos (inicializarGraficos ja tem o .destroy() no inicio)
            inicializarGraficos();
        } else {
            console.error(data.mensagem);
        }
    } catch (e) {
        console.error("Erro ao gerar relatório:", e);
    } finally {
        if (btn) btn.textContent = "Aplicar Filtros";
    }
}

/**
 * Atualiza visualmente os novos cards de métricas rápidas (primeira fileira do dashboard)
 */
function atualizarCardsMetricas(m) {
    if (!m) return;
    const elTotal = document.getElementById("valMetricTotal");
    const elCorretas = document.getElementById("valMetricCorretas");
    const elParciais = document.getElementById("valMetricParciais");
    const elIncorretas = document.getElementById("valMetricIncorretas");

    const barCorretas = document.getElementById("barMetricCorretas");
    const barParciais = document.getElementById("barMetricParciais");
    const barIncorretas = document.getElementById("barMetricIncorretas");

    const pctCorretas = document.getElementById("pctMetricCorretas");
    const pctParciais = document.getElementById("pctMetricParciais");
    const pctIncorretas = document.getElementById("pctMetricIncorretas");

    if (elTotal) elTotal.textContent = m.total ?? 0;
    if (elCorretas) elCorretas.textContent = m.corretos ?? 0;
    if (elParciais) elParciais.textContent = m.parciais ?? 0;
    if (elIncorretas) elIncorretas.textContent = m.incorretos ?? 0;

    const pC = m.pct_correto ?? 0;
    const pP = m.pct_parcial ?? 0;
    const pI = m.pct_incorreto ?? 0;

    if (barCorretas) barCorretas.style.width = `${pC}%`;
    if (barParciais) barParciais.style.width = `${pP}%`;
    if (barIncorretas) barIncorretas.style.width = `${pI}%`;

    if (pctCorretas) pctCorretas.textContent = `${pC}%`;
    if (pctParciais) pctParciais.textContent = `${pP}%`;
    if (pctIncorretas) pctIncorretas.textContent = `${pI}%`;
}
window.atualizarCardsMetricas = atualizarCardsMetricas;

// Make sure to bind to window since it's global
window.STATUS_LABELS = STATUS_LABELS;
window.STATUS_VALORES = STATUS_VALORES;
window.TEMA_LABELS = TEMA_LABELS;
window.TEMA_ACERTOS = TEMA_ACERTOS;
window.TEMA_ERROS = TEMA_ERROS;
window.TEMA_PARCIAIS = TEMA_PARCIAIS;

// ===================================================================
// PAGINAÇÃO E CONTROLE DE LINHAS DA TABELA DE ALUNOS EM DIFICULDADE
// ===================================================================
const riscoPaginationState = {
    paginaAtual: 1,
    linhasPorPagina: 10
};

function renderizarPaginacaoRisco() {
    const tabela = document.getElementById("tabelaAlunosRisco");
    if (!tabela) return;

    const rows = Array.from(tabela.querySelectorAll("tbody tr.risk-row"));
    const total = rows.length;
    const infoEl = document.getElementById("infoPaginacaoRisco");
    const btnPrev = document.getElementById("btnRiscoPrev");
    const btnNext = document.getElementById("btnRiscoNext");
    const pillsWrap = document.getElementById("numerosPaginaRisco");

    if (total === 0) {
        if (infoEl) infoEl.innerHTML = "Nenhuma ocorrência registrada";
        if (btnPrev) btnPrev.disabled = true;
        if (btnNext) btnNext.disabled = true;
        if (pillsWrap) pillsWrap.innerHTML = "";
        return;
    }

    const pageSize = riscoPaginationState.linhasPorPagina;
    const totalPaginas = (pageSize === "todos") ? 1 : Math.ceil(total / pageSize);

    // Garante que a página atual está no limite válido
    if (riscoPaginationState.paginaAtual > totalPaginas) {
        riscoPaginationState.paginaAtual = totalPaginas;
    }
    if (riscoPaginationState.paginaAtual < 1) {
        riscoPaginationState.paginaAtual = 1;
    }

    const inicio = (pageSize === "todos") ? 0 : (riscoPaginationState.paginaAtual - 1) * pageSize;
    const fim = (pageSize === "todos") ? total : Math.min(inicio + pageSize, total);

    let visivelIndex = 0;
    rows.forEach((row, index) => {
        if (index >= inicio && index < fim) {
            row.style.display = "";
            row.classList.remove("risk-row-even", "risk-row-odd");
            if (visivelIndex % 2 === 1) {
                row.classList.add("risk-row-even");
            } else {
                row.classList.add("risk-row-odd");
            }
            visivelIndex++;
        } else {
            row.style.display = "none";
            row.classList.remove("risk-row-even", "risk-row-odd");
        }
    });

    // Atualiza texto informativo
    if (infoEl) {
        infoEl.innerHTML = `Exibindo <strong>${inicio + 1} - ${fim}</strong> de <strong>${total}</strong> ocorrências`;
    }

    // Atualiza botões Anterior / Próxima
    if (btnPrev) {
        btnPrev.disabled = (riscoPaginationState.paginaAtual <= 1);
    }
    if (btnNext) {
        btnNext.disabled = (riscoPaginationState.paginaAtual >= totalPaginas || pageSize === "todos");
    }

    // Renderiza pílulas numéricas de páginas
    if (pillsWrap) {
        pillsWrap.innerHTML = "";
        if (totalPaginas > 1) {
            for (let p = 1; p <= totalPaginas; p++) {
                const btnP = document.createElement("button");
                btnP.type = "button";
                btnP.className = `btn-page-number ${p === riscoPaginationState.paginaAtual ? "active" : ""}`;
                btnP.textContent = p;
                btnP.title = `Ir para página ${p}`;
                btnP.onclick = () => irParaPaginaRisco(p);
                pillsWrap.appendChild(btnP);
            }
        }
    }
}

function mudarPaginaRisco(delta) {
    riscoPaginationState.paginaAtual += delta;
    renderizarPaginacaoRisco();
}

function irParaPaginaRisco(num) {
    riscoPaginationState.paginaAtual = num;
    renderizarPaginacaoRisco();
}

function mudarQtdLinhasRisco(val) {
    riscoPaginationState.linhasPorPagina = (val === "todos") ? "todos" : parseInt(val, 10);
    riscoPaginationState.paginaAtual = 1;
    renderizarPaginacaoRisco();
}

window.renderizarPaginacaoRisco = renderizarPaginacaoRisco;
window.mudarPaginaRisco = mudarPaginaRisco;
window.irParaPaginaRisco = irParaPaginaRisco;
window.mudarQtdLinhasRisco = mudarQtdLinhasRisco;

// ===================================================================
// PAGINAÇÃO E CONTROLE DE LINHAS DA TABELA DE SUBMISSÕES (HISTÓRICO)
// ===================================================================
const submissoesPaginationState = {
    paginaAtual: 1,
    linhasPorPagina: 10
};

function renderizarPaginacaoSubmissoes(resetPagina = false) {
    if (resetPagina) {
        submissoesPaginationState.paginaAtual = 1;
    }
    const tabela = document.getElementById("tabelaSubmissoes");
    if (!tabela) return;

    const todasLinhas = Array.from(tabela.querySelectorAll("tbody tr.submission-row"));
    
    // Filtra quais linhas correspondem aos filtros ativos (CEFR, Status, Tema)
    const linhasFiltradas = todasLinhas.filter(linha => {
        const linhaCefr = (linha.getAttribute("data-cefr") || "A2").toUpperCase();
        const linhaStatus = linha.getAttribute("data-status") || "";
        const linhaTema = (linha.getAttribute("data-tema") || "").trim();

        const correspondeCefr = (typeof filtroCefrAtivo === "undefined" || filtroCefrAtivo === "TODOS" || linhaCefr === filtroCefrAtivo);
        const correspondeStatus = (typeof filtroStatusAtivo === "undefined" || filtroStatusAtivo === "TODOS" || linhaStatus === filtroStatusAtivo);
        const correspondeTema = (typeof filtroTemaAtivo === "undefined" || filtroTemaAtivo === "TODOS" || linhaTema === filtroTemaAtivo || linhaTema.includes(filtroTemaAtivo));

        return (correspondeCefr && correspondeStatus && correspondeTema);
    });

    const total = linhasFiltradas.length;
    const infoEl = document.getElementById("infoPaginacaoSubmissoes");
    const btnPrev = document.getElementById("btnSubmissoesPrev");
    const btnNext = document.getElementById("btnSubmissoesNext");
    const pillsWrap = document.getElementById("numerosPaginaSubmissoes");
    const badgeCount = document.getElementById("badgeSubmissoesCount");

    // Oculta todas as linhas inicialmente
    todasLinhas.forEach(l => {
        l.style.display = "none";
        l.classList.remove("sub-row-even", "sub-row-odd");
    });

    if (badgeCount) {
        let txt = `${total} submissões`;
        if (typeof filtroStatusAtivo !== "undefined" && filtroStatusAtivo !== "TODOS") txt += ` • Filtro: ${filtroStatusAtivo}`;
        if (typeof filtroTemaAtivo !== "undefined" && filtroTemaAtivo !== "TODOS") txt += ` • Tema: ${filtroTemaAtivo}`;
        badgeCount.textContent = txt;
    }

    if (total === 0) {
        if (infoEl) infoEl.innerHTML = "Nenhuma submissão para este filtro";
        if (btnPrev) btnPrev.disabled = true;
        if (btnNext) btnNext.disabled = true;
        if (pillsWrap) pillsWrap.innerHTML = "";
        return;
    }

    const pageSize = submissoesPaginationState.linhasPorPagina;
    const totalPaginas = (pageSize === "todos") ? 1 : Math.ceil(total / pageSize);

    if (submissoesPaginationState.paginaAtual > totalPaginas) {
        submissoesPaginationState.paginaAtual = totalPaginas;
    }
    if (submissoesPaginationState.paginaAtual < 1) {
        submissoesPaginationState.paginaAtual = 1;
    }

    const inicio = (pageSize === "todos") ? 0 : (submissoesPaginationState.paginaAtual - 1) * pageSize;
    const fim = (pageSize === "todos") ? total : Math.min(inicio + pageSize, total);

    let visivelIndex = 0;
    linhasFiltradas.forEach((linha, idx) => {
        if (idx >= inicio && idx < fim) {
            linha.style.display = "";
            linha.classList.remove("sub-row-even", "sub-row-odd");
            if (visivelIndex % 2 === 1) {
                linha.classList.add("sub-row-even");
            } else {
                linha.classList.add("sub-row-odd");
            }
            visivelIndex++;
        }
    });

    if (infoEl) {
        infoEl.innerHTML = `Exibindo <strong>${inicio + 1} - ${fim}</strong> de <strong>${total}</strong> submissões`;
    }

    if (btnPrev) {
        btnPrev.disabled = (submissoesPaginationState.paginaAtual <= 1);
    }
    if (btnNext) {
        btnNext.disabled = (submissoesPaginationState.paginaAtual >= totalPaginas || pageSize === "todos");
    }

    if (pillsWrap) {
        pillsWrap.innerHTML = "";
        if (totalPaginas > 1) {
            let paginasParaExibir = [];
            const cur = submissoesPaginationState.paginaAtual;
            if (totalPaginas <= 7) {
                for (let i = 1; i <= totalPaginas; i++) paginasParaExibir.push(i);
            } else {
                paginasParaExibir.push(1);
                if (cur > 3) paginasParaExibir.push("...");
                for (let i = Math.max(2, cur - 1); i <= Math.min(totalPaginas - 1, cur + 1); i++) {
                    paginasParaExibir.push(i);
                }
                if (cur < totalPaginas - 2) paginasParaExibir.push("...");
                paginasParaExibir.push(totalPaginas);
            }

            paginasParaExibir.forEach(p => {
                if (p === "...") {
                    const span = document.createElement("span");
                    span.textContent = "...";
                    span.style.padding = "0 4px";
                    span.style.color = "var(--text-muted)";
                    pillsWrap.appendChild(span);
                } else {
                    const btnP = document.createElement("button");
                    btnP.type = "button";
                    btnP.className = `btn-page-number ${p === cur ? "active" : ""}`;
                    btnP.textContent = p;
                    btnP.title = `Ir para página ${p}`;
                    btnP.onclick = () => irParaPaginaSubmissoes(p);
                    pillsWrap.appendChild(btnP);
                }
            });
        }
    }
}

function mudarPaginaSubmissoes(delta) {
    submissoesPaginationState.paginaAtual += delta;
    renderizarPaginacaoSubmissoes();
}

function irParaPaginaSubmissoes(num) {
    submissoesPaginationState.paginaAtual = num;
    renderizarPaginacaoSubmissoes();
}

function mudarQtdLinhasSubmissoes(val) {
    submissoesPaginationState.linhasPorPagina = (val === "todos") ? "todos" : parseInt(val, 10);
    submissoesPaginationState.paginaAtual = 1;
    renderizarPaginacaoSubmissoes();
}

window.renderizarPaginacaoSubmissoes = renderizarPaginacaoSubmissoes;
window.mudarPaginaSubmissoes = mudarPaginaSubmissoes;
window.irParaPaginaSubmissoes = irParaPaginaSubmissoes;
window.mudarQtdLinhasSubmissoes = mudarQtdLinhasSubmissoes;
