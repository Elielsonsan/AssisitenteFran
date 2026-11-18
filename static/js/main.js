/**
 * Assistente Fran - main.js
 * Gerenciamento do envio do formulário, indicador 'Carregando...' e renderização de feedback em Francês
 */

// O array estático de exemplos foi removido, agora todos os exercícios vêm do DB.

let numeroTentativa = 1;
let dicaAtual = "";
let nivelCEFRSelecionado = "A2";

const CEFR_DESCRICOES = {
    "A1": "A1 • Débutant (explicações simples em português, regras essenciais)",
    "A2": "A2 • Élémentaire (estruturas compostas, dicas em português com destaque em francês)",
    "B1": "B1 • Intermédiaire (maior rigor com pronomes e subjonctif, feedback bilíngue)",
    "B2": "B2 • Avancé (acordos complexos, registro culto, feedback predominantemente em francês)"
};

function selecionarNivelCEFR(lvl) {
    if (!lvl) return;
    const nivelUpper = lvl.toUpperCase();
    nivelCEFRSelecionado = nivelUpper;

    const inputNivel = document.getElementById("nivel_cefr");
    if (inputNivel) inputNivel.value = nivelUpper;

    const descEl = document.getElementById("cefrDesc");
    if (descEl && CEFR_DESCRICOES[nivelUpper]) {
        descEl.textContent = CEFR_DESCRICOES[nivelUpper];
    }

    const btnGerarNivel = document.getElementById("btnGerarNivel");
    if (btnGerarNivel) {
        btnGerarNivel.textContent = nivelUpper;
    }

    // Sincroniza pílulas do formulário
    const pills = document.querySelectorAll(".cefr-pill");
    pills.forEach(p => {
        if (p.getAttribute("data-level") === nivelUpper) {
            p.classList.add("active");
        } else {
            p.classList.remove("active");
        }
    });

    // Sincroniza botões da barra lateral
    const sidebarBtns = document.querySelectorAll(".sidebar-level-btn");
    sidebarBtns.forEach(b => {
        if (b.getAttribute("data-level") === nivelUpper) {
            b.classList.add("active");
        } else {
            b.classList.remove("active");
        }
    });

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(`Nível CEFR ${nivelUpper} selecionado: ${CEFR_DESCRICOES[nivelUpper] || nivelUpper}`);
    }
}

function ocultarFeedbackAnterior() {
    const resultContainer = document.getElementById("resultContainer");
    const analiseProfessorBox = document.getElementById("analiseProfessorBox");
    const btnTentarNovamente = document.getElementById("btnTentarNovamenteDica");
    const arrow = document.getElementById("arrowIcon");
    const feedbackContent = document.getElementById("feedbackContent");

    if (resultContainer) resultContainer.classList.add("hidden");
    if (analiseProfessorBox) analiseProfessorBox.classList.add("hidden");
    if (btnTentarNovamente) btnTentarNovamente.classList.add("hidden");
    if (arrow) arrow.style.transform = "rotate(0deg)";
    if (feedbackContent) feedbackContent.innerHTML = "";

    ultimaRespostaSubmetida = "";
    if ("speechSynthesis" in window) {
        try { window.speechSynthesis.cancel(); } catch (e) {}
    }
}
window.ocultarFeedbackAnterior = ocultarFeedbackAnterior;

