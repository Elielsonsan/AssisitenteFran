from guia_fle_data import VERBOS_CONJUGADOS, TEMAS_GUIA_FLE
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from blueprints.extensions import (
    get_db, login_required, login_required_prof, parse_retorno_gemini_frances,
    genai_model, BASE_DIR, GEMINI_MODEL_NAME, gerar_feedback_frances,
    feedback_demonstracao_frances, validar_magic_bytes_imagem,
    BANCO_PEDAGOGICO_TEMAS, mapear_chave_tema, gerar_questoes_pedagogicas_completas,
    eh_questao_valida, sanitizar_questoes_geradas
)
import sqlite3, json, random, datetime, re, os, csv, io

aluno_bp = Blueprint('aluno', __name__)

@aluno_bp.route("/pratica", methods=["GET"])
@login_required
def index():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nivel_cefr FROM alunos WHERE id = ?;", (aluno_id,))
    row = cursor.fetchone()
    nivel_aluno = row["nivel_cefr"] if row and row["nivel_cefr"] else "A2"
    session["nivel_cefr"] = nivel_aluno
        
    # Buscar reforço pendente
    cursor.execute("SELECT id, mensagem_tutor, tema_id FROM reforcos_individuais WHERE aluno_id=? AND LOWER(status)='pendente' ORDER BY id DESC LIMIT 1", (aluno_id,))
    reforco = cursor.fetchone()

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC;")
    lista_temas = [dict(r) for r in cursor.fetchall()]

    # Exercício inicial recomendado automático de acordo com o nível do aluno
    exercicio_inicial = None
    if not reforco:
        cursor.execute("""
            SELECT e.id, e.enunciado, t.nome_tema
            FROM exercicios e
            JOIN temas t ON e.tema_id = t.id
            WHERE e.nivel_exigido = ?
            ORDER BY RANDOM()
            LIMIT 1;
        """, (nivel_aluno,))
        ex_row = cursor.fetchone()
        if not ex_row:
            cursor.execute("""
                SELECT e.id, e.enunciado, t.nome_tema
                FROM exercicios e
                JOIN temas t ON e.tema_id = t.id
                ORDER BY RANDOM()
                LIMIT 1;
            """)
            ex_row = cursor.fetchone()
        if ex_row:
            exercicio_inicial = dict(ex_row)
    
    conn.close()
    return render_template(
        "index.html", 
        active_page="student", 
        aluno_nivel=nivel_aluno, 
        reforco=reforco,
        exercicio_inicial=exercicio_inicial,
        lista_temas=lista_temas
    )

# ===================== ROTAS DE ALUNO (GERAR E AVALIAR) =====================

