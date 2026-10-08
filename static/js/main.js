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
}

async function gerarNovoDesafioIA() {
    cancelarTentativa();
    const btn = document.getElementById("btnGerarDesafio");
    const nivel = nivelCEFRSelecionado || "A2";

    let originalHtml = "";
    if (btn) {
        originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span>Criando Desafio (${nivel})...</span>`;
    }

    try {
        const response = await fetch(`/gerar-desafio?nivel_cefr=${encodeURIComponent(nivel)}`);
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        const data = await response.json();

        const temaInput = document.getElementById("tema_aula");
        const perguntaInput = document.getElementById("pergunta");
        const respostaInput = document.getElementById("resposta_aluno");
        const exercicioIdInput = document.getElementById("exercicio_id");

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

        if (data.dica_inicial) {
            dicaAtual = data.dica_inicial;
        }

        // Destaque visual suave no formulário
        const formCard = document.querySelector(".form-card");
        if (formCard) {
            formCard.classList.add("highlight-generator");
            setTimeout(() => formCard.classList.remove("highlight-generator"), 1200);
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

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const tema = document.getElementById("tema_aula").value.trim();
        const pergunta = document.getElementById("pergunta").value.trim();
        const resposta = document.getElementById("resposta_aluno").value.trim();
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

        try {
            // 2. Envio via POST para a rota /avaliar incluindo tentativa e nível CEFR
            const response = await fetch("/avaliar", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
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

    // Converter Markdown para HTML via marked
    if (typeof marked !== "undefined" && marked.parse) {
        feedbackContent.innerHTML = marked.parse(data.feedback_ia || "");
    } else {
        feedbackContent.textContent = data.feedback_ia || "";
    }

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
            dicaText.innerHTML = marked.parse(dicaAtual || "Aplique a dica gramatical e tente novamente!");
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
}

function cancelarTentativa() {
    numeroTentativa = 1;
    dicaAtual = "";
    const banner = document.getElementById("activeDicaBanner");
    if (banner) banner.classList.add("hidden");
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
    if (resultContainer) resultContainer.classList.add("hidden");
    if (textarea) {
        textarea.value = "";
        textarea.focus();
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
    const textarea = document.getElementById("resposta_aluno");
    if (!textarea) return;

    const start = textarea.selectionStart !== undefined ? textarea.selectionStart : textarea.value.length;
    const end = textarea.selectionEnd !== undefined ? textarea.selectionEnd : textarea.value.length;
    const text = textarea.value;

    if (char === "« »") {
        textarea.value = text.substring(0, start) + "«  »" + text.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + 2;
    } else {
        textarea.value = text.substring(0, start) + char + text.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + char.length;
    }

    textarea.focus();
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

    if (!texto || !texto.trim()) {
        showToast("Digite ou selecione uma frase em francês para ouvir a pronúncia.");
        return;
    }

    window.speechSynthesis.cancel();

    // Limpeza de marcações Markdown
    const textoLimpo = texto.replace(/[*_#`~>«»]/g, "").trim();

    const utterance = new SpeechSynthesisUtterance(textoLimpo);
    utterance.lang = 'fr-FR';
    utterance.rate = 0.88; // Cadência pausada para estudantes
    utterance.pitch = 1.0;

    const vozes = window.speechSynthesis.getVoices();
    const vozFrancesa = vozes.find(v => v.lang === 'fr-FR' || v.lang.startsWith('fr'));
    if (vozFrancesa) {
        utterance.voice = vozFrancesa;
    }

    if (btnElement) {
        const textoOriginal = btnElement.innerHTML;
        btnElement.classList.add("speaking");
        btnElement.innerHTML = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> <span>Écoute...</span>`;

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

function ouvirTextoDigitado() {
    const textarea = document.getElementById("resposta_aluno");
    const btn = document.getElementById("btnAudioInput");
    if (!textarea || !textarea.value.trim()) {
        showToast("Digite uma frase em francês no campo abaixo para ouvir a pronúncia.");
        if (textarea) textarea.focus();
        return;
    }
    falarTextoFrances(textarea.value, btn);
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
                btn.innerHTML = `<svg class="line-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 3px; vertical-align: text-bottom;"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="3"></circle></svg> <span>Ouvindo...</span>`;
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
        const response = await fetch("/api/aluno/aceitar_reforco", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ reforco_id: reforcoId })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "sucesso") {
            const temaInput = document.getElementById("tema_aula");
            const perguntaInput = document.getElementById("pergunta");
            const respostaInput = document.getElementById("resposta_aluno");
            const exercicioIdInput = document.getElementById("exercicio_id");

            if (temaInput && data.tema) temaInput.value = data.tema;
            if (perguntaInput && data.exercicio) perguntaInput.value = data.exercicio;
            if (exercicioIdInput && data.exercicio_id) exercicioIdInput.value = data.exercicio_id;
            
            if (respostaInput) {
                respostaInput.value = "";
                respostaInput.focus();
            }

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
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    const bg = tipo === 'erro' ? '#ef4444' : '#10b981';
    toast.style.cssText = \ackground: \; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 0.95rem; font-weight: 500; opacity: 0; transform: translateY(10px); transition: all 0.3s ease;\;
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
