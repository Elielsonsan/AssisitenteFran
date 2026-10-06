import os
import re
import json
import threading
import sqlite3
import random
import datetime
from functools import wraps
import csv
import io
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

# Carrega variaveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'assistente_fran_dev_key_2026')
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route("/imagens/<path:filename>")
def servir_imagens(filename):
    return send_from_directory(os.path.join(BASE_DIR, "imagens"), filename)

@app.template_filter("iniciais")
def iniciais_filter(nome):
    if not nome:
        return "U"
    partes = [p for p in str(nome).strip().split() if p]
    if not partes:
        return "U"
    if len(partes) >= 2:
        return (partes[0][0] + partes[-1][0]).upper()
    return partes[0][:2].upper()

@app.template_filter("data_br")
def data_br_filter(val):
    """Converte YYYY-MM-DD HH:MM:SS para dd/mm/aaaa"""
    if not val:
        return ""
    s = str(val).strip()
    try:
        data_parte = s.split()[0].split("T")[0]
        partes = data_parte.split("-")
        if len(partes) == 3 and len(partes[0]) == 4:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
    except Exception:
        pass
    return s

@app.template_filter("data_hora_br")
def data_hora_br_filter(val):
    """Converte YYYY-MM-DD HH:MM:SS para dd/mm/aaaa às HH:MM:SS"""
    if not val:
        return ""
    s = str(val).strip()
    try:
        partes_espaco = s.replace("T", " ").split()
        data_parte = partes_espaco[0].split("-")
        hora_parte = partes_espaco[1] if len(partes_espaco) > 1 else ""
        if len(data_parte) == 3 and len(data_parte[0]) == 4:
            data_formatada = f"{data_parte[2]}/{data_parte[1]}/{data_parte[0]}"
            return f"{data_formatada} às {hora_parte}" if hora_parte else data_formatada
    except Exception:
        pass
    return s

# Configuracao da API do Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

genai_model = None
if GEMINI_API_KEY and GEMINI_API_KEY != "sua_chave_aqui":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        genai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print(f"[+] Google Gemini conectado com sucesso no modelo: {GEMINI_MODEL_NAME}")
    except Exception as e:
        print(f"[!] Aviso: Nao foi possivel inicializar a API do Gemini: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")

# Auto-inicialização dos Planos de Aula
try:
    from seed_planos_aula import init_planos_aula
    init_planos_aula()