@aluno_bp.route("/aluno/dashboard", methods=["GET"])
@login_required
def aluno_dashboard():
    aluno_id = session.get("aluno_id")
    aluno_nivel = session.get("nivel_cefr", "A2")
    
    # Níveis para calcular XP/próximo nível
    niveis = ["A1", "A2", "B1", "B2", "C1", "C2"]
    idx = niveis.index(aluno_nivel) if aluno_nivel in niveis else 1
    proximo_nivel = niveis[idx + 1] if idx + 1 < len(niveis) else "Fluência (Concluído)"
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Buscar atividades e acertos do aluno
    cursor.execute("""
        SELECT 
            COUNT(*) as total_atividades,
            SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
            SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
            SUM(CASE WHEN status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros
        FROM submissoes 
        WHERE aluno_id = ?
    """, (aluno_id,))
    stats = cursor.fetchone()
    
    total = stats["total_atividades"] or 0
    acertos = stats["acertos"] or 0
    parciais = stats["parciais"] or 0
    erros = stats["erros"] or 0
    
    # Progresso simulado (para gamificação) = mínimo(100, (acertos * 10 + parciais * 5) % 100)
    progresso_xp = min(100, (acertos * 10 + parciais * 5))
    if progresso_xp > 100: progresso_xp = progresso_xp % 100
    if total == 0: progresso_xp = 0
    
    # Participação semanal calculada a partir das submissões reais dos últimos 5 dias
    hoje = datetime.date.today()
    dias_iso = [(hoje - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(4, -1, -1)]
    cursor.execute("""
        SELECT substr(data_hora, 1, 10) as dia, COUNT(*) as qtd
        FROM submissoes
        WHERE aluno_id = ? AND substr(data_hora, 1, 10) >= ?
        GROUP BY dia
    """, (aluno_id, dias_iso[0]))
    mapa_dias = {r["dia"]: r["qtd"] for r in cursor.fetchall()}
    participacao_semanal = [mapa_dias.get(d, 0) for d in dias_iso]
    if sum(participacao_semanal) == 0 and total > 0:
        # Se o aluno possui histórico anterior aos últimos 5 dias, distribui as últimas submissões
        cursor.execute("""
            SELECT substr(data_hora, 1, 10) as dia, COUNT(*) as qtd
            FROM submissoes
            WHERE aluno_id = ?
            GROUP BY dia
            ORDER BY dia DESC
            LIMIT 5
        """, (aluno_id,))
        ultimos = [r["qtd"] for r in cursor.fetchall()][::-1]
        participacao_semanal = ([0] * (5 - len(ultimos))) + ultimos
    
    # Buscar Missão de Foco pendente (reforço)
    cursor.execute("SELECT * FROM reforcos_individuais WHERE aluno_id = ? AND LOWER(status) = 'pendente' ORDER BY id DESC LIMIT 1", (aluno_id,))
    reforco_row = cursor.fetchone()
    
    reforco = None
    if reforco_row:
        reforco = dict(reforco_row)
        try:
            reforco["exercicios_lista"] = json.loads(reforco["exercicios_json"]) if reforco.get("exercicios_json") else []
        except:
            reforco["exercicios_lista"] = []
    
    # Checar se enviou áudio em alguma avaliação oral
    cursor.execute("SELECT COUNT(*) as total_audio FROM submissoes WHERE aluno_id = ? AND arquivo_audio_path IS NOT NULL AND arquivo_audio_path != ''", (aluno_id,))
    audio_row = cursor.fetchone()
    tem_audio = (audio_row["total_audio"] or 0) > 0

    # Checar se concluiu missão de reforço
    cursor.execute("SELECT COUNT(*) as total_reforco FROM reforcos_individuais WHERE aluno_id = ? AND LOWER(status) = 'concluido'", (aluno_id,))
    ref_row = cursor.fetchone()
    tem_reforco = (ref_row["total_reforco"] or 0) > 0

    # Calcular frequência de presença em aulas ministradas
    cursor.execute("""
        SELECT COUNT(*) as total_aulas,
               SUM(CASE WHEN status IN ('Presente', 'Justificado') THEN 1 ELSE 0 END) as presencas,
               SUM(CASE WHEN status = 'Falta' THEN 1 ELSE 0 END) as faltas
        FROM presencas_aula
        WHERE aluno_id = ?
    """, (aluno_id,))
    freq_row = cursor.fetchone()
    total_aulas_chamada = (freq_row["total_aulas"] or 0) if freq_row else 0
    presencas_count = (freq_row["presencas"] or 0) if freq_row else 0
    faltas_count = (freq_row["faltas"] or 0) if freq_row else 0
    taxa_frequencia = round((presencas_count / total_aulas_chamada) * 100) if total_aulas_chamada > 0 else 100

    # Sistema de Medalhas Gamificadas (Badges FLE)
    badges = [
        {
            "id": "premier_pas",
            "nome": "Premier Pas",
            "icone": "star",
            "descricao": "Concluiu sua primeira atividade de francês.",
            "desbloqueado": total >= 1
        },
        {
            "id": "tir_precis",
            "nome": "Tir Précis",
            "icone": "target",
            "descricao": "Alcançou 5 acertos perfeitos nas atividades.",
            "desbloqueado": acertos >= 5
        },
        {
            "id": "erudit_fle",
            "nome": "Érudit du FLE",
            "icone": "book",
            "descricao": "Praticou pelo menos 10 exercícios na plataforma.",
            "desbloqueado": total >= 10
        },
        {
            "id": "voix_paris",
            "nome": "Voix de Paris",
            "icone": "mic",
            "descricao": "Gravou e enviou áudio em uma prova oral.",
            "desbloqueado": tem_audio
        },
        {
            "id": "niveau_avance",
            "nome": "Niveau Avancé",
            "icone": "award",
            "descricao": "Alcançou o nível intermediário B1 ou superior.",
            "desbloqueado": aluno_nivel in ["B1", "B2", "C1", "C2"]
        },
        {
            "id": "perseverance",
            "nome": "Persévérance",
            "icone": "shield",
            "descricao": "Concluiu uma missão de reforço guiada pelo tutor.",
            "desbloqueado": tem_reforco
        }
    ]
    
    conn.close()
    
    return render_template(
        "aluno_dashboard.html",
        active_page="aluno_dashboard",
        aluno_nivel=aluno_nivel,
        proximo_nivel=proximo_nivel,
        progresso_xp=progresso_xp,
        total_atividades=total,
        acertos=acertos,
        parciais=parciais,
        erros=erros,
        participacao_semanal=participacao_semanal,
        reforco=reforco,
        badges=badges,
        taxa_frequencia=taxa_frequencia,
        total_aulas_chamada=total_aulas_chamada,
        presencas_count=presencas_count,
        faltas_count=faltas_count
    )

@aluno_bp.route("/api/responder_missao", methods=["POST"])
@login_required
def api_responder_missao():
    aluno_id = session.get("aluno_id")
    nivel_aluno = session.get("nivel_cefr", "A2")
    dados = request.get_json(silent=True) if request.is_json else request.form
    reforco_id = dados.get("reforco_id")
    resposta = (dados.get("resposta") or "").strip()
    
    if not reforco_id or not resposta:
        return jsonify({"status": "erro", "mensagem": "Resposta em branco."}), 400
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.tema_id, r.exercicios_json, t.nome_tema
            FROM reforcos_individuais r
            LEFT JOIN temas t ON r.tema_id = t.id
            WHERE r.id = ? AND r.aluno_id = ?
        """, (reforco_id, aluno_id))
        ref_row = cursor.fetchone()
        if not ref_row:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Missão não encontrada ou não autorizada."}), 403

        tema_id = ref_row["tema_id"]
        nome_tema = ref_row["nome_tema"] or "Reforço Gramatical"
        try:
            ex_lista = json.loads(ref_row["exercicios_json"]) if ref_row["exercicios_json"] else []
        except Exception:
            ex_lista = []
        enunciado_ref = ex_lista[0] if ex_lista else f"Exercício de reforço sobre {nome_tema}"

        # Garante um exercicio_id associado ao tema para registrar a submissão e contabilizar XP
        cursor.execute("SELECT id, enunciado FROM exercicios WHERE tema_id = ? ORDER BY id DESC LIMIT 1", (tema_id,))
        ex_db = cursor.fetchone()
        if ex_db:
            exercicio_id = ex_db["id"]
        else:
            cursor.execute(
                "INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?)",
                (tema_id, nivel_aluno, enunciado_ref)
            )
            exercicio_id = cursor.lastrowid

        status_resposta, analise_prof, feedback_ia = gerar_feedback_frances(
            nome_tema, enunciado_ref, resposta, tentativa=1, nivel_cefr=nivel_aluno
        )
        data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO submissoes (aluno_id, exercicio_id, resposta_aluno, feedback_ia, analise_professor, status_resposta, tentativa, data_hora)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (aluno_id, exercicio_id, resposta, feedback_ia, analise_prof, status_resposta, data_hora))

        cursor.execute("UPDATE reforcos_individuais SET status = 'Concluido' WHERE id = ? AND aluno_id = ?", (reforco_id, aluno_id))
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": "Missão concluída com sucesso! Medalha Persévérance desbloqueada.",
            "status_resposta": status_resposta,
            "feedback_ia": feedback_ia
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@aluno_bp.route("/gerar-desafio", methods=["GET", "POST"])
@login_required
def rota_gerar_desafio():
    # Permite parâmetro na query ou da sessão do aluno
    nivel = request.args.get("nivel_cefr") or session.get("nivel_cefr", "A2")
    nivel = (nivel or "A2").strip().upper()
    tema_filtro = (request.args.get("tema") or "").strip()
    tipo_atividade = (request.args.get("tipo_atividade") or "lacunas").strip().lower()
    excluir_id = request.args.get("excluir_id")

    conn = get_db()
    cursor = conn.cursor()
    row = None

    # Usa o banco diretamente apenas quando a modalidade for "lacunas" (padrão) e não houver pedido de outra modalidade específica
    if tipo_atividade == "lacunas":
        if tema_filtro:
            if excluir_id:
                cursor.execute("""
                    SELECT e.id as exercicio_id, t.nome_tema as tema, e.enunciado as exercicio, e.nivel_exigido as nivel_cefr
                    FROM exercicios e
                    JOIN temas t ON e.tema_id = t.id
                    WHERE LOWER(t.nome_tema) = LOWER(?) AND e.id != ?
                    ORDER BY CASE WHEN e.nivel_exigido = ? THEN 0 ELSE 1 END, RANDOM()
                    LIMIT 1;
                """, (tema_filtro, excluir_id, nivel))
                row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    SELECT e.id as exercicio_id, t.nome_tema as tema, e.enunciado as exercicio, e.nivel_exigido as nivel_cefr
                    FROM exercicios e
                    JOIN temas t ON e.tema_id = t.id
                    WHERE LOWER(t.nome_tema) = LOWER(?)
                    ORDER BY CASE WHEN e.nivel_exigido = ? THEN 0 ELSE 1 END, RANDOM()
                    LIMIT 1;
                """, (tema_filtro, nivel))
                row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT e.id as exercicio_id, t.nome_tema as tema, e.enunciado as exercicio, e.nivel_exigido as nivel_cefr
                FROM exercicios e
                JOIN temas t ON e.tema_id = t.id
                WHERE e.nivel_exigido = ?
                ORDER BY RANDOM() LIMIT 1;
            """, (nivel,))
            row = cursor.fetchone()

        if row:
            conn.close()
            opcoes = []
            if tipo_atividade == "multipla_escolha" and row["exercicio"]:
                for line in row["exercicio"].split("\n"):
                    m = re.match(r"^\s*([A-D][\)\.\-]\s*.+)$", line.strip())
                    if m:
                        opcoes.append(m.group(1))
            return jsonify({
                "status": "sucesso",
                "exercicio_id": row["exercicio_id"],
                "tema": row["tema"],
                "exercicio": row["exercicio"],
                "opcoes": opcoes,
                "nivel_cefr": row["nivel_cefr"],
                "tipo_atividade": tipo_atividade,
                "dica_inicial": "Preste atenção à gramática e à concordância."
            })

    # Instruções específicas por modalidade de atividade
    instrucoes_modalidade = {
        "lacunas": "no formato 'Completar Sentença (Preenchimento de Lacunas)', apresentando uma frase em francês com '___' e o verbo/termo base entre parênteses",
        "vf": "no formato 'Julgamento Gramatical (Verdadeiro ou Falso)', apresentando uma frase em francês e pedindo que o aluno indique Vrai (Verdadeiro) ou Faux (Falso) e corrija caso seja Faux",
        "multipla_escolha": "no formato 'Múltipla Escolha', apresentando uma frase com lacuna em francês seguida de 4 alternativas em linhas separadas (A) ..., B) ..., C) ..., D) ...)",
        "ditado": "no formato 'Compreensão Auditiva & Transcrição (Dictée)', retornando APENAS uma frase autêntica e completa em francês (sem instruções em português no enunciado) para o aluno ouvir o áudio e transcrever",
        "expressao_oral": "no formato 'Expressão Oral & Pronúncia', apresentando uma frase ou pergunta curta em francês para o aluno pronunciar em voz alta no microfone",
        "producao_escrita": "no formato 'Produção Escrita & Tradução', propondo uma frase em português para traduzir ao francês ou uma situação curta para redigir em francês"
    }
    desc_mod = instrucoes_modalidade.get(tipo_atividade, instrucoes_modalidade["lacunas"])

    exercicio_gerado = None
    tema_nome = tema_filtro if tema_filtro else "Le Passé Composé: Être vs Avoir"
    dica_inicial = "Observe atentamente a estrutura gramatical e a concordância."

    if genai_model:
        try:
            foco_tema = f" sobre o tema '{tema_nome}'" if tema_nome else ""
            prompt_desafio = f"""Você é um professor especialista em Francês Língua Estrangeira (FLE) para brasileiros.