async function gerarNovoDesafioIA(temaEscolhido = null, tipoEscolhido = null) {
    cancelarTentativa();
    ocultarFeedbackAnterior();
    const btn = document.getElementById("btnGerarDesafio");
    const inputNivel = document.getElementById("nivel_cefr");
    const nivelText = document.getElementById("btnGerarNivel");
    const temaInput = document.getElementById("tema_aula");
    const tipoInput = document.getElementById("tipo_atividade");
    const perguntaInput = document.getElementById("pergunta");
    const respostaInput = document.getElementById("resposta_aluno");
    const exercicioIdInput = document.getElementById("exercicio_id");
    const nivel = (inputNivel && inputNivel.value ? inputNivel.value : (nivelText ? nivelText.textContent.trim() : nivelCEFRSelecionado)) || "A1";
    const temaParam = temaEscolhido !== null ? temaEscolhido : (temaInput ? temaInput.value.trim() : "");
    const tipoParam = tipoEscolhido !== null ? tipoEscolhido : (tipoInput ? tipoInput.value.trim() : "lacunas");
    const excluirId = exercicioIdInput ? exercicioIdInput.value.trim() : "";

    if (tipoInput && tipoEscolhido) {
        tipoInput.value = tipoEscolhido;
    }

    let originalHtml = "";
    if (btn) {
        originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span>Criando Desafio (${nivel})...</span>`;
    }

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(`Gerando novo desafio de francês (${tipoParam}) para o nível ${nivel}. Por favor, aguarde...`);
    }

    try {
        let url = `/gerar-desafio?nivel_cefr=${encodeURIComponent(nivel)}&tipo_atividade=${encodeURIComponent(tipoParam)}`;
        if (temaParam) {
            url += `&tema=${encodeURIComponent(temaParam)}`;
        }
        if (excluirId) {
            url += `&excluir_id=${encodeURIComponent(excluirId)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        const data = await response.json();

        if (temaInput && data.tema) {
            temaInput.value = data.tema;
        }
        if (perguntaInput && data.exercicio) {
            perguntaInput.value = data.exercicio;
        }
        if (exercicioIdInput && data.exercicio_id) {
            exercicioIdInput.value = data.exercicio_id;
        }
        if (respostaInput) {
            respostaInput.value = "";
            respostaInput.focus();
        }

        // Se houver callback para ajustar UI da modalidade (ex: dicas de ditado ou botões rápidos)
        if (typeof aplicarAjustesModalidadeUI === "function") {
            aplicarAjustesModalidadeUI(tipoParam, data.exercicio, data.opcoes);
        } else if (perguntaInput && typeof autoAjustarAlturaTextarea === "function") {
            autoAjustarAlturaTextarea(perguntaInput, 76);
        }

        if (data.dica_inicial) {
            dicaAtual = data.dica_inicial;
        }

        // Destaque visual suave no formulário
        const formCard = document.querySelector(".form-card");
        if (formCard) {
            formCard.classList.add("highlight-generator");
            setTimeout(() => formCard.classList.remove("highlight-generator"), 1200);
        }

        if (typeof anunciarParaLeitorDeTela === "function") {
            anunciarParaLeitorDeTela(`Novo exercício de francês gerado com sucesso! Tema: ${data.tema || 'Francês'}. O enunciado está pronto no formulário.`);
        }

    } catch (err) {
        console.error("Erro ao gerar desafio:", err);
        showToast("Não foi possível gerar o desafio no momento. Tente novamente.", 'erro');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

function obterCampoRespostaAtivo() {
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const vfInput = document.getElementById("vfCorrecaoInput");
    const vfWrap = document.getElementById("vfCorrecaoWrap");
    const textarea = document.getElementById("resposta_aluno");

    if (lacunaInput && lacunaInput.offsetParent !== null) {
        return lacunaInput;
    }
    if (vfInput && vfWrap && vfWrap.style.display !== "none" && vfInput.offsetParent !== null) {
        return vfInput;
    }
    return textarea;
}

function sincronizarCampoAtivo(target) {
    if (!target) return;
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const vfInput = document.getElementById("vfCorrecaoInput");
    const textarea = document.getElementById("resposta_aluno");

    if (typeof autoAjustarAlturaTextarea === "function") {
        autoAjustarAlturaTextarea(target, target === textarea ? 88 : 76);
    }
    if (target === lacunaInput && textarea) {
        textarea.value = target.value;
    } else if (target === vfInput && typeof atualizarRespostaVFPeloInput === "function") {
        atualizarRespostaVFPeloInput();
    }
}

// Função carregarExemplo removida pois os exercícios agora requerem um exercicio_id validado via DB.

document.addEventListener("DOMContentLoaded", () => {
    // Redirecionar mémento para /guia-fle se solicitado via URL (?memento=1)
    if (window.location.search.includes("memento=1")) {
        window.location.href = "/guia-fle";
    }

    const form = document.getElementById("submissionForm");
    const btnSubmit = document.getElementById("btnSubmit");
    const btnText = document.getElementById("btnText");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const resultContainer = document.getElementById("resultContainer");

    if (!form) return;

    // Acessibilidade WCAG: Atalho de Teclado (Ctrl+Enter ou Cmd+Enter) para submeter a resposta + auto-expansão
    const respostaInput = document.getElementById("resposta_aluno");
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const vfCorrecaoInput = document.getElementById("vfCorrecaoInput");
    if (respostaInput) {
        respostaInput.addEventListener("input", () => {
            if (typeof autoAjustarAlturaTextarea === "function") {
                autoAjustarAlturaTextarea(respostaInput, 88);
            }
        });
    }
    [respostaInput, lacunaInput, vfCorrecaoInput].forEach(inp => {
        if (inp) {
            inp.addEventListener("keydown", (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    if (typeof form.requestSubmit === "function") {
                        form.requestSubmit();
                    } else if (btnSubmit) {
                        btnSubmit.click();
                    }
                }
            });
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (typeof pararDitadoVozForcado === "function") {
            pararDitadoVozForcado();
        }
        if (typeof pararDitadoAudioPlayer === "function") {
            pararDitadoAudioPlayer();
        }

        const tema = document.getElementById("tema_aula").value.trim();
        const pergunta = document.getElementById("pergunta").value.trim();
        const tipoAtiv = (document.getElementById("tipo_atividade")?.value || "lacunas").trim().toLowerCase();
        const lacunaInp = document.getElementById("respostaLacunaInput");
        const vfInp = document.getElementById("vfCorrecaoInput");
        const respostaElem = document.getElementById("resposta_aluno");

        if (lacunaInp && lacunaInp.offsetParent !== null && lacunaInp.value.trim()) {
            respostaElem.value = lacunaInp.value.trim();
        } else if (tipoAtiv === "vf" && vfInp && vfInp.offsetParent !== null && typeof atualizarRespostaVFPeloInput === "function") {
            atualizarRespostaVFPeloInput();
        }

        const resposta = respostaElem ? respostaElem.value.trim() : "";
        const exercicioId = document.getElementById("exercicio_id").value;
        if (tipoAtiv === "expressao_oral" && window._oralGravandoAtivo) {
            showToast("Clique em 'Parar Gravação' antes de enviar seu áudio para análise.", "aviso");
            return;
        }
        const transcricaoOral = String(window._oralTranscricaoCapturada || resposta || "").trim();
        const temAudioOralGravado = (tipoAtiv === "expressao_oral" && Boolean(window._oralAudioBlob));

        if (!tema || !pergunta) {
            showToast("Por favor, selecione o tema e o exercício antes de enviar.", "aviso");
            return;
        }
        if (tipoAtiv === "expressao_oral") {
            if (!temAudioOralGravado && !transcricaoOral) {
                showToast("Por favor, clique em 'Gravar Áudio' e pronuncie a frase em francês antes de analisar.", "aviso");
                return;
            }
        } else if (!resposta) {
            showToast("Por favor, preencha ou selecione sua resposta antes de enviar.", "aviso");
            return;
        }

        // 1. Ativar estado de 'Carregando...' no botão e no container
        btnSubmit.disabled = true;
        if (btnText) {
            btnText.textContent = numeroTentativa > 1 
                ? `Analisando Tentativa ${numeroTentativa}...` 
                : "Analisando...";
        }
        loadingIndicator.classList.remove("hidden");
        resultContainer.classList.add("hidden");

        if (typeof anunciarParaLeitorDeTela === "function") {
            anunciarParaLeitorDeTela("Enviando sua resposta. O Assistente Fran está analisando sua conjugação, gramática e pronúncia...");
        }

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                              document.querySelector('input[name="csrf_token"]')?.value || "";

            let fetchOptions;
            if (temAudioOralGravado) {
                const fd = new FormData();
                fd.append("exercicio_id", exercicioId);
                fd.append("tema", tema);
                fd.append("exercicio", pergunta);
                fd.append("resposta_aluno", transcricaoOral);
                fd.append("transcricao_oral", transcricaoOral);
                fd.append("tentativa", String(numeroTentativa));
                fd.append("dica_anterior", dicaAtual || "");
                fd.append("nivel_cefr", nivelCEFRSelecionado || "A2");
                fd.append("tipo_atividade", tipoAtiv);
                fd.append("audio_oral", window._oralAudioBlob, "expressao_oral.webm");
                fetchOptions = {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken },
                    body: fd
                };
            } else {
                fetchOptions = {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({
                        exercicio_id: exercicioId,
                        tema: tema,
                        exercicio: pergunta,
                        resposta_aluno: resposta,
                        tentativa: numeroTentativa,
                        dica_anterior: dicaAtual,
                        nivel_cefr: nivelCEFRSelecionado,
                        tipo_atividade: tipoAtiv
                    })
                };
            }

            // 2. Envio via POST para a rota /avaliar
            const response = await fetch("/avaliar", fetchOptions);

            const data = await response.json();

            if (!response.ok || data.status === "erro") {
                throw new Error(data.mensagem || "Falha na comunicação com o assistente.");
            }

            // 3. Exibir resultado formatado
            exibirFeedback(data);

        } catch (err) {
            console.error("Erro:", err);
            showToast("Erro ao avaliar a resposta: " + err.message, 'erro');
        } finally {
            // 4. Restaurar botão e ocultar loading
            btnSubmit.disabled = false;
            if (btnText) btnText.textContent = "Analisar com o Assistente Fran";
            loadingIndicator.classList.add("hidden");
        }
    });
});

function sanitizarHtmlMarkdown(html) {
    if (!html) return "";
    return String(html)
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
        .replace(/<(iframe|object|embed|form|meta|link|style)\b[^>]*>/gi, "")
        .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
        .replace(/href\s*=\s*["']?\s*javascript:[^"'\s>]*/gi, 'href="#"');
}

function extrairDicaDoFeedback(feedbackTexto) {
    if (!feedbackTexto) return "";
    // Tenta encontrar a seção de dica gramatical
    const matchDica = feedbackTexto.match(/\*\*(?:Dica|Dica Gramatical|Dica do Professeur|O que faltou|Attention).*?\*\*.*?(?=(?:\n\n|\n-|\n>|$))/is);
    if (matchDica) {
        return matchDica[0].trim();
    }
    // Caso não encontre seção específica, retorna o texto completo
    return feedbackTexto;
}

function exibirFeedback(data) {
    const resultContainer = document.getElementById("resultContainer");
    const statusBadge = document.getElementById("statusBadge");
    const cefrBadge = document.getElementById("cefrBadge");
    const xpGainBadge = document.getElementById("xpGainBadge");
    const feedbackContent = document.getElementById("feedbackContent");
    const analiseProfessorText = document.getElementById("analiseProfessorText");
    const analiseProfessorBox = document.getElementById("analiseProfessorBox");
    const resultTimestamp = document.getElementById("resultTimestamp");
    const btnTentarNovamente = document.getElementById("btnTentarNovamenteDica");

    // Configurar o badge de status (Correto, Parcialmente Correto, Incorreto)
    const status = data.status_resposta || "Correto";
    statusBadge.textContent = status;
    statusBadge.className = "status-badge";

    // Configurar o badge de Nível CEFR
    if (cefrBadge) {
        const lvl = (data.nivel_cefr || nivelCEFRSelecionado || "A2").toUpperCase();
        cefrBadge.textContent = `Niveau ${lvl}`;
        cefrBadge.className = `cefr-level-badge lvl-${lvl.toLowerCase()}`;
    }

    // Configurar feedback imediato de XP Pessoal e conquistas (separado do XP do curso)
    if (xpGainBadge) {
        if (typeof data.xp_ganho === "number" && data.xp_ganho > 0) {
            const totalTexto = (typeof data.progresso_xp === "number" && data.progresso_xp > 0)
                ? ` • Total na Prática: ${data.progresso_xp} XP`
                : "";
            xpGainBadge.textContent = `⚡ +${data.xp_ganho} XP Pessoal${totalTexto}`;
            xpGainBadge.classList.remove("hidden");
        } else {
            xpGainBadge.classList.add("hidden");
        }
    }

    const xpTopoValor = document.getElementById("xpPessoalTopoValor");
    if (xpTopoValor && typeof data.progresso_xp === "number") {
        xpTopoValor.textContent = `${data.progresso_xp} XP`;
    }

    if (data.conquista_desbloqueada && typeof showToast === "function") {
        showToast(`🏅 Nova insígnia desbloqueada: ${data.conquista_desbloqueada}!`, "sucesso");
    }

    if (status === "Correto") {
        statusBadge.classList.add("status-correta");
        if (numeroTentativa > 1) {
            statusBadge.textContent = `Correto (Superado na Tentativa ${numeroTentativa}!)`;
        }
        if (btnTentarNovamente) btnTentarNovamente.classList.add("hidden");
        // Sucesso: finaliza o ciclo de dicas ativas
        cancelarTentativa();
    } else {
        if (status === "Parcialmente Correto") {
            statusBadge.classList.add("status-parcial");
        } else {
            statusBadge.classList.add("status-incorreta");
        }

        // Se ainda não estiver 100% correto, extrai a dica e habilita o botão de Tentar Novamente
        dicaAtual = extrairDicaDoFeedback(data.feedback_ia || "");
        if (btnTentarNovamente) {
            btnTentarNovamente.classList.remove("hidden");
            btnTentarNovamente.innerHTML = `<svg class="line-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: text-bottom;"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg> <span>Tentar Novamente com a Dica (Tentativa ${numeroTentativa + 1})</span>`;
        }
    }

    resultTimestamp.textContent = data.data_hora || "Agora";

    // Converter Markdown para HTML via marked (com sanitização anti-XSS)
    if (typeof marked !== "undefined" && marked.parse) {
        feedbackContent.innerHTML = sanitizarHtmlMarkdown(marked.parse(data.feedback_ia || ""));
    } else {
        feedbackContent.textContent = data.feedback_ia || "";
    }

    // Acessibilidade FLE: marcar trechos em francês e tornar citações ouviveis ao clicar
    feedbackContent.querySelectorAll("code, em, strong, blockquote").forEach(el => {
        el.setAttribute("lang", "fr");
        el.setAttribute("title", "Clique para ouvir a pronúncia em francês");
        el.style.cursor = "pointer";
        el.addEventListener("click", (e) => {
            e.stopPropagation();
            falarTextoFrances(el.textContent);
        });
    });

    // Preencher a análise técnica do professor
    if (analiseProfessorText) {
        analiseProfessorText.textContent = data.analise_professor || "Análise gramatical registrada.";
    }
    if (analiseProfessorBox) {
        analiseProfessorBox.classList.add("hidden");
    }

    // Armazena a resposta para o botão de reprodução de pronúncia
    ultimaRespostaSubmetida = data.resposta_aluno || "";

    resultContainer.classList.remove("hidden");
    resultContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });

    if (typeof anunciarParaLeitorDeTela === "function") {
        const msgStatus = status === "Correto" 
            ? "Avaliação concluída com sucesso! Resultado: Correto. Parabéns pelo desempenho!" 
            : `Avaliação concluída. Diagnóstico: ${status}. O Assistente Fran preparou orientações pedagógicas detalhadas abaixo.`;
        anunciarParaLeitorDeTela(msgStatus);
    }

    resultContainer.setAttribute("tabindex", "-1");
    resultContainer.focus();
}

function tentarNovamenteComDica() {
    numeroTentativa++;

    // Exibe o banner fixo com a dica acima do campo de resposta
    const banner = document.getElementById("activeDicaBanner");
    const badge = document.getElementById("badgeTentativa");
    const dicaText = document.getElementById("activeDicaText");
    const tipoAtiv = (document.getElementById("tipo_atividade")?.value || "lacunas").trim().toLowerCase();
    const campoAtivo = typeof obterCampoRespostaAtivo === "function"
        ? obterCampoRespostaAtivo()
        : document.getElementById("resposta_aluno");
    const resultContainer = document.getElementById("resultContainer");

    if (badge) badge.textContent = `Tentativa ${numeroTentativa}`;
    if (dicaText) {
        if (typeof marked !== "undefined" && marked.parse) {
            dicaText.innerHTML = sanitizarHtmlMarkdown(marked.parse(dicaAtual || "Aplique a dica gramatical e tente novamente!"));
        } else {
            dicaText.textContent = dicaAtual || "Aplique a dica gramatical e tente novamente!";
        }
    }

    if (banner) banner.classList.remove("hidden");
    if (resultContainer) resultContainer.classList.add("hidden");

    if (tipoAtiv === "expressao_oral") {
        if (typeof limparAudioOralGravado === "function") {
            limparAudioOralGravado();
        }
        const btnGravar = document.getElementById("btnGravarOral");
        const oralBox = document.getElementById("respostaOralContainer");
        if (btnGravar) {
            btnGravar.scrollIntoView({ behavior: "smooth", block: "center" });
            btnGravar.focus();
        } else if (oralBox) {
            oralBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    } else if (campoAtivo) {
        campoAtivo.focus();
        campoAtivo.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(`Tentativa ${numeroTentativa} iniciada com dica pedagógica ativa. Pronto para sua nova resposta.`);
    }
}

function cancelarTentativa() {
    const eraTentativaAtiva = numeroTentativa > 1;
    numeroTentativa = 1;
    dicaAtual = "";
    const banner = document.getElementById("activeDicaBanner");
    if (banner) banner.classList.add("hidden");
    if (eraTentativaAtiva && typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela("Tentativa anterior cancelada.");
    }
}

function toggleAnaliseProfessor() {
    const box = document.getElementById("analiseProfessorBox");
    const arrow = document.getElementById("arrowIcon");
    if (!box) return;

    const isHidden = box.classList.contains("hidden");
    if (isHidden) {
        box.classList.remove("hidden");
        if (arrow) arrow.style.transform = "rotate(180deg)";
    } else {
        box.classList.add("hidden");
        if (arrow) arrow.style.transform = "rotate(0deg)";
    }
}

function novaSubmissao() {
    cancelarTentativa();
    ocultarFeedbackAnterior();
    if (typeof pararDitadoVozForcado === "function") pararDitadoVozForcado();
    if (typeof pararDitadoAudioPlayer === "function") pararDitadoAudioPlayer();
    if (typeof limparAudioOralGravado === "function") limparAudioOralGravado();
    const textarea = document.getElementById("resposta_aluno");
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const vfInput = document.getElementById("vfCorrecaoInput");
    if (textarea) textarea.value = "";
    if (lacunaInput) lacunaInput.value = "";
    if (vfInput) vfInput.value = "";
    if (typeof gerarNovoDesafioIA === "function") {
        gerarNovoDesafioIA();
    } else {
        const tipo = document.getElementById("tipo_atividade")?.value || "lacunas";
        const pergunta = document.getElementById("pergunta")?.value || "";
        if (typeof aplicarAjustesModalidadeUI === "function") {
            aplicarAjustesModalidadeUI(tipo, pergunta);
        }
    }
    const formCard = document.querySelector(".form-card");
    if (formCard) {
        formCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

/**
 * Funções da Barra de Caracteres Especiais Franceses
 */
let isMaj = false;

function toggleMaj() {
    isMaj = !isMaj;
    const buttons = document.querySelectorAll(".french-char-btn[data-char]");
    buttons.forEach(btn => {
        const lower = btn.getAttribute("data-char");
        const upper = btn.getAttribute("data-char-maj") || lower.toUpperCase();
        btn.textContent = isMaj ? upper : lower;
    });
    const majBtn = document.getElementById("btnToggleMaj");
    if (majBtn) {
        majBtn.classList.toggle("active", isMaj);
        majBtn.textContent = isMaj ? "A/a" : "a/A";
    }
}

function inserirCharBotao(btn) {
    const char = btn.textContent.trim();
    inserirCaractere(char);
}

function inserirCaractere(char) {
    const target = obterCampoRespostaAtivo();
    if (!target) return;

    const start = target.selectionStart !== undefined ? target.selectionStart : target.value.length;
    const end = target.selectionEnd !== undefined ? target.selectionEnd : target.value.length;
    const text = target.value;

    if (char === "« »") {
        target.value = text.substring(0, start) + "«  »" + text.substring(end);
        target.selectionStart = target.selectionEnd = start + 2;
    } else {
        target.value = text.substring(0, start) + char + text.substring(end);
        target.selectionStart = target.selectionEnd = start + char.length;
    }

    target.focus();
    sincronizarCampoAtivo(target);
}

/**
 * Síntese de Voz Nativa em Francês (Web Speech API)
 */
let ultimaRespostaSubmetida = "";

// Carregamento de vozes do sistema
let vozesDisponiveis = [];
function carregarVozes() {
    if ('speechSynthesis' in window) {
        vozesDisponiveis = window.speechSynthesis.getVoices();
    }
}
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = carregarVozes;
    carregarVozes();
}

function falarTextoFrances(texto, btnElement = null) {
    if (typeof window.falarTextoFrancesBase === "function") {
        window.falarTextoFrancesBase(texto, btnElement);
        return;
    }

    if (!('speechSynthesis' in window)) {
        showToast("Seu navegador não possui suporte à síntese de voz nativa.", "aviso");
        return;
    }

    window.speechSynthesis.cancel();
    const textoLimpo = String(texto || "").replace(/[*_#`~>«»\\]/g, " ").replace(/\s+/g, " ").trim();
    if (!textoLimpo) return;
    const utterance = new SpeechSynthesisUtterance(textoLimpo);
    utterance.lang = 'fr-FR';
    utterance.rate = 0.88;
    const vozes = window.speechSynthesis.getVoices();
    const vozFrancesa = vozes.find(v => v.lang === 'fr-FR' || v.lang.startsWith('fr') || v.lang.includes('fr'));
    if (vozFrancesa) utterance.voice = vozFrancesa;
    window.speechSynthesis.speak(utterance);
}

function ouvirTextoDigitado() {
    const target = obterCampoRespostaAtivo();
    const btn = document.getElementById("btnAudioInput");
    if (!target || !target.value.trim()) {
        showToast("Digite ou dite uma frase em francês no campo abaixo para ouvir a pronúncia.", "info");
        if (target) target.focus();
        return;
    }
    falarTextoFrances(target.value, btn);
}

function ouvirRespostaSubmetida() {
    const btn = document.getElementById("btnOuvirResposta");
    const textarea = document.getElementById("resposta_aluno");
    const texto = ultimaRespostaSubmetida || (textarea ? textarea.value : "");
    if (!texto || texto.startsWith("[")) {
        showToast("Nenhuma frase falada/digitada pôde ser transcrita para reprodução.", 'aviso');
        return;
    }
    falarTextoFrances(texto, btn);
}

function ouvirFeedbackFran() {
    const btn = document.getElementById("btnOuvirFeedback");
    const feedbackContent = document.getElementById("feedbackContent");
    if (!feedbackContent || !feedbackContent.textContent.trim()) {
        showToast("Nenhum feedback disponível para reproduzir.", 'erro');
        return;
    }
    falarTextoFrances(feedbackContent.textContent, btn);
}

function ouvirEnunciado() {
    const perguntaInput = document.getElementById("pergunta");
    const btn = document.getElementById("btnAudioPergunta");
    if (!perguntaInput || !perguntaInput.value.trim()) {
        showToast("Nenhum exercício carregado para ouvir.", 'erro');
        return;
    }
    falarTextoFrances(perguntaInput.value, btn);
}

/**
 * Reconhecimento de Voz Nativo em Francês Contínuo e Interativo (Web Speech Recognition API)
 */
let reconhecimentoVoz = null;
let gravandoVoz = false;
let ditadoAtivoPeloUsuario = false;

const ICONE_MIC_PADRAO = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>Falar`;
const ICONE_MIC_PARAR = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style="margin-right: 4px; vertical-align: text-bottom;"><rect x="5" y="5" width="14" height="14" rx="2"></rect></svg><span>Parar Fala</span>`;

function atualizarEstadoBotaoFalar(ativo, textoParcial = "") {
    const btn = document.getElementById("btnDictation");
    const liveBar = document.getElementById("dictationLiveBar");
    const liveText = document.getElementById("dictationLiveText");

    if (btn) {
        btn.classList.toggle("recording", ativo);
        btn.setAttribute("aria-pressed", ativo ? "true" : "false");
        btn.setAttribute("aria-label", ativo ? "Ouvindo em francês — clique para parar de falar" : "Ditar resposta por voz em francês");
        btn.innerHTML = ativo ? ICONE_MIC_PARAR : ICONE_MIC_PADRAO;
    }
    if (liveBar) {
        liveBar.classList.toggle("hidden", !ativo);
    }
    if (liveText && ativo) {
        liveText.textContent = textoParcial
            ? `🎙️ Ouvindo (fr-FR): "${textoParcial}"`
            : '🎙️ Ouvindo em francês (fr-FR)... fale sua frase com calma; clique em "Parar Fala" ao terminar.';
    }
}

function pararDitadoVozForcado() {
    ditadoAtivoPeloUsuario = false;
    gravandoVoz = false;
    if (reconhecimentoVoz) {
        try {
            reconhecimentoVoz.onend = null;
            reconhecimentoVoz.stop();
        } catch (e) {}
    }
    atualizarEstadoBotaoFalar(false);
}

function iniciarDitadoVozSeInativo() {
    if (!ditadoAtivoPeloUsuario) {
        alternarDitadoVoz();
    }
}
window.iniciarDitadoVozSeInativo = iniciarDitadoVozSeInativo;

function _inserirTranscricaoNoCampoAtivo(transcricao) {
    const target = obterCampoRespostaAtivo();
    if (!target || !transcricao) return;

    const start = target.selectionStart !== undefined ? target.selectionStart : target.value.length;
    const end = target.selectionEnd !== undefined ? target.selectionEnd : target.value.length;
    const currentText = target.value;

    const charAntes = start > 0 ? currentText[start - 1] : "";
    const precisaEspacoAntes = start > 0 && !/\s/.test(charAntes) && charAntes !== "'";
    const espacoAntes = precisaEspacoAntes ? " " : "";
    const novoTexto = currentText.substring(0, start) + espacoAntes + transcricao + currentText.substring(end);
    target.value = novoTexto;
    const novaPos = start + espacoAntes.length + transcricao.length;
    try {
        target.selectionStart = target.selectionEnd = novaPos;
    } catch (e) {}
    target.focus();
    sincronizarCampoAtivo(target);
}

function _criarEIniciarSessaoVoz() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    reconhecimentoVoz = new SpeechRecognition();
    reconhecimentoVoz.lang = 'fr-FR';
    reconhecimentoVoz.continuous = true;
    reconhecimentoVoz.interimResults = true;
    reconhecimentoVoz.maxAlternatives = 1;

    reconhecimentoVoz.onstart = () => {
        gravandoVoz = true;
        atualizarEstadoBotaoFalar(true);
        if (typeof anunciarParaLeitorDeTela === "function") {
            anunciarParaLeitorDeTela("Microfone contínuo ativado. Fale em francês e clique em Parar Fala ao terminar.");
        }
    };

    reconhecimentoVoz.onresult = (event) => {
        const tipoAtiv = (document.getElementById("tipo_atividade")?.value || "").trim().toLowerCase();
        let interimTxt = "";
        let finalTxt = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const res = event.results[i];
            const trecho = res[0] ? res[0].transcript : "";
            if (res.isFinal) {
                finalTxt += (finalTxt ? " " : "") + trecho.trim();
            } else {
                interimTxt += trecho;
            }
        }
        if (tipoAtiv === "expressao_oral" || window._oralGravandoAtivo) {
            if (interimTxt.trim()) {
                window._oralTranscricaoParcial = interimTxt.trim();
            }
            if (finalTxt.trim()) {
                window._oralTranscricaoCapturada = [window._oralTranscricaoCapturada || "", finalTxt.trim()]
                    .map(s => String(s || "").trim())
                    .filter(Boolean)
                    .join(" ")
                    .trim();
                window._oralTranscricaoParcial = "";
            }
            if (typeof window.atualizarOralTranscricaoUI === "function") {
                window.atualizarOralTranscricaoUI(window._oralTranscricaoCapturada || "", window._oralTranscricaoParcial || "");
            }
            return;
        }
        if (interimTxt.trim()) {
            atualizarEstadoBotaoFalar(true, interimTxt.trim());
        }
        if (finalTxt.trim()) {
            _inserirTranscricaoNoCampoAtivo(finalTxt.trim());
            atualizarEstadoBotaoFalar(true, "");
            if (typeof anunciarParaLeitorDeTela === "function") {
                anunciarParaLeitorDeTela(`Texto reconhecido: ${finalTxt.trim()}`);
            }
        }
    };

    reconhecimentoVoz.onerror = (event) => {
        console.warn("Aviso no reconhecimento de voz:", event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed' || event.error === 'audio-capture') {
            const gravandoOral = Boolean(window._oralGravandoAtivo);
            pararDitadoVozForcado();
            if (!gravandoOral) {
                showToast("Acesso ao microfone foi negado ou indisponível. Libere a permissão no navegador para usar a fala em francês.", 'erro');
            }
        }
        // Em 'no-speech' ou 'aborted', mantém ditadoAtivoPeloUsuario = true para retomar até o aluno clicar em Parar
    };

    reconhecimentoVoz.onend = () => {
        gravandoVoz = false;
        if (ditadoAtivoPeloUsuario) {
            setTimeout(() => {
                if (ditadoAtivoPeloUsuario) {
                    try {
                        _criarEIniciarSessaoVoz();
                    } catch (e) {
                        pararDitadoVozForcado();
                    }
                }
            }, 140);
        } else {
            atualizarEstadoBotaoFalar(false);
        }
    };

    reconhecimentoVoz.start();
}

function alternarDitadoVoz() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("Seu navegador não possui suporte ao reconhecimento de voz nativo.\nRecomendamos usar Google Chrome, Microsoft Edge ou Safari para ditar em francês.", "aviso");
        return;
    }

    if (ditadoAtivoPeloUsuario) {
        pararDitadoVozForcado();
        return;
    }

    try {
        ditadoAtivoPeloUsuario = true;
        _criarEIniciarSessaoVoz();
    } catch (e) {
        console.error("Falha ao iniciar SpeechRecognition:", e);
        pararDitadoVozForcado();
        showToast("Não foi possível iniciar o microfone no momento.", 'erro');
    }
}

/**
 * Mémento Gramatical FLE (Página Completa /guia-fle)
 */
function abrirMementoGramatical() {
    window.location.href = "/guia-fle";
}

function copiarFeedbackFormativo() {
    const feedbackEl = document.getElementById("feedbackContent");
    const texto = feedbackEl ? feedbackEl.innerText.trim() : "";
    if (!texto) {
        showToast("Nenhum feedback para copiar.", 'erro');
        return;
    }

    navigator.clipboard.writeText(texto).then(() => {
        const btn = document.getElementById("btnCopiarFeedback");
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = `<svg class="line-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: text-bottom;"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>Copiado!</span>`;
            setTimeout(() => { btn.innerHTML = original; }, 2000);
        }
    }).catch(() => {
        showToast("Não foi possível copiar o texto automaticamente.", 'erro');
    });
}