except Exception as _e:
    print(f"[!] Aviso ao inicializar planos de aula: {_e}")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "aluno_id" not in session:
            if request.is_json or request.path == "/avaliar":
                return jsonify({"status": "erro", "mensagem": "Sessão expirada."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def login_required_prof(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "prof_id" not in session:
            if request.is_json:
                return jsonify({"status": "erro", "mensagem": "Acesso restrito ao Professor."}), 403
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ===================== FUNCOES GEMINI =====================

def parse_retorno_gemini_frances(texto):
    texto = texto.strip()
    status = "Parcialmente Correto"
    match_status = re.search(r"\*\*Status:\*\*\s*(Correto|Parcialmente Correto|Incorreto)", texto, re.IGNORECASE)
    if match_status:
        status_raw = match_status.group(1).strip().title()
        if "Parcial" in status_raw: status = "Parcialmente Correto"
        elif "Incorret" in status_raw: status = "Incorreto"
        else: status = "Correto"

    analise_professor = "Análise registrada pelo professor virtual."
    match_analise = re.search(r"\*\*Análise do Professor:\*\*\s*(.*?)(?=\n- \*\*Feedback|\n\*\*Feedback|$)", texto, re.DOTALL | re.IGNORECASE)
    if match_analise:
        analise_professor = match_analise.group(1).strip()

    feedback_aluno = ""
    match_feedback = re.search(r"\*\*Feedback pour l'élève:\*\*\s*(.*)", texto, re.DOTALL | re.IGNORECASE)
    if not match_feedback:
        match_feedback = re.search(r"\*\*Feedback para o Aluno:\*\*\s*(.*)", texto, re.DOTALL | re.IGNORECASE)
    if match_feedback:
        feedback_aluno = match_feedback.group(1).strip()
    else:
        feedback_aluno = re.sub(r"-\s*\*\*Status:\*\*.*?\n+", "", texto).strip()

    return status, analise_professor, feedback_aluno

def feedback_demonstracao_frances(tema, exercicio, resposta_aluno):
    return "Correto", "Análise de teste.", "### *Très bien!*\n\nVocê acertou."

def gerar_feedback_frances(tema, exercicio, resposta_aluno, tentativa=1, dica_anterior="", nivel_cefr="A2"):
    nivel = (nivel_cefr or "A2").strip().upper()

    prompt_sistema = f"""Você é um professor nativo de francês auxiliando brasileiros.
Nível CEFR do aluno: {nivel}.
Tema: {tema}
Exercício: {exercicio}
Resposta do aluno: {resposta_aluno}

Responda EXATAMENTE:
- **Status:** (Correto / Parcialmente Correto / Incorreto)
- **Análise do Professor:** (Qual foi o erro e a regra)
- **Feedback para o Aluno:** (Mensagem encorajadora com dica para corrigir)"""

    if genai_model:
        try:
            response = genai_model.generate_content(prompt_sistema)
            return parse_retorno_gemini_frances(response.text)
        except Exception as e:
            return "Parcialmente Correto", f"Erro: {e}", "Erro na IA."

    return feedback_demonstracao_frances(tema, exercicio, resposta_aluno)

# ===================== ROTAS DE LOGIN E INDEX =====================

@app.route("/login", methods=["GET", "POST"])
def login():
    if "aluno_id" in session:
        return redirect(url_for("index"))
    if "prof_id" in session:
        return redirect(url_for("dashboard"))
        
    erro = None
    if request.method == "POST":
        tipo_acesso = request.form.get("tipo_acesso", "aluno")
        senha = request.form.get("senha", "").strip()
        
        conn = get_db()
        cursor = conn.cursor()
        
        if tipo_acesso == "aluno":
            matricula = request.form.get("matricula", "").strip()
            if not matricula or not senha:
                erro = "Preencha matrícula e senha."
            else:
                cursor.execute("""
                    SELECT a.id, a.nome, a.matricula, a.senha_hash, a.turma_id, a.nivel_cefr, t.nome as turma_nome
                    FROM alunos a JOIN turmas t ON a.turma_id = t.id WHERE a.matricula = ?;
                """, (matricula,))
                aluno = cursor.fetchone()
                if aluno and check_password_hash(aluno["senha_hash"], senha):
                    session["aluno_id"] = aluno["id"]
                    session["aluno_nome"] = aluno["nome"]
                    session["matricula"] = aluno["matricula"]
                    session["turma_id"] = aluno["turma_id"]
                    session["turma_nome"] = aluno["turma_nome"]
                    session["nivel_cefr"] = aluno["nivel_cefr"] or "A2"
                    conn.close()
                    return redirect(url_for("index"))
                else:
                    erro = "Matrícula ou senha incorreta."
                    
        elif tipo_acesso == "professor":
            usuario = request.form.get("usuario", "").strip()
            if not usuario or not senha:
                erro = "Preencha usuário e senha."
            else:
                cursor.execute("SELECT id, nome, usuario, senha_hash FROM professores WHERE usuario = ?", (usuario,))
                prof = cursor.fetchone()
                if prof and check_password_hash(prof["senha_hash"], senha):
                    session["prof_id"] = prof["id"]
                    session["prof_nome"] = prof["nome"]
                    session["prof_usuario"] = prof["usuario"]
                    conn.close()
                    return redirect(url_for("dashboard"))
                else:
                    erro = "Usuário ou senha incorretos."
        conn.close()
    return render_template("login.html", erro=erro, active_page="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
def home_publica():
    return render_template("home_publica.html")

@app.route("/pratica", methods=["GET"])
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
    cursor.execute("SELECT id, mensagem_tutor, tema_id FROM reforcos_individuais WHERE aluno_id=? AND status='Pendente' ORDER BY id DESC LIMIT 1", (aluno_id,))
    reforco = cursor.fetchone()

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
        exercicio_inicial=exercicio_inicial
    )

# ===================== ROTAS DE ALUNO (GERAR E AVALIAR) =====================

@app.route("/aluno/dashboard", methods=["GET"])
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
    
    # Participação semanal mockada para o gráfico de barras
    participacao_semanal = [2, 5, 3, 7, 4]
    
    # Buscar Missão de Foco pendente (reforço)
    cursor.execute("SELECT * FROM reforcos_individuais WHERE aluno_id = ? AND status = 'Pendente' ORDER BY id DESC LIMIT 1", (aluno_id,))
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
    cursor.execute("SELECT COUNT(*) as total_reforco FROM reforcos_individuais WHERE aluno_id = ? AND status = 'Concluido'", (aluno_id,))
    ref_row = cursor.fetchone()
    tem_reforco = (ref_row["total_reforco"] or 0) > 0

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
        badges=badges
    )

@app.route("/api/responder_missao", methods=["POST"])
@login_required
def api_responder_missao():
    aluno_id = session.get("aluno_id")
    dados = request.get_json() if request.is_json else request.form
    reforco_id = dados.get("reforco_id")
    resposta = dados.get("resposta", "").strip()
    
    if not reforco_id or not resposta:
        return jsonify({"status": "erro", "mensagem": "Resposta em branco."}), 400
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE reforcos_individuais SET status = 'Concluido' WHERE id = ? AND aluno_id = ?", (reforco_id, aluno_id))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Missão não encontrada ou não autorizada."}), 403
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": "Missão enviada com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route("/gerar-desafio", methods=["GET", "POST"])
@login_required
def rota_gerar_desafio():
    # Permite parâmetro na query ou da sessão do aluno
    nivel = request.args.get("nivel_cefr") or session.get("nivel_cefr", "A2")
    nivel = (nivel or "A2").strip().upper()
    
    conn = get_db()
    cursor = conn.cursor()
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
        return jsonify({
            "status": "sucesso",
            "exercicio_id": row["exercicio_id"],
            "tema": row["tema"],
            "exercicio": row["exercicio"],
            "nivel_cefr": row["nivel_cefr"],
            "dica_inicial": "Preste atenção à gramática e à concordância."
        })

    # Caso não haja exercício no banco para esse nível, gera dinamicamente com IA
    exercicio_gerado = None
    tema_nome = "Grammaire et Vocabulaire"
    dica_inicial = "Foco na estrutura da frase em francês."

    if genai_model:
        try:
            prompt_desafio = f"""Você é um professor de francês para brasileiros.
Gere 1 exercício inédito e curto de francês adequado estritamente ao nível CEFR {nivel}.
Retorne EXATAMENTE um JSON com as chaves:
- "tema": (título conciso do tema gramatical, ex: 'Le Passé Composé' ou 'Le Subjonctif')
- "enunciado": (instrução clara e a frase com lacuna ou instrução direta para o aluno responder)
- "dica": (uma dica pedagógica curta sobre a regra)"""

            resp = genai_model.generate_content(prompt_desafio)
            texto_limpo = re.sub(r"^```json\s*", "", resp.text.strip(), flags=re.IGNORECASE)
            texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
            texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
            dados = json.loads(texto_limpo)
            if "tema" in dados and "enunciado" in dados:
                tema_nome = dados["tema"].strip()
                exercicio_gerado = dados["enunciado"].strip()
                dica_inicial = dados.get("dica", dica_inicial)
        except Exception as e:
            print(f"[!] Erro ao gerar desafio com IA para nível {nivel}: {e}")

    # Fallback estruturado se a IA não estiver disponível
    if not exercicio_gerado:
        fallbacks_nivel = {
            "B1": ("L'Accord du Participe Passé", "Complétez avec le participe passé convenable: 'Voici la lettre que j\\'ai ___ (écrire) pour mon ami.'"),
            "B2": ("Le Subjonctif Présent", "Mettez le verbe au subjonctif: 'Il faut absolument que vous ___ (faire) attention aux détails.'"),
            "C1": ("Le Conditionnel Passé", "Conjuguez au conditionnel passé: 'Si j\\'avais su la vérité, je n\\'___ (agir) pas de cette façon.'"),
            "A1": ("La Négation Simple", "Transformez la phrase à la forme négative: 'Je regarde la télévision ce soir.'"),
            "A2": ("Le Passé Composé", "Complétez avec le verbe être ou avoir au passé composé: 'Nous ___ (partir) en vacances très tôt.'")
        }
        tema_nome, exercicio_gerado = fallbacks_nivel.get(nivel, ("Exercice Général", f"Traduisez en français: 'Hoje está um belo dia para estudar francês.'"))

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
        conn.close()

        return jsonify({
            "status": "sucesso",
            "exercicio_id": novo_exercicio_id,
            "tema": tema_nome,
            "exercicio": exercicio_gerado,
            "nivel_cefr": nivel,
            "dica_inicial": dica_inicial
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao registrar exercício: {e}"}), 500

@app.route("/api/aluno/aceitar_reforco", methods=["POST"])
@login_required
def aceitar_reforco():
    aluno_id = session.get("aluno_id")
    dados = request.get_json() if request.is_json else request.form
    reforco_id = dados.get("reforco_id")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT tema_id FROM reforcos_individuais WHERE id=? AND aluno_id=?", (reforco_id, aluno_id))
    row = cursor.fetchone()
    
    if row:
        tema_id = row["tema_id"]
        cursor.execute("UPDATE reforcos_individuais SET status='Concluido' WHERE id=? AND aluno_id=?", (reforco_id, aluno_id))
        
        # Obter exercício do tema
        cursor.execute("""
            SELECT e.id as exercicio_id, t.nome_tema as tema, e.enunciado as exercicio, e.nivel_exigido as nivel_cefr
            FROM exercicios e
            JOIN temas t ON e.tema_id = t.id
            WHERE e.tema_id = ?
            ORDER BY RANDOM() LIMIT 1;
        """, (tema_id,))
        ex_row = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if ex_row:
            return jsonify({
                "status": "sucesso",
                "exercicio_id": ex_row["exercicio_id"],
                "tema": ex_row["tema"],
                "exercicio": ex_row["exercicio"],
                "nivel_cefr": ex_row["nivel_cefr"],
                "dica_inicial": "Foco neste tema! O professor recomendou este reforço para você."
            })
        
    conn.close()
    return jsonify({"status": "erro", "mensagem": "Não foi possível carregar o exercício de reforço."})

@app.route("/avaliar", methods=["POST"])
@login_required
def avaliar():
    aluno_id = session.get("aluno_id")
    dados = request.get_json() if request.is_json else request.form
    
    exercicio_id = dados.get("exercicio_id")
    resposta = dados.get("resposta_aluno", "").strip()
    tentativa = int(dados.get("tentativa", 1))

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
        tema, exercicio, resposta, tentativa=tentativa, nivel_cefr=nivel_cefr
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

@app.route("/dashboard", methods=["GET"])
@login_required_prof
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC;")
    turmas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC;")
    temas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT a.id, a.nome, a.matricula, a.turma_id, a.nivel_cefr, t.nome as turma_nome,
               COUNT(s.id) as total_atividades,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros
        FROM alunos a
        JOIN turmas t ON a.turma_id = t.id
        LEFT JOIN submissoes s ON s.aluno_id = a.id
        GROUP BY a.id ORDER BY t.nome ASC, a.nome ASC;
    """)
    alunos_cadastrados = [dict(row) for row in cursor.fetchall()]

    turma_id_raw = request.args.get("turma_id")
    turma_id = None
    turma_selecionada_nome = None

    if turma_id_raw and str(turma_id_raw).strip().isdigit():
        turma_id = int(turma_id_raw)
        for t in turmas:
            if t["id"] == turma_id:
                turma_selecionada_nome = t["nome"]
                break

    filtro_sql = "WHERE t.id = ?" if turma_id else ""
    filtro_params = (turma_id,) if turma_id else ()

    sql_status = f"""
        SELECT s.status_resposta, COUNT(*) as total
        FROM submissoes s JOIN alunos a ON s.aluno_id = a.id JOIN turmas t ON a.turma_id = t.id
        {filtro_sql} GROUP BY s.status_resposta
    """
    cursor.execute(sql_status, filtro_params)
    rows_status = cursor.fetchall()
    status_labels = [row["status_resposta"] for row in rows_status]
    status_valores = [row["total"] for row in rows_status]

    sql_temas = f"""
        SELECT te.nome_tema,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) AS acertos,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) AS erros,
               SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) AS parciais
        FROM submissoes s
        LEFT JOIN exercicios e ON s.exercicio_id = e.id
        LEFT JOIN temas te ON e.tema_id = te.id
        JOIN alunos a ON s.aluno_id = a.id
        JOIN turmas t ON a.turma_id = t.id
        {filtro_sql} GROUP BY te.nome_tema
    """
    cursor.execute(sql_temas, filtro_params)
    rows_temas = cursor.fetchall()
    tema_labels = [row["nome_tema"] if row["nome_tema"] else "Prova Multimodal" for row in rows_temas]
    tema_acertos = [int(row["acertos"] or 0) for row in rows_temas]
    tema_erros = [int(row["erros"] or 0) for row in rows_temas]
    tema_parciais = [int(row["parciais"] or 0) for row in rows_temas]

    sql_submissoes = f"""
        SELECT s.id, a.nome as aluno_nome, a.matricula as aluno_matricula, t.nome as turma_nome, 
               te.nome_tema as tema, te.nome_tema as tema_aula,
               COALESCE(e.enunciado, pq.enunciado) as pergunta, COALESCE(e.enunciado, pq.enunciado) as exercicio,
               s.resposta_aluno as resposta, s.resposta_aluno as resposta_aluno,
               s.feedback_ia as feedback, s.analise_professor as analise,
               s.status_resposta as status, COALESCE(e.nivel_exigido, 'A2') as nivel_cefr, s.tentativa, s.data_hora,
               s.aluno_id, e.tema_id
        FROM submissoes s
        LEFT JOIN exercicios e ON s.exercicio_id = e.id
        LEFT JOIN temas te ON e.tema_id = te.id
        LEFT JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        JOIN alunos a ON s.aluno_id = a.id
        JOIN turmas t ON a.turma_id = t.id
        {filtro_sql} ORDER BY s.id DESC;
    """
    cursor.execute(sql_submissoes, filtro_params)
    submissoes = [dict(row) for row in cursor.fetchall()]

    alunos_em_risco = [sub for sub in submissoes if sub["status"] == "Incorreto"]
    
    total_submissoes = len(submissoes)
    total_corretos = sum(1 for s in submissoes if s['status'] == 'Correto')
    total_parciais = sum(1 for s in submissoes if s['status'] == 'Parcialmente Correto')
    total_incorretos = sum(1 for s in submissoes if s['status'] == 'Incorreto')
    pct_acerto = round((total_corretos / total_submissoes * 100), 1) if total_submissoes > 0 else 0
    pct_parcial = round((total_parciais / total_submissoes * 100), 1) if total_submissoes > 0 else 0
    pct_incorreto = round((total_incorretos / total_submissoes * 100), 1) if total_submissoes > 0 else 0

    submissoes_dict = {str(s["id"]): s for s in submissoes}

    conn.close()

    return render_template(
        "dashboard.html", active_page="dashboard", turmas=turmas, temas=temas,
        turma_selecionada=turma_id, turma_selecionada_nome=turma_selecionada_nome,
        alunos_em_risco=alunos_em_risco, status_labels=status_labels, status_valores=status_valores,
        tema_labels=tema_labels, tema_acertos=tema_acertos, tema_erros=tema_erros, tema_parciais=tema_parciais,
        submissoes=submissoes, submissoes_dict=submissoes_dict, total_submissoes=total_submissoes,
        total_corretos=total_corretos, total_parciais=total_parciais, total_incorretos=total_incorretos,
        pct_acerto=pct_acerto, pct_parcial=pct_parcial, pct_incorreto=pct_incorreto,
        temas_unicos=tema_labels, alunos_cadastrados=alunos_cadastrados
    )

# ===================== ROTAS DE API: TURMAS & EXPORTAÇÃO =====================

@app.route("/api/turmas", methods=["GET"])
@login_required_prof
def api_listar_turmas():
    """Retorna todas as turmas cadastradas com total de alunos vinculados."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.nome, COUNT(a.id) AS total_alunos
            FROM turmas t
            LEFT JOIN alunos a ON a.turma_id = t.id
            GROUP BY t.id, t.nome
            ORDER BY t.nome ASC;
        """)
        rows = cursor.fetchall()
        conn.close()
        turmas = [{"id": r["id"], "nome": r["nome"], "total_alunos": r["total_alunos"]} for r in rows]
        return jsonify({"status": "sucesso", "turmas": turmas})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/turmas/cadastrar", methods=["POST"])
@login_required_prof
def api_cadastrar_turma():
    dados = request.get_json() if request.is_json else request.form
    nome = dados.get("nome", "").strip()

    if not nome:
        return jsonify({"status": "erro", "mensagem": "O nome da turma é obrigatório."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM turmas WHERE LOWER(nome) = LOWER(?)", (nome,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Já existe uma turma cadastrada com esse nome."}), 400

    try:
        cursor.execute("INSERT INTO turmas (nome) VALUES (?)", (nome,))
        conn.commit()
        nova_turma_id = cursor.lastrowid
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Turma '{nome}' criada com sucesso!",
            "turma": {"id": nova_turma_id, "nome": nome}
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/turmas/<int:turma_id>/editar", methods=["POST"])
@login_required_prof
def api_editar_turma(turma_id):
    """Atualiza o nome de uma turma existente."""
    dados = request.get_json() if request.is_json else request.form
    nome = dados.get("nome", "").strip()

    if not nome:
        return jsonify({"status": "erro", "mensagem": "O nome da turma é obrigatório."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM turmas WHERE LOWER(nome) = LOWER(?) AND id != ?", (nome, turma_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Já existe outra turma com esse nome."}), 400

    try:
        cursor.execute("UPDATE turmas SET nome = ? WHERE id = ?", (nome, turma_id))
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Turma renomeada para '{nome}' com sucesso!",
            "turma": {"id": turma_id, "nome": nome}
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/turmas/<int:turma_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_excluir_turma(turma_id):
    """Exclui uma turma caso não haja alunos matriculados nela."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id) FROM alunos WHERE turma_id = ?", (turma_id,))
    total = cursor.fetchone()[0]
    if total > 0:
        conn.close()
        return jsonify({
            "status": "erro",
            "mensagem": f"Não é possível excluir esta turma: existem {total} aluno(s) vinculados a ela."
        }), 400

    try:
        cursor.execute("DELETE FROM turmas WHERE id = ?", (turma_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": "Turma excluída com sucesso!"})
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route("/api/relatorio/exportar_csv", methods=["GET"])
@login_required_prof
def api_exportar_csv():
    turma_id_raw = request.args.get("turma_id")
    turma_id = int(turma_id_raw) if turma_id_raw and str(turma_id_raw).strip().isdigit() and str(turma_id_raw) != "todas" else None
    nivel_cefr = request.args.get("nivel_cefr", "").strip().upper()
    n_cefr = nivel_cefr if nivel_cefr and nivel_cefr != "TODOS" else None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.nome, a.matricula, t.nome as turma_nome, a.nivel_cefr,
               COUNT(s.id) as total_atividades,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros,
               ROUND(AVG(s.nota_professor), 1) as media_provas
        FROM alunos a
        JOIN turmas t ON a.turma_id = t.id
        LEFT JOIN submissoes s ON s.aluno_id = a.id
        WHERE (? IS NULL OR t.id = ?)
          AND (? IS NULL OR a.nivel_cefr = ?)
        GROUP BY a.id
        ORDER BY t.nome ASC, a.nome ASC;
    """, (turma_id, turma_id, n_cefr, n_cefr))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        "ID", "Nome do Aluno", "Matrícula", "Turma", "Nível CEFR",
        "Total Atividades", "Acertos", "Parciais", "Erros",
        "Aproveitamento (%)", "Média Provas (0-10)"
    ])

    for r in rows:
        tot = r["total_atividades"] or 0
        acertos = r["acertos"] or 0
        parciais = r["parciais"] or 0
        taxa = round(((acertos + parciais * 0.5) / tot * 100), 1) if tot > 0 else 0.0
        media_p = r["media_provas"] if r["media_provas"] is not None else "Sem notas"

        writer.writerow([
            r["id"], r["nome"], r["matricula"], r["turma_nome"], r["nivel_cefr"],
            tot, acertos, parciais, r["erros"] or 0,
            f"{taxa}%", media_p
        ])

    csv_data = output.getvalue()
    csv_bytes = csv_data.encode("utf-8-sig")

    filename = f"boletim_fle_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/api/relatorio/boletim_dados", methods=["GET"])
@login_required_prof
def api_boletim_dados():
    turma_id_raw = request.args.get("turma_id")
    turma_id = int(turma_id_raw) if turma_id_raw and str(turma_id_raw).strip().isdigit() and str(turma_id_raw) != "todas" else None
    nivel_cefr = request.args.get("nivel_cefr", "").strip().upper()
    n_cefr = nivel_cefr if nivel_cefr and nivel_cefr != "TODOS" else None

    conn = get_db()
    cursor = conn.cursor()

    turma_nome_filtro = "Todas as Turmas"
    if turma_id:
        cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,))
        t_row = cursor.fetchone()
        if t_row:
            turma_nome_filtro = t_row["nome"]

    cursor.execute("""
        SELECT a.id, a.nome, a.matricula, t.nome as turma_nome, a.nivel_cefr,
               COUNT(s.id) as total_atividades,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros,
               ROUND(AVG(s.nota_professor), 1) as media_provas
        FROM alunos a
        JOIN turmas t ON a.turma_id = t.id
        LEFT JOIN submissoes s ON s.aluno_id = a.id
        WHERE (? IS NULL OR t.id = ?)
          AND (? IS NULL OR a.nivel_cefr = ?)
        GROUP BY a.id
        ORDER BY t.nome ASC, a.nome ASC;
    """, (turma_id, turma_id, n_cefr, n_cefr))
    rows = cursor.fetchall()
    conn.close()

    alunos = []
    soma_aproveitamento = 0.0
    soma_media_provas = 0.0
    qtd_provas_validas = 0
    alunos_aprovados = 0

    for r in rows:
        tot = r["total_atividades"] or 0
        acertos = r["acertos"] or 0
        parciais = r["parciais"] or 0
        erros = r["erros"] or 0
        taxa = round(((acertos + parciais * 0.5) / tot * 100), 1) if tot > 0 else 0.0
        media_p = r["media_provas"]

        soma_aproveitamento += taxa
        if taxa >= 60.0:
            alunos_aprovados += 1

        if media_p is not None:
            soma_media_provas += media_p
            qtd_provas_validas += 1

        if taxa >= 85:
            conceito = "Excelente (Très Bien)"
        elif taxa >= 70:
            conceito = "Bom Domínio (Bien)"
        elif taxa >= 50:
            conceito = "Em Desenvolvimento (Passable)"
        elif tot > 0:
            conceito = "Necessita Reforço (Insuffisant)"
        else:
            conceito = "Sem Atividades"

        alunos.append({
            "id": r["id"],
            "nome": r["nome"],
            "matricula": r["matricula"],
            "turma_nome": r["turma_nome"],
            "nivel_cefr": r["nivel_cefr"],
            "total_atividades": tot,
            "acertos": acertos,
            "parciais": parciais,
            "erros": erros,
            "taxa_aproveitamento": taxa,
            "media_provas": media_p if media_p is not None else "—",
            "conceito": conceito
        })

    total_alunos = len(alunos)
    media_aprov = round(soma_aproveitamento / total_alunos, 1) if total_alunos > 0 else 0.0
    media_provas_turma = round(soma_media_provas / qtd_provas_validas, 1) if qtd_provas_validas > 0 else "—"
    taxa_aprov_pct = round(alunos_aprovados / total_alunos * 100, 1) if total_alunos > 0 else 0.0

    return jsonify({
        "status": "sucesso",
        "turma_nome": turma_nome_filtro,
        "nivel_cefr_filtro": n_cefr or "Todos os Níveis",
        "data_emissao": datetime.datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "total_alunos": total_alunos,
        "media_aproveitamento_turma": media_aprov,
        "media_provas_turma": media_provas_turma,
        "taxa_aprovacao_turma": taxa_aprov_pct,
        "alunos": alunos
    })

# ===================== ROTAS DE API: ALUNOS =====================

@app.route("/api/alunos", methods=["GET"])
@login_required_prof
def api_listar_alunos():
    """Retorna a lista completa de alunos cadastrados com informações da turma."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.nome, a.matricula, a.nivel_cefr, a.turma_id,
                   COALESCE(t.nome, 'Sem Turma') AS turma_nome,
                   COUNT(s.id) AS total_atividades
            FROM alunos a
            LEFT JOIN turmas t ON t.id = a.turma_id
            LEFT JOIN submissoes s ON s.aluno_id = a.id
            GROUP BY a.id, a.nome, a.matricula, a.nivel_cefr, a.turma_id, t.nome
            ORDER BY a.nome ASC;
        """)
        rows = cursor.fetchall()
        conn.close()
        alunos = [{
            "id": r["id"],
            "nome": r["nome"],
            "matricula": r["matricula"],
            "nivel_cefr": r["nivel_cefr"],
            "turma_id": r["turma_id"],
            "turma_nome": r["turma_nome"],
            "total_atividades": r["total_atividades"]
        } for r in rows]
        return jsonify({"status": "sucesso", "alunos": alunos})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/alunos/cadastrar", methods=["POST"])
@login_required_prof
def api_cadastrar_aluno():
    dados = request.get_json() if request.is_json else request.form
    nome = dados.get("nome", "").strip()
    matricula = dados.get("matricula", "").strip()
    senha = dados.get("senha", "").strip()
    turma_id = dados.get("turma_id")
    nivel_cefr = dados.get("nivel_cefr", "A2").strip().upper()

    if not nome or not matricula or not senha or not turma_id:
        return jsonify({"status": "erro", "mensagem": "Preencha todos os campos obrigatórios."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM alunos WHERE matricula = ?;", (matricula,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Já existe um aluno cadastrado com essa matrícula."}), 400

        cursor.execute("""
            INSERT INTO alunos (nome, matricula, senha_hash, turma_id, nivel_cefr)
            VALUES (?, ?, ?, ?, ?);
        """, (nome, matricula, generate_password_hash(senha), turma_id, nivel_cefr))
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Aluno '{nome}' cadastrado com sucesso!",
            "aluno": {"id": novo_id, "nome": nome, "matricula": matricula}
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/alunos/<int:aluno_id>/nivel", methods=["POST"])
@login_required_prof
def api_atualizar_nivel_aluno(aluno_id):
    dados = request.get_json() if request.is_json else request.form
    nivel = dados.get("nivel_cefr", "").strip().upper()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE alunos SET nivel_cefr = ? WHERE id = ?;", (nivel, aluno_id))
        conn.commit()
        conn.close()
        if session.get("aluno_id") == aluno_id: session["nivel_cefr"] = nivel
        return jsonify({"status": "sucesso", "mensagem": f"Nível atualizado para {nivel}!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/alunos/<int:aluno_id>/editar", methods=["POST"])
@login_required_prof
def api_editar_aluno(aluno_id):
    dados = request.get_json() if request.is_json else request.form
    nome = dados.get("nome", "").strip()
    matricula = dados.get("matricula", "").strip()
    senha = dados.get("senha", "").strip()
    turma_id = dados.get("turma_id")
    nivel_cefr = dados.get("nivel_cefr", "A2").strip().upper()

    if not nome or not matricula or not turma_id:
        return jsonify({"status": "erro", "mensagem": "Nome, matrícula e turma são obrigatórios."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Verificar se matrícula já é usada por outro aluno
        cursor.execute("SELECT id FROM alunos WHERE matricula = ? AND id != ?;", (matricula, aluno_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Outro aluno já está utilizando esta matrícula."}), 400

        if senha:
            cursor.execute("""
                UPDATE alunos
                SET nome = ?, matricula = ?, senha_hash = ?, turma_id = ?, nivel_cefr = ?
                WHERE id = ?;
            """, (nome, matricula, generate_password_hash(senha), turma_id, nivel_cefr, aluno_id))
        else:
            cursor.execute("""
                UPDATE alunos
                SET nome = ?, matricula = ?, turma_id = ?, nivel_cefr = ?
                WHERE id = ?;
            """, (nome, matricula, turma_id, nivel_cefr, aluno_id))

        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": f"Dados do aluno '{nome}' atualizados com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/alunos/<int:aluno_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_excluir_aluno(aluno_id):
    """Exclui o aluno e suas submissões associadas."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissoes WHERE aluno_id = ?;", (aluno_id,))
        cursor.execute("DELETE FROM alunos WHERE id = ?;", (aluno_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": "Aluno excluído com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

# ===================== CO-PILOTO PEDAGÓGICO =====================

@app.route("/api/copiloto/gerar_exercicio", methods=["POST"])
@login_required_prof
def api_copiloto_gerar():
    dados = request.get_json() if request.is_json else request.form
    tema_id = dados.get("tema_id")
    nivel = dados.get("nivel", "A2").strip().upper()
    quantidade = int(dados.get("quantidade", 3))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_tema FROM temas WHERE id = ?;", (tema_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "erro", "mensagem": "Tema não encontrado."}), 404
    
    tema_nome = row["nome_tema"]

    prompt = f"""Atue como um professor de francês FLE.
Gere {quantidade} exercícios práticos curtos sobre o tema '{tema_nome}' para o nível '{nivel}'.
Cada exercício DEVE conter uma frase concreta em francês com lacuna '___' ou indicação entre parênteses para conjugar/preencher.
Retorne JSON com a chave 'exercicios' (array de strings)."""
    exercicios = []
    if genai_model:
        try:
            response = genai_model.generate_content(prompt)
            texto_limpo = re.sub(r"^```json\s*", "", response.text.strip(), flags=re.IGNORECASE)
            texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
            texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
            dados_ia = json.loads(texto_limpo)
            exercicios = dados_ia.get("exercicios", [])
        except Exception as e:
            print(f"Erro no copiloto: {e}")
            pass

    # Valida e substitui fallbacks por questões pedagógicas completas com frases
    if not exercicios or any("fallback" in str(ex).lower() or len(str(ex).strip()) < 15 for ex in exercicios):
        questoes_ped = gerar_questoes_pedagogicas_completas(tema_nome, nivel, "exercicio", quantidade)
        exercicios = [q["enunciado"] for q in questoes_ped]

    return jsonify({"status": "sucesso", "exercicios": exercicios[:quantidade]})

@app.route("/api/copiloto/salvar_exercicios", methods=["POST"])
@login_required_prof
def api_copiloto_salvar():
    dados = request.get_json() if request.is_json else request.form
    tema_id = dados.get("tema_id")
    nivel = dados.get("nivel", "A2").strip().upper()
    exercicios = dados.get("exercicios", [])

    if not exercicios or not tema_id:
        return jsonify({"status": "erro", "mensagem": "Dados insuficientes."}), 400

    conn = get_db()
    cursor = conn.cursor()
    for ex in exercicios:
        cursor.execute("""
            INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?)
        """, (tema_id, nivel, ex.strip()))
    conn.commit()
    conn.close()

    return jsonify({"status": "sucesso", "salvos": len(exercicios)})

# ===================== RADAR DE INTERVENÇÃO =====================

@app.route("/api/radar/reforco", methods=["POST"])
@login_required_prof
def api_radar_reforco():
    """Gera um plano de reforço individualizado e salva na tabela reforcos_individuais"""
    dados = request.get_json() if request.is_json else request.form
    aluno_id = dados.get("aluno_id")
    tema_id = dados.get("tema_id")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM alunos WHERE id=?;", (aluno_id,))
    aluno = cursor.fetchone()
    cursor.execute("SELECT nome_tema FROM temas WHERE id=?;", (tema_id,))
    tema = cursor.fetchone()

    if not aluno or not tema:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Aluno ou Tema inválidos."}), 404

    # Fake IA Generation for Intervention Plan
    mensagem = f"Olá {aluno['nome']}, notei que você teve dificuldades com {tema['nome_tema']}. Vamos praticar mais!"
    exercicios_reforco = [f"Reforço 1: {tema['nome_tema']}"]

    cursor.execute("""
        INSERT INTO reforcos_individuais (aluno_id, tema_id, mensagem_tutor, exercicios_json)
        VALUES (?, ?, ?, ?)
    """, (aluno_id, tema_id, mensagem, json.dumps(exercicios_reforco)))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "sucesso",
        "mensagem": f"Plano de reforço enviado para {aluno['nome']} com sucesso!"
    })


# ===================== MÓDULO DO PROFESSOR (ESQUELETOS) =====================

@app.route("/professor/avaliacoes", methods=["GET"])
@login_required_prof
def prof_avaliacoes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.titulo, a.tipo, a.data_limite, t.nome as turma_nome
        FROM avaliacoes a
        JOIN turmas t ON a.turma_id = t.id
        ORDER BY a.id DESC
    """)
    avaliacoes = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
    turmas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC")
    temas = [dict(row) for row in cursor.fetchall()]
    
    # Obter também as submissões aguardando revisão manual
    cursor.execute("""
        SELECT s.id, al.nome as aluno_nome, e.titulo as avaliacao_nome, pq.tipo_questao, s.nota_professor, s.arquivo_audio_path
        FROM submissoes s
        JOIN alunos al ON s.aluno_id = al.id
        JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        JOIN avaliacoes e ON pq.avaliacao_id = e.id
        WHERE s.status_resposta = 'Aguardando Revisão Manual'
        ORDER BY s.id ASC
    """)
    pendentes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template("professor_avaliacoes.html", avaliacoes=avaliacoes, turmas=turmas, temas=temas, pendentes=pendentes, active_page="prof_avaliacoes")

@app.route("/professor/forum", methods=["GET"])
@login_required_prof
def prof_forum():
    return redirect(url_for("forum_lista"))

# ===================== MÓDULO DO ALUNO =====================

@app.route("/aluno/atividades", methods=["GET"])
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

@app.route("/aluno/forum", methods=["GET"])
@login_required
def aluno_forum():
    return redirect(url_for("forum_lista"))

@app.route("/aluno/perfil", methods=["GET"])
@login_required
def aluno_perfil():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.nome, a.matricula, a.nivel_cefr, a.turno, a.sala, t.nome as turma_nome
        FROM alunos a
        JOIN turmas t ON a.turma_id = t.id
        WHERE a.id = ?
    """, (aluno_id,))
    aluno_row = cursor.fetchone()
    aluno = dict(aluno_row) if aluno_row else {}

    cursor.execute("""
        SELECT m.id, m.assunto, m.corpo, m.data_envio, m.lida_status, p.nome as remetente_nome
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

# ===================== BANCO PEDAGÓGICO E GERADOR DE QUESTÕES =====================
BANCO_PEDAGOGICO_TEMAS = {
    "passe_compose": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase au passé composé avec l'auxiliaire 'avoir' ou 'être' : 'Hier soir, nous ___ (regarder) un documentaire très intéressant sur la France.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase au passé composé : 'Ce matin, Sophie ___ (partir) de la maison à huit heures précises.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Transformez la phrase au passé composé : 'Ils choisissent un bon restaurant en ville.' -> 'Hier, ils ___ (choisir) un bon restaurant en ville.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le participe passé correct : 'Paul et Lucas ont ___ (finir) leur travail avant midi.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la forme correcte au passé composé : 'Hier, mes amis ___ à Paris.'\n(a) sont arrivés\n(b) ont arrivés\n(c) sont arrivé\n(d) ont arrivé", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle phrase utilise correctement l'auxiliaire 'être' ?\n(a) Elle a descendu la rue\n(b) Elle est allée à la gare\n(c) Elle a allée au marché\n(d) Elle est allé à la gare", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez avec le participe passé du verbe 'prendre' : 'Tu as ___ ton manteau pour sortir.'\n(a) pris\n(b) prendu\n(c) prenant\n(d) prené", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Identifiez l'erreur dans la phrase suivante et réécrivez-la correctement : 'Nous avons restés chez nos grands-parents tout le week-end.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au passé composé : 'Hier après-midi, nous ___ (visiter) le musée du Louvre.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o Passé Composé:", "texto_referencia": "Ontem eu comprei um livro muito bom na livraria.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase em francês:", "texto_referencia": "Hier, nous avons mangé dans une boulangerie typique.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia a frase em voz alta com clareza e boa entonação:", "texto_referencia": "Le week-end dernier, je suis allé à la plage avec mes amis et nous avons passé une excellente journée.", "pontuacao_maxima": 2.5}
        ]
    },
    "accord_participe": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Faites l'accord du participe passé si nécessaire : 'Les lettres que j'ai ___ (écrire) sont sur la table.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'accord approprié : 'Elles sont ___ (partir) très tôt pour la gare.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Accordez le participe passé avec le COD placé avant le verbe : 'Quelle belle chanson ! Tu l'as ___ (entendre) à la radio ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Réécrivez la phrase en accordant le verbe : 'Ces pommes, nous les avons ___ (manger) au dessert.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne forme accordée : 'La robe qu'elle a ___ est magnifique.'\n(a) acheté\n(b) achetée\n(c) achetées\n(d) achetés", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Identifiez la phrase avec un accord correct du participe passé :\n(a) Ils se sont téléphoné hier soir.\n(b) Ils se sont téléphonés hier soir.\n(c) Ils ont téléphonés hier soir.\n(d) Ils ont téléphoné hier soir.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez l'accord : 'Marie et Claire sont ___ à l'heure au rendez-vous.'\n(a) venue\n(b) venus\n(c) venues\n(d) venu", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Justifiez et corrigez l'accord dans : 'Les exercices que le professeur a donné étaient difficiles.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec le participe passé correctement accordé : 'Les photos que nous avons ___ (prendre) pendant le voyage sont superbes.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês, respeitando o acordo do particípio passado:", "texto_referencia": "As cartas que ela escreveu foram enviadas ontem.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e escreva a frase com o acordo correto:", "texto_referencia": "Toutes les fenêtres de la maison sont restées ouvertes cette nuit.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para avaliar pronúncia e ritmo:", "texto_referencia": "Les fleurs que tu as achetées pour mon anniversaire sentent très bon dans le salon.", "pontuacao_maxima": 2.5}
        ]
    },
    "negation": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase à la forme négative avec 'ne ... pas' : 'Alexandre mange de la viande rouge tous les jours.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Transformez à la forme négative en utilisant 'ne ... jamais' : 'Je prends toujours le métro à sept heures.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec les éléments de négation : 'Il ___ parle ___ anglais avec ses collègues.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase au passé composé à la forme négative : 'Nous avons regardé la télévision hier.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle est la négation correcte de la phrase 'Il a encore faim' ?\n(a) Il n'a plus faim.\n(b) Il n'a jamais faim.\n(c) Il n'a rien faim.\n(d) Il n'a personne faim.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne syntaxe négative au passé composé :\n(a) Je n'ai pas compris la leçon.\n(b) Je ai pas ne compris la leçon.\n(c) Je n'ai compris pas la leçon.\n(d) Je pas n'ai compris la leçon.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la phrase : 'Dans ce café, il ___ y a ___ de sucre.'\n(a) ne / pas\n(b) n' / pas\n(c) ne / rien\n(d) n' / plus", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Transformez la phrase affirmative à la négation absolue : 'Il y a quelqu'un dans la salle de classe.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe à la forme négative (ne ... pas) au présent : 'Nous ___ (ne pas aimer) le froid en hiver.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza a seguinte frase para o francês utilizando a negação correta:", "texto_referencia": "Eles não querem viajar sozinhos este ano.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase negativa em francês:", "texto_referencia": "Je ne comprends pas la réponse de cet exercice difficile.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta prestando atenção na elisão do 'ne':", "texto_referencia": "Nous n'avons pas le temps de déjeuner au restaurant aujourd'hui.", "pontuacao_maxima": 2.5}
        ]
    },
    "famille": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase avec le membre de la famille approprié : 'Le père de mon père est mon ___.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le possessif correct : 'J'adore ___ (mon/ma/mes) grand-mère car elle est très gentille.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Rédigez une phrase pour présenter votre frère ou votre sœur en francês (prénom, âge, profession).", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez le lien de parenté : 'La fille de ma tante est ma ___.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Comment appelle-t-on le frère de votre mère en français ?\n(a) Le cousin\n(b) L'oncle\n(c) Le neveu\n(d) Le beau-père", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez le déterminant possessif adéquat : '___ parents habitent dans une grande maison à Bordeaux.'\n(a) Mes\n(b) Mon\n(c) Ma\n(d) Sa", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "La sœur de mon père est ma :\n(a) Cousine\n(b) Nièce\n(c) Tante\n(d) Belle-sœur", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la phrase : 'Marc et Julie ont deux enfants : un fils et une ___.'\n(a) sœur\n(b) fille\n(c) mère\n(d) cousine", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent : 'Toute ma famille ___ (se réunir) le dimanche pour le déjeuner.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza a frase a seguir sobre família para o francês:", "texto_referencia": "Meus avós moram em uma casa perto do parque.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase sobre família em francês:", "texto_referencia": "Mon grand-père raconte toujours des histoires intéressantes à ses petits-enfants.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta com entonação clara:", "texto_referencia": "Ma famille est très unie : mes parents, mes deux frères et moi passons toutes nos vacances ensemble en Normandie.", "pontuacao_maxima": 2.5}
        ]
    },
    "verbes_present": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe du 1er groupe au présent : 'Nous ___ (parler) couramment français et portugais.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la terminaison correcte : 'Ils écout___ de la musique classique chaque soir.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au présent de l'indicatif : 'Tu ___ (habiter) dans quel quartier de Paris ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase avec le verbe 'aimer' au présent : 'Vous ___ (aimer) voyager pendant les vacances d'été ?'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle est la forme correcte au présent pour 'nous' avec le verbe 'manger' ?\n(a) mangons\n(b) mangeons\n(c) mangiez\n(d) mangez", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez la forme correcte : 'Elles ___ à l'université de la Sorbonne.'\n(a) étudient\n(b) étudies\n(c) étudiez\n(d) étudions", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle terminaison correspond au pronom 'tu' au présent pour les verbes en -er ?\n(a) -e\n(b) -es\n(c) -ent\n(d) -ons", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Je ___ (travailler) dans une entreprise internationale.'\n(a) travaille\n(b) travailles\n(c) travaillent\n(d) travaillons", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent : 'Chaque matin, vous ___ (commencer) le travail à huit heures.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o presente do indicativo:", "texto_referencia": "Nós moramos em um belo apartamento no centro da cidade.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase em francês:", "texto_referencia": "Les étudiants préparent leurs devoirs de français avec beaucoup de sérieux.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta prestando atenção nas ligações:", "texto_referencia": "Nous habitons ensemble et nous partageons un grand appartement lumineux au centre-ville.", "pontuacao_maxima": 2.5}
        ]
    },
    "articles": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'article défini approprié (le, la, l', les) : '___ soleil brille et ___ oiseaux chantent dans le jardin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'article indéfini (un, une, des) : 'J'ai acheté ___ nouveau livre et ___ stylos pour l'école.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec un article partitif (du, de la, de l', des) : 'Au petit-déjeuner, je prends ___ café avec ___ confiture.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez au négatif en observant la règle de l'article : 'J'ai un vélo' -> 'Je n'ai pas ___ vélo.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quel article partitif convient pour : 'Il boit ___ eau minérale fraîche.' ?\n(a) du\n(b) de la\n(c) de l'\n(d) des", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez l'article correct : 'C'est ___ amie brésilienne de Pierre.'\n(a) le\n(b) une\n(c) des\n(d) du", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Après une négation absolue, l'article indéfini ou partitif devient généralement :\n(a) du\n(b) des\n(c) de / d'\n(d) le / la", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Vous mangez ___ fromage après le plat principal ?'\n(a) du\n(b) le\n(c) un\n(d) des", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec l'article contracté ou partitif approprié : 'Le professeur parle ___ (à + les) élèves ___ (de + le) prochain examen.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza prestando atenção aos artigos definidos e partitivos:", "texto_referencia": "Eu tomo café com leite e como um pedaço de pão de manhã.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva com os artigos corretos:", "texto_referencia": "Le matin, je bois du thé chaud et je mange des croissants au beurre.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para praticar a fluidez e a pronúncia das vogais nasais:", "texto_referencia": "Dans mon quartier, il y a une boulangerie artisanale, du bon pain frais et des commerces accueillants.", "pontuacao_maxima": 2.5}
        ]
    },
    "imparfait": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe à l'imparfait pour exprimer une habitude : 'Quand nous étions petits, nous ___ (jouer) tous les jours dans le jardin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez à l'imparfait : 'Pendant les vacances, il ___ (faire) toujours un temps magnifique.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Choisissez entre passé composé et imparfait : 'Pendant que je lisais tranquillement, le téléphone ___ (sonner).'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe 'être' à l'imparfait : 'À cette époque, vous ___ (être) étudiants à Paris.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle terminaison prend l'imparfait avec le pronom 'ils' ?\n(a) -aient\n(b) -ait\n(c) -iez\n(d) -ions", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle phrase exprime une description ou une habitude dans le passé ?\n(a) Soudain, il a plu.\n(b) Tous les étés, nous allions à la mer.\n(c) Hier, j'ai fini à midi.\n(d) Il est entré rapidement.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez à l'imparfait : 'Tu ___ (finir) toujours tes cours à seize heures.'\n(a) finissais\n(b) finissait\n(c) as fini\n(d) finissaient", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Le radical de l'imparfait se forme à partir de quelle personne du présent ?\n(a) Je\n(b) Nous\n(c) Ils\n(d) Vous", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez les deux verbes au temps approprié (imparfait vs passé composé) : 'Il ___ (faire) beau quand tout à coup l'orage ___ (éclater).'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o Imparfait para expressar hábito passado:", "texto_referencia": "Quando eu era criança, eu lia muitos livros antes de dormir.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e escreva a frase em francês no imperfeito:", "texto_referencia": "Autrefois, le village était calme et les habitants vivaient simplement.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o trecho em voz alta prestando atenção na sonoridade do imperfeito:", "texto_referencia": "Quand j'avais dix ans, ma famille habitait dans un petit village au bord d'un lac magnifique.", "pontuacao_maxima": 2.5}
        ]
    },
    "pronoms": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Remplacez le mot souligné par le pronom COD approprié (le, la, l', les) : 'Je regarde ce film français ce soir' -> 'Je ___ regarde ce soir.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Remplacez le complément par un pronom COI (lui, leur) : 'Elle écrit une lettre à ses parents' -> 'Elle ___ écrit une lettre.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Répondez affirmativement en utilisant le pronom 'y' : 'Tu vas souvent au musée ?' -> 'Oui, j'___ vais souvent.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Répondez avec le pronom 'en' : 'Tu manges des fruits chaque jour ?' -> 'Oui, j'___ mange tous les jours.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quel pronom remplace 'à mon professeur' dans 'Je pose une question à mon professeur' ?\n(a) le\n(b) lui\n(c) leur\n(d) y", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Où se place le pronom personnel au passé composé ?\n(a) Après le participe passé\n(b) Entre l'auxiliaire et le participe\n(c) Avant l'auxiliaire\n(d) À la fin de la phrase", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Remplacez le complément dans : 'Vous connaissez cette histoire ?'\n(a) Oui, nous la connaissons.\n(b) Oui, nous lui connaissons.\n(c) Oui, nous y connaissons.\n(d) Oui, nous les connaissons.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Paul a acheté des croissants ? Oui, il ___ a acheté six.'\n(a) les\n(b) en\n(c) y\n(d) lui", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Réécrivez la phrase en remplaçant les compléments par les pronoms COD/COI adéquats : 'Nous donnons ces clés à nos voisins.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza utilizando o pronome adequado em francês:", "texto_referencia": "Eu o vejo todos os dias na estação de metrô.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase com pronomes:", "texto_referencia": "Je lui ai expliqué la situation et il m'a écouté attentivement.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta articulando claramente os pronomes:", "texto_referencia": "Si vous avez des questions sur cette leçon, posez-les-moi dès la fin du cours.", "pontuacao_maxima": 2.5}
        ]
    },
    "conditionnel_subjonctif": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Mettez le verbe au conditionnel présent pour exprimer un souhait poli : 'Nous ___ (vouloir) réserver une table pour deux personnes.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la structure de l'hypothèse : 'Si j'avais plus de temps, je ___ (voyager) à travers toute la France.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le verbe au subjonctif présent : 'Il faut absolument que vous ___ (faire) vos exercices.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au subjonctif après l'expression de volonté : 'Je souhaite qu'il ___ (venir) à notre réunion demain.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle forme est au conditionnel présent pour le verbe 'pouvoir' ?\n(a) Je pourrai\n(b) Je pourrais\n(c) Je peux\n(d) Je pouvais", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle conjonction exige obligatoirement le subjonctif ?\n(a) Pour que\n(b) Parce que\n(c) Pendant que\n(d) Dès que", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez au subjonctif : 'Il est important que nous ___ (être) à l'heure.'\n(a) sommes\n(b) soyons\n(c) serons\n(d) étions", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la formule de politesse : '___ (Aimer)-vous un verre d'eau fraîche ?'\n(a) Aimerez\n(b) Aimeriez\n(c) Aimez\n(d) Aimiez", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez au subjonctif présent : 'Le professeur exige que tous les étudiants ___ (apprendre) cette règle.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza utilizando o condicional de polidez:", "texto_referencia": "Eu gostaria de pedir um café e a conta, por favor.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase em francês:", "texto_referencia": "Il faudrait partir plus tôt pour éviter les embouteillages du matin.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para avaliar a entonação da hipótese:", "texto_referencia": "Si nous avions l'opportunité de vivre à Paris, nous visiterions tous les musées et jardins historiques.", "pontuacao_maxima": 2.5}
        ]
    },
    "prepositions": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de pays appropriée (en, au, aux) : 'Cet été, je vais passer mes vacances ___ France, puis ___ Portugal et enfin ___ États-Unis.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de ville ou de moyen de transport : 'Marie habite ___ Lyon et elle se déplace toujours ___ vélo.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de lieu appropriée (sur, sous, devant, derrière, dans) : 'Le chat dort paisiblement ___ la table du salon.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez : 'Nous allons ___ (à + le) cinéma ce soir, puis ___ (à + le) restaurant avec nos amis.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle préposition s'utilise devant un pays féminin comme la France ou l'Italie ?\n(a) à\n(b) en\n(c) au\n(d) aux", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Mon frère travaille ___ Brésil depuis deux ans.'\n(a) en\n(b) au\n(c) à\n(d) dans", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Devant un nom de ville, on utilise la préposition :\n(a) au\n(b) à\n(c) en\n(d) de", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'La pharmacie se trouve juste ___ face de la gare centrale.'\n(a) en\n(b) à\n(c) de\n(d) par", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec la préposition contractée (au, à la, à l', aux) : 'Dimanche, nous allons ___ (à + le) marché et les enfants vont ___ (à + les) manèges.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza com as preposições de lugar e transporte corretas:", "texto_referencia": "Eu moro em Paris e vou ao trabalho de metrô todos os dias.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase sobre deslocamentos:", "texto_referencia": "Nous voyageons en train pour visiter plusieurs villes en France et en Belgique.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta prestando atenção nas preposições e na melodia frasal:", "texto_referencia": "Pour aller au musée depuis l'hôtel, traversez le pont, tournez à droite sur le boulevard et continuez tout droit.", "pontuacao_maxima": 2.5}
        ]
    },
    "salutations": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez le dialogue de salutation : '- Bonjour, comment allez-vous ? - Je vais très bien, ___ (merci / de rien) !'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la présentation personnelle : 'Je m'___ (appeler) Lucas et j'ai vingt-quatre ans.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Associez la formule formelle pour prendre congé : 'Au ___ (revoir / merci) et bonne journée, Monsieur.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la réponse de nationalité : 'De quelle nationalité êtes-vous ? - Je suis ___ (brésilien / brésilienne).'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle formule de salutation est appropriée pour une rencontre formelle le soir ?\n(a) Salut !\n(b) Bonsoir Monsieur.\n(c) Coucou !\n(d) À plus !", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Pour demander poliment le nom de quelqu'un, on dit :\n(a) Comment vous vous appelez ?\n(b) C'est qui toi ?\n(c) Tu as quel nom ?\n(d) Où habitez-vous ?", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle est la réponse la plus courante à 'Enchanté' ?\n(a) Au revoir.\n(b) Enchanté(e), de même.\n(c) S'il vous plaît.\n(d) Bonne nuit.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Comment ça va ? - Ça va ___ , merci !'\n(a) bien\n(b) bon\n(c) beau\n(d) bonne", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe 's'appeler' au présent : 'Comment vous ___ (s'appeler), Madame ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza as saudações e apresentação para o francês:", "texto_referencia": "Bom dia, eu me chamo Jean e sou estudante de francês.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva as saudações em francês:", "texto_referencia": "Bonjour madame, enchanté de faire votre connaissance aujourd'hui.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta simulando uma apresentação formal e amigável:", "texto_referencia": "Bonjour à toutes et à tous, je m'appelle Julien et je suis très heureux d'être ici avec vous pour ce cours de français.", "pontuacao_maxima": 2.5}
        ]
    },
    "geral": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase en conjuguant le verbe entre parenthèses au présent : 'Chaque jour, nous ___ (étudier) la langue et la culture françaises.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le pronom ou l'article adéquat : 'Marie a acheté ___ beau bouquet de fleurs pour son amie.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase suivante à la forme négative : 'Pierre boit toujours du café le matin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au passé composé : 'Hier soir, les enfants ___ (dormir) très tôt.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne forme pour compléter : 'Nous ___ le dîner à vingt heures.'\n(a) préparons\n(b) préparent\n(c) préparez\n(d) préparions", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle est la phrase correcte au passé composé ?\n(a) Elle est venu hier.\n(b) Elle est venue hier.\n(c) Elle a venue hier.\n(d) Elle a venu hier.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Je ne bois ___ de café après dix-sept heures.'\n(a) pas\n(b) rien\n(c) aucun\n(d) plus", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez le mot correct : 'C'est un exercice très ___ pour s'entraîner.'\n(a) utile\n(b) utilise\n(c) utilité\n(d) utilisable", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent de l'indicatif : 'Nous ___ (choisir) d'étudier le français avec enthousiasme.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês a seguinte frase com precisão gramatical:", "texto_referencia": "Eu estudo francês todos os dias para viajar pela Europa.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase em francês:", "texto_referencia": "La pratique régulière est essentielle pour progresser rapidement en français.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta com boa articulação e fluência:", "texto_referencia": "Apprendre une nouvelle langue permet de découvrir de nouvelles cultures et d'ouvrir son esprit au monde.", "pontuacao_maxima": 2.5}
        ]
    }
}

def mapear_chave_tema(tema: str) -> str:
    t = (tema or "").lower()
    if any(k in t for k in ["accord", "participe"]):
        return "accord_participe"
    if any(k in t for k in ["passé", "passe", "composé", "compose"]):
        return "passe_compose"
    if any(k in t for k in ["négat", "negat", "ne ... pas", "ne pas"]):
        return "negation"
    if any(k in t for k in ["famill", "parent"]):
        return "famille"
    if any(k in t for k in ["1er groupe", "présent", "present", "verbe"]):
        return "verbes_present"
    if any(k in t for k in ["article", "défini", "defini", "indéfini", "indefini", "partitif"]):
        return "articles"
    if any(k in t for k in ["imparfait"]):
        return "imparfait"
    if any(k in t for k in ["pronom", "cod", "coi"]):
        return "pronoms"
    if any(k in t for k in ["conditionnel", "subjonctif", "hypothèse", "hypothese"]):
        return "conditionnel_subjonctif"
    if any(k in t for k in ["préposition", "preposition", "lieu", "déplacement", "deplacement"]):
        return "prepositions"
    if any(k in t for k in ["salutation", "présentation", "presentation"]):
        return "salutations"
    return "geral"

def gerar_questoes_pedagogicas_completas(tema: str, nivel: str = "A2", tipo: str = "Prova", quantidade: int = 4) -> list:
    chave = mapear_chave_tema(tema)
    banco_tema = BANCO_PEDAGOGICO_TEMAS.get(chave, BANCO_PEDAGOGICO_TEMAS["geral"])
    tipo_l = (tipo or "").strip().lower()

    if tipo_l in ["exercicios", "exercício", "exercicio", "exercícios"]:
        pool = banco_tema.get("exercicios", BANCO_PEDAGOGICO_TEMAS["geral"]["exercicios"])
        res = [dict(q) for q in pool]
        while len(res) < quantidade:
            res.extend([dict(q) for q in BANCO_PEDAGOGICO_TEMAS["geral"]["exercicios"]])
        return res[:quantidade]

    elif tipo_l in ["teste", "testes"]:
        pool = banco_tema.get("testes", BANCO_PEDAGOGICO_TEMAS["geral"]["testes"])
        res = [dict(q) for q in pool]
        while len(res) < quantidade:
            res.extend([dict(q) for q in BANCO_PEDAGOGICO_TEMAS["geral"]["testes"]])
        return res[:quantidade]

    else:
        pool = banco_tema.get("prova", BANCO_PEDAGOGICO_TEMAS["geral"]["prova"])
        res = [dict(q) for q in pool]
        while len(res) < quantidade:
            res.extend([dict(q) for q in BANCO_PEDAGOGICO_TEMAS["geral"]["prova"]])
        return res[:quantidade]

def eh_questao_valida(q: dict) -> bool:
    enunciado = (q.get("enunciado") or "").strip()
    texto_ref = (q.get("texto_referencia") or "").strip()
    tipo_q = (q.get("tipo_questao") or "").strip().lower()

    if not enunciado or len(enunciado) < 10:
        return False

    proibidos = [
        "complétez les phrases en utilisant la règle",
        "transformez les phrases suivantes en appliquant",
        "rédigez deux phrases correctes",
        "test de connaissance: conjuguez",
        "choisissez ou écrivez la forme correcte en français concernant",
        "identifiez l'erreur dans la phrase et réécrivez-la",
        "question rapide: traduisez en français",
        "exercice de fallback 1",
        "conjuguez au présent ou passé composé selon le sujet",
        "traduisez la phrase suivante pour le français ("
    ]
    if any(p in enunciado.lower() for p in proibidos):
        return False

    if tipo_q == "traducao":
        if (not texto_ref or texto_ref in ["La phrase", "Tradução contextual", "A frase"]) and not ('"' in enunciado or "'" in enunciado):
            return False

    if tipo_q in ["ditado", "leitura_oral"]:
        if len(texto_ref) < 8 or texto_ref in ["Le chat mange la souris.", "La phrase"]:
            return False

    if tipo_q in ["exercicio", "teste", "conjugacao", "complete", "multipla_escolha", "verdadeiro_falso"]:
        tem_frase = ('___' in enunciado) or ('"' in enunciado) or ("'" in enunciado) or ('(' in enunciado and ')' in enunciado) or ('\n' in enunciado) or ('vrai' in enunciado.lower()) or ('?' in enunciado) or ('(a)' in enunciado.lower())
        if not tem_frase:
            return False

    return True

def sanitizar_questoes_geradas(questoes: list, tema: str, nivel: str = "A2", tipo: str = "Prova", quantidade: int = 4) -> list:
    questoes_padrao = gerar_questoes_pedagogicas_completas(tema, nivel, tipo, quantidade)
    
    if not questoes:
        questoes_limpas = [dict(q) for q in questoes_padrao]
    else:
        questoes_limpas = []
        for idx, q in enumerate(questoes):
            if eh_questao_valida(q):
                questoes_limpas.append({
                    "tipo_questao": (q.get("tipo_questao") or "exercicio").strip(),
                    "enunciado": (q.get("enunciado") or "").strip(),
                    "texto_referencia": (q.get("texto_referencia") or "").strip(),
                    "pontuacao_maxima": float(q.get("pontuacao_maxima") or 2.5)
                })
            else:
                substituta = questoes_padrao[idx % len(questoes_padrao)]
                questoes_limpas.append(dict(substituta))

    # Garante quantidade solicitada
    while len(questoes_limpas) < quantidade:
        questoes_limpas.append(dict(questoes_padrao[len(questoes_limpas) % len(questoes_padrao)]))

    if len(questoes_limpas) > quantidade:
        questoes_limpas = questoes_limpas[:quantidade]

    # Distribui a pontuação entre as questões para somar exatamente 10.0 pts
    if questoes_limpas:
        n_q = len(questoes_limpas)
        base_pts = round(10.0 / n_q, 1)
        soma_pts = 0.0
        for q in questoes_limpas[:-1]:
            q["pontuacao_maxima"] = base_pts
            soma_pts += base_pts
        questoes_limpas[-1]["pontuacao_maxima"] = round(10.0 - soma_pts, 1)

    return questoes_limpas

# ===================== MÓDULO DE PROVAS MULTIMODAIS =====================
from werkzeug.utils import secure_filename

@app.route("/api/gerar_prova_completa_ia", methods=["POST"])
@login_required_prof
def api_gerar_prova_completa_ia():
    dados = request.json or {}
    tema = dados.get("tema", "").strip()
    nivel = dados.get("nivel", "A2").strip().upper()
    tipo = dados.get("tipo", "Prova").strip()
    quantidade = int(dados.get("quantidade", 4))
    formato_questoes = dados.get("formato_questoes", "aleatorio").strip().lower()
    if quantidade < 1:
        quantidade = 4

    if not tema:
        tema = "Grammaire Française"

    # Define instruções de formato de acordo com a seleção
    if formato_questoes == "multipla_escolha":
        formato_instrucao = f"""Gere exatamente {quantidade} questões de MÚLTIPLA ESCOLHA (QCM) sobre '{tema}' no nível {nivel}.
Cada questão DEVE conter:
- Enunciado com uma frase contextual autêntica em francês.
- Exatamente 4 opções de resposta: (a), (b), (c) e (d), sendo apenas uma correta.
No JSON retornado, use "tipo_questao": "multipla_escolha"."""

    elif formato_questoes == "verdadeiro_falso":
        formato_instrucao = f"""Gere exatamente {quantidade} questões de VERDADEIRO OU FALSO (Vrai ou Faux) sobre '{tema}' no nível {nivel}.
Cada questão DEVE apresentar uma frase ou afirmação em francês para o aluno analisar se é 'Vrai' ou 'Faux' e justificar.
No JSON retornado, use "tipo_questao": "verdadeiro_falso"."""

    elif formato_questoes == "complete":
        formato_instrucao = f"""Gere exatamente {quantidade} exercícios de PREENCHIMENTO DE LACUNAS (Complete a Frase) sobre '{tema}' no nível {nivel}.
Cada questão DEVE conter uma frase autêntica em francês com lacuna indicada por '___' ou verbo entre parênteses para conjugar/preencher.
No JSON retornado, use "tipo_questao": "complete"."""

    elif formato_questoes == "traducao":
        formato_instrucao = f"""Gere exatamente {quantidade} questões de TRADUÇÃO (Português para Francês) sobre '{tema}' no nível {nivel}.
Cada questão deve conter:
- "enunciado": instrução de tradução com a frase.
- "texto_referencia": a frase completa em português a ser traduzida.
No JSON retornado, use "tipo_questao": "traducao"."""

    elif formato_questoes == "ditado":
        formato_instrucao = f"""Gere exatamente {quantidade} questões de DITADO / COMPREENSÃO ORAL sobre '{tema}' no nível {nivel}.
Cada questão deve conter:
- "enunciado": "Ouça o áudio com atenção e transcreva a frase em francês:"
- "texto_referencia": frase completa, natural e correta em francês para síntese de voz nativa.
No JSON retornado, use "tipo_questao": "ditado"."""

    elif formato_questoes == "leitura_oral":
        formato_instrucao = f"""Gere exatamente {quantidade} questões de EXPRESSÃO ORAL / LEITURA EM VOZ ALTA sobre '{tema}' no nível {nivel}.
Cada questão deve conter:
- "enunciado": "Leia o texto em voz alta com clareza, boa entonação e ritmo:"
- "texto_referencia": frase ou texto expressivo em francês para o aluno gravar áudio.
No JSON retornado, use "tipo_questao": "leitura_oral"."""

    elif formato_questoes == "dissertativa":
        formato_instrucao = f"""Gere exatamente {quantidade} questões DISSERTATIVAS / RESPOSTA CURTA sobre '{tema}' no nível {nivel}.
Cada questão deve pedir para formular ou transformar uma frase em francês.
No JSON retornado, use "tipo_questao": "exercicio"."""

    else:
        # Modo 'aleatorio' / 'misto' / 'variado':
        if tipo.lower() in ["exercicios", "exercício", "exercicio", "exercícios"]:
            formato_instrucao = f"""Gere exatamente {quantidade} exercícios práticos com formatos variados e sorteados (alterne entre complete lacunas '___', tradução, múltipla escolha QCM e verdadeiro ou falso) sobre '{tema}' para o nível {nivel}.
Cada questão deve conter uma frase autêntica em francês para o aluno responder."""
        elif tipo.lower() in ["teste", "testes"]:
            formato_instrucao = f"""Gere exatamente {quantidade} questões objetivas com formatos variados e sorteados (sorteie entre múltipla escolha QCM com opções a/b/c/d e verdadeiro ou falso Vrai/Faux) sobre '{tema}' para o nível {nivel}."""
        else:
            # Prova formal multimodal
            formato_instrucao = f"""Gere exatamente {quantidade} questões para uma PROVA COMPLETA E VARIADA sobre '{tema}' no nível {nivel}.
Distribua os formatos de forma equilibrada e diversificada entre:
- 'complete': frase com lacuna '___' ou verbo entre parênteses.
- 'multipla_escolha': frase com opções (a), (b), (c), (d).
- 'verdadeiro_falso': afirmação para julgar Vrai ou Faux.
- 'traducao': frase em português no 'texto_referencia'.
- 'ditado': frase em francês no 'texto_referencia' para áudio.
- 'leitura_oral': texto em francês no 'texto_referencia' para gravação de fala."""

    prompt = f"""Atue como um professor nativo de francês língua estrangeira (FLE).
{formato_instrucao}

REGRA CRUCIAL DE QUALIDADE PEDAGÓGICA:
- Cada questão DEVE OBRIGATORIAMENTE conter frases autênticas e completas. NUNCA gere enunciados abstratos ou vazios.
- O aluno precisa ter a frase completa para poder responder.

Retorne EXATAMENTE um JSON válido no formato:
{{
  "questoes": [
    {{"tipo_questao": "...", "enunciado": "...", "texto_referencia": "", "pontuacao_maxima": 2.5}}
  ]
}}"""

    questoes = []
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        texto_limpo = re.sub(r"^```json\s*", "", response.text.strip(), flags=re.IGNORECASE)
        texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
        texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
        dados_ia = json.loads(texto_limpo)
        questoes = dados_ia.get("questoes", [])
    except Exception as e:
        print(f"Erro no Gemini ao gerar avaliação: {e}")
        questoes = []

    # Sanitiza, valida e garante quantidade e pontuação exatas (soma = 10.0 pts)
    questoes = sanitizar_questoes_geradas(questoes, tema, nivel, tipo, quantidade)

    return jsonify({"status": "sucesso", "questoes": questoes, "tipo": tipo, "formato": formato_questoes})

@app.route("/api/salvar_avaliacao", methods=["POST"])
@login_required_prof
def api_salvar_avaliacao():
    dados = request.json or {}
    try:
        titulo = dados.get("titulo", "Nova Avaliação").strip()
        tipo = dados.get("tipo", "Exercícios").strip()
        turma_id = int(dados.get("turma_id", 1))
        data_limite = dados.get("data_limite", "2026-12-31 23:59:00").strip()
        questoes = dados.get("questoes", [])

        if not questoes:
            return jsonify({"status": "erro", "mensagem": "Nenhuma questão informada para a avaliação."}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Valida turma_id existente
        cursor.execute("SELECT id FROM turmas WHERE id = ?", (turma_id,))
        if not cursor.fetchone():
            cursor.execute("SELECT id FROM turmas ORDER BY id ASC LIMIT 1")
            row_t = cursor.fetchone()
            if row_t:
                turma_id = row_t["id"]

        cursor.execute("INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES (?, ?, ?, ?)",
                       (titulo, tipo, turma_id, data_limite))
        avaliacao_id = cursor.lastrowid
        
        for q in questoes:
            tipo_q = q.get('tipo_questao') or ('exercicio' if tipo.lower() in ['exercicios', 'exercícios'] else 'teste')
            cursor.execute("INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima) VALUES (?, ?, ?, ?, ?)",
                           (avaliacao_id, tipo_q, q['enunciado'].strip(), q.get('texto_referencia', ''), float(q.get('pontuacao_maxima', 2.5))))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "avaliacao_id": avaliacao_id, "mensagem": f"{tipo} cadastrada com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/aluno/prova/<int:avaliacao_id>", methods=["GET"])
@login_required
def aluno_prova(avaliacao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM avaliacoes WHERE id = ?", (avaliacao_id,))
    avaliacao = dict(cursor.fetchone())
    cursor.execute("SELECT * FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_id,))
    questoes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template("aluno_prova.html", avaliacao=avaliacao, questoes=questoes, active_page="aluno_atividades")

@app.route("/api/enviar_prova", methods=["POST"])
@login_required
def api_enviar_prova():
    aluno_id = session.get("aluno_id")
    avaliacao_id = request.form.get("avaliacao_id")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Iterar sobre todas as chaves do FormData que começam com "questao_"
    for key in request.form.keys():
        if key.startswith("questao_"):
            q_id = key.split("_")[1]
            resposta_texto = request.form.get(key, "").strip()
            if not resposta_texto:
                continue

            # Busca detalhes da questão para avaliação via IA
            cursor.execute("""
                SELECT pq.enunciado, pq.texto_referencia, pq.tipo_questao, a.titulo
                FROM prova_questoes pq
                JOIN avaliacoes a ON pq.avaliacao_id = a.id
                WHERE pq.id = ?
            """, (q_id,))
            q_row = cursor.fetchone()

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
                upload_dir = os.path.join(app.root_path, "static", "uploads", "audios")
                os.makedirs(upload_dir, exist_ok=True)
                filename = secure_filename(f"aluno_{aluno_id}_q_{q_id}_{int(datetime.datetime.now().timestamp())}.webm")
                filepath = os.path.join(upload_dir, filename)
                audio_file.save(filepath)
                
                # Busca o texto de referência da questão para passar ao Gemini
                cursor.execute("SELECT texto_referencia FROM prova_questoes WHERE id = ?", (q_id,))
                q_row = cursor.fetchone()
                texto_ref = q_row["texto_referencia"] if q_row else ""
                
                feedback_ia = "Análise pendente."
                try:
                    import google.generativeai as genai
                    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
                    
                    # Lê os bytes salvos para enviar à IA
                    with open(filepath, "rb") as f:
                        audio_bytes = f.read()
                        
                    audio_blob = {
                        "mime_type": "audio/webm",
                        "data": audio_bytes
                    }
                    
                    prompt_audio = f"O aluno leu em francês: '{texto_ref}'. Analise o áudio anexo, atribua nota de 0-10 para a pronúncia e aponte erros de fonética. Retorne JSON no formato: {{\"nota\": 8.5, \"analise\": \"Sua justificativa\"}}"
                    
                    res = model.generate_content([prompt_audio, audio_blob])
                    
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

@app.route("/professor/correcao/<int:submissao_id>", methods=["GET"])
@login_required_prof
def professor_correcao(submissao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, a.nome as aluno_nome, pq.enunciado, pq.texto_referencia 
        FROM submissoes s 
        JOIN alunos a ON s.aluno_id = a.id
        JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        WHERE s.id = ?
    """, (submissao_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Submissão não encontrada", 404
    submissao = dict(row)
    return render_template("professor_correcao.html", submissao=submissao, active_page="prof_avaliacoes")

@app.route("/api/professor/salvar_correcao", methods=["POST"])
@login_required_prof
def api_salvar_correcao():
    dados = request.get_json() if request.is_json else request.form
    submissao_id = dados.get("submissao_id")
    nota_raw = dados.get("nota_professor")
    analise_professor = dados.get("analise_professor", "").strip()

    if not submissao_id or nota_raw is None or str(nota_raw).strip() == "":
        return jsonify({"status": "erro", "mensagem": "Submissão e nota são obrigatórios."}), 400

    try:
        nota = float(nota_raw)
        if nota < 0 or nota > 10:
            return jsonify({"status": "erro", "mensagem": "A nota deve ser entre 0 e 10."}), 400

        status_novo = "Correto" if nota >= 6.0 else "Incorreto"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE submissoes 
            SET nota_professor = ?, analise_professor = ?, status_resposta = ?
            WHERE id = ?;
        """, (nota, analise_professor or "Correção concluída pelo professor.", status_novo, submissao_id))
        conn.commit()
        conn.close()

        return jsonify({"status": "sucesso", "mensagem": "Correção salva com sucesso!"})
    except ValueError:
        return jsonify({"status": "erro", "mensagem": "Nota inválida."}), 400
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/professor/enviar_mensagem", methods=["POST"])
@login_required_prof
def api_professor_enviar_mensagem():
    prof_id = session.get("prof_id")
    dados = request.get_json() if request.is_json else request.form
    
    tipo_destinatario = dados.get("tipo_destinatario", "aluno")
    destinatario_id = dados.get("destinatario_id")
    assunto = dados.get("assunto", "").strip()
    corpo = dados.get("corpo", "").strip()

    if not assunto or not corpo or not destinatario_id:
        return jsonify({"status": "erro", "mensagem": "Assunto, destinatário e mensagem são obrigatórios."}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        total_enviadas = 0
        if tipo_destinatario == "turma":
            turma_id = int(destinatario_id)
            cursor.execute("SELECT id FROM alunos WHERE turma_id = ?", (turma_id,))
            alunos = cursor.fetchall()
            if not alunos:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Nenhum aluno encontrado nesta turma."}), 404
            
            for a in alunos:
                cursor.execute("""
                    INSERT INTO mensagens_inbox (remetente_id, destinatario_id, assunto, corpo)
                    VALUES (?, ?, ?, ?)
                """, (prof_id, a["id"], assunto, corpo))
                total_enviadas += 1
        else:
            aluno_id = int(destinatario_id)
            cursor.execute("SELECT id FROM alunos WHERE id = ?", (aluno_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Aluno não encontrado."}), 404
            cursor.execute("""
                INSERT INTO mensagens_inbox (remetente_id, destinatario_id, assunto, corpo)
                VALUES (?, ?, ?, ?)
            """, (prof_id, aluno_id, assunto, corpo))
            total_enviadas = 1

        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso", 
            "mensagem": f"Recado enviado com sucesso para {total_enviadas} aluno(s)!"
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# ===================== PLANOS DE AULA & SEQUÊNCIAS DIDÁTICAS =====================

@app.route("/professor/planos-aula", methods=["GET"])
@login_required_prof
def professor_planos_aula():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
    turmas = [dict(r) for r in cursor.fetchall()]

    # Contagens rápidas por ciclo
    cursor.execute("SELECT COUNT(*) FROM planos_aula WHERE nivel IN ('A1', 'A2')")
    total_iniciante = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM planos_aula WHERE nivel IN ('B1', 'B2')")
    total_intermediario = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM planos_aula WHERE nivel IN ('C1', 'C2')")
    total_avancado = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM planos_aula")
    total_planos = cursor.fetchone()[0]

    # Busca inicial de todos os planos
    cursor.execute("""
        SELECT p.*, t.nome as turma_nome
        FROM planos_aula p
        LEFT JOIN turmas t ON p.turma_id = t.id
        ORDER BY 
            CASE 
                WHEN p.nivel = 'A1' THEN 1
                WHEN p.nivel = 'A2' THEN 2
                WHEN p.nivel = 'B1' THEN 3
                WHEN p.nivel = 'B2' THEN 4
                WHEN p.nivel = 'C1' THEN 5
                WHEN p.nivel = 'C2' THEN 6
                ELSE 7
            END,
            p.aula_numero ASC, p.id ASC
    """)
    planos = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template(
        "professor_planos_aula.html",
        planos=planos,
        turmas=turmas,
        total_planos=total_planos,
        total_iniciante=total_iniciante,
        total_intermediario=total_intermediario,
        total_avancado=total_avancado,
        active_page="prof_planos"
    )

@app.route("/api/planos-aula", methods=["GET"])
@login_required_prof
def api_listar_planos():
    nivel = request.args.get("nivel", "").strip().upper()
    busca = request.args.get("busca", "").strip().lower()
    habilidade = request.args.get("habilidade", "").strip().upper()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT p.*, t.nome as turma_nome
        FROM planos_aula p
        LEFT JOIN turmas t ON p.turma_id = t.id
        WHERE 1=1
    """
    params = []

    if nivel and nivel != "TODOS":
        if nivel == "INICIANTE":
            query += " AND p.nivel IN ('A1', 'A2')"
        elif nivel == "INTERMEDIARIO":
            query += " AND p.nivel IN ('B1', 'B2')"
        elif nivel == "AVANCADO":
            query += " AND p.nivel IN ('C1', 'C2')"
        else:
            query += " AND p.nivel = ?"
            params.append(nivel)

    if habilidade and habilidade != "TODAS":
        query += " AND UPPER(p.habilidades) LIKE ?"
        params.append(f"%{habilidade}%")

    if busca:
        query += " AND (LOWER(p.tema) LIKE ? OR LOWER(p.conteudos) LIKE ? OR LOWER(p.objetivos) LIKE ?)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    query += """
        ORDER BY 
            CASE 
                WHEN p.nivel = 'A1' THEN 1
                WHEN p.nivel = 'A2' THEN 2
                WHEN p.nivel = 'B1' THEN 3
                WHEN p.nivel = 'B2' THEN 4
                WHEN p.nivel = 'C1' THEN 5
                WHEN p.nivel = 'C2' THEN 6
                ELSE 7
            END,
            p.aula_numero ASC, p.id ASC
    """

    cursor.execute(query, params)
    planos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"status": "sucesso", "total": len(planos), "planos": planos})

@app.route("/api/planos-aula/<int:plano_id>", methods=["GET"])
@login_required_prof
def api_obter_plano(plano_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, t.nome as turma_nome
        FROM planos_aula p
        LEFT JOIN turmas t ON p.turma_id = t.id
        WHERE p.id = ?
    """, (plano_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "erro", "mensagem": "Plano de aula não encontrado."}), 404
    return jsonify({"status": "sucesso", "plano": dict(row)})

@app.route("/api/planos-aula/cadastrar", methods=["POST"])
@login_required_prof
def api_cadastrar_plano():
    dados = request.get_json() if request.is_json else request.form
    tema = dados.get("tema", "").strip()
    nivel = dados.get("nivel", "A1").strip().upper()
    duracao = dados.get("duracao", "50 min").strip()
    objetivos = dados.get("objetivos", "").strip()

    if not tema or not objetivos:
        return jsonify({"status": "erro", "mensagem": "Tema e objetivos de aprendizagem são obrigatórios."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO planos_aula (
                aula_numero, tema, nivel, duracao, objetivos, habilidades,
                conteudos, metodologia, recursos, etapa_aquecimento,
                etapa_apresentacao, etapa_pratica, etapa_producao,
                etapa_fechamento, avaliacao_formativa, avaliacao_somativa,
                dever_casa, reforco, turma_id, criador_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(dados.get("aula_numero", 1)),
            tema,
            nivel,
            duracao,
            objetivos,
            dados.get("habilidades", "PO, PE, GR").strip(),
            dados.get("conteudos", "").strip(),
            dados.get("metodologia", "Abordagem comunicativa e ação-orientada").strip(),
            dados.get("recursos", "Material autêntico, fichas, áudio").strip(),
            dados.get("etapa_aquecimento", "").strip(),
            dados.get("etapa_apresentacao", "").strip(),
            dados.get("etapa_pratica", "").strip(),
            dados.get("etapa_producao", "").strip(),
            dados.get("etapa_fechamento", "").strip(),
            dados.get("avaliacao_formativa", "").strip(),
            dados.get("avaliacao_somativa", "").strip(),
            dados.get("dever_casa", "").strip(),
            dados.get("reforco", "").strip(),
            int(dados["turma_id"]) if dados.get("turma_id") and str(dados["turma_id"]).isdigit() else None,
            session.get("prof_id", 1)
        ))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Plano de aula '{tema}' cadastrado com sucesso!",
            "plano_id": novo_id
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/planos-aula/gerar-ia", methods=["POST"])
@login_required_prof
def api_gerar_plano_ia():
    dados = request.get_json() if request.is_json else request.form
    tema = dados.get("tema", "").strip()
    nivel = dados.get("nivel", "A2").strip().upper()
    duracao = dados.get("duracao", "50 min").strip()
    foco = dados.get("foco", "").strip()

    if not tema:
        return jsonify({"status": "erro", "mensagem": "Informe o tema da aula para a IA."}), 400

    prompt = f"""Atue como um especialista em didática e engenharia pedagógica de Francês Língua Estrangeira (FLE).
Elabore um Plano de Aula completo, rigoroso e profissional para:
- Tema: '{tema}'
- Nível CEFR: {nivel}
- Duração: {duracao}
{f"- Foco Pedagógico Específico: {foco}" if foco else ""}

Siga ESTRITAMENTE a metodologia FLE dos 10 elementos e a sequência didática P.P.P. (Présentation, Pratique, Production) com minutagem coerente com {duracao}.

Retorne EXATAMENTE um JSON válido com a estrutura abaixo (sem texto fora do JSON e sem markdown ```json):
{{
  "tema": "{tema}",
  "nivel": "{nivel}",
  "duracao": "{duracao}",
  "objetivos": "Objetivo de aprendizagem claro (ex: 'Saber pedir em restaurante e expressar cortesia')",
  "habilidades": "Siglas das habilidades principais (ex: PO, IO, CO, GR)",
  "conteudos": "Gramática, vocabulário e funções comunicativas trabalhadas",
  "metodologia": "Abordagem comunicativa, inductiva ou ação-orientada com tarefas",
  "recursos": "Materiais, áudios, slides, fichas de trabalho",
  "etapa_aquecimento": "5-10 min: Ativação de conhecimentos prévios e estímulo inicial",
  "etapa_apresentacao": "15-20 min: Introdução e modelagem do conteúdo",
  "etapa_pratica": "15-20 min: Prática guiada em duplas ou grupos com correção imediata",
  "etapa_producao": "15-20 min: Tarefa comunicativa livre, diálogo ou produção",
  "etapa_fechamento": "5-10 min: Síntese, feedback e orientações",
  "avaliacao_formativa": "Como verificar o aprendizado em aula (rubrica, role-play)",
  "avaliacao_somativa": "Sugestão de questão ou formato de prova para este tema",
  "dever_casa": "Exercício de fixação para casa",
  "reforco": "Atividade de remediação recomendada para quem apresentar dúvidas"
}}"""

    plano_gerado = None
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        texto_limpo = re.sub(r"^```json\s*", "", response.text.strip(), flags=re.IGNORECASE)
        texto_limpo = re.sub(r"^```\s*", "", texto_limpo)
        texto_limpo = re.sub(r"\s*```$", "", texto_limpo)
        plano_gerado = json.loads(texto_limpo)
    except Exception as e:
        print(f"[!] Erro no Gemini ao gerar plano de aula: {e}")
        # Fallback pedagógico inteligente
        plano_gerado = {
            "tema": tema,
            "nivel": nivel,
            "duracao": duracao,
            "objetivos": f"Compreender e aplicar estruturas linguísticas essenciais do tema '{tema}' no nível {nivel}.",
            "habilidades": "PO, PE, GR, CO",
            "conteudos": f"Vocabulário temático de '{tema}', estruturas gramaticais essenciais do nível {nivel} e marcadores discursivos.",
            "metodologia": "Abordagem comunicativa e método P.P.P. focado em interação em pares.",
            "recursos": "Projeção de imagens/slides, fichas pedagógicas de apoio e áudios de diálogo.",
            "etapa_aquecimento": "5-10 min: Imagens provocativas e levantamento do léxico que os alunos já conhecem sobre o tema.",
            "etapa_apresentacao": "15 min: Introdução das estruturas-chave e modelagem de diálogos com foco em pronúncia correta.",
            "etapa_pratica": "15 min: Exercício guiado de transformação e preenchimento de lacunas em duplas com verificação mediada.",
            "etapa_producao": "15 min: Simulação comunicativa (Role-play) ou elaboração de pequeno texto situacional em contexto real.",
            "etapa_fechamento": "5 min: Síntese dos conceitos principais no quadro e alinhamento de dúvidas frequentes.",
            "avaliacao_formativa": f"Observação da interação comunicativa em duplas e rubrica de precisão gramatical em '{tema}'.",
            "avaliacao_somativa": f"Questões integradas de compreensão e produção textual sobre '{tema}' na prova periódica.",
            "dever_casa": f"Elaboração de um texto de 8 a 10 linhas sobre '{tema}' aplicando as regras estudadas.",
            "reforco": "Prática de exercícios adicionais e escuta atenta dos áudios de referência no Assistente Fran."
        }

    # Salva automaticamente como novo plano
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO planos_aula (
            aula_numero, tema, nivel, duracao, objetivos, habilidades,
            conteudos, metodologia, recursos, etapa_aquecimento,
            etapa_apresentacao, etapa_pratica, etapa_producao,
            etapa_fechamento, avaliacao_formativa, avaliacao_somativa,
            dever_casa, reforco, criador_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        99,
        plano_gerado.get("tema", tema),
        plano_gerado.get("nivel", nivel),
        plano_gerado.get("duracao", duracao),
        plano_gerado.get("objetivos", ""),
        plano_gerado.get("habilidades", "PO, PE, GR"),
        plano_gerado.get("conteudos", ""),
        plano_gerado.get("metodologia", ""),
        plano_gerado.get("recursos", ""),
        plano_gerado.get("etapa_aquecimento", ""),
        plano_gerado.get("etapa_apresentacao", ""),
        plano_gerado.get("etapa_pratica", ""),
        plano_gerado.get("etapa_producao", ""),
        plano_gerado.get("etapa_fechamento", ""),
        plano_gerado.get("avaliacao_formativa", ""),
        plano_gerado.get("avaliacao_somativa", ""),
        plano_gerado.get("dever_casa", ""),
        plano_gerado.get("reforco", ""),
        session.get("prof_id", 1)
    ))
    plano_id = cursor.lastrowid
    conn.commit()
    conn.close()

    plano_gerado["id"] = plano_id
    return jsonify({
        "status": "sucesso",
        "mensagem": f"Plano de aula '{tema}' gerado com sucesso pela IA e salvo no catálogo!",
        "plano": plano_gerado
    })

@app.route("/api/planos-aula/<int:plano_id>/gerar-prova", methods=["POST"])
@login_required_prof
def api_plano_gerar_prova(plano_id):
    dados = request.get_json() if request.is_json else request.form
    turma_id = dados.get("turma_id")
    data_limite = dados.get("data_limite", "2026-12-31 23:59:00")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM planos_aula WHERE id = ?", (plano_id,))
    plano = cursor.fetchone()
    if not plano:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Plano de aula não encontrado."}), 404

    plano = dict(plano)

    # Valida se a turma informada existe; caso contrário, usa a primeira turma cadastrada
    cursor.execute("SELECT id FROM turmas WHERE id = ?", (turma_id,))
    if not cursor.fetchone():
        cursor.execute("SELECT id FROM turmas ORDER BY id ASC LIMIT 1")
        t_row = cursor.fetchone()
        turma_id = t_row["id"] if t_row else 14

    # Cria a avaliação no banco
    titulo_prova = f"Prova Alinhada: {plano['tema']} ({plano['nivel']})"
    tipo_prova = "Prova"

    cursor.execute("INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES (?, ?, ?, ?)",
                   (titulo_prova, tipo_prova, int(turma_id), data_limite))
    avaliacao_id = cursor.lastrowid

    questoes = []
    prompt_q = f"""Atue como professor de francês. Crie 4 questões para a prova '{titulo_prova}', alinhada ao nível {plano['nivel']}.
Conteúdo abordado na aula: {plano['conteudos']}.
Objetivo da aula: {plano['objetivos']}.

Gere estritamente 4 questões:
1. 'conjugacao' (enunciado pedindo conjugação de verbo do tema)
2. 'traducao' (enunciado pedindo tradução de frase do tema)
3. 'ditado' (texto_referencia com frase para o aluno ouvir e transcrever)
4. 'leitura_oral' (texto_referencia com frase/parágrafo para pronúncia oral)

Retorne EXATAMENTE um JSON:
{{
  "questoes": [
    {{"tipo_questao": "conjugacao", "enunciado": "...", "texto_referencia": "", "pontuacao_maxima": 2.5}},
    {{"tipo_questao": "traducao", "enunciado": "...", "texto_referencia": "...", "pontuacao_maxima": 2.5}},
    {{"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva:", "texto_referencia": "...", "pontuacao_maxima": 2.5}},
    {{"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para avaliar pronúncia:", "texto_referencia": "...", "pontuacao_maxima": 2.5}}
  ]
}}"""
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.0-flash")
        res_q = model.generate_content(prompt_q)
        t_limpo = re.sub(r"^```json\s*", "", res_q.text.strip(), flags=re.IGNORECASE)
        t_limpo = re.sub(r"^```\s*", "", t_limpo)
        t_limpo = re.sub(r"\s*```$", "", t_limpo)
        questoes = json.loads(t_limpo).get("questoes", [])
    except Exception as e:
        print(f"[!] Erro ao gerar questões de prova do plano via Gemini: {e}")
        questoes = []

    # Garante questões completas com frases reais para o aluno responder
    questoes = sanitizar_questoes_geradas(questoes, plano['tema'], plano['nivel'], "Prova", 4)

    for q in questoes:
        cursor.execute("""
            INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
            VALUES (?, ?, ?, ?, ?)
        """, (avaliacao_id, q["tipo_questao"], q["enunciado"], q.get("texto_referencia", ""), q.get("pontuacao_maxima", 2.5)))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "sucesso",
        "mensagem": f"Avaliação '{titulo_prova}' criada com sucesso a partir do Plano de Aula!",
        "avaliacao_id": avaliacao_id
    })