Gere 1 exercício inédito e objetivo adequado ao nível CEFR {nivel}{foco_tema}, {desc_mod}.
Retorne EXATAMENTE um JSON válido com as chaves:
- "tema": "{tema_nome}"
- "enunciado": (o texto do exercício conforme a modalidade solicitada)
- "dica": (uma dica pedagógica curta sobre a regra)"""

            resp = genai_model.generate_content(prompt_desafio)
            texto_limpo = re.sub(r"^```json\s*", "", resp.text.strip(), flags=re.IGNORECASE)
            texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
            texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
            dados = json.loads(texto_limpo)
            if "enunciado" in dados:
                tema_nome = tema_filtro if tema_filtro else dados.get("tema", tema_nome).strip()
                exercicio_gerado = dados["enunciado"].strip()
                dica_inicial = dados.get("dica", dica_inicial)
        except Exception as e:
            print(f"[!] Erro ao gerar desafio com IA ({tipo_atividade} / {nivel}): {e}")

    # Gerador estruturado por modalidade e tema caso a IA não esteja ativa
    if not exercicio_gerado:
        frases_base_tema = {
            "Le Passé Composé: Être vs Avoir": {
                "correta": "Hier soir, Marie et Sophie sont arrivées en avance au théâtre.",
                "incorreta": "Hier soir, Marie et Sophie ont arrivé en avance au théâtre.",
                "lacuna": "Complétez au passé composé : « Hier soir, Marie et Sophie ___ (arriver) en avance au théâtre. »",
                "mc": "Escolha a alternativa que preenche corretamente a lacuna:\n« Hier soir, Marie et Sophie ___ en avance au théâtre. »\nA) ont arrivé\nB) sont arrivées\nC) êtes arrivées\nD) sont arrivé",
                "trad": "Traduza para o francês aplicando o Passé Composé: « Ontem à noite, nós fomos ao cinema juntos. »"
            },
            "La Maison d'Être": {
                "correta": "Elle est partie très tôt ce matin pour prendre le train à Lyon.",
                "incorreta": "Elle a parti très tôt ce matin pour prendre le train à Lyon.",
                "lacuna": "Complétez avec l'auxiliaire Être au passé composé : « Elle ___ (partir) très tôt ce matin pour Lyon. »",
                "mc": "Assinale a forma correta no Passé Composé (Maison d'Être):\n« Mes sœurs ___ nées au Brésil. »\nA) ont\nB) sont\nC) sommes\nD) êtes",
                "trad": "Traduza para o francês: « Ela subiu pelas escadas e entrou na sala. »"
            },
            "L'Imparfait": {
                "correta": "Quand j'étais enfant, nous allions tous les étés à la plage en Bretagne.",
                "incorreta": "Quand j'étais enfant, nous allons tous les étés à la plage en Bretagne.",
                "lacuna": "Conjuguez le verbe à l'imparfait : « Quand j'étais enfant, nous ___ (aller) tous les étés en Bretagne. »",
                "mc": "Escolha a conjugação correta no Imparfait:\n« Autrefois, ils ___ dans un petit village calme. »\nA) habitent\nB) habitaient\nC) ont habité\nD) habiteront",
                "trad": "Traduza para o francês usando o Imparfait: « Quando eu morava em Paris, tomava café na padaria todas as manhãs. »"
            },
            "Les Articles Définis, Indéfinis et Partitifs": {
                "correta": "Au petit-déjeuner, je prends du pain complet, de la confiture et de l'eau.",
                "incorreta": "Je ne bois pas du café le soir, je préfère de la tisane.",
                "lacuna": "Complétez avec l'article partitif convenable (du, de la, de l', de) : « Le matin, je prends ___ café, mais je ne mets pas ___ sucre. »",
                "mc": "Assinale a alternativa correta na frase negativa:\n« Non merci, je ne prends pas ___ sucre dans mon thé. »\nA) du\nB) de la\nC) de\nD) des",
                "trad": "Traduza para o francês: « Eu gosto de queijo, mas hoje não comprei queijo. »"
            },
            "Les Pronoms Adverbiaux (Y et EN)": {
                "correta": "Tu vas à la bibliothèque cet après-midi ? Oui, j'y vais à quatorze heures.",
                "incorreta": "Tu manges des fruits le matin ? Oui, j'y mange tous les jours.",
                "lacuna": "Complétez avec le pronom Y ou EN : « — Tu prends du café le matin ? — Oui, j'___ prends une tasse. »",
                "mc": "Qual pronome substitui corretamente o termo sublinhado em « Je vais [à Lyon] demain » ?\nA) J'en vais demain.\nB) J'y vais demain.\nC) Je le vais demain.\nD) Je lui vais demain.",
                "trad": "Responda em francês usando Y ou EN: « — Combien de frères as-tu ? (Responda: Tenho dois) »"
            },
            "Les Pronoms Personnels (COD et COI)": {
                "correta": "Pierre est l'anniversaire de ma mère ; je lui ai téléphoné pour la féliciter.",
                "incorreta": "Je téléphone à mes parents tous les dimanches : je les téléphone.",
                "lacuna": "Complétez avec le pronom COI (lui ou leur) : « Mes parents habitent loin, mais je ___ écris chaque semaine. »",
                "mc": "Escolha o pronome correto para substituir « à Sophie » em « Je parle à Sophie »:\nA) Je la parle.\nB) Je lui parle.\nC) Je leur parle.\nD) J'y parle.",
                "trad": "Traduza usando pronomes complemento: « Eu o vejo todos os dias e lhe falo em francês. »"
            },
            "Le Subjonctif Présent et la Nécessité": {
                "correta": "Il faut absolument que vous fassiez attention aux détails de ce contrat.",
                "incorreta": "Il est nécessaire que tu prends le train de huit heures.",
                "lacuna": "Mettez le verbe au subjonctif présent : « Il faut absolument que vous ___ (faire) attention aux détails. »",
                "mc": "Qual forma preenche corretamente a frase no Subjonctif Présent?\n« Mon professeur exige que nous ___ à l'heure. »\nA) sommes\nB) soyons\nC) soient\nD) serons",
                "trad": "Traduza usando o Subjonctif: « É preciso que você venha conosco amanhã. »"
            }
        }
        base = frases_base_tema.get(tema_nome, {
            "correta": f"Aujourd'hui, nous pratiquons le français avec enthousiasme sur le thème « {tema_nome} ».",
            "incorreta": f"Hier, nous avons aller au cours de français pour étudier « {tema_nome} ».",
            "lacuna": f"Complétez la phrase selon la règle de « {tema_nome} » : « Nous ___ (étudier) attentivement les structures du français. »",
            "mc": f"Escolha a opção gramaticalmente correta dentro do tema « {tema_nome} »:\n« Les étudiants ___ leurs exercices de français avec soin. »\nA) finissent\nB) finissons\nC) finit\nD) finir",
            "trad": f"Elabore ou traduza uma frase em francês aplicando o tema « {tema_nome} » : « Nós aprendemos francês todos os dias para viajar à França. »"
        })

        if tipo_atividade == "vf":
            usar_correta = random.choice([True, False])
            frase_vf = base["correta"] if usar_correta else base["incorreta"]
            exercicio_gerado = (
                f"Julgamento Gramatical (Vrai ou Faux) — Analise a sentença abaixo segundo o tema « {tema_nome} ». "
                f"Indique se ela é Vrai (Verdadeira) ou Faux (Falsa) e, caso seja Faux, reescreva-a corrigida:\n\n"
                f"« {frase_vf} »"
            )
        elif tipo_atividade == "multipla_escolha":
            exercicio_gerado = base["mc"]
        elif tipo_atividade == "ditado":
            exercicio_gerado = base["correta"]
        elif tipo_atividade == "expressao_oral":
            exercicio_gerado = (
                f"Pronuncie em voz alta utilizando o botão 'Falar' (microfone) a seguinte frase em francês:\n\n"
                f"« {base['correta']} »"
            )
        elif tipo_atividade == "producao_escrita":
            exercicio_gerado = base["trad"]
        else:
            exercicio_gerado = base["lacuna"]

    # Salva o novo tema (se não existir) e o exercício no banco para que /avaliar funcione perfeitamente
    try:
        cursor.execute("SELECT id FROM temas WHERE nome_tema = ?", (tema_nome,))
        tema_row = cursor.fetchone()
        if tema_row:
            tema_id = tema_row["id"]
        else:
            cursor.execute("INSERT INTO temas (nome_tema) VALUES (?)", (tema_nome,))
            tema_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO exercicios (tema_id, nivel_exigido, enunciado)
            VALUES (?, ?, ?)
        """, (tema_id, nivel, exercicio_gerado))
        conn.commit()
        novo_exercicio_id = cursor.lastrowid
        opcoes = []
        if tipo_atividade == "multipla_escolha" and exercicio_gerado:
            for line in exercicio_gerado.split("\n"):
                m = re.match(r"^\s*([A-D][\)\.\-]\s*.+)$", line.strip())
                if m:
                    opcoes.append(m.group(1))

        return jsonify({
            "status": "sucesso",
            "exercicio_id": novo_exercicio_id,
            "tema": tema_nome,
            "exercicio": exercicio_gerado,
            "opcoes": opcoes,
            "nivel_cefr": nivel,
            "tipo_atividade": tipo_atividade,
            "dica_inicial": dica_inicial
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao registrar exercício: {e}"}), 500

@aluno_bp.route("/api/aluno/aceitar_reforco", methods=["POST"])
@login_required
def aceitar_reforco():
    aluno_id = session.get("aluno_id")
    nivel_aluno = session.get("nivel_cefr", "A2")
    dados = request.get_json(silent=True) if request.is_json else request.form
    reforco_id = dados.get("reforco_id")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.tema_id, r.exercicios_json, t.nome_tema
        FROM reforcos_individuais r
        LEFT JOIN temas t ON r.tema_id = t.id
        WHERE r.id=? AND r.aluno_id=?
    """, (reforco_id, aluno_id))
    row = cursor.fetchone()
    
    if row:
        tema_id = row["tema_id"]
        nome_tema = row["nome_tema"] or "Le Passé Composé: Être vs Avoir"
        
        # Obter exercício do tema ou criar um automaticamente se ainda não houver
        cursor.execute("""
            SELECT e.id as exercicio_id, t.nome_tema as tema, e.enunciado as exercicio, e.nivel_exigido as nivel_cefr
            FROM exercicios e
            JOIN temas t ON e.tema_id = t.id
            WHERE e.tema_id = ?
            ORDER BY RANDOM() LIMIT 1;
        """, (tema_id,))
        ex_row = cursor.fetchone()

        if not ex_row:
            questoes_ped = gerar_questoes_pedagogicas_completas(nome_tema, nivel_aluno, "exercicio", 1)
            enunciado_novo = questoes_ped[0]["enunciado"] if questoes_ped else f"Complétez selon la règle de « {nome_tema} » : « Nous ___ (étudier) le français. »"
            cursor.execute(
                "INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?)",
                (tema_id, nivel_aluno, enunciado_novo)
            )
            novo_ex_id = cursor.lastrowid
            ex_dict = {
                "exercicio_id": novo_ex_id,
                "tema": nome_tema,
                "exercicio": enunciado_novo,
                "nivel_cefr": nivel_aluno
            }
        else:
            ex_dict = dict(ex_row)

        cursor.execute("UPDATE reforcos_individuais SET status='Concluido' WHERE id=? AND aluno_id=?", (reforco_id, aluno_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "sucesso",
            "exercicio_id": ex_dict["exercicio_id"],
            "tema": ex_dict["tema"],
            "exercicio": ex_dict["exercicio"],
            "nivel_cefr": ex_dict["nivel_cefr"],
            "dica_inicial": "Foco neste tema! O professor recomendou este reforço para você."
        })
        
    conn.close()
    return jsonify({"status": "erro", "mensagem": "Não foi possível carregar o exercício de reforço."}), 404

@aluno_bp.route("/avaliar", methods=["POST"])
@login_required
def avaliar():
    aluno_id = session.get("aluno_id")
    dados = request.get_json() if request.is_json else request.form
    
    exercicio_id = dados.get("exercicio_id")
    resposta = dados.get("resposta_aluno", "").strip()
    tentativa = int(dados.get("tentativa", 1))
    dica_anterior = (dados.get("dica_anterior") or "").strip()

    if not exercicio_id or not resposta:
        return jsonify({"status": "erro", "mensagem": "Preencha todos os campos."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.enunciado, t.nome_tema, e.nivel_exigido
        FROM exercicios e JOIN temas t ON e.tema_id = t.id
        WHERE e.id = ?
    """, (exercicio_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Exercício inválido."}), 400
    
    tema = row["nome_tema"]
    exercicio = row["enunciado"]
    nivel_cefr = row["nivel_exigido"]

    status_resposta, analise_prof, feedback_ia = gerar_feedback_frances(
        tema, exercicio, resposta, tentativa=tentativa, dica_anterior=dica_anterior, nivel_cefr=nivel_cefr
    )
    
    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO submissoes (aluno_id, exercicio_id, resposta_aluno, feedback_ia, analise_professor, status_resposta, tentativa, data_hora)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (aluno_id, exercicio_id, resposta, feedback_ia, analise_prof, status_resposta, tentativa, data_hora))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "sucesso",
        "id": novo_id,
        "tema": tema,
        "exercicio": exercicio,
        "resposta_aluno": resposta,
        "status_resposta": status_resposta,
        "feedback_ia": feedback_ia,
        "analise_professor": analise_prof,
        "tentativa": tentativa
    })

