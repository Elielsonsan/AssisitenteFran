from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
from blueprints.extensions import get_db, login_required, login_required_prof, parse_retorno_gemini_frances, BASE_DIR, GEMINI_MODEL_NAME, genai_model
import sqlite3, json, random, datetime, re, os, csv, io, threading

forum_bp = Blueprint('forum', __name__)

@forum_bp.route("/professor/forum", methods=["GET"])
@login_required_prof
def prof_forum():
    return redirect(url_for("forum.forum_lista"))

# ===================== MÓDULO DO ALUNO =====================

@forum_bp.route("/aluno/forum", methods=["GET"])
@login_required
def aluno_forum():
    return redirect(url_for("forum.forum_lista"))

@forum_bp.route("/forum", methods=["GET"])
def forum_lista():
    # Verifica se é aluno ou prof
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    
    if not aluno_id and not prof_id:
        return redirect(url_for("auth.login"))
        
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
            SELECT ft.*, p.nome_completo as criador_nome, t.nome as turma_nome,
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
            SELECT ft.*, p.nome_completo as criador_nome, t.nome as turma_nome,
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


@forum_bp.route("/forum/topico/<int:topico_id>", methods=["GET"])
def forum_topico(topico_id):
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    
    if not aluno_id and not prof_id:
        return redirect(url_for("auth.login"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ft.*, t.nome as turma_nome, p.nome_completo as criador_nome
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
            return redirect(url_for("forum.forum_lista"))
            
    cursor.execute("""
        SELECT fm.*, 
               CASE WHEN fm.autor_tipo = 'Aluno' THEN a.nome_completo
                    WHEN fm.autor_tipo = 'Professor' THEN p.nome_completo
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
        if not genai_model:
            return
        resposta = genai_model.generate_content(prompt)
        conteudo = resposta.text
        
        # Parse JSON
        import re, json
        json_str = conteudo
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            json_str = match.group(0)
        dados_ia = json.loads(json_str)
        
        if dados_ia.get("precisa_intervencao", True):
            resposta_ia = dados_ia.get("resposta_ia", "Très bien!")
            
            # Conecta no DB raiz em background
            DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")
            conn = sqlite3.connect(DB_PATH, timeout=15.0)
            c = conn.cursor()
            c.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo)
                VALUES (?, NULL, 'IA', ?)
            """, (topico_id, resposta_ia))
            conn.commit()
            conn.close()
            
    except Exception as e:
        print("Erro na IA do forum:", str(e))


@forum_bp.route("/api/forum/responder", methods=["POST"])
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
        if autor_tipo == "Aluno" :
            thread = threading.Thread(target=processar_resposta_ia, args=(topico_id, conteudo))
            thread.start()
            
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/criar_topico", methods=["POST"])
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

