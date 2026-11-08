Chart.register(ChartDataLabels);
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
let chartBestInstance = null;
let chartWorstInstance = null;

/**
 * Retorna as cores apropriadas para os gráficos de acordo com o tema atual
 */
function getChartThemeColors(tema) {
    const isLight = tema === "light";
    return {
        textColor: isLight ? "#14213D" : "#E5E7EB",
        mutedTextColor: isLight ? "#4B5563" : "#9CA3AF",
        gridColor: isLight ? "rgba(20, 33, 61, 0.06)" : "rgba(255, 255, 255, 0.06)",
        doughnutBorder: isLight ? "#FFFFFF" : "#181920"
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

    [chartTemasInstance, chartBestInstance, chartWorstInstance].forEach(inst => {
        if (!inst) return;
        if (inst.options.plugins && inst.options.plugins.legend) {
            inst.options.plugins.legend.labels.color = colors.textColor;
        }
        if (inst.options.scales) {
            if (inst.options.scales.x) {
                inst.options.scales.x.ticks.color = colors.mutedTextColor;
                inst.options.scales.x.grid.color = colors.gridColor;
            }
            if (inst.options.scales.y) {
                inst.options.scales.y.ticks.color = colors.mutedTextColor;
                inst.options.scales.y.grid.color = colors.gridColor;
            }
        }
        inst.update();
    });
};

function carregarDadosDashboard() {
    const dataScript = document.getElementById("dashboard-data");
    if (dataScript && dataScript.textContent) {
        try {
            const dados = JSON.parse(dataScript.textContent);
            window.dashboardData = dados;
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
 * 2. Gráficos de Barras Horizontais: Top 10 Melhores e Top 10 em Atenção
 */
function inicializarGraficos() {
    const temaAtual = document.documentElement.getAttribute("data-theme") || "light";
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
    if (chartBestInstance) {
        chartBestInstance.destroy();
        chartBestInstance = null;
    }
    if (chartWorstInstance) {
        chartWorstInstance.destroy();
        chartWorstInstance = null;
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
                    borderWidth: 2.5,
                    offset: getDoughnutStatusOffsets(filtroStatusAtivo),
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements, chart) => {
                    if (!elements || elements.length === 0) {
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
                    datalabels: {
                        display: false
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }

    // Configuração comum para os gráficos horizontais editoriais
    const criarOpcoesBarraEditorial = () => ({
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        onClick: (event, elements, chart) => {
            if (elements && elements.length > 0) {
                const idx = elements[0].index;
                const topico = chart.data.labels[idx];
                if (typeof alternarAbaPainelDocente === 'function') {
                    alternarAbaPainelDocente('submissoes');
                }
                filtrarTabelaPorTopico(topico);
            }
        },
        onHover: (event, elements) => {
            if (event && event.native && event.native.target) {
                event.native.target.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
            }
        },
        plugins: {
            datalabels: {
                display: false
            },
            legend: {
                position: 'top',
                align: 'end',
                labels: {
                    usePointStyle: true,
                    pointStyle: 'circle',
                    boxWidth: 8,
                    color: themeColors.textColor,
                    font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                }
            },
            tooltip: {
                callbacks: {
                    footer: () => 'Clique na barra para filtrar a tabela por este tema'
                }
            }
        },
        scales: {
            x: {
                stacked: true,
                beginAtZero: true,
                grid: { color: themeColors.gridColor, drawBorder: false },
                ticks: { color: themeColors.mutedTextColor, font: { size: 11 } }
            },
            y: {
                stacked: true,
                grid: { display: false, drawBorder: false },
                ticks: { color: themeColors.textColor, font: { size: 11, weight: '600' } }
            }
        }
    });

    // GRÁFICO 2A: Top 10 Melhores Temas
    const ctxBest = document.getElementById('graficoBest');
    if (ctxBest && window.dashboardData && window.dashboardData.best_labels) {
        chartBestInstance = new Chart(ctxBest, {
            type: 'bar',
            data: {
                labels: window.dashboardData.best_labels,
                datasets: [
                    { label: 'Acertos', data: window.dashboardData.best_acertos, backgroundColor: '#2A9D8F', borderRadius: 6, barThickness: 16 },
                    { label: 'Parciais', data: window.dashboardData.best_parciais, backgroundColor: '#FCA311', borderRadius: 6, barThickness: 16 },
                    { label: 'Erros', data: window.dashboardData.best_erros, backgroundColor: '#E11D48', borderRadius: 6, barThickness: 16 }
                ]
            },
            options: criarOpcoesBarraEditorial()
        });
    }

    // GRÁFICO 2B: Top 10 Temas em Atenção
    const ctxWorst = document.getElementById('graficoWorst');
    if (ctxWorst && window.dashboardData && window.dashboardData.worst_labels) {
        chartWorstInstance = new Chart(ctxWorst, {
            type: 'bar',
            data: {
                labels: window.dashboardData.worst_labels,
                datasets: [
                    { label: 'Erros', data: window.dashboardData.worst_erros, backgroundColor: '#E11D48', borderRadius: 6, barThickness: 16 },
                    { label: 'Parciais', data: window.dashboardData.worst_parciais, backgroundColor: '#FCA311', borderRadius: 6, barThickness: 16 },
                    { label: 'Acertos', data: window.dashboardData.worst_acertos, backgroundColor: '#2A9D8F', borderRadius: 6, barThickness: 16 }
                ]
            },
            options: criarOpcoesBarraEditorial()
        });
    }
}

let submissaoModalAtualId = null;

/**
 * Funções de Controle do Modal de Detalhes com Análise do Professor
 */
function abrirModalFeedback(id) {
    if (typeof submissoesData === "undefined" || !submissoesData[id]) return;

    submissaoModalAtualId = Number(id);
    const sub = submissoesData[id];
    const modal = document.getElementById("feedbackModal");

    document.getElementById("modalTitle").textContent = `Submissão #${sub.id}`;
    document.getElementById("modalTopicBadge").textContent = sub.tema || "Geral";
    document.getElementById("modalQuestion").textContent = sub.pergunta;
    document.getElementById("modalAnswer").textContent = sub.resposta;
    document.getElementById("modalTimestamp").textContent = `Enviado em: ${sub.data_hora}`;

    const studentBadge = document.getElementById("modalStudentBadge");
    if (studentBadge) {
        studentBadge.textContent = `${sub.aluno_nome || 'Estudante'}${sub.turma_nome ? ' • ' + sub.turma_nome : ''}`;
    }

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
        const rawHtml = marked.parse(sub.feedback || "");
        feedbackBox.innerHTML = String(rawHtml)
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
            .replace(/<(iframe|object|embed|form|meta|link|style)\b[^>]*>/gi, "")
            .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
            .replace(/href\s*=\s*["']?\s*javascript:[^"'\s>]*/gi, 'href="#"');
    } else {
        feedbackBox.textContent = sub.feedback || "";
    }

    ultimoElementoFocado = document.activeElement;
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    setTimeout(() => {
        const btnFechar = modal.querySelector(".btn-close-modal");
        if (btnFechar) btnFechar.focus();
    }, 50);

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(`Detalhes da submissão #${sub.id} abertos. Diagnóstico: ${sub.status}. Pressione Escape para fechar.`);
    }
}

function navegarSubmissaoModal(delta) {
    const ids = Object.keys(submissoesData || {}).map(Number).sort((a, b) => b - a);
    if (ids.length <= 1 || !submissaoModalAtualId) return;
    const idx = ids.indexOf(Number(submissaoModalAtualId));
    if (idx === -1) return;
    const novoIdx = (idx + delta + ids.length) % ids.length;
    abrirModalFeedback(ids[novoIdx]);
}
window.navegarSubmissaoModal = navegarSubmissaoModal;

function enviarRecadoDaSubmissaoModal() {
    if (!submissaoModalAtualId || !submissoesData || !submissoesData[submissaoModalAtualId]) return;
    const sub = submissoesData[submissaoModalAtualId];
    fecharModal();
    if (typeof abrirRecadoRapidoAluno === "function") {
        abrirRecadoRapidoAluno(sub.aluno_id, sub.aluno_nome);
        const inpAssunto = document.getElementById("msg_assunto");
        const inpCorpo = document.getElementById("msg_corpo");
        if (inpAssunto) {
            inpAssunto.value = `Feedback Pedagógico: ${sub.tema || 'Exercício'} (Submissão #${sub.id})`;
        }
        if (inpCorpo) {
            inpCorpo.value = `Bonjour ${sub.aluno_nome || ''} ! Em relação à sua resposta « ${sub.resposta || ''} » no tópico ${sub.tema || 'de francês'}: `;
            inpCorpo.focus();
        }
    }
}
window.enviarRecadoDaSubmissaoModal = enviarRecadoDaSubmissaoModal;

function gerarReforcoDaSubmissaoModal() {
    if (!submissaoModalAtualId || !submissoesData || !submissoesData[submissaoModalAtualId]) return;
    const sub = submissoesData[submissaoModalAtualId];
    gerarReforcoRadar(sub.aluno_id, sub.tema_id || 1);
}
window.gerarReforcoDaSubmissaoModal = gerarReforcoDaSubmissaoModal;

let respostaAtualModal = "";

function ouvirRespostaModal() {
    const btn = document.getElementById("btnAudioModal");
    const modalAnswer = document.getElementById("modalAnswer");
    const texto = modalAnswer ? modalAnswer.textContent : "";
    if (!texto || !texto.trim()) {
        showToast("Nenhuma resposta para reproduzir.", 'erro');
        return;
    }
    falarTextoFrancesDashboard(texto, btn);
}

function falarTextoFrancesDashboard(texto, btnElement = null) {
    if (!('speechSynthesis' in window)) {
        showToast("Seu navegador não possui suporte à síntese de voz nativa.");
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
        if (typeof anunciarParaLeitorDeTela === "function") {
            anunciarParaLeitorDeTela("Janela de detalhes fechada.");
        }
        if (ultimoElementoFocado && typeof ultimoElementoFocado.focus === "function") {
            try { ultimoElementoFocado.focus(); } catch (e) {}
        }
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
        "Correto": "#2A9D8F",
        "Parcialmente Correto": "#FCA311",
        "Incorreto": "#E11D48"
    };
    const statusColorsDimmed = {
        "Correto": "rgba(42, 157, 143, 0.22)",
        "Parcialmente Correto": "rgba(252, 163, 17, 0.22)",
        "Incorreto": "rgba(225, 29, 72, 0.22)"
    };
    return (STATUS_LABELS || []).map(label => {
        if (!filtroAtivo || filtroAtivo === "TODOS") {
            return statusColors[label] || "#14213D";
        }
        return label === filtroAtivo ? (statusColors[label] || "#14213D") : (statusColorsDimmed[label] || "rgba(148, 163, 184, 0.2)");
    });
}

/**
 * Retorna os offsets dos segmentos do gráfico de rosca (destaca a fatia clicada)
 */
function getDoughnutStatusOffsets(filtroAtivo) {
    return (STATUS_LABELS || []).map(label => {
        return (filtroAtivo && filtroAtivo !== "TODOS" && label === filtroAtivo) ? 10 : 0;
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
            if (hintTotal) hintTotal.textContent = "▲ 100%";
        }
        cards.forEach(c => {
            if (c.el) {
                c.el.classList.remove("metric-card-selected", "metric-card-dimmed");
            }
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
            } else {
                c.el.classList.remove("metric-card-selected");
                c.el.classList.add("metric-card-dimmed");
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
 * Sincroniza as pílulas de filtro da tabela e alterna a aba ativa se necessário
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

    if (typeof alternarAbaPainelDocente === "function") {
        alternarAbaPainelDocente("submissoes");
    }

    aplicarFiltrosTabela();
}

/**
 * Exibe ou oculta o banner unificado de filtros ativos acima dos gráficos
 */
function atualizarBannerFiltroAtivo(status) {
    const banner = document.getElementById("bannerFiltroInterativo");
    const texto = document.getElementById("textoFiltroAtivo");
    const badge = document.getElementById("badgeFiltroAtivoCount");
    const chipsWrap = document.getElementById("chipsFiltrosAtivosContainer");
    if (!banner) return;

    const selTurma = document.getElementById("filtroTurma");
    const selNivel = document.getElementById("filtroNivel");
    const selAluno = document.getElementById("filtroAluno");

    const turmaVal = selTurma ? selTurma.value : "todas";
    const nivelVal = selNivel ? selNivel.value : "todos";
    const alunoVal = selAluno ? selAluno.value : "todos";
    const statusVal = typeof filtroStatusAtivo !== "undefined" ? filtroStatusAtivo : (status || "TODOS");
    const temaVal = typeof filtroTemaAtivo !== "undefined" ? filtroTemaAtivo : "TODOS";
    const cefrTabVal = typeof filtroCefrAtivo !== "undefined" ? filtroCefrAtivo : "TODOS";

    const chips = [];

    if (turmaVal && turmaVal !== "todas" && selTurma) {
        const nomeTurma = selTurma.options[selTurma.selectedIndex]?.text || "Turma";
        chips.push({ tipo: "turma", label: `Turma: ${nomeTurma}` });
    }
    if (nivelVal && nivelVal !== "todos") {
        chips.push({ tipo: "nivel", label: `Nível: ${nivelVal}` });
    }
    if (alunoVal && alunoVal !== "todos" && selAluno) {
        const nomeAluno = selAluno.options[selAluno.selectedIndex]?.text || "Estudante";
        chips.push({ tipo: "aluno", label: `Dossiê: ${nomeAluno}` });
    }
    if (temaVal && temaVal !== "TODOS") {
        chips.push({ tipo: "tema", label: `Tema: ${temaVal}` });
    }
    if (statusVal && statusVal !== "TODOS") {
        const nomes = {
            "Correto": "Domínio Pleno (Correto)",
            "Parcialmente Correto": "Parcialmente Correto",
            "Incorreto": "Respostas Incorretas"
        };
        chips.push({ tipo: "status", label: `Status: ${nomes[statusVal] || statusVal}` });
    }
    if (cefrTabVal && cefrTabVal !== "TODOS") {
        chips.push({ tipo: "cefr_tab", label: `Tabela CEFR: ${cefrTabVal}` });
    }

    if (chips.length === 0) {
        banner.classList.remove("visible");
        if (chipsWrap) chipsWrap.innerHTML = "";
        return;
    }

    if (texto) {
        texto.textContent = chips.map(c => c.label).join(" • ");
    }

    if (chipsWrap) {
        chipsWrap.innerHTML = chips.map(c => `
            <button type="button" class="docente-chip-btn active" style="width: auto; padding: 4px 12px; font-size: 0.75rem;" onclick="removerFiltroIndividual('${c.tipo}')" title="Clique para remover este filtro">
                <span>${escapeHtml(c.label)}</span>
                <span style="margin-left: 4px; opacity: 0.85;">✕</span>
            </button>
        `).join("");
    }

    if (badge) {
        const badgeSub = document.getElementById("badgeSubmissoesCount");
        badge.textContent = badgeSub ? badgeSub.textContent : "";
    }

    banner.classList.add("visible");
}
window.atualizarBannerFiltroAtivo = atualizarBannerFiltroAtivo;

function removerFiltroIndividual(tipo) {
    if (tipo === "turma") {
        const s = document.getElementById("filtroTurma");
        if (s) s.value = "todas";
        carregarAlunosPorTurma();
        gerarRelatorioVisual();
    } else if (tipo === "nivel") {
        const s = document.getElementById("filtroNivel");
        if (s) s.value = "todos";
        gerarRelatorioVisual();
    } else if (tipo === "aluno") {
        const s = document.getElementById("filtroAluno");
        if (s) s.value = "todos";
        gerarRelatorioVisual();
    } else if (tipo === "tema") {
        filtroTemaAtivo = "TODOS";
        aplicarFiltrosTabela();
    } else if (tipo === "status") {
        alternarFiltroInterativoStatus("TODOS", "banner");
    } else if (tipo === "cefr_tab") {
        filtrarTabelaCefr("TODOS");
    }
}
window.removerFiltroIndividual = removerFiltroIndividual;

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
 * Aplica os filtros combinados (Escopo Inline + CEFR + Status + Tema) sobre as 3 tabelas
 * e sincroniza com o sistema de paginação dinâmica e o banner de filtros ativos
 */
function aplicarFiltrosTabela() {
    if (typeof renderizarPaginacaoSubmissoes === "function") {
        renderizarPaginacaoSubmissoes(true);
    }
    if (typeof renderizarPaginacaoRisco === "function") {
        riscoPaginationState.paginaAtual = 1;
        renderizarPaginacaoRisco();
    }
    filtrarTabelaDesempenhoAlunosPorEscopo();
    if (typeof atualizarBannerFiltroAtivo === "function") {
        atualizarBannerFiltroAtivo(filtroStatusAtivo);
    }
}
window.aplicarFiltrosTabela = aplicarFiltrosTabela;

function filtrarTabelaDesempenhoAlunosPorEscopo() {
    const selTurma = document.getElementById("filtroTurma")?.value || "todas";
    const selNivel = (document.getElementById("filtroNivel")?.value || "todos").toUpperCase();
    const selAluno = document.getElementById("filtroAluno")?.value || "todos";

    const rows = document.querySelectorAll("#tabelaDesempenhoAlunos tbody tr.student-perf-row");
    let visiveis = 0;
    rows.forEach(row => {
        const rTurma = row.getAttribute("data-turma-id") || "";
        const rCefr = (row.getAttribute("data-cefr") || "A2").toUpperCase();
        const rAluno = row.getAttribute("data-aluno-id") || "";

        const okTurma = (selTurma === "todas" || rTurma === String(selTurma));
        const okNivel = (selNivel === "TODOS" || rCefr === selNivel);
        const okAluno = (selAluno === "todos" || rAluno === String(selAluno));

        if (okTurma && okNivel && okAluno) {
            row.style.display = "";
            visiveis++;
        } else {
            row.style.display = "none";
        }
    });

    const tabCountAlunos = document.getElementById("tabCountAlunos");
    if (tabCountAlunos) tabCountAlunos.textContent = visiveis;
}
window.filtrarTabelaDesempenhoAlunosPorEscopo = filtrarTabelaDesempenhoAlunosPorEscopo;

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
    const turmaEl = document.getElementById("filtroTurma");
    const alunoSelect = document.getElementById("filtroAluno");
    if (!turmaEl || !alunoSelect) return;

    const turmaId = turmaEl.value || "todas";
    const alunoAnterior = alunoSelect.value;

    alunoSelect.innerHTML = '<option value="todos">Visão Macro / Todos os Alunos</option>';

    try {
        const response = await fetch(`/api/alunos_por_turma/${encodeURIComponent(turmaId)}`);
        const alunos = await response.json();
        if (Array.isArray(alunos)) {
            alunos.forEach(a => {
                const opt = document.createElement("option");
                opt.value = a.id;
                opt.textContent = a.nome;
                alunoSelect.appendChild(opt);
            });
            if (alunoAnterior && alunoAnterior !== "todos" && alunos.some(a => String(a.id) === String(alunoAnterior))) {
                alunoSelect.value = alunoAnterior;
            }
        }
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

            // Atualiza as variáveis e window.dashboardData que o inicializarGraficos() consome
            STATUS_LABELS = window.STATUS_LABELS = data.desempenho_geral.labels || [];
            STATUS_VALORES = window.STATUS_VALORES = data.desempenho_geral.data || [];
            if (window.dashboardData) {
                window.dashboardData.status_labels = STATUS_LABELS;
                window.dashboardData.status_valores = STATUS_VALORES;
            }
            
            if (data.desempenho_tema) {
                TEMA_LABELS = window.TEMA_LABELS = data.desempenho_tema.labels || [];
                TEMA_ACERTOS = window.TEMA_ACERTOS = data.desempenho_tema.acertos || [];
                TEMA_PARCIAIS = window.TEMA_PARCIAIS = data.desempenho_tema.parciais || [];
                TEMA_ERROS = window.TEMA_ERROS = data.desempenho_tema.erros || [];

                if (window.dashboardData) {
                    const zipped = TEMA_LABELS.map((lbl, idx) => ({
                        label: lbl,
                        acertos: Number(TEMA_ACERTOS[idx] || 0),
                        erros: Number(TEMA_ERROS[idx] || 0),
                        parciais: Number(TEMA_PARCIAIS[idx] || 0)
                    }));
                    const best = [...zipped].sort((a, b) => b.acertos - a.acertos).slice(0, 10);
                    const worst = [...zipped].sort((a, b) => b.erros - a.erros).slice(0, 10);

                    window.dashboardData.best_labels = best.map(x => x.label);
                    window.dashboardData.best_acertos = best.map(x => x.acertos);
                    window.dashboardData.best_erros = best.map(x => x.erros);
                    window.dashboardData.best_parciais = best.map(x => x.parciais);

                    window.dashboardData.worst_labels = worst.map(x => x.label);
                    window.dashboardData.worst_acertos = worst.map(x => x.acertos);
                    window.dashboardData.worst_erros = worst.map(x => x.erros);
                    window.dashboardData.worst_parciais = worst.map(x => x.parciais);
                }
            }
            
            // Recria graficos e filtra as 3 tabelas simultaneamente
            inicializarGraficos();
            aplicarFiltrosTabela();
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

    const selTurma = document.getElementById("filtroTurma")?.value || "todas";
    const selNivel = (document.getElementById("filtroNivel")?.value || "todos").toUpperCase();
    const selAluno = document.getElementById("filtroAluno")?.value || "todos";

    const todasRows = Array.from(tabela.querySelectorAll("tbody tr.risk-row"));
    const rows = todasRows.filter(row => {
        const rTurma = row.getAttribute("data-turma-id") || "";
        const rCefr = (row.getAttribute("data-cefr") || "A2").toUpperCase();
        const rAluno = row.getAttribute("data-aluno-id") || "";
        const rTema = (row.getAttribute("data-tema") || "").trim();

        const okTurma = (selTurma === "todas" || rTurma === String(selTurma));
        const okNivel = (selNivel === "TODOS" || rCefr === selNivel);
        const okAluno = (selAluno === "todos" || rAluno === String(selAluno));
        const okTema = (typeof filtroTemaAtivo === "undefined" || filtroTemaAtivo === "TODOS" || rTema === filtroTemaAtivo || rTema.includes(filtroTemaAtivo));

        return okTurma && okNivel && okAluno && okTema;
    });

    todasRows.forEach(r => {
        r.style.display = "none";
        r.classList.remove("risk-row-even", "risk-row-odd");
    });

    const total = rows.length;
    const tabCountRisco = document.getElementById("tabCountRisco");
    if (tabCountRisco) tabCountRisco.textContent = total;

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

    const selTurma = document.getElementById("filtroTurma")?.value || "todas";
    const selNivel = (document.getElementById("filtroNivel")?.value || "todos").toUpperCase();
    const selAluno = document.getElementById("filtroAluno")?.value || "todos";

    const todasLinhas = Array.from(tabela.querySelectorAll("tbody tr.submission-row"));
    
    // Filtra quais linhas correspondem aos filtros ativos (Escopo Inline + CEFR + Status + Tema)
    const linhasFiltradas = todasLinhas.filter(linha => {
        const linhaTurma = linha.getAttribute("data-turma-id") || "";
        const linhaAluno = linha.getAttribute("data-aluno-id") || "";
        const linhaCefr = (linha.getAttribute("data-cefr") || "A2").toUpperCase();
        const linhaStatus = linha.getAttribute("data-status") || "";
        const linhaTema = (linha.getAttribute("data-tema") || "").trim();

        const correspondeTurma = (selTurma === "todas" || linhaTurma === String(selTurma));
        const correspondeNivelInline = (selNivel === "TODOS" || linhaCefr === selNivel);
        const correspondeAluno = (selAluno === "todos" || linhaAluno === String(selAluno));
        const correspondeCefr = (typeof filtroCefrAtivo === "undefined" || filtroCefrAtivo === "TODOS" || linhaCefr === filtroCefrAtivo);
        const correspondeStatus = (typeof filtroStatusAtivo === "undefined" || filtroStatusAtivo === "TODOS" || linhaStatus === filtroStatusAtivo);
        const correspondeTema = (typeof filtroTemaAtivo === "undefined" || filtroTemaAtivo === "TODOS" || linhaTema === filtroTemaAtivo || linhaTema.includes(filtroTemaAtivo));

        return (correspondeTurma && correspondeNivelInline && correspondeAluno && correspondeCefr && correspondeStatus && correspondeTema);
    });

    const total = linhasFiltradas.length;
    const tabCountSub = document.getElementById("tabCountSubmissoes");
    if (tabCountSub) tabCountSub.textContent = total;

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