# ===================== DASHBOARD DO PROFESSOR =====================

@aluno_bp.route("/aluno/atividades", methods=["GET"])
@login_required
def aluno_atividades():
    aluno_id = session.get("aluno_id")
    turma_id = session.get("turma_id")
    conn = get_db()
    cursor = conn.cursor()
    
    if not turma_id:
        cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
        al_row = cursor.fetchone()
        turma_id = al_row["turma_id"] if al_row else 1
        session["turma_id"] = turma_id

    # Busca avaliações destinadas à turma do aluno com status de conclusão
    cursor.execute("""
        SELECT a.id, a.titulo, a.tipo, a.data_limite,
               (SELECT COUNT(*) FROM prova_questoes pq WHERE pq.avaliacao_id = a.id) as total_questoes,
               (SELECT COUNT(DISTINCT s.prova_questao_id) FROM submissoes s 
                JOIN prova_questoes pq ON s.prova_questao_id = pq.id 
                WHERE s.aluno_id = ? AND pq.avaliacao_id = a.id) as questoes_respondidas,
               (SELECT ROUND(AVG(s.nota_professor), 1) FROM submissoes s 
                JOIN prova_questoes pq ON s.prova_questao_id = pq.id 
                WHERE s.aluno_id = ? AND pq.avaliacao_id = a.id AND s.nota_professor IS NOT NULL) as media_nota
        FROM avaliacoes a
        WHERE a.turma_id = ?
        ORDER BY a.id DESC
    """, (aluno_id, aluno_id, turma_id))
    avaliacoes = [dict(row) for row in cursor.fetchall()]

    avaliacoes_pendentes = []
    avaliacoes_concluidas = []
    for a in avaliacoes:
        total = a.get("total_questoes") or 0
        resp = a.get("questoes_respondidas") or 0
        conc = (resp is not None and resp > 0 and resp >= total and total > 0)
        a["concluida"] = conc
        if conc:
            avaliacoes_concluidas.append(a)
        else:
            avaliacoes_pendentes.append(a)

    # Histórico recente de exercícios e feedbacks para consulta do aluno
    cursor.execute("""
        SELECT s.id, s.resposta_aluno, s.status_resposta, s.feedback_ia, s.analise_professor, s.data_hora,
               COALESCE(e.enunciado, pq.enunciado) as enunciado,
               COALESCE(te.nome_tema, 'Exercício de Avaliação') as tema
        FROM submissoes s
        LEFT JOIN exercicios e ON s.exercicio_id = e.id
        LEFT JOIN temas te ON e.tema_id = te.id
        LEFT JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        WHERE s.aluno_id = ?
        ORDER BY s.id DESC
        LIMIT 10;
    """, (aluno_id,))
    historico = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return render_template(
        "aluno_atividades.html",
        avaliacoes=avaliacoes,
        avaliacoes_pendentes=avaliacoes_pendentes,
        avaliacoes_concluidas=avaliacoes_concluidas,
        historico=historico,
        active_page="aluno_atividades"
    )