@app.route("/api/planos-aula/<int:plano_id>", methods=["DELETE"])
@login_required_prof
def api_excluir_plano(plano_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, tema FROM planos_aula WHERE id = ?", (plano_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Plano não encontrado."}), 404

    cursor.execute("DELETE FROM planos_aula WHERE id = ?", (plano_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso", "mensagem": f"Plano de aula '{row['tema']}' excluído com sucesso."})


# ===================== FÓRUM SOCRÁTICO =====================

@app.route("/forum", methods=["GET"])
def forum_lista():
    # Verifica se é aluno ou prof
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    
    if not aluno_id and not prof_id:
        return redirect(url_for("login"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    filtro_turma = request.args.get("turma", "todas").strip()
    busca = request.args.get("busca", "").strip()
    
    aluno_turma_id = None
    aluno_turma_nome = None
    total_minha_turma = 0
    turmas = []
    
    if prof_id:
        # 1. Carrega todas as turmas para o professor
        cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
        turmas_raw = cursor.fetchall()
        
        # 2. Contagens para o professor
        cursor.execute("SELECT COUNT(*) as cnt FROM forum_topicos WHERE turma_id IS NULL")
        total_geral = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM forum_topicos")
        total_todos = cursor.fetchone()["cnt"]
        
        cursor.execute("""
            SELECT turma_id, COUNT(*) as cnt 
            FROM forum_topicos 
            WHERE turma_id IS NOT NULL 
            GROUP BY turma_id
        """)
        counts_por_turma = {row["turma_id"]: row["cnt"] for row in cursor.fetchall()}
        
        turmas = []
        for t in turmas_raw:
            t_dict = dict(t)
            t_dict["total_topicos"] = counts_por_turma.get(t["id"], 0)
            turmas.append(t_dict)
            
        # 3. Consulta de tópicos com filtro
        query = """
            SELECT ft.*, p.nome as criador_nome, t.nome as turma_nome,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id) as total_mensagens
            FROM forum_topicos ft
            JOIN professores p ON ft.criador_id = p.id
            LEFT JOIN turmas t ON ft.turma_id = t.id
            WHERE 1=1
        """
        params = []
        
        if filtro_turma == "geral":
            query += " AND ft.turma_id IS NULL"
        elif filtro_turma != "todas" and filtro_turma.isdigit():
            query += " AND ft.turma_id = ?"
            params.append(int(filtro_turma))
            
        if busca:
            query += " AND (LOWER(ft.titulo) LIKE ? OR LOWER(ft.descricao) LIKE ?)"
            termo = f"%{busca.lower()}%"
            params.extend([termo, termo])
            
        query += " ORDER BY ft.data_criacao DESC"
        cursor.execute(query, params)
        topicos = [dict(row) for row in cursor.fetchall()]
        
    else:
        # Visão do Aluno: restrito à sua turma e ao Fórum Geral
        cursor.execute("""
            SELECT a.turma_id, t.nome as turma_nome 
            FROM alunos a 
            LEFT JOIN turmas t ON a.turma_id = t.id 
            WHERE a.id = ?
        """, (aluno_id,))
        aluno_info = cursor.fetchone()
        aluno_turma_id = aluno_info["turma_id"] if aluno_info else None
        aluno_turma_nome = aluno_info["turma_nome"] if aluno_info else "Minha Turma"
        
        # Contagens para o aluno
        cursor.execute("SELECT COUNT(*) as cnt FROM forum_topicos WHERE turma_id IS NULL")
        total_geral = cursor.fetchone()["cnt"]
        
        if aluno_turma_id:
            cursor.execute("SELECT COUNT(*) as cnt FROM forum_topicos WHERE turma_id = ?", (aluno_turma_id,))
            total_minha_turma = cursor.fetchone()["cnt"]
        else:
            total_minha_turma = 0
            
        total_todos = total_geral + total_minha_turma
        
        # Consulta de tópicos com filtro restrito
        query = """
            SELECT ft.*, p.nome as criador_nome, t.nome as turma_nome,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id) as total_mensagens
            FROM forum_topicos ft
            JOIN professores p ON ft.criador_id = p.id
            LEFT JOIN turmas t ON ft.turma_id = t.id
            WHERE (ft.turma_id = ? OR ft.turma_id IS NULL)
        """
        params = [aluno_turma_id]
        
        if filtro_turma == "geral":
            query += " AND ft.turma_id IS NULL"
        elif filtro_turma == "minha" or (aluno_turma_id and filtro_turma == str(aluno_turma_id)):
            query += " AND ft.turma_id = ?"
            params.append(aluno_turma_id)
            
        if busca:
            query += " AND (LOWER(ft.titulo) LIKE ? OR LOWER(ft.descricao) LIKE ?)"
            termo = f"%{busca.lower()}%"
            params.extend([termo, termo])
            
        query += " ORDER BY ft.data_criacao DESC"
        cursor.execute(query, params)
        topicos = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    
    active_page = "aluno_forum" if aluno_id else "prof_forum"
    return render_template(
        "forum_lista.html",
        topicos=topicos,
        is_prof=bool(prof_id),
        turmas=turmas,
        total_geral=total_geral,
        total_todos=total_todos,
        total_minha_turma=total_minha_turma,
        aluno_turma_id=aluno_turma_id,
        aluno_turma_nome=aluno_turma_nome,
        filtro_ativo=filtro_turma,
        busca=busca,
        active_page=active_page
    )


@app.route("/forum/topico/<int:topico_id>", methods=["GET"])
def forum_topico(topico_id):
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    
    if not aluno_id and not prof_id:
        return redirect(url_for("login"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ft.*, t.nome as turma_nome, p.nome as criador_nome
        FROM forum_topicos ft
        JOIN professores p ON ft.criador_id = p.id
        LEFT JOIN turmas t ON ft.turma_id = t.id
        WHERE ft.id = ?
    """, (topico_id,))
    topico = cursor.fetchone()
    if not topico:
        conn.close()
        return "Tópico não encontrado", 404
        
    # Verificação de segurança: aluno só pode ver tópicos de sua turma ou Fórum Geral
    if aluno_id and not prof_id:
        cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
        aluno_turma = cursor.fetchone()
        aluno_turma_id = aluno_turma["turma_id"] if aluno_turma else None
        
        if topico["turma_id"] is not None and topico["turma_id"] != aluno_turma_id:
            conn.close()
            flash("Acesso restrito: este tópico de discussão é exclusivo de outra turma.", "warning")
            return redirect(url_for("forum_lista"))
            
    cursor.execute("""
        SELECT fm.*, 
               CASE WHEN fm.autor_tipo = 'Aluno' THEN a.nome
                    WHEN fm.autor_tipo = 'Professor' THEN p.nome
                    ELSE 'Assistente Fran' END as autor_nome
        FROM forum_mensagens fm
        LEFT JOIN alunos a ON fm.autor_id = a.id AND fm.autor_tipo = 'Aluno'
        LEFT JOIN professores p ON fm.autor_id = p.id AND fm.autor_tipo = 'Professor'
        WHERE fm.topico_id = ?
        ORDER BY fm.data_envio ASC
    """, (topico_id,))
    
    mensagens = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    active_page = "aluno_forum" if aluno_id else "prof_forum"
    return render_template(
        "forum_topico.html",
        topico=dict(topico),
        mensagens=mensagens,
        is_prof=bool(prof_id),
        active_page=active_page
    )


def processar_resposta_ia(topico_id, mensagem_aluno):
    """ Roda em background para nao travar o Flask """
    prompt = f"""
    Atue como o Assistente Fran, um tutor socrático de francês em um fórum escolar. 
    O aluno escreveu: '{mensagem_aluno}'. 
    Avalie se há erros gramaticais ou de vocabulário. 
    Se estiver perfeito, retorne um elogio curto. 
    Se houver erro, NÃO dê a resposta direta. Formule uma pergunta gentil que faça o aluno refletir sobre o erro gramatical. 
    Retorne EXATAMENTE um JSON com as chaves 'precisa_intervencao' (booleano) e 'resposta_ia' (texto).
    """
    try:
        import google.generativeai as genai
        # Como estamos em thread isolada, podemos apenas criar uma nova ref caso necessite ou usar o genai do app
        model = genai.GenerativeModel("gemini-2.0-flash")
        resposta = model.generate_content(prompt)
        conteudo = resposta.text
        
        # Parse JSON
        import re, json
        json_str = conteudo
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            json_str = match.group(0)
        dados_ia = json.loads(json_str)
        
        if dados_ia.get("precisa_intervencao") or True: # Ou True pra garantir que a IA responda se for elogio
            resposta_ia = dados_ia.get("resposta_ia", "Très bien!")
            
            # Conecta no DB em background
            import sqlite3
            import os
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo)
                VALUES (?, NULL, 'IA', ?)
            """, (topico_id, resposta_ia))
            conn.commit()
            conn.close()
            
    except Exception as e:
        print("Erro na IA do forum:", str(e))


@app.route("/api/forum/responder", methods=["POST"])
def api_forum_responder():
    dados = request.get_json() if request.is_json else request.form
    topico_id = dados.get("topico_id")
    conteudo = dados.get("conteudo", "").strip()
    
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    
    if not aluno_id and not prof_id:
        return jsonify({"status": "erro", "mensagem": "Não autorizado"}), 401
        
    if not conteudo or not topico_id:
        return jsonify({"status": "erro", "mensagem": "Dados incompletos"}), 400
        
    autor_id = prof_id if prof_id else aluno_id
    autor_tipo = "Professor" if prof_id else "Aluno"
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Validação de segurança para aluno
        if autor_tipo == "Aluno":
            cursor.execute("SELECT turma_id FROM forum_topicos WHERE id = ?", (topico_id,))
            top = cursor.fetchone()
            if not top:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Tópico não encontrado"}), 404
            if top["turma_id"] is not None:
                cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
                aluno_t = cursor.fetchone()
                if not aluno_t or aluno_t["turma_id"] != top["turma_id"]:
                    conn.close()
                    return jsonify({"status": "erro", "mensagem": "Acesso não autorizado para esta turma."}), 403
                    
        cursor.execute("""
            INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo)
            VALUES (?, ?, ?, ?)
        """, (topico_id, autor_id, autor_tipo, conteudo))
        conn.commit()
        conn.close()
        
        # Dispara IA em background SE for aluno
        if autor_tipo == "Aluno" and genai_model is not None:
            thread = threading.Thread(target=processar_resposta_ia, args=(topico_id, conteudo))
            thread.start()
            
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route("/api/forum/criar_topico", methods=["POST"])
@login_required_prof
def api_forum_criar_topico():
    dados = request.get_json() if request.is_json else request.form
    titulo = dados.get("titulo", "").strip()
    descricao = dados.get("descricao", "").strip()
    turma_id = dados.get("turma_id")
    categoria = dados.get("categoria", "geral").strip().lower() or "geral"
    prof_id = session.get("prof_id")
    
    if not titulo:
        return jsonify({"status": "erro", "mensagem": "O título do tópico é obrigatório."}), 400
        
    turma_id_val = None
    if turma_id and str(turma_id).strip().lower() not in ["geral", "", "none"]:
        try:
            turma_id_val = int(turma_id)
        except ValueError:
            turma_id_val = None
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id, categoria)
            VALUES (?, ?, ?, ?, ?)
        """, (titulo, descricao, prof_id, turma_id_val, categoria))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "topico_id": novo_id})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500



# ===================== API DO PROFESSOR (DASHBOARD) =====================

@app.route("/api/alunos_por_turma/<turma_id>", methods=["GET"])
@login_required_prof
def api_alunos_por_turma(turma_id):
    if turma_id == "todas" or not turma_id:
        return jsonify([])
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ? ORDER BY nome ASC", (turma_id,))
        alunos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(alunos)
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/dashboard/estatisticas", methods=["GET"])
@login_required_prof
def api_dashboard_estatisticas():
    turma_id = request.args.get("turma_id", "")
    nivel_cefr = request.args.get("nivel_cefr", "")
    aluno_id = request.args.get("aluno_id", "")

    # Prepara variaveis para binding SQL
    t_id = int(turma_id) if turma_id and turma_id != "todas" else None
    n_cefr = nivel_cefr if nivel_cefr and nivel_cefr != "todos" else None
    a_id = int(aluno_id) if aluno_id and aluno_id != "todos" else None

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Query 1: Desempenho Geral (Agregação de status_resposta)
        sql_geral = """
            SELECT s.status_resposta, COUNT(s.id) as total 
            FROM submissoes s
            JOIN alunos a ON s.aluno_id = a.id
            WHERE (? IS NULL OR a.turma_id = ?) 
              AND (? IS NULL OR a.nivel_cefr = ?)
              AND (? IS NULL OR a.id = ?)
            GROUP BY s.status_resposta;
        """
        cursor.execute(sql_geral, (t_id, t_id, n_cefr, n_cefr, a_id, a_id))
        rows_geral = cursor.fetchall()
        
        geral_dict = {"Correto": 0, "Parcialmente Correto": 0, "Incorreto": 0}
        for row in rows_geral:
            st = row["status_resposta"]
            if st in geral_dict:
                geral_dict[st] = row["total"]
            else:
                geral_dict[st] = geral_dict.get(st, 0) + row["total"]

        # Query 2: Desempenho por Tema Gramatical (Acertos, Parciais e Erros)
        sql_temas = """
            SELECT COALESCE(t.nome_tema, 'Prova Multimodal') as nome_tema,
                   SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
                   SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
                   SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros
            FROM submissoes s
            LEFT JOIN exercicios e ON s.exercicio_id = e.id
            LEFT JOIN temas t ON e.tema_id = t.id
            JOIN alunos a ON s.aluno_id = a.id
            WHERE (? IS NULL OR a.turma_id = ?) 
              AND (? IS NULL OR a.nivel_cefr = ?)
              AND (? IS NULL OR a.id = ?)
            GROUP BY COALESCE(t.nome_tema, 'Prova Multimodal')
            ORDER BY (acertos + parciais + erros) DESC, nome_tema ASC;
        """
        cursor.execute(sql_temas, (t_id, t_id, n_cefr, n_cefr, a_id, a_id))
        rows_temas = cursor.fetchall()

        temas_labels = []
        temas_acertos = []
        temas_parciais = []
        temas_erros = []
        for row in rows_temas:
            temas_labels.append(row["nome_tema"])
            temas_acertos.append(int(row["acertos"] or 0))
            temas_parciais.append(int(row["parciais"] or 0))
            temas_erros.append(int(row["erros"] or 0))

        conn.close()

        total_sub = sum(geral_dict.values())
        corretos = geral_dict.get("Correto", 0)
        parciais = geral_dict.get("Parcialmente Correto", 0)
        incorretos = geral_dict.get("Incorreto", 0)
        pct_c = round((corretos / total_sub * 100), 1) if total_sub > 0 else 0
        pct_p = round((parciais / total_sub * 100), 1) if total_sub > 0 else 0
        pct_i = round((incorretos / total_sub * 100), 1) if total_sub > 0 else 0

        return jsonify({
            "status": "sucesso",
            "metricas": {
                "total": total_sub,
                "corretos": corretos,
                "parciais": parciais,
                "incorretos": incorretos,
                "pct_correto": pct_c,
                "pct_parcial": pct_p,
                "pct_incorreto": pct_i
            },
            "desempenho_geral": {
                "labels": list(geral_dict.keys()),
                "data": list(geral_dict.values())
            },
            "desempenho_tema": {
                "labels": temas_labels,
                "acertos": temas_acertos,
                "parciais": temas_parciais,
                "erros": temas_erros
            },
            "dificuldade_tema": {
                "labels": temas_labels[:5],
                "data": temas_erros[:5]
            }
        })

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route("/api/avaliacoes/<int:avaliacao_id>/submissoes", methods=["GET"])
@login_required_prof
def api_avaliacao_submissoes(avaliacao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, tipo, turma_id, data_limite FROM avaliacoes WHERE id = ?", (avaliacao_id,))
    av_row = cursor.fetchone()
    if not av_row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404

    cursor.execute("""
        SELECT s.id, a.nome as aluno_nome, a.matricula, pq.enunciado, pq.tipo_questao, pq.pontuacao_maxima,
               s.resposta_aluno, s.arquivo_audio_path, s.status_resposta, s.feedback_ia,
               s.nota_professor, s.analise_professor, s.data_hora
        FROM submissoes s
        JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        JOIN alunos a ON s.aluno_id = a.id
        WHERE pq.avaliacao_id = ?
        ORDER BY a.nome ASC, s.id ASC;
    """, (avaliacao_id,))
    submissoes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"status": "sucesso", "avaliacao": dict(av_row), "submissoes": submissoes})


# ============================================================================
# GUIA GRAMATICAL FLE (PÁGINA COMPLETA DEDICADA & API DE CONJUGAÇÃO)
# ============================================================================

from guia_fle_data import VERBOS_CONJUGADOS, TEMAS_GUIA_FLE

@app.route("/guia-fle", methods=["GET"])
def guia_fle():
    """Página completa dedicada do Guia Gramatical FLE com barra lateral e conjugador interativo."""
    return render_template(
        "guia_fle.html",
        active_page="guia_fle",
        verbos=VERBOS_CONJUGADOS,
        temas=TEMAS_GUIA_FLE
    )

@app.route("/api/guia-fle/verbo/<verb_id>", methods=["GET"])
def api_guia_fle_verbo(verb_id):
    """API para retornar conjugação completa, tempos e exemplos de um verbo."""
    verb_key = str(verb_id).strip().lower()
    if verb_key in VERBOS_CONJUGADOS:
        return jsonify({"status": "sucesso", "verbo": VERBOS_CONJUGADOS[verb_key]})
    return jsonify({"status": "erro", "mensagem": f"Verbo '{verb_id}' não encontrado."}), 404


if __name__ == "__main__":
    porta = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"[*] Assistente Fran rodando em: http://127.0.0.1:{porta}")
    app.run(host="127.0.0.1", port=porta, debug=debug)


