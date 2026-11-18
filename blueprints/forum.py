from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
import blueprints.extensions as ext
from blueprints.extensions import get_db, login_required, login_required_prof, parse_retorno_gemini_frances, BASE_DIR, GEMINI_MODEL_NAME
import sqlite3, json, random, datetime, re, os, csv, io, threading

forum_bp = Blueprint('forum', __name__)


def _garantir_colunas_forum(cursor, conn=None):
    """Garante colunas incrementais criador_tipo e autor_aluno_id em forum_topicos."""
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(forum_topicos)").fetchall()]
    alterou = False
    if cols:
        if "criador_tipo" not in cols:
            cursor.execute("ALTER TABLE forum_topicos ADD COLUMN criador_tipo TEXT DEFAULT 'Professor'")
            cursor.execute("UPDATE forum_topicos SET criador_tipo = 'Professor' WHERE criador_tipo IS NULL")
            alterou = True
        if "autor_aluno_id" not in cols:
            cursor.execute("ALTER TABLE forum_topicos ADD COLUMN autor_aluno_id INTEGER")
            alterou = True
    if alterou and conn is not None:
        conn.commit()


def gerar_resposta_socratica_fle(titulo_topico, categoria, mensagem_aluno):
    """Motor socrático FLE determinístico para orientar alunos em francês mesmo sem API externa."""
    msg = (mensagem_aluno or "").strip()
    msg_low = msg.lower()
    titulo = (titulo_topico or "discussão FLE").strip()
    cat = (categoria or "geral").strip().lower()

    # 1. Desvios clássicos de Passé Composé (Auxiliar Être vs Avoir / Maison d'Être)
    if re.search(
        r"\b(?:avons|as|a|ai|ont|avez)\s+(?:aller|all[ée]e?s?|parti[er]?s?|arriv[ée]e?s?|venu[es]?|rest[ée]e?s?|tomb[ée]e?s?|n[ée]e?s?|sorti[es]?)\b",
        msg_low,
    ):
        return (
            "Observe com atenção o verbo principal no *Passé Composé*! Verbos de movimento e mudança de estado "
            "(como *aller, partir, arriver, venir*) pertencem à **Maison d'Être** e exigem o auxiliar **être**, "
            "além da concordância do particípio. Qual auxiliar você usaria aqui para corrigir a frase?"
        )

    # 2. Negação com partitivos (ne ... pas de)
    if re.search(r"\b(?:pas|jamais|plus)\s+(?:du|de\s+la|des)\b", msg_low):
        return (
            "Quase lá! Em frases negativas em francês (`ne ... pas`), os artigos partitivos e indefinidos "
            "(*du, de la, des*) sofrem uma transformação importante. Como fica a expressão sem o artigo definido combinado?"
        )

    # 3. Subjonctif após necessidade
    if re.search(r"\b(?:il\s+faut\s+que|est\s+n[ée]cessaire\s+que)\b", msg_low) and re.search(
        r"\b(?:prends|fais|vas|es|as|est|peux|veux|aller|faire)\b", msg_low
    ):
        return (
            "Boa tentativa com *il faut que*! Lembre-se de que expressões de necessidade pedem o **Subjonctif Présent**. "
            "Como ficaria o verbo na forma do subjuntivo depois de *que*?"
        )

    # 4. Pronomes COD / COI com verbos de comunicação
    if re.search(r"\b(?:les|la|le)\s+(?:t[ée]l[ée]phone|parle|[ée]cris|r[ée]ponds)\b", msg_low) or re.search(
        r"\bparle\s+[àa]\s+(?:lui|elle|eux|elles)\b", msg_low
    ):
        return (
            "Atenção à regência em francês! Verbos como *parler à*, *téléphoner à* e *écrire à* introduzem um objeto indireto (COI). "
            "Qual pronome (singular ou plural) substitui *à quelqu'un* antes do verbo?"
        )

    # 5. Perguntas ou dúvidas diretas do estudante
    eh_duvida = ("?" in msg) or any(
        w in msg_low
        for w in ("dúvida", "duvida", "como ", "por que", "porque", "não entendi", "nao entendi", "explica", "diferença", "diferenca", "ajuda", "quand ", "comment ")
    )
    if eh_duvida:
        dica_cat = {
            "gramatica": "analisar qual é o sujeito, o tempo verbal e o auxiliar ou pronome envolvido",
            "dicas": "reparar nas vogais nasais, liaisons e sílabas finais mudas",
            "vocabulario": "observar o gênero da palavra e em qual contexto cotidiano ela aparece",
            "cultura": "conectar a expressão ao contexto cultural francófono do tema",
            "debate": "estruturar sua ideia com um conector lógico como *À mon avis* ou *Cependant*",
        }.get(cat, "observar a estrutura da frase e testar uma construção curta")
        return (
            f"Ótima questão sobre « {titulo} »! Antes da resposta pronta, experimente {dica_cat}. "
            "Você consegue formular uma frase curta em francês aplicando essa ideia (pode começar com *À mon avis...* ou *Par exemple...*)?"
        )

    # 6. Contribuição afirmativa
    return (
        f"Très bonne contribution ! 👏 Sua participação em « {titulo} » mantém a discussão ativa. "
        "Pour approfondir en français : você consegue acrescentar um exemplo curto usando um conector como *Par exemple* ou *Cependant*?"
    )

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
    _garantir_colunas_forum(cursor, conn)

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
            SELECT ft.*,
                   COALESCE(ft.criador_tipo, 'Professor') as criador_tipo,
                   CASE WHEN COALESCE(ft.criador_tipo, 'Professor') = 'Aluno'
                        THEN COALESCE(al_c.nome_completo, 'Estudante')
                        ELSE COALESCE(p.nome_completo, 'Docente') END as criador_nome,
                   t.nome as turma_nome,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id) as total_mensagens,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id AND autor_tipo = 'IA') as total_ia,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id AND autor_tipo = 'Professor' AND autor_id = ?) as minhas_respostas
            FROM forum_topicos ft
            LEFT JOIN professores p ON ft.criador_id = p.id
            LEFT JOIN alunos al_c ON ft.autor_aluno_id = al_c.id
            LEFT JOIN turmas t ON ft.turma_id = t.id
            WHERE 1=1
        """
        params = [prof_id]

        if filtro_turma == "geral":
            query += " AND ft.turma_id IS NULL"
        elif filtro_turma != "todas" and filtro_turma.isdigit():
            query += " AND ft.turma_id = ?"
            params.append(int(filtro_turma))

        if busca:
            query += " AND (LOWER(ft.titulo) LIKE ? OR LOWER(ft.descricao) LIKE ?)"
            termo = f"%{busca.lower()}%"
            params.extend([termo, termo])

        query += " ORDER BY ft.id DESC, ft.data_criacao DESC"
        cursor.execute(query, params)
        topicos = []
        for row in cursor.fetchall():
            t_item = dict(row)
            t_item["tem_ia"] = bool((t_item.get("total_ia") or 0) > 0)
            t_item["aluno_participou"] = bool(
                (t_item.get("minhas_respostas") or 0) > 0
                or (t_item.get("criador_tipo") == "Professor" and t_item.get("criador_id") == prof_id)
            )
            t_item["sem_resposta_prof"] = bool(
                (t_item.get("minhas_respostas") or 0) == 0
                and t_item.get("criador_tipo") == "Aluno"
            )
            topicos.append(t_item)

        cursor.execute("SELECT COUNT(*) as c FROM forum_mensagens WHERE autor_tipo = 'Professor' AND autor_id = ?", (prof_id,))
        msgs_user = cursor.fetchone()["c"] or 0
        cursor.execute("SELECT COUNT(*) as c FROM forum_topicos WHERE COALESCE(criador_tipo, 'Professor') = 'Professor' AND criador_id = ?", (prof_id,))
        tops_user = cursor.fetchone()["c"] or 0
        minhas_participacoes = msgs_user + tops_user
        total_pendentes_prof = sum(1 for t in topicos if t.get("sem_resposta_prof"))

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
            SELECT ft.*,
                   COALESCE(ft.criador_tipo, 'Professor') as criador_tipo,
                   CASE WHEN COALESCE(ft.criador_tipo, 'Professor') = 'Aluno'
                        THEN COALESCE(al_c.nome_completo, 'Estudante')
                        ELSE COALESCE(p.nome_completo, 'Docente') END as criador_nome,
                   t.nome as turma_nome,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id) as total_mensagens,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id AND autor_tipo = 'IA') as total_ia,
                   (SELECT COUNT(*) FROM forum_mensagens WHERE topico_id = ft.id AND autor_tipo = 'Aluno' AND autor_id = ?) as respostas_aluno
            FROM forum_topicos ft
            LEFT JOIN professores p ON ft.criador_id = p.id
            LEFT JOIN alunos al_c ON ft.autor_aluno_id = al_c.id
            LEFT JOIN turmas t ON ft.turma_id = t.id
            WHERE (ft.turma_id = ? OR ft.turma_id IS NULL)
        """
        params = [aluno_id, aluno_turma_id]
        
        if filtro_turma == "geral":
            query += " AND ft.turma_id IS NULL"
        elif filtro_turma == "minha" or (aluno_turma_id and filtro_turma == str(aluno_turma_id)):
            query += " AND ft.turma_id = ?"
            params.append(aluno_turma_id)
            
        if busca:
            query += " AND (LOWER(ft.titulo) LIKE ? OR LOWER(ft.descricao) LIKE ?)"
            termo = f"%{busca.lower()}%"
            params.extend([termo, termo])
            
        query += " ORDER BY ft.id DESC, ft.data_criacao DESC"
        cursor.execute(query, params)
        topicos = []
        for row in cursor.fetchall():
            t_item = dict(row)
            t_item["tem_ia"] = bool((t_item.get("total_ia") or 0) > 0)
            t_item["aluno_participou"] = bool(
                (t_item.get("respostas_aluno") or 0) > 0
                or (t_item.get("criador_tipo") == "Aluno" and t_item.get("autor_aluno_id") == aluno_id)
            )
            topicos.append(t_item)

        cursor.execute("SELECT COUNT(*) as c FROM forum_mensagens WHERE autor_tipo = 'Aluno' AND autor_id = ?", (aluno_id,))
        msgs_user = cursor.fetchone()["c"] or 0
        cursor.execute("SELECT COUNT(*) as c FROM forum_topicos WHERE criador_tipo = 'Aluno' AND autor_aluno_id = ?", (aluno_id,))
        tops_user = cursor.fetchone()["c"] or 0
        minhas_participacoes = msgs_user + tops_user
        total_pendentes_prof = 0

    total_mensagens_forum = sum((t.get("total_mensagens") or 0) for t in topicos)
    total_intervencoes_ia = sum((t.get("total_ia") or 0) for t in topicos)

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
        total_mensagens_forum=total_mensagens_forum,
        total_intervencoes_ia=total_intervencoes_ia,
        minhas_participacoes=minhas_participacoes,
        total_pendentes_prof=total_pendentes_prof,
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
    _garantir_colunas_forum(cursor, conn)
    
    cursor.execute("""
        SELECT ft.*,
               COALESCE(ft.criador_tipo, 'Professor') as criador_tipo,
               t.nome as turma_nome,
               CASE WHEN COALESCE(ft.criador_tipo, 'Professor') = 'Aluno'
                    THEN COALESCE(al_c.nome_completo, 'Estudante')
                    ELSE COALESCE(p.nome_completo, 'Docente') END as criador_nome
        FROM forum_topicos ft
        LEFT JOIN professores p ON ft.criador_id = p.id
        LEFT JOIN alunos al_c ON ft.autor_aluno_id = al_c.id
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
    turmas_prof = []
    if prof_id:
        cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
        turmas_prof = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    active_page = "aluno_forum" if aluno_id else "prof_forum"
    return render_template(
        "forum_topico.html",
        topico=dict(topico),
        mensagens=mensagens,
        turmas=turmas_prof,
        is_prof=bool(prof_id),
        active_page=active_page
    )


def processar_resposta_ia(topico_id, mensagem_aluno, db_path=None):
    """Processa intervenção socrática da Assistente Fran com suporte a Gemini ou fallback determinístico."""
    caminho_banco = db_path or ext.DB_PATH
    titulo_topico = ""
    categoria = "geral"
    try:
        conn_info = sqlite3.connect(caminho_banco, timeout=15.0)
        conn_info.row_factory = sqlite3.Row
        row_top = conn_info.execute(
            "SELECT titulo, categoria FROM forum_topicos WHERE id = ?",
            (topico_id,),
        ).fetchone()
        if row_top:
            titulo_topico = row_top["titulo"] or ""
            categoria = row_top["categoria"] or "geral"
        conn_info.close()
    except Exception:
        pass

    resposta_ia = None
    if ext.genai_model:
        prompt = f"""
        Atue como a Assistente Fran, uma tutora socrática de Francês Língua Estrangeira (FLE) em um fórum escolar.
        Tópico da discussão: "{titulo_topico}" (categoria: {categoria}).
        O estudante escreveu: "{mensagem_aluno}".
        Avalie se há erros gramaticais ou de vocabulário em francês ou se ele apresentou uma dúvida.
        Se estiver bem construído, elogie com entusiasmo em francês/português e faça uma pergunta de aprofundamento.
        Se houver erro, NÃO dê a resposta direta. Formule uma pergunta gentil socrática para fazê-lo refletir sobre a regra.
        Retorne EXATAMENTE um JSON com as chaves "precisa_intervencao" (booleano) e "resposta_ia" (texto).
        """
        try:
            resposta = ext.genai_model.generate_content(prompt)
            conteudo = resposta.text or ""
            match = re.search(r"\{.*\}", conteudo, re.DOTALL)
            json_str = match.group(0) if match else conteudo
            dados_ia = json.loads(json_str)
            if dados_ia.get("precisa_intervencao", True) and dados_ia.get("resposta_ia"):
                resposta_ia = str(dados_ia.get("resposta_ia")).strip()
        except Exception as e:
            print(f"[i] Fallback socrático local no fórum ({e})")

    if not resposta_ia:
        resposta_ia = gerar_resposta_socratica_fle(titulo_topico, categoria, mensagem_aluno)

    try:
        conn = sqlite3.connect(caminho_banco, timeout=15.0)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo)
            VALUES (?, NULL, 'IA', ?)
            """,
            (topico_id, resposta_ia),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Erro ao salvar resposta IA no forum:", str(e))


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
        _garantir_colunas_forum(cursor, conn)
        
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
        nova_msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Dispara tutoria da Fran quando a intervenção parte do aluno
        if autor_tipo == "Aluno":
            if ext.genai_model:
                thread = threading.Thread(
                    target=processar_resposta_ia,
                    args=(topico_id, conteudo, ext.DB_PATH),
                )
                thread.start()
            else:
                processar_resposta_ia(topico_id, conteudo, ext.DB_PATH)
            
        return jsonify({
            "status": "sucesso",
            "mensagem_id": nova_msg_id,
            "autor_tipo": autor_tipo
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/topico/<int:topico_id>/mensagens", methods=["GET"])
def api_forum_mensagens(topico_id):
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")

    if not aluno_id and not prof_id:
        return jsonify({"status": "erro", "mensagem": "Não autorizado"}), 401

    after_id = request.args.get("after_id", type=int, default=0)

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id, turma_id FROM forum_topicos WHERE id = ?", (topico_id,))
        top = cursor.fetchone()
        if not top:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Tópico não encontrado"}), 404

        if aluno_id and not prof_id and top["turma_id"] is not None:
            cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
            aluno_t = cursor.fetchone()
            if not aluno_t or aluno_t["turma_id"] != top["turma_id"]:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Acesso não autorizado para esta turma."}), 403

        cursor.execute("""
            SELECT fm.id, fm.topico_id, fm.autor_id, fm.autor_tipo, fm.conteudo, fm.data_envio,
                   CASE WHEN fm.autor_tipo = 'Aluno' THEN a.nome_completo
                        WHEN fm.autor_tipo = 'Professor' THEN p.nome_completo
                        ELSE 'Assistente Fran' END as autor_nome
            FROM forum_mensagens fm
            LEFT JOIN alunos a ON fm.autor_id = a.id AND fm.autor_tipo = 'Aluno'
            LEFT JOIN professores p ON fm.autor_id = p.id AND fm.autor_tipo = 'Professor'
            WHERE fm.topico_id = ? AND fm.id > ?
            ORDER BY fm.id ASC
        """, (topico_id, after_id))

        novas = []
        for row in cursor.fetchall():
            item = dict(row)
            is_me = (
                (item["autor_tipo"] == "Professor" and bool(prof_id) and item["autor_id"] == prof_id)
                or (item["autor_tipo"] == "Aluno" and bool(aluno_id) and not prof_id and item["autor_id"] == aluno_id)
            )
            item["is_me"] = is_me
            novas.append(item)

        cursor.execute("SELECT COUNT(*) as total FROM forum_mensagens WHERE topico_id = ?", (topico_id,))
        total_row = cursor.fetchone()
        total_mensagens = total_row["total"] if total_row else len(novas)

        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagens": novas,
            "total_mensagens": total_mensagens
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/criar_topico", methods=["POST"])
def api_forum_criar_topico():
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")

    if not aluno_id and not prof_id:
        return jsonify({"status": "erro", "mensagem": "Não autorizado"}), 401

    dados = request.get_json() if request.is_json else request.form
    titulo = (dados.get("titulo") or "").strip()
    descricao = (dados.get("descricao") or "").strip()
    turma_id = dados.get("turma_id")
    categoria = (dados.get("categoria") or "geral").strip().lower() or "geral"

    if not titulo:
        return jsonify({"status": "erro", "mensagem": "O título do tópico é obrigatório."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        _garantir_colunas_forum(cursor, conn)

        if prof_id:
            criador_id = prof_id
            criador_tipo = "Professor"
            autor_aluno_id = None
            turma_id_val = None
            if turma_id and str(turma_id).strip().lower() not in ["geral", "", "none"]:
                try:
                    turma_id_val = int(turma_id)
                except ValueError:
                    turma_id_val = None
        else:
            cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
            al_row = cursor.fetchone()
            aluno_turma_id = al_row["turma_id"] if al_row else None

            cursor.execute("SELECT id FROM professores ORDER BY id ASC LIMIT 1")
            prof_ref = cursor.fetchone()
            criador_id = prof_ref["id"] if prof_ref else 1
            criador_tipo = "Aluno"
            autor_aluno_id = aluno_id

            t_str = str(turma_id or "").strip().lower()
            if aluno_turma_id and (t_str == "minha" or t_str == str(aluno_turma_id)):
                turma_id_val = aluno_turma_id
            else:
                turma_id_val = None

        cursor.execute(
            """
            INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id, categoria, criador_tipo, autor_aluno_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (titulo, descricao, criador_id, turma_id_val, categoria, criador_tipo, autor_aluno_id),
        )
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Quando aluno abre uma nova dúvida/tópico, a Assistente Fran oferece a primeira orientação socrática
        if criador_tipo == "Aluno":
            texto_inicial = f"{titulo}. {descricao}".strip()
            if ext.genai_model:
                thread = threading.Thread(
                    target=processar_resposta_ia,
                    args=(novo_id, texto_inicial, ext.DB_PATH),
                )
                thread.start()
            else:
                processar_resposta_ia(novo_id, texto_inicial, ext.DB_PATH)

        return jsonify({"status": "sucesso", "topico_id": novo_id})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/topico/<int:topico_id>/editar", methods=["POST"])
@login_required_prof
def api_forum_editar_topico(topico_id):
    dados = (request.get_json(silent=True) or {}) if request.is_json else request.form
    titulo = (dados.get("titulo") or "").strip()
    descricao = (dados.get("descricao") or "").strip()
    categoria = (dados.get("categoria") or "geral").strip().lower() or "geral"
    turma_id = dados.get("turma_id")

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
        cursor.execute("SELECT id FROM forum_topicos WHERE id = ?", (topico_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Tópico não encontrado."}), 404

        cursor.execute(
            """
            UPDATE forum_topicos
            SET titulo = ?, descricao = ?, categoria = ?, turma_id = ?
            WHERE id = ?
            """,
            (titulo, descricao, categoria, turma_id_val, topico_id),
        )
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": "Tópico atualizado com sucesso!",
            "topico": {
                "id": topico_id,
                "titulo": titulo,
                "descricao": descricao,
                "categoria": categoria,
                "turma_id": turma_id_val
            }
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/topico/<int:topico_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_forum_excluir_topico(topico_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo FROM forum_topicos WHERE id = ?", (topico_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Tópico não encontrado."}), 404

        cursor.execute("DELETE FROM forum_mensagens WHERE topico_id = ?", (topico_id,))
        cursor.execute("DELETE FROM forum_topicos WHERE id = ?", (topico_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": f"Tópico '{row['titulo']}' excluído com sucesso."})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/mensagem/<int:msg_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_forum_excluir_mensagem(msg_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, topico_id FROM forum_mensagens WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Mensagem não encontrada."}), 404

        topico_id = row["topico_id"]
        cursor.execute("DELETE FROM forum_mensagens WHERE id = ?", (msg_id,))
        conn.commit()

        cursor.execute("SELECT COUNT(*) as total FROM forum_mensagens WHERE topico_id = ?", (topico_id,))
        total_row = cursor.fetchone()
        total_mensagens = total_row["total"] if total_row else 0
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": "Mensagem removida da discussão.",
            "topico_id": topico_id,
            "total_mensagens": total_mensagens
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@forum_bp.route("/api/forum/topico/<int:topico_id>/intervencao_ia", methods=["POST"])
@login_required_prof
def api_forum_intervencao_ia(topico_id):
    """Permite ao professor acionar a Assistente Fran sob demanda em qualquer discussão."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo, descricao, categoria FROM forum_topicos WHERE id = ?", (topico_id,))
        top = cursor.fetchone()
        if not top:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Tópico não encontrado."}), 404

        cursor.execute("""
            SELECT conteudo FROM forum_mensagens
            WHERE topico_id = ? AND autor_tipo != 'IA'
            ORDER BY id DESC LIMIT 1
        """, (topico_id,))
        ult_msg = cursor.fetchone()
        conn.close()

        texto_contexto = (ult_msg["conteudo"] if ult_msg else "") or f"{top['titulo']}. {top['descricao'] or ''}".strip()
        processar_resposta_ia(topico_id, texto_contexto, ext.DB_PATH)

        conn2 = get_db()
        c2 = conn2.cursor()
        c2.execute("""
            SELECT fm.id, fm.topico_id, fm.autor_id, fm.autor_tipo, fm.conteudo, fm.data_envio,
                   'Assistente Fran' as autor_nome
            FROM forum_mensagens fm
            WHERE fm.topico_id = ? AND fm.autor_tipo = 'IA'
            ORDER BY fm.id DESC LIMIT 1
        """, (topico_id,))
        nova_msg = c2.fetchone()
        c2.execute("SELECT COUNT(*) as total FROM forum_mensagens WHERE topico_id = ?", (topico_id,))
        total_row = c2.fetchone()
        total_mensagens = total_row["total"] if total_row else 0
        conn2.close()

        msg_dict = dict(nova_msg) if nova_msg else None
        if msg_dict:
            msg_dict["is_me"] = False
        return jsonify({
            "status": "sucesso",
            "mensagem_ia": msg_dict,
            "total_mensagens": total_mensagens
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500



# ===================== API DO PROFESSOR (DASHBOARD) =====================

