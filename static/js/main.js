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

async function gerarNovoDesafioIA(temaEscolhido = null, tipoEscolhido = null) {
    cancelarTentativa();
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

    // Acessibilidade WCAG: Atalho de Teclado (Ctrl+Enter ou Cmd+Enter) para submeter a resposta
    const respostaInput = document.getElementById("resposta_aluno");
    const lacunaInput = document.getElementById("respostaLacunaInput");
    [respostaInput, lacunaInput].forEach(inp => {
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

        const tema = document.getElementById("tema_aula").value.trim();
        const pergunta = document.getElementById("pergunta").value.trim();
        const lacunaInput = document.getElementById("respostaLacunaInput");
        const respostaElem = document.getElementById("resposta_aluno");
        if (lacunaInput && lacunaInput.offsetParent !== null && lacunaInput.value.trim()) {
            respostaElem.value = lacunaInput.value.trim();
        }
        const resposta = respostaElem ? respostaElem.value.trim() : "";
        const exercicioId = document.getElementById("exercicio_id").value;

        if (!tema || !pergunta || !resposta) {
            showToast("Por favor, preencha todos os campos antes de enviar.");
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
            anunciarParaLeitorDeTela("Enviando sua resposta. O Assistente Fran está analisando sua conjugação, gramática e concordância...");
        }

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                              document.querySelector('input[name="csrf_token"]')?.value || "";

            // 2. Envio via POST para a rota /avaliar incluindo tentativa e nível CEFR
            const response = await fetch("/avaliar", {
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
                    nivel_cefr: nivelCEFRSelecionado
                })
            });

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

    // Exibe o banner fixo com a dica acima do campo de digitação
    const banner = document.getElementById("activeDicaBanner");
    const badge = document.getElementById("badgeTentativa");
    const dicaText = document.getElementById("activeDicaText");
    const textarea = document.getElementById("resposta_aluno");
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

    if (textarea) {
        textarea.focus();
        textarea.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(`Tentativa ${numeroTentativa} iniciada com dica pedagógica ativa. Campo de resposta pronto para sua revisão.`);
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
    const resultContainer = document.getElementById("resultContainer");
    const textarea = document.getElementById("resposta_aluno");
    const lacunaInput = document.getElementById("respostaLacunaInput");
    if (resultContainer) resultContainer.classList.add("hidden");
    if (textarea) textarea.value = "";
    if (lacunaInput) lacunaInput.value = "";
    const tipo = document.getElementById("tipo_atividade")?.value || "lacunas";
    const pergunta = document.getElementById("pergunta")?.value || "";
    if (typeof aplicarAjustesModalidadeUI === "function") {
        aplicarAjustesModalidadeUI(tipo, pergunta);
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
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const vfInput = document.getElementById("vfCorrecaoInput");
    const textarea = document.getElementById("resposta_aluno");
    
    let target = textarea;
    if (lacunaInput && lacunaInput.offsetParent !== null) {
        target = lacunaInput;
    } else if (vfInput && vfInput.offsetParent !== null && (document.activeElement === vfInput || (textarea && textarea.offsetParent === null))) {
        target = vfInput;
    }
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
    if (target === lacunaInput && textarea) {
        textarea.value = target.value;
    } else if (target === vfInput && typeof atualizarRespostaVFPeloInput === "function") {
        atualizarRespostaVFPeloInput();
    }
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
    if (!('speechSynthesis' in window)) {
        showToast("Seu navegador não possui suporte à síntese de voz nativa.");
        return;
    }

    // Se clicou no botão que já está falando, para a reprodução
    if (btnElement && btnElement.classList.contains("speaking")) {
        window.speechSynthesis.cancel();
        btnElement.classList.remove("speaking");
        btnElement.setAttribute("aria-pressed", "false");
        if (btnElement._originalHtmlSalvo) {
            btnElement.innerHTML = btnElement._originalHtmlSalvo;
        }
        return;
    }

    if (!texto || !texto.trim()) {
        showToast("Digite ou selecione uma frase em francês para ouvir a pronúncia.");
        return;
    }

    // Para qualquer áudio em andamento e reseta botões ativos
    window.speechSynthesis.cancel();
    document.querySelectorAll(".btn-audio-pill.speaking, .french-char-btn.speaking, .btn-ouvir-exemplo.speaking").forEach(b => {
        b.classList.remove("speaking");
        b.setAttribute("aria-pressed", "false");
        if (b._originalHtmlSalvo) {
            b.innerHTML = b._originalHtmlSalvo;
        }
    });

    // Limpeza inteligente de Markdown e formatações para leitura pura
    const textoLimpo = texto
        .replace(/[*_#`~>«»\\]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    const utterance = new SpeechSynthesisUtterance(textoLimpo);
    utterance.lang = 'fr-FR';
    utterance.rate = 0.88; // Cadência pedagógica levemente pausada para estudantes de FLE
    utterance.pitch = 1.0;

    const vozes = window.speechSynthesis.getVoices();
    const vozFrancesa = vozes.find(v => v.lang === 'fr-FR' || v.lang.startsWith('fr') || v.lang.includes('fr'));
    if (vozFrancesa) {
        utterance.voice = vozFrancesa;
    }

    if (btnElement) {
        if (!btnElement._originalHtmlSalvo) {
            btnElement._originalHtmlSalvo = btnElement.innerHTML;
        }
        btnElement.classList.add("speaking");
        btnElement.setAttribute("aria-pressed", "true");
        btnElement.innerHTML = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg> <span>Parar</span>`;

        const resetarBtn = () => {
            btnElement.classList.remove("speaking");
            btnElement.setAttribute("aria-pressed", "false");
            if (btnElement._originalHtmlSalvo) {
                btnElement.innerHTML = btnElement._originalHtmlSalvo;
            }
        };

        utterance.onend = resetarBtn;
        utterance.onerror = (e) => {
            console.warn("SpeechSynthesis error:", e);
            resetarBtn();
        };
    }

    // Bugfix comum do Chrome: timeout após cancel() e verificação de paused
    setTimeout(() => {
        try {
            if (window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
            }
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.error("Erro ao reproduzir voz:", e);
        }
    }, 40);
}

function ouvirTextoDigitado() {
    const lacunaInput = document.getElementById("respostaLacunaInput");
    const textarea = document.getElementById("resposta_aluno");
    const target = (lacunaInput && lacunaInput.offsetParent !== null) ? lacunaInput : textarea;
    const btn = document.getElementById("btnAudioInput");
    if (!target || !target.value.trim()) {
        showToast("Digite uma frase em francês no campo abaixo para ouvir a pronúncia.");
        if (target) target.focus();
        return;
    }
    falarTextoFrances(target.value, btn);
}

function ouvirRespostaSubmetida() {
    const btn = document.getElementById("btnOuvirResposta");
    const textarea = document.getElementById("resposta_aluno");
    const texto = ultimaRespostaSubmetida || (textarea ? textarea.value : "");
    if (!texto) {
        showToast("Nenhuma frase submetida para reproduzir.", 'erro');
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
 * Reconhecimento de Voz Nativo em Francês (Web Speech Recognition API)
 */
let reconhecimentoVoz = null;
let gravandoVoz = false;

function alternarDitadoVoz() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("Seu navegador não possui suporte ao reconhecimento de voz nativo.\nRecomendamos usar Google Chrome, Microsoft Edge ou Safari para ditar em francês.");
        return;
    }

    const btn = document.getElementById("btnDictation");
    const textarea = document.getElementById("resposta_aluno");

    if (gravandoVoz && reconhecimentoVoz) {
        reconhecimentoVoz.stop();
        return;
    }

    try {
        reconhecimentoVoz = new SpeechRecognition();
        reconhecimentoVoz.lang = 'fr-FR';
        reconhecimentoVoz.interimResults = false;
        reconhecimentoVoz.maxAlternatives = 1;

        reconhecimentoVoz.onstart = () => {
            gravandoVoz = true;
            if (btn) {
                btn.classList.add("recording");
                btn.setAttribute("aria-label", "Gravando voz em francês... Clique para parar");
                btn.innerHTML = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="3"></circle></svg> <span>Ouvindo...</span>`;
            }
            if (typeof anunciarParaLeitorDeTela === "function") {
                anunciarParaLeitorDeTela("Microfone ativado. Fale em francês...");
            }
        };

        reconhecimentoVoz.onresult = (event) => {
            const transcricao = event.results[0][0].transcript;
            if (textarea && transcricao) {
                const start = textarea.selectionStart !== undefined ? textarea.selectionStart : textarea.value.length;
                const end = textarea.selectionEnd !== undefined ? textarea.selectionEnd : textarea.value.length;
                const currentText = textarea.value;

                const espacoAntes = (start > 0 && currentText[start - 1] !== ' ') ? ' ' : '';
                const novoTexto = currentText.substring(0, start) + espacoAntes + transcricao + currentText.substring(end);
                textarea.value = novoTexto;
                textarea.selectionStart = textarea.selectionEnd = start + espacoAntes.length + transcricao.length;
                textarea.focus();
                if (typeof anunciarParaLeitorDeTela === "function") {
                    anunciarParaLeitorDeTela(`Texto reconhecido: ${transcricao}`);
                }
            }
        };

        reconhecimentoVoz.onerror = (event) => {
            console.warn("Aviso no reconhecimento de voz:", event.error);
            if (event.error === 'not-allowed') {
                showToast("Acesso ao microfone foi negado. Por favor, libere a permissão no navegador para usar o ditado em francês.", 'erro');
            }
        };

        reconhecimentoVoz.onend = () => {
            gravandoVoz = false;
            if (btn) {
                btn.classList.remove("recording");
                btn.setAttribute("aria-label", "Ditar resposta por voz em francês");
                btn.innerHTML = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>Falar`;
            }
        };

        reconhecimentoVoz.start();

    } catch (e) {
        console.error("Falha ao iniciar SpeechRecognition:", e);
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
            
            if (respostaInput) {
                respostaInput.value = "";
            }
            if (respostaLacunaInput) {
                respostaLacunaInput.value = "";
                respostaLacunaInput.focus();
            } else if (respostaInput) {
                respostaInput.focus();
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
    if (typeof anunciarParaLeitorDeTela === "function") {
        anunciarParaLeitorDeTela(mensagem, tipo === 'erro');
    }
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
    toast.setAttribute('aria-live', tipo === 'erro' ? 'assertive' : 'polite');
    const bg = tipo === 'erro' ? '#ef4444' : '#10b981';
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