// Inicialização de Nível CEFR e parâmetros de URL na inicialização
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const cefrParam = params.get("cefr");
    if (cefrParam && CEFR_DESCRICOES[cefrParam.toUpperCase()]) {
        selecionarNivelCEFR(cefrParam.toUpperCase());
    } else {
        selecionarNivelCEFR(nivelCEFRSelecionado || "A2");
    }

    if (params.get("gerar") === "1") {
        gerarNovoDesafioIA();
    }
});

async function aceitarReforco(reforcoId) {
    cancelarTentativa();
    ocultarFeedbackAnterior();
    const btn = document.getElementById("btnAceitarReforco");
    const banner = document.getElementById("reforco-banner");
    
    let originalHtml = "";
    if (btn) {
        originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = "<span>Carregando...</span>";
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                          document.querySelector('input[name="csrf_token"]')?.value || "";

        const response = await fetch("/api/aluno/aceitar_reforco", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({ reforco_id: reforcoId })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "sucesso") {
            const temaInput = document.getElementById("tema_aula");
            const perguntaInput = document.getElementById("pergunta");
            const respostaInput = document.getElementById("resposta_aluno");
            const respostaLacunaInput = document.getElementById("respostaLacunaInput");
            const exercicioIdInput = document.getElementById("exercicio_id");

            if (temaInput && data.tema) temaInput.value = data.tema;
            if (perguntaInput && data.exercicio) perguntaInput.value = data.exercicio;
            if (exercicioIdInput && data.exercicio_id) exercicioIdInput.value = data.exercicio_id;

            const tipoAtivInput = document.getElementById("tipo_atividade");
            if (tipoAtivInput) tipoAtivInput.value = "lacunas";

            if (typeof selecionarModalidadeFormato === "function") {
                selecionarModalidadeFormato("lacunas");
            } else if (typeof aplicarAjustesModalidadeUI === "function") {
                aplicarAjustesModalidadeUI("lacunas", data.exercicio || "");
            } else {
                if (respostaInput) respostaInput.value = "";
                if (respostaLacunaInput) {
                    respostaLacunaInput.value = "";
                    respostaLacunaInput.focus();
                } else if (respostaInput) {
                    respostaInput.focus();
                }
            }

            showToast("Missão de reforço carregada! Complete o exercício abaixo.", "sucesso");

            if (data.dica_inicial) {
                dicaAtual = data.dica_inicial;
            }

            // Oculta o banner de reforço pois já foi iniciado
            if (banner) {
                banner.classList.add("hidden");
            }

            // Destaque visual
            const formCard = document.querySelector(".form-card");
            if (formCard) {
                formCard.classList.add("highlight-generator");
                setTimeout(() => formCard.classList.remove("highlight-generator"), 1200);
            }
        } else {
            showToast(data.mensagem || "Erro ao carregar o reforço.", 'erro');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    } catch (err) {
        console.error("Erro ao aceitar reforço:", err);
        showToast("Erro de conexão ao carregar o exercício de reforço.", 'erro');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}


// Sistema Global de Toasts
function showToast(mensagem, tipo = 'sucesso') {
    const tipoNorm = String(tipo || 'sucesso').toLowerCase();
    const isErro = tipoNorm === 'erro' || tipoNorm === 'error';
    const isAviso = tipoNorm === 'aviso' || tipoNorm === 'warning';
    const isInfo = tipoNorm === 'info';

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(mensagem, isErro);
    }
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.setAttribute('role', isErro ? 'alert' : 'status');
    toast.setAttribute('aria-live', isErro ? 'assertive' : 'polite');
    const bg = isErro ? '#ef4444' : (isAviso ? '#f59e0b' : (isInfo ? '#3b82f6' : '#10b981'));
    toast.style.cssText = 'background: ' + bg + '; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 0.95rem; font-weight: 500; opacity: 0; transform: translateY(10px); transition: all 0.3s ease;';
    toast.innerText = mensagem;
    container.appendChild(toast);
    
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