@aluno_bp.route("/aluno/perfil", methods=["GET"])
@login_required
def aluno_perfil():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.nome_completo as nome, a.matricula,
               a.nivel_cefr, a.turno, a.email, a.telefone, a.data_nascimento,
               a.endereco, a.foto_url, t.nome as turma_nome
        FROM alunos a
        LEFT JOIN turmas t ON a.turma_id = t.id
        WHERE a.id = ?
    """, (aluno_id,))
    aluno_row = cursor.fetchone()
    aluno = dict(aluno_row) if aluno_row else {}

    if aluno.get("foto_url"):
        session["foto_url"] = aluno["foto_url"]
    if aluno.get("nome_completo"):
        session["aluno_nome"] = aluno["nome_completo"]

    cursor.execute("""
        SELECT m.id, m.assunto, m.corpo, m.data_envio, m.lida_status, p.nome_completo as remetente_nome
        FROM mensagens_inbox m
        LEFT JOIN professores p ON m.remetente_id = p.id
        WHERE m.destinatario_id = ?
        ORDER BY m.id DESC
    """, (aluno_id,))
    mensagens = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM submissoes WHERE aluno_id = ?", (aluno_id,))
    sub_row = cursor.fetchone()
    total_submissoes = sub_row["total"] if sub_row else 0

    conn.close()
    return render_template("aluno_perfil.html", aluno=aluno, mensagens=mensagens, total_submissoes=total_submissoes, active_page="aluno_perfil")


@aluno_bp.route("/api/aluno/atualizar_perfil", methods=["POST"])
@login_required
def api_atualizar_perfil():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url FROM alunos WHERE id = ?", (aluno_id,))
    atual = cursor.fetchone()
    if not atual:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Aluno não encontrado."}), 404

    dados = request.get_json(silent=True) if request.is_json else request.form

    nome_completo = (dados.get("nome_completo") or atual["nome_completo"] or "").strip()
    if not nome_completo:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "O nome completo não pode ficar em branco."}), 400

    email = (dados.get("email") if "email" in dados else (atual["email"] or "")).strip()
    telefone = (dados.get("telefone") if "telefone" in dados else (atual["telefone"] or "")).strip()
    data_nascimento = (dados.get("data_nascimento") if "data_nascimento" in dados else (atual["data_nascimento"] or "")).strip()
    endereco = (dados.get("endereco") if "endereco" in dados else (atual["endereco"] or "")).strip()
    turno = (dados.get("turno") if "turno" in dados else (atual["turno"] or "Matutino")).strip() or "Matutino"
    nova_senha = (dados.get("nova_senha") or "").strip()
    remover_foto = str(dados.get("remover_foto") or "0").strip() == "1"

    foto_url = atual["foto_url"]
    if remover_foto:
        foto_url = None

    arquivo_foto = request.files.get("foto_perfil")
    if arquivo_foto and arquivo_foto.filename:
        ext = os.path.splitext(arquivo_foto.filename)[1].lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif"] or not validar_magic_bytes_imagem(arquivo_foto, ext):
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Formato ou conteúdo de imagem inválido. Use PNG, JPG, WEBP ou GIF válidos."}), 400

        upload_dir = os.path.join(BASE_DIR, "static", "uploads", "perfis")
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(f"aluno_{aluno_id}_{int(datetime.datetime.now().timestamp())}{ext}")
        filepath = os.path.join(upload_dir, filename)
        arquivo_foto.save(filepath)
        foto_url = f"/static/uploads/perfis/{filename}"

    try:
        if nova_senha:
            if len(nova_senha) < 4:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "A nova senha deve ter pelo menos 4 caracteres."}), 400
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute("""
                UPDATE alunos
                SET nome_completo = ?, email = ?, telefone = ?, data_nascimento = ?,
                    endereco = ?, turno = ?, foto_url = ?, senha_hash = ?
                WHERE id = ?
            """, (nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url, senha_hash, aluno_id))
        else:
            cursor.execute("""
                UPDATE alunos
                SET nome_completo = ?, email = ?, telefone = ?, data_nascimento = ?,
                    endereco = ?, turno = ?, foto_url = ?
                WHERE id = ?
            """, (nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url, aluno_id))

        conn.commit()
        conn.close()

        session["aluno_nome"] = nome_completo
        session["foto_url"] = foto_url

        return jsonify({
            "status": "sucesso",
            "mensagem": "Dados do perfil atualizados com sucesso!",
            "nome": nome_completo,
            "foto_url": foto_url
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao atualizar perfil: {e}"}), 500

# ===================== MÓDULO DE PROVAS MULTIMODAIS =====================
@aluno_bp.route("/aluno/prova/<int:avaliacao_id>", methods=["GET"])
@login_required
def aluno_prova(avaliacao_id):
    aluno_id = session.get("aluno_id")
    turma_id = session.get("turma_id")
    conn = get_db()
    cursor = conn.cursor()

    if not turma_id:
        cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
        al_row = cursor.fetchone()
        turma_id = al_row["turma_id"] if al_row else None
        session["turma_id"] = turma_id

    cursor.execute("SELECT * FROM avaliacoes WHERE id = ?", (avaliacao_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash("Avaliação não encontrada.", "erro")
        return redirect(url_for("aluno.aluno_atividades")), 404

    avaliacao = dict(row)
    if avaliacao.get("turma_id") and turma_id and int(avaliacao["turma_id"]) != int(turma_id):
        conn.close()
        flash("Acesso não autorizado para esta avaliação.", "erro")
        return redirect(url_for("aluno.aluno_atividades")), 403

    cursor.execute("SELECT * FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_id,))
    questoes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return render_template("aluno_prova.html", avaliacao=avaliacao, questoes=questoes, active_page="aluno_atividades")

@aluno_bp.route("/api/enviar_prova", methods=["POST"])
@login_required
def api_enviar_prova():
    aluno_id = session.get("aluno_id")
    turma_id = session.get("turma_id")
    avaliacao_id = request.form.get("avaliacao_id")

    if not avaliacao_id:
        return jsonify({"status": "erro", "mensagem": "Avaliação não informada."}), 400
    
    conn = get_db()
    cursor = conn.cursor()

    if not turma_id:
        cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
        al_row = cursor.fetchone()
        turma_id = al_row["turma_id"] if al_row else None

    cursor.execute("SELECT id, turma_id, titulo FROM avaliacoes WHERE id = ?", (avaliacao_id,))
    av_row = cursor.fetchone()
    if not av_row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404
    if av_row["turma_id"] and turma_id and int(av_row["turma_id"]) != int(turma_id):
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Acesso não autorizado para enviar esta avaliação."}), 403
    
    # Iterar sobre todas as chaves do FormData que começam com "questao_"
    for key in request.form.keys():
        if key.startswith("questao_"):
            q_id = key.split("_")[1]
            resposta_texto = request.form.get(key, "").strip()
            if not resposta_texto:
                continue

            # Busca detalhes da questão validando se pertence à avaliação
            cursor.execute("""
                SELECT pq.enunciado, pq.texto_referencia, pq.tipo_questao, a.titulo
                FROM prova_questoes pq
                JOIN avaliacoes a ON pq.avaliacao_id = a.id
                WHERE pq.id = ? AND pq.avaliacao_id = ?
            """, (q_id, avaliacao_id))
            q_row = cursor.fetchone()
            if not q_row:
                continue

            tema_q = q_row["titulo"] if q_row else "Avaliação"
            tipo_q = q_row["tipo_questao"] if q_row else "questão"
            enunciado_q = q_row["enunciado"] if q_row else "Exercício"
            ref_q = q_row["texto_referencia"] if q_row and q_row["texto_referencia"] else ""

            exercicio_contexto = f"[{tipo_q.upper()}] {enunciado_q}"
            if ref_q:
                exercicio_contexto += f" (Referência: '{ref_q}')"

            status_ia, analise_ia, feedback_aluno = gerar_feedback_frances(
                tema=f"{tema_q} ({tipo_q})",
                exercicio=exercicio_contexto,
                resposta_aluno=resposta_texto,
                tentativa=1,
                nivel_cefr=session.get("nivel_cefr", "A2")
            )

            cursor.execute("""
                INSERT INTO submissoes (
                    aluno_id, prova_questao_id, resposta_aluno, 
                    feedback_ia, analise_professor, status_resposta, data_hora
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                aluno_id, q_id, resposta_texto, 
                feedback_aluno, analise_ia, status_ia, 
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
    
    # Processar áudios gravados (MediaRecorder blob)
    for key in request.files.keys():
        if key.startswith("audio_questao_"):
            q_id = key.split("_")[2]
            audio_file = request.files[key]
            if audio_file:
                cursor.execute("SELECT texto_referencia FROM prova_questoes WHERE id = ? AND avaliacao_id = ?", (q_id, avaliacao_id))
                q_row = cursor.fetchone()
                if not q_row:
                    continue
                texto_ref = q_row["texto_referencia"] if q_row else ""

                upload_dir = os.path.join(BASE_DIR, "static", "uploads", "audios")
                os.makedirs(upload_dir, exist_ok=True)
                filename = secure_filename(f"aluno_{aluno_id}_q_{q_id}_{int(datetime.datetime.now().timestamp())}.webm")
                filepath = os.path.join(upload_dir, filename)
                audio_file.save(filepath)
                
                feedback_ia = "Análise pendente."
                try:
                    if not genai_model:
                        raise RuntimeError("Modelo Gemini não configurado")
                    
                    # Lê os bytes salvos para enviar à IA
                    with open(filepath, "rb") as f:
                        audio_bytes = f.read()
                        
                    audio_blob = {
                        "mime_type": "audio/webm",
                        "data": audio_bytes
                    }
                    
                    prompt_audio = f"O aluno leu em francês: '{texto_ref}'. Analise o áudio anexo, atribua nota de 0-10 para a pronúncia e aponte erros de fonética. Retorne JSON no formato: {{\"nota\": 8.5, \"analise\": \"Sua justificativa\"}}"
                    
                    res = genai_model.generate_content([prompt_audio, audio_blob])
                    
                    texto_limpo = re.sub(r"^```json\s*", "", res.text.strip(), flags=re.IGNORECASE)
                    texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
                    texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
                    dados_analise = json.loads(texto_limpo)
                    
                    feedback_ia = f"Análise Gemini: Nota {dados_analise.get('nota')} - {dados_analise.get('analise')}"
                except Exception as e:
                    print(f"Erro Gemini Áudio: {e}")
                    feedback_ia = "Análise preliminar (Gemini Falhou): A pronúncia está compreensível, mas faltou a nasalidade."
                
                cursor.execute("INSERT INTO submissoes (aluno_id, prova_questao_id, arquivo_audio_path, status_resposta, feedback_ia, data_hora) VALUES (?, ?, ?, ?, ?, ?)",
                               (aluno_id, q_id, f"static/uploads/audios/{filename}", 'Aguardando Revisão Manual', feedback_ia, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso"})

@aluno_bp.route("/guia-fle", methods=["GET"])
def guia_fle():
    """Página completa dedicada do Guia Gramatical FLE com barra lateral e conjugador interativo."""
    return render_template(
        "guia_fle.html",
        active_page="guia_fle",
        verbos=VERBOS_CONJUGADOS,
        temas=TEMAS_GUIA_FLE
    )

@aluno_bp.route("/api/guia-fle/verbo/<verb_id>", methods=["GET"])
def api_guia_fle_verbo(verb_id):
    """API para retornar conjugação completa, tempos e exemplos de um verbo."""
    verb_key = str(verb_id).strip().lower()
    if verb_key in VERBOS_CONJUGADOS:
        return jsonify({"status": "sucesso", "verbo": VERBOS_CONJUGADOS[verb_key]})
    return jsonify({"status": "erro", "mensagem": f"Verbo '{verb_id}' não encontrado."}), 404


