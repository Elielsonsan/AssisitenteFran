from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from blueprints.extensions import (
    get_db, login_required, login_required_prof, parse_retorno_gemini_frances,
    genai_model, BASE_DIR, GEMINI_MODEL_NAME, validar_magic_bytes_imagem,
    gerar_questoes_pedagogicas_completas, sanitizar_questoes_geradas
)
import sqlite3, json, random, datetime, re, os, csv, io

professor_bp = Blueprint('professor', __name__)

@professor_bp.route("/dashboard", methods=["GET"])
@login_required_prof
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC;")
    turmas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC;")
    temas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.matricula, a.turma_id, a.nivel_cefr, t.nome as turma_nome,
               COUNT(s.id) as total_atividades,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros
        FROM alunos a
        JOIN turmas t ON a.turma_id = t.id
        LEFT JOIN submissoes s ON s.aluno_id = a.id
        GROUP BY a.id ORDER BY t.nome ASC, a.nome_completo ASC;
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

    # --- TOP 10 BEST AND WORST LOGIC ---
    temas_zipped = list(zip(tema_labels, tema_acertos, tema_erros, tema_parciais))
    
    # Top 10 Melhores (ordenado por mais acertos)
    temas_best = sorted(temas_zipped, key=lambda x: x[1], reverse=True)[:10]
    best_labels = [x[0] for x in temas_best]
    best_acertos = [x[1] for x in temas_best]
    best_erros = [x[2] for x in temas_best]
    best_parciais = [x[3] for x in temas_best]
    
    # Top 10 Piores (ordenado por mais erros)
    temas_worst = sorted(temas_zipped, key=lambda x: x[2], reverse=True)[:10]
    worst_labels = [x[0] for x in temas_worst]
    worst_acertos = [x[1] for x in temas_worst]
    worst_erros = [x[2] for x in temas_worst]
    worst_parciais = [x[3] for x in temas_worst]

    sql_submissoes = f"""
        SELECT s.id, a.nome_completo as aluno_nome, a.matricula as aluno_matricula, a.turma_id, t.nome as turma_nome, 
               COALESCE(te.nome_tema, 'Prova Multimodal') as tema, COALESCE(te.nome_tema, 'Prova Multimodal') as tema_aula,
               COALESCE(e.enunciado, pq.enunciado) as pergunta, COALESCE(e.enunciado, pq.enunciado) as exercicio,
               s.resposta_aluno as resposta, s.resposta_aluno as resposta_aluno,
               s.feedback_ia as feedback, s.analise_professor as analise,
               s.status_resposta, s.status_resposta as status, COALESCE(e.nivel_exigido, a.nivel_cefr, 'A2') as nivel_cefr, s.tentativa, s.data_hora,
               s.aluno_id, COALESCE(e.tema_id, 1) as tema_id
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
        best_labels=best_labels, best_acertos=best_acertos, best_erros=best_erros, best_parciais=best_parciais,
        worst_labels=worst_labels, worst_acertos=worst_acertos, worst_erros=worst_erros, worst_parciais=worst_parciais,
        submissoes=submissoes, submissoes_dict=submissoes_dict, total_submissoes=total_submissoes,
        total_corretos=total_corretos, total_parciais=total_parciais, total_incorretos=total_incorretos,
        pct_acerto=pct_acerto, pct_parcial=pct_parcial, pct_incorreto=pct_incorreto,
        temas_unicos=tema_labels, alunos_cadastrados=alunos_cadastrados
    )

# ===================== ROTAS DE API: TURMAS & EXPORTAÇÃO =====================

@professor_bp.route("/api/turmas", methods=["GET"])
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

@professor_bp.route("/api/turmas/cadastrar", methods=["POST"])
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

@professor_bp.route("/api/turmas/<int:turma_id>/editar", methods=["POST"])
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

@professor_bp.route("/api/turmas/<int:turma_id>/excluir", methods=["POST", "DELETE"])
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


@professor_bp.route("/api/relatorio/exportar_csv", methods=["GET"])
@login_required_prof
def api_exportar_csv():
    turma_id_raw = request.args.get("turma_id")
    turma_id = int(turma_id_raw) if turma_id_raw and str(turma_id_raw).strip().isdigit() and str(turma_id_raw) != "todas" else None
    nivel_cefr = request.args.get("nivel_cefr", "").strip().upper()
    n_cefr = nivel_cefr if nivel_cefr and nivel_cefr != "TODOS" else None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.matricula, t.nome as turma_nome, a.nivel_cefr,
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
        ORDER BY t.nome ASC, a.nome_completo ASC;
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
            r["id"], r["nome_completo"], r["matricula"], r["turma_nome"], r["nivel_cefr"],
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

@professor_bp.route("/api/relatorio/boletim_dados", methods=["GET"])
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
        SELECT a.id, a.nome_completo, a.matricula, t.nome as turma_nome, a.nivel_cefr,
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
        ORDER BY t.nome ASC, a.nome_completo ASC;
    """, (turma_id, turma_id, n_cefr, n_cefr))
    rows = cursor.fetchall()

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

        cursor.execute("""
            SELECT COUNT(*) as total_aulas,
                   SUM(CASE WHEN status IN ('Presente', 'Justificado') THEN 1 ELSE 0 END) as presencas
            FROM presencas_aula
            WHERE aluno_id = ?
        """, (r["id"],))
        freq_row = cursor.fetchone()
        tot_aulas_freq = (freq_row["total_aulas"] or 0) if freq_row else 0
        pres_freq = (freq_row["presencas"] or 0) if freq_row else 0
        taxa_freq = round((pres_freq / tot_aulas_freq) * 100, 1) if tot_aulas_freq > 0 else 100.0

        alunos.append({
            "id": r["id"],
            "nome": r["nome_completo"],
            "nome_completo": r["nome_completo"],
            "matricula": r["matricula"],
            "turma_nome": r["turma_nome"],
            "nivel_cefr": r["nivel_cefr"],
            "total_atividades": tot,
            "acertos": acertos,
            "parciais": parciais,
            "erros": erros,
            "taxa_aproveitamento": taxa,
            "taxa_frequencia": taxa_freq,
            "media_provas": media_p if media_p is not None else "—",
            "conceito": conceito
        })

    conn.close()

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

def _garantir_colunas_professor_e_aluno(conn):
    """Migrações de schema já são garantidas na inicialização (init_schema_migrations)."""
    pass


@professor_bp.route("/professor/perfil", methods=["GET"])
@login_required_prof
def professor_perfil():
    """Página dedicada de Perfil Docente & Gestão de Alunos (Matrícula, Nível CEFR, Edição e Exclusão)."""
    prof_id = session.get("prof_id", 1)
    conn = get_db()
    _garantir_colunas_professor_e_aluno(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome_completo, usuario, email_acesso, email, telefone,
               formacao_academica, especializacao, mini_curriculo,
               link_sala_virtual, foto_perfil, perfil_acesso, status_acesso
        FROM professores
        WHERE id = ?
    """, (prof_id,))
    prof_row = cursor.fetchone()
    if not prof_row:
        cursor.execute("""
            SELECT id, nome_completo, usuario, email_acesso, email, telefone,
                   formacao_academica, especializacao, mini_curriculo,
                   link_sala_virtual, foto_perfil, perfil_acesso, status_acesso
            FROM professores
            ORDER BY id ASC LIMIT 1
        """)
        prof_row = cursor.fetchone()

    professor = dict(prof_row) if prof_row else {
        "id": prof_id,
        "nome_completo": session.get("prof_nome", "Professor Admin"),
        "usuario": session.get("prof_usuario", "admin"),
        "email_acesso": "admin@escola.com",
        "email": "admin@escola.com",
        "telefone": "",
        "formacao_academica": "Licenciatura em Letras — Francês (FLE)",
        "especializacao": "Didática FLE & Certificações DELF/DALF",
        "mini_curriculo": "",
        "link_sala_virtual": "",
        "foto_perfil": None,
        "perfil_acesso": "Professor",
        "status_acesso": "Ativo",
    }

    if professor.get("nome_completo"):
        session["prof_nome"] = professor["nome_completo"]
    if professor.get("usuario"):
        session["prof_usuario"] = professor["usuario"]
    if professor.get("foto_perfil"):
        session["foto_url"] = professor["foto_perfil"]

    cursor.execute("""
        SELECT t.id, t.nome, COUNT(a.id) AS total_alunos
        FROM turmas t
        LEFT JOIN alunos a ON a.turma_id = t.id
        GROUP BY t.id, t.nome
        ORDER BY t.nome ASC;
    """)
    turmas = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.matricula, a.nivel_cefr, a.turma_id,
               a.email, a.telefone, a.turno, a.status_matricula, a.foto_url,
               COALESCE(t.nome, 'Sem Turma') AS turma_nome,
               COUNT(s.id) AS total_atividades,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) AS acertos,
               SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) AS parciais,
               SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) AS erros
        FROM alunos a
        LEFT JOIN turmas t ON t.id = a.turma_id
        LEFT JOIN submissoes s ON s.aluno_id = a.id
        GROUP BY a.id
        ORDER BY a.nome_completo ASC;
    """)
    alunos = []
    soma_taxas = 0.0
    total_submissoes_geral = 0
    for r in cursor.fetchall():
        d = dict(r)
        tot = int(d.get("total_atividades") or 0)
        ac = int(d.get("acertos") or 0)
        pa = int(d.get("parciais") or 0)
        er = int(d.get("erros") or 0)
        taxa = round(((ac + pa * 0.5) / tot * 100), 1) if tot > 0 else 0.0
        d["total_atividades"] = tot
        d["acertos"] = ac
        d["parciais"] = pa
        d["erros"] = er
        d["taxa_acerto"] = taxa
        d["nivel_cefr"] = (d.get("nivel_cefr") or "A2").upper()
        d["turno"] = d.get("turno") or "Matutino"
        d["status_matricula"] = d.get("status_matricula") or "Ativo"
        alunos.append(d)
        soma_taxas += taxa
        total_submissoes_geral += tot

    total_alunos = len(alunos)
    total_turmas = len(turmas)
    media_acerto_geral = round(soma_taxas / total_alunos, 1) if total_alunos > 0 else 0.0

    conn.close()
    return render_template(
        "professor_perfil.html",
        active_page="prof_perfil",
        professor=professor,
        turmas=turmas,
        alunos=alunos,
        total_alunos=total_alunos,
        total_turmas=total_turmas,
        media_acerto_geral=media_acerto_geral,
        total_submissoes_geral=total_submissoes_geral,
    )


@professor_bp.route("/api/professor/atualizar_perfil", methods=["POST"])
@login_required_prof
def api_professor_atualizar_perfil():
    """Atualiza os dados cadastrais, foto de perfil e credenciais de acesso do professor."""
    prof_id = session.get("prof_id", 1)
    conn = get_db()
    _garantir_colunas_professor_e_aluno(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome_completo, usuario, email_acesso, email, telefone,
               formacao_academica, especializacao, mini_curriculo,
               link_sala_virtual, foto_perfil
        FROM professores
        WHERE id = ?
    """, (prof_id,))
    atual = cursor.fetchone()
    if not atual:
        cursor.execute("SELECT * FROM professores ORDER BY id ASC LIMIT 1")
        atual = cursor.fetchone()
        if atual:
            prof_id = atual["id"]
        else:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Perfil de professor não encontrado."}), 404

    dados = request.get_json(silent=True) if request.is_json else request.form

    nome_completo = (dados.get("nome_completo") or atual["nome_completo"] or "").strip()
    usuario = (dados.get("usuario") or atual["usuario"] or "").strip()
    if not nome_completo or not usuario:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Nome completo e usuário de acesso são obrigatórios."}), 400

    # Verifica se outro professor já usa o mesmo login
    cursor.execute("SELECT id FROM professores WHERE LOWER(usuario) = LOWER(?) AND id != ?", (usuario, prof_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Este nome de usuário já está em uso por outro docente."}), 400

    email_val = (dados.get("email") if "email" in dados else (atual["email"] or atual["email_acesso"] or "")).strip()
    email_acesso = email_val or (atual["email_acesso"] or "admin@escola.com")
    telefone = (dados.get("telefone") if "telefone" in dados else (atual["telefone"] or "")).strip()
    formacao_academica = (dados.get("formacao_academica") if "formacao_academica" in dados else (atual["formacao_academica"] or "")).strip()
    especializacao = (dados.get("especializacao") if "especializacao" in dados else (atual["especializacao"] or "")).strip()
    mini_curriculo = (dados.get("mini_curriculo") if "mini_curriculo" in dados else (atual["mini_curriculo"] or "")).strip()
    link_sala_virtual = (dados.get("link_sala_virtual") if "link_sala_virtual" in dados else (atual["link_sala_virtual"] or "")).strip()
    nova_senha = (dados.get("nova_senha") or "").strip()
    remover_foto = str(dados.get("remover_foto") or "0").strip() == "1"

    foto_perfil = atual["foto_perfil"]
    if remover_foto:
        foto_perfil = None

    arquivo_foto = request.files.get("foto_perfil")
    if arquivo_foto and arquivo_foto.filename:
        ext = os.path.splitext(arquivo_foto.filename)[1].lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif"] or not validar_magic_bytes_imagem(arquivo_foto, ext):
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Formato ou conteúdo de imagem inválido. Use PNG, JPG, WEBP ou GIF válidos."}), 400

        upload_dir = os.path.join(BASE_DIR, "static", "uploads", "perfis")
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(f"prof_{prof_id}_{int(datetime.datetime.now().timestamp())}{ext}")
        filepath = os.path.join(upload_dir, filename)
        arquivo_foto.save(filepath)
        foto_perfil = f"/static/uploads/perfis/{filename}"

    try:
        if nova_senha:
            if len(nova_senha) < 4:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "A nova senha deve ter pelo menos 4 caracteres."}), 400
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute("""
                UPDATE professores
                SET nome_completo = ?, usuario = ?, email = ?, email_acesso = ?,
                    telefone = ?, formacao_academica = ?, especializacao = ?,
                    mini_curriculo = ?, link_sala_virtual = ?, foto_perfil = ?,
                    senha_hash = ?
                WHERE id = ?
            """, (
                nome_completo, usuario, email_val, email_acesso,
                telefone, formacao_academica, especializacao,
                mini_curriculo, link_sala_virtual, foto_perfil,
                senha_hash, prof_id
            ))
        else:
            cursor.execute("""
                UPDATE professores
                SET nome_completo = ?, usuario = ?, email = ?, email_acesso = ?,
                    telefone = ?, formacao_academica = ?, especializacao = ?,
                    mini_curriculo = ?, link_sala_virtual = ?, foto_perfil = ?
                WHERE id = ?
            """, (
                nome_completo, usuario, email_val, email_acesso,
                telefone, formacao_academica, especializacao,
                mini_curriculo, link_sala_virtual, foto_perfil,
                prof_id
            ))

        conn.commit()
        conn.close()

        session["prof_nome"] = nome_completo
        session["prof_usuario"] = usuario
        session["foto_url"] = foto_perfil

        return jsonify({
            "status": "sucesso",
            "mensagem": "Perfil docente atualizado com sucesso!",
            "professor": {
                "id": prof_id,
                "nome_completo": nome_completo,
                "usuario": usuario,
                "email": email_val,
                "telefone": telefone,
                "formacao_academica": formacao_academica,
                "especializacao": especializacao,
                "mini_curriculo": mini_curriculo,
                "link_sala_virtual": link_sala_virtual,
                "foto_perfil": foto_perfil,
            }
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao atualizar perfil: {e}"}), 500


@professor_bp.route("/api/alunos", methods=["GET"])
@login_required_prof
def api_listar_alunos():
    """Retorna a lista completa de alunos cadastrados com informações da turma."""
    try:
        conn = get_db()
        _garantir_colunas_professor_e_aluno(conn)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.nome_completo, a.matricula, a.nivel_cefr, a.turma_id,
                   a.email, a.telefone, a.turno, a.status_matricula, a.foto_url,
                   COALESCE(t.nome, 'Sem Turma') AS turma_nome,
                   COUNT(s.id) AS total_atividades,
                   SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) AS acertos,
                   SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) AS parciais
            FROM alunos a
            LEFT JOIN turmas t ON t.id = a.turma_id
            LEFT JOIN submissoes s ON s.aluno_id = a.id
            GROUP BY a.id
            ORDER BY a.nome_completo ASC;
        """)
        rows = cursor.fetchall()
        conn.close()
        alunos = []
        for r in rows:
            tot = int(r["total_atividades"] or 0)
            ac = int(r["acertos"] or 0)
            pa = int(r["parciais"] or 0)
            taxa = round(((ac + pa * 0.5) / tot * 100), 1) if tot > 0 else 0.0
            alunos.append({
                "id": r["id"],
                "nome": r["nome_completo"],
                "nome_completo": r["nome_completo"],
                "matricula": r["matricula"],
                "nivel_cefr": (r["nivel_cefr"] or "A2").upper(),
                "turma_id": r["turma_id"],
                "turma_nome": r["turma_nome"],
                "email": r["email"] or "",
                "telefone": r["telefone"] or "",
                "turno": r["turno"] or "Matutino",
                "status_matricula": r["status_matricula"] or "Ativo",
                "foto_url": r["foto_url"],
                "total_atividades": tot,
                "taxa_acerto": taxa
            })
        return jsonify({"status": "sucesso", "alunos": alunos})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@professor_bp.route("/api/alunos/cadastrar", methods=["POST"])
@login_required_prof
def api_cadastrar_aluno():
    dados = request.get_json(silent=True) if request.is_json else request.form
    nome = (dados.get("nome") or dados.get("nome_completo") or "").strip()
    matricula = (dados.get("matricula") or "").strip()
    senha = (dados.get("senha") or "").strip()
    turma_id = dados.get("turma_id")
    nivel_cefr = (dados.get("nivel_cefr") or "A2").strip().upper()
    email = (dados.get("email") or "").strip()
    telefone = (dados.get("telefone") or "").strip()
    turno = (dados.get("turno") or "Matutino").strip() or "Matutino"

    if not nome or not matricula or not senha or not turma_id:
        return jsonify({"status": "erro", "mensagem": "Preencha todos os campos obrigatórios (Nome, Matrícula, Turma e Senha)."}), 400

    try:
        conn = get_db()
        _garantir_colunas_professor_e_aluno(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM alunos WHERE matricula = ?;", (matricula,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Já existe um aluno cadastrado com essa matrícula."}), 400

        cursor.execute("""
            INSERT INTO alunos (nome_completo, matricula, senha_hash, turma_id, nivel_cefr, email, telefone, turno, status_matricula)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Ativo');
        """, (nome, matricula, generate_password_hash(senha), turma_id, nivel_cefr, email, telefone, turno))
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,))
        t_row = cursor.fetchone()
        turma_nome = t_row["nome"] if t_row else "Turma FLE"
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Aluno '{nome}' matriculado com sucesso!",
            "aluno": {
                "id": novo_id,
                "nome": nome,
                "nome_completo": nome,
                "matricula": matricula,
                "turma_id": int(turma_id),
                "turma_nome": turma_nome,
                "nivel_cefr": nivel_cefr,
                "email": email,
                "telefone": telefone,
                "turno": turno,
                "total_atividades": 0,
                "taxa_acerto": 0.0
            }
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@professor_bp.route("/api/alunos/<int:aluno_id>/nivel", methods=["POST"])
@login_required_prof
def api_atualizar_nivel_aluno(aluno_id):
    dados = request.get_json(silent=True) if request.is_json else request.form
    nivel = (dados.get("nivel_cefr") or "").strip().upper()
    if nivel not in ("A1", "A2", "B1", "B2", "C1", "C2"):
        return jsonify({"status": "erro", "mensagem": "Nível CEFR inválido. Escolha entre A1, A2, B1, B2, C1 ou C2."}), 400
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE alunos SET nivel_cefr = ? WHERE id = ?;", (nivel, aluno_id))
        conn.commit()
        conn.close()
        if session.get("aluno_id") == aluno_id: session["nivel_cefr"] = nivel
        return jsonify({"status": "sucesso", "nivel_cefr": nivel, "mensagem": f"Nível CEFR atualizado para {nivel}!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@professor_bp.route("/api/alunos/<int:aluno_id>/editar", methods=["POST"])
@login_required_prof
def api_editar_aluno(aluno_id):
    dados = request.get_json(silent=True) if request.is_json else request.form
    nome = (dados.get("nome") or dados.get("nome_completo") or "").strip()
    matricula = (dados.get("matricula") or "").strip()
    senha = (dados.get("senha") or "").strip()
    turma_id = dados.get("turma_id")
    nivel_cefr = (dados.get("nivel_cefr") or "A2").strip().upper()

    if not nome or not matricula or not turma_id:
        return jsonify({"status": "erro", "mensagem": "Nome, matrícula e turma são obrigatórios."}), 400

    try:
        conn = get_db()
        _garantir_colunas_professor_e_aluno(conn)
        cursor = conn.cursor()

        # Verificar se matrícula já é usada por outro aluno
        cursor.execute("SELECT id FROM alunos WHERE matricula = ? AND id != ?;", (matricula, aluno_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Outro aluno já está utilizando esta matrícula."}), 400

        cursor.execute("SELECT email, telefone, turno, status_matricula FROM alunos WHERE id = ?", (aluno_id,))
        atual_a = cursor.fetchone()
        email = (dados.get("email") if "email" in dados else (atual_a["email"] if atual_a else "") or "").strip()
        telefone = (dados.get("telefone") if "telefone" in dados else (atual_a["telefone"] if atual_a else "") or "").strip()
        turno = (dados.get("turno") if "turno" in dados else (atual_a["turno"] if atual_a else "Matutino") or "Matutino").strip() or "Matutino"
        status_matricula = (dados.get("status_matricula") if "status_matricula" in dados else (atual_a["status_matricula"] if atual_a else "Ativo") or "Ativo").strip() or "Ativo"

        if senha:
            cursor.execute("""
                UPDATE alunos
                SET nome_completo = ?, matricula = ?, senha_hash = ?, turma_id = ?, nivel_cefr = ?,
                    email = ?, telefone = ?, turno = ?, status_matricula = ?
                WHERE id = ?;
            """, (nome, matricula, generate_password_hash(senha), turma_id, nivel_cefr, email, telefone, turno, status_matricula, aluno_id))
        else:
            cursor.execute("""
                UPDATE alunos
                SET nome_completo = ?, matricula = ?, turma_id = ?, nivel_cefr = ?,
                    email = ?, telefone = ?, turno = ?, status_matricula = ?
                WHERE id = ?;
            """, (nome, matricula, turma_id, nivel_cefr, email, telefone, turno, status_matricula, aluno_id))

        cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,))
        t_row = cursor.fetchone()
        turma_nome = t_row["nome"] if t_row else "Turma FLE"

        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Dados do aluno '{nome}' atualizados com sucesso!",
            "aluno": {
                "id": aluno_id,
                "nome": nome,
                "nome_completo": nome,
                "matricula": matricula,
                "turma_id": int(turma_id),
                "turma_nome": turma_nome,
                "nivel_cefr": nivel_cefr,
                "email": email,
                "telefone": telefone,
                "turno": turno,
                "status_matricula": status_matricula
            }
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@professor_bp.route("/api/alunos/<int:aluno_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_excluir_aluno(aluno_id):
    """Exclui o aluno e suas submissões/reforços associados."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissoes WHERE aluno_id = ?;", (aluno_id,))
        try:
            cursor.execute("DELETE FROM reforcos_individuais WHERE aluno_id = ?;", (aluno_id,))
        except Exception:
            pass
        cursor.execute("DELETE FROM alunos WHERE id = ?;", (aluno_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "mensagem": "Aluno removido com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

# ===================== CO-PILOTO PEDAGÓGICO =====================

@professor_bp.route("/api/copiloto/gerar_exercicio", methods=["POST"])
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

@professor_bp.route("/api/copiloto/salvar_exercicios", methods=["POST"])
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

@professor_bp.route("/api/radar/reforco", methods=["POST"])
@login_required_prof
def api_radar_reforco():
    """Gera um plano de reforço individualizado e salva na tabela reforcos_individuais"""
    dados = request.get_json() if request.is_json else request.form
    aluno_id = dados.get("aluno_id")
    tema_id = dados.get("tema_id")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_completo, nivel_cefr FROM alunos WHERE id=?;", (aluno_id,))
    aluno = cursor.fetchone()
    cursor.execute("SELECT id, nome_tema FROM temas WHERE id=?;", (tema_id,))
    tema = cursor.fetchone()
    if not tema:
        cursor.execute("SELECT id, nome_tema FROM temas ORDER BY id ASC LIMIT 1;")
        tema = cursor.fetchone()

    if not aluno or not tema:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Aluno ou Tema inválidos."}), 404

    tema_id_real = tema["id"]
    nivel_aluno = (aluno["nivel_cefr"] or "A2").upper()
    mensagem = (
        f"Bonjour {aluno['nome_completo']} ! Notei oportunidade de evolução em « {tema['nome_tema']} » "
        f"(Nível {nivel_aluno}). Preparei exercícios práticos de reforço para consolidar sua precisão gramatical."
    )
    questoes_ped = gerar_questoes_pedagogicas_completas(tema["nome_tema"], nivel_aluno, "exercicio", 2)
    exercicios_reforco = [q["enunciado"] for q in questoes_ped] if questoes_ped else [f"Complétez selon la règle de « {tema['nome_tema']} » : « Nous ___ (étudier) le français. »"]

    # Garante que haja ao menos um exercício desse tema na tabela exercicios para prática direta
    cursor.execute("SELECT COUNT(*) FROM exercicios WHERE tema_id = ?", (tema_id_real,))
    if (cursor.fetchone()[0] or 0) == 0 and exercicios_reforco:
        cursor.execute(
            "INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?)",
            (tema_id_real, nivel_aluno, exercicios_reforco[0])
        )

    cursor.execute("""
        INSERT INTO reforcos_individuais (aluno_id, tema_id, mensagem_tutor, exercicios_json, status)
        VALUES (?, ?, ?, ?, 'Pendente')
    """, (aluno_id, tema_id_real, mensagem, json.dumps(exercicios_reforco)))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "sucesso",
        "mensagem": f"Plano de reforço enviado para {aluno['nome_completo']} com sucesso!"
    })


# ===================== MÓDULO DO PROFESSOR (ESQUELETOS) =====================

@professor_bp.route("/professor/avaliacoes", methods=["GET"])
@login_required_prof
def prof_avaliacoes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.titulo, a.tipo, a.data_limite, a.turma_id, t.nome as turma_nome,
               (SELECT COUNT(*) FROM alunos al WHERE al.turma_id = a.turma_id) as total_alunos_turma,
               (SELECT COUNT(*) FROM prova_questoes pq WHERE pq.avaliacao_id = a.id) as total_questoes,
               (SELECT COUNT(*) FROM submissoes s JOIN prova_questoes pq ON s.prova_questao_id = pq.id WHERE pq.avaliacao_id = a.id) as total_submissoes,
               (SELECT COUNT(DISTINCT s.aluno_id) FROM submissoes s JOIN prova_questoes pq ON s.prova_questao_id = pq.id WHERE pq.avaliacao_id = a.id) as alunos_participantes
        FROM avaliacoes a
        JOIN turmas t ON a.turma_id = t.id
        ORDER BY a.id DESC
    """)
    hoje_str = datetime.datetime.now().strftime("%Y-%m-%d")
    avaliacoes = []
    for row in cursor.fetchall():
        item = dict(row)
        dl = (item.get("data_limite") or "").strip()
        item["prazo_encerrado"] = bool(dl and dl[:10] < hoje_str)
        tot_al = item.get("total_alunos_turma") or 0
        part = item.get("alunos_participantes") or 0
        item["taxa_entrega_pct"] = int(round((part / tot_al) * 100)) if tot_al > 0 else 0
        avaliacoes.append(item)

    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
    turmas = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC")
    temas = [dict(row) for row in cursor.fetchall()]
    
    # Obter também as submissões aguardando revisão manual com enunciado e texto de referência para correção rápida
    cursor.execute("""
        SELECT s.id, al.nome_completo as aluno_nome, e.titulo as avaliacao_nome, pq.tipo_questao,
               pq.enunciado, pq.texto_referencia, s.nota_professor, s.analise_professor,
               s.feedback_ia, s.arquivo_audio_path, s.data_hora
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

@professor_bp.route("/api/gerar_prova_completa_ia", methods=["POST"])
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
    if genai_model:
        try:
            response = genai_model.generate_content(prompt)
            
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

@professor_bp.route("/api/salvar_avaliacao", methods=["POST"])
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

@professor_bp.route("/professor/correcao/<int:submissao_id>", methods=["GET"])
@login_required_prof
def professor_correcao(submissao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, a.nome_completo as aluno_nome, pq.enunciado, pq.texto_referencia 
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

@professor_bp.route("/api/professor/salvar_correcao", methods=["POST"])
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

@professor_bp.route("/api/professor/enviar_mensagem", methods=["POST"])
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

@professor_bp.route("/professor/planos-aula", methods=["GET"])
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

    total_ministradas = sum(1 for p in planos if int(p.get("ministrada") or 0) == 1)
    pct_ministradas = round((total_ministradas / total_planos) * 100) if total_planos > 0 else 0

    return render_template(
        "professor_planos_aula.html",
        planos=planos,
        turmas=turmas,
        total_planos=total_planos,
        total_iniciante=total_iniciante,
        total_intermediario=total_intermediario,
        total_avancado=total_avancado,
        total_ministradas=total_ministradas,
        pct_ministradas=pct_ministradas,
        active_page="prof_planos"
    )

@professor_bp.route("/api/planos-aula", methods=["GET"])
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

@professor_bp.route("/api/planos-aula/<int:plano_id>", methods=["GET"])
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

@professor_bp.route("/api/planos-aula/cadastrar", methods=["POST"])
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

@professor_bp.route("/api/planos-aula/gerar-ia", methods=["POST"])
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
        if not genai_model:
            raise RuntimeError("Modelo Gemini não configurado")
        response = genai_model.generate_content(prompt)
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

@professor_bp.route("/api/planos-aula/<int:plano_id>/gerar-prova", methods=["POST"])
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
    if genai_model:
        try:
            res_q = genai_model.generate_content(prompt_q)
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

@professor_bp.route("/api/planos-aula/<int:plano_id>", methods=["DELETE"])
@professor_bp.route("/api/planos-aula/<int:plano_id>/excluir", methods=["POST", "DELETE"])
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


@professor_bp.route("/api/planos-aula/<int:plano_id>/editar", methods=["POST"])
@login_required_prof
def api_editar_plano(plano_id):
    dados = request.get_json() if request.is_json else request.form
    tema = (dados.get("tema") or "").strip()
    nivel = (dados.get("nivel") or "A1").strip().upper()
    duracao = (dados.get("duracao") or "50 min").strip()
    objetivos = (dados.get("objetivos") or "").strip()

    if not tema or not objetivos:
        return jsonify({"status": "erro", "mensagem": "Tema e objetivos de aprendizagem são obrigatórios."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, aula_numero FROM planos_aula WHERE id = ?", (plano_id,))
        atual = cursor.fetchone()
        if not atual:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Plano de aula não encontrado."}), 404

        aula_num = int(dados.get("aula_numero") or atual["aula_numero"] or 1)
        turma_id_raw = dados.get("turma_id")
        turma_id = int(turma_id_raw) if turma_id_raw and str(turma_id_raw).isdigit() else None

        cursor.execute("""
            UPDATE planos_aula
            SET aula_numero = ?, tema = ?, nivel = ?, duracao = ?, objetivos = ?,
                habilidades = ?, conteudos = ?, metodologia = ?, recursos = ?,
                etapa_aquecimento = ?, etapa_apresentacao = ?, etapa_pratica = ?,
                etapa_producao = ?, etapa_fechamento = ?, avaliacao_formativa = ?,
                avaliacao_somativa = ?, dever_casa = ?, reforco = ?, turma_id = ?
            WHERE id = ?
        """, (
            aula_num,
            tema,
            nivel,
            duracao,
            objetivos,
            (dados.get("habilidades") or "PO, PE, GR").strip(),
            (dados.get("conteudos") or "").strip(),
            (dados.get("metodologia") or "").strip(),
            (dados.get("recursos") or "").strip(),
            (dados.get("etapa_aquecimento") or "").strip(),
            (dados.get("etapa_apresentacao") or "").strip(),
            (dados.get("etapa_pratica") or "").strip(),
            (dados.get("etapa_producao") or "").strip(),
            (dados.get("etapa_fechamento") or "").strip(),
            (dados.get("avaliacao_formativa") or "").strip(),
            (dados.get("avaliacao_somativa") or "").strip(),
            (dados.get("dever_casa") or "").strip(),
            (dados.get("reforco") or "").strip(),
            turma_id,
            plano_id
        ))
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Plano de aula '{tema}' atualizado com sucesso!",
            "plano_id": plano_id
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@professor_bp.route("/api/planos-aula/<int:plano_id>/duplicar", methods=["POST"])
@login_required_prof
def api_duplicar_plano(plano_id):
    dados = (request.get_json(silent=True) or {}) if request.is_json else request.form
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM planos_aula WHERE id = ?", (plano_id,))
        orig = cursor.fetchone()
        if not orig:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Plano original não encontrado."}), 404

        orig = dict(orig)
        novo_tema = (dados.get("tema") or "").strip() or f"{orig['tema']} (Cópia)"
        novo_nivel = (dados.get("nivel") or orig["nivel"] or "A1").strip().upper()
        turma_id_raw = dados.get("turma_id")
        turma_id = int(turma_id_raw) if turma_id_raw and str(turma_id_raw).isdigit() else orig.get("turma_id")

        cursor.execute("""
            INSERT INTO planos_aula (
                aula_numero, tema, nivel, duracao, objetivos, habilidades,
                conteudos, metodologia, recursos, etapa_aquecimento,
                etapa_apresentacao, etapa_pratica, etapa_producao,
                etapa_fechamento, avaliacao_formativa, avaliacao_somativa,
                dever_casa, reforco, turma_id, criador_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            orig.get("aula_numero") or 1,
            novo_tema,
            novo_nivel,
            orig.get("duracao") or "50 min",
            orig.get("objetivos") or "",
            orig.get("habilidades") or "PO, PE, GR",
            orig.get("conteudos") or "",
            orig.get("metodologia") or "",
            orig.get("recursos") or "",
            orig.get("etapa_aquecimento") or "",
            orig.get("etapa_apresentacao") or "",
            orig.get("etapa_pratica") or "",
            orig.get("etapa_producao") or "",
            orig.get("etapa_fechamento") or "",
            orig.get("avaliacao_formativa") or "",
            orig.get("avaliacao_somativa") or "",
            orig.get("dever_casa") or "",
            orig.get("reforco") or "",
            turma_id,
            session.get("prof_id", 1)
        ))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Plano '{novo_tema}' duplicado com sucesso!",
            "id": novo_id,
            "tema": novo_tema
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@professor_bp.route("/api/planos-aula/<int:plano_id>/status-ministrada", methods=["POST"])
@login_required_prof
def api_toggle_plano_ministrada(plano_id):
    dados = (request.get_json(silent=True) or {}) if request.is_json else request.form
    conn = get_db()
    cursor = conn.cursor()
    try:
        try:
            cursor.execute("ALTER TABLE planos_aula ADD COLUMN ministrada INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE planos_aula ADD COLUMN data_ministrada TEXT")
            conn.commit()
        except Exception:
            pass

        cursor.execute("SELECT id, tema, ministrada FROM planos_aula WHERE id = ?", (plano_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Plano não encontrado."}), 404

        atual = int(row["ministrada"] or 0)
        if "ministrada" in dados and dados["ministrada"] is not None:
            novo_status = 1 if int(dados["ministrada"]) else 0
        else:
            novo_status = 0 if atual == 1 else 1

        data_hoje = datetime.datetime.now().strftime("%d/%m/%Y") if novo_status == 1 else None
        cursor.execute(
            "UPDATE planos_aula SET ministrada = ?, data_ministrada = ? WHERE id = ?",
            (novo_status, data_hoje, plano_id)
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM planos_aula WHERE ministrada = 1")
        total_min = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM planos_aula")
        total_pl = cursor.fetchone()[0]
        conn.close()

        return jsonify({
            "status": "sucesso",
            "id": plano_id,
            "ministrada": novo_status,
            "data_ministrada": data_hoje or "",
            "total_ministradas": total_min,
            "total_planos": total_pl,
            "pct_ministradas": round((total_min / total_pl) * 100) if total_pl > 0 else 0
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@professor_bp.route("/api/planos-aula/<int:plano_id>/chamada", methods=["GET"])
@login_required_prof
def api_obter_chamada_plano(plano_id):
    """Retorna os alunos da turma e o registro de frequência para o Plano de Aula informado."""
    turma_id_arg = request.args.get("turma_id", "").strip()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, aula_numero, tema, nivel, turma_id, ministrada, data_ministrada FROM planos_aula WHERE id = ?", (plano_id,))
    plano = cursor.fetchone()
    if not plano:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Plano de aula não encontrado."}), 404

    plano_dict = dict(plano)
    cursor.execute("SELECT id, nome FROM turmas ORDER BY nome ASC")
    turmas = [dict(r) for r in cursor.fetchall()]

    if turma_id_arg and turma_id_arg.isdigit():
        turma_id = int(turma_id_arg)
    elif plano_dict.get("turma_id"):
        turma_id = int(plano_dict["turma_id"])
    else:
        # Verifica se já há chamada salva para este plano em alguma turma
        cursor.execute("SELECT turma_id FROM presencas_aula WHERE plano_id = ? LIMIT 1", (plano_id,))
        existing_t = cursor.fetchone()
        if existing_t:
            turma_id = int(existing_t["turma_id"])
        else:
            turma_id = turmas[0]["id"] if turmas else 1

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.matricula, a.nivel_cefr,
               pa.status as status_presenca, pa.observacao, pa.data_registro
        FROM alunos a
        LEFT JOIN presencas_aula pa ON pa.aluno_id = a.id AND pa.plano_id = ?
        WHERE a.turma_id = ?
        ORDER BY a.nome_completo ASC
    """, (plano_id, turma_id))
    rows = cursor.fetchall()

    alunos_chamada = []
    ja_registrada = False
    for r in rows:
        if r["status_presenca"]:
            ja_registrada = True
        alunos_chamada.append({
            "aluno_id": r["id"],
            "nome_completo": r["nome_completo"],
            "matricula": r["matricula"],
            "nivel_cefr": r["nivel_cefr"] or "A2",
            "status": r["status_presenca"] or "Presente",
            "observacao": r["observacao"] or ""
        })

    conn.close()
    return jsonify({
        "status": "sucesso",
        "plano": plano_dict,
        "turmas": turmas,
        "turma_id": turma_id,
        "ja_registrada": ja_registrada,
        "alunos": alunos_chamada
    })


@professor_bp.route("/api/planos-aula/<int:plano_id>/chamada", methods=["POST"])
@login_required_prof
def api_salvar_chamada_plano(plano_id):
    """Salva o Diário de Classe (chamada/frequência) vinculado a um Plano de Aula."""
    dados = request.get_json(silent=True) or {}
    turma_id = dados.get("turma_id")
    presencas = dados.get("presencas", [])
    marcar_ministrada = dados.get("marcar_ministrada", True)

    if not turma_id or not isinstance(presencas, list):
        return jsonify({"status": "erro", "mensagem": "Informe a turma e a lista de presença."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, tema FROM planos_aula WHERE id = ?", (plano_id,))
        plano = cursor.fetchone()
        if not plano:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Plano de aula não encontrado."}), 404

        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        presentes = 0
        faltas = 0
        justificados = 0

        for item in presencas:
            al_id = item.get("aluno_id")
            st = (item.get("status") or "Presente").strip().capitalize()
            if st not in ("Presente", "Falta", "Justificado"):
                st = "Presente"
            obs = (item.get("observacao") or "").strip()

            if st == "Presente":
                presentes += 1
            elif st == "Falta":
                faltas += 1
            else:
                justificados += 1

            cursor.execute("""
                INSERT INTO presencas_aula (plano_id, turma_id, aluno_id, status, observacao, data_registro)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(plano_id, aluno_id) DO UPDATE SET
                    turma_id = excluded.turma_id,
                    status = excluded.status,
                    observacao = excluded.observacao,
                    data_registro = excluded.data_registro
            """, (plano_id, int(turma_id), int(al_id), st, obs, agora))

        if marcar_ministrada:
            data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
            cursor.execute(
                "UPDATE planos_aula SET ministrada = 1, data_ministrada = COALESCE(data_ministrada, ?) WHERE id = ?",
                (data_hoje, plano_id)
            )

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM planos_aula WHERE ministrada = 1")
        total_min = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM planos_aula")
        total_pl = cursor.fetchone()[0]
        conn.close()

        total_alunos = len(presencas)
        taxa_presenca = round(((presentes + justificados) / total_alunos) * 100, 1) if total_alunos > 0 else 100.0

        return jsonify({
            "status": "sucesso",
            "mensagem": f"Chamada registrada com sucesso! ({presentes} presentes, {faltas} faltas, {justificados} justificados)",
            "resumo": {
                "total": total_alunos,
                "presentes": presentes,
                "faltas": faltas,
                "justificados": justificados,
                "taxa_presenca": taxa_presenca
            },
            "total_ministradas": total_min,
            "total_planos": total_pl,
            "pct_ministradas": round((total_min / total_pl) * 100) if total_pl > 0 else 0
        })
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao salvar chamada: {e}"}), 500


# ===================== FÓRUM SOCRÁTICO =====================

@professor_bp.route("/api/alunos_por_turma/<turma_id>", methods=["GET"])
@login_required_prof
def api_alunos_por_turma(turma_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        if turma_id == "todas" or not turma_id:
            cursor.execute("SELECT id, nome_completo as nome FROM alunos ORDER BY nome_completo ASC")
        else:
            cursor.execute("SELECT id, nome_completo as nome FROM alunos WHERE turma_id = ? ORDER BY nome_completo ASC", (turma_id,))
        alunos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(alunos)
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@professor_bp.route("/api/dashboard/estatisticas", methods=["GET"])
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


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/submissoes", methods=["GET"])
@login_required_prof
def api_avaliacao_submissoes(avaliacao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.titulo, a.tipo, a.turma_id, a.data_limite, t.nome as turma_nome
        FROM avaliacoes a
        LEFT JOIN turmas t ON a.turma_id = t.id
        WHERE a.id = ?
    """, (avaliacao_id,))
    av_row = cursor.fetchone()
    if not av_row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404

    cursor.execute("""
        SELECT s.id, s.id as submissao_id, a.id as aluno_id, a.nome_completo as aluno_nome, a.matricula,
               pq.enunciado, pq.texto_referencia, pq.tipo_questao, pq.pontuacao_maxima,
               s.resposta_aluno, s.arquivo_audio_path, s.status_resposta, s.feedback_ia,
               s.nota_professor, s.analise_professor, s.data_hora
        FROM submissoes s
        JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        JOIN alunos a ON s.aluno_id = a.id
        WHERE pq.avaliacao_id = ?
        ORDER BY a.nome_completo ASC, s.id ASC;
    """, (avaliacao_id,))
    submissoes = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT al.id, al.nome_completo, al.matricula, al.nivel_cefr
        FROM alunos al
        WHERE al.turma_id = ?
          AND al.id NOT IN (
              SELECT DISTINCT s.aluno_id
              FROM submissoes s
              JOIN prova_questoes pq ON s.prova_questao_id = pq.id
              WHERE pq.avaliacao_id = ?
          )
        ORDER BY al.nome_completo ASC
    """, (av_row["turma_id"], avaliacao_id))
    alunos_pendentes = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        "status": "sucesso",
        "avaliacao": dict(av_row),
        "submissoes": submissoes,
        "alunos_pendentes": alunos_pendentes
    })


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/detalhes", methods=["GET"])
@login_required_prof
def api_avaliacao_detalhes(avaliacao_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.titulo, a.tipo, a.data_limite, a.turma_id, t.nome as turma_nome
        FROM avaliacoes a
        LEFT JOIN turmas t ON a.turma_id = t.id
        WHERE a.id = ?
    """, (avaliacao_id,))
    av_row = cursor.fetchone()
    if not av_row:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404
    cursor.execute("""
        SELECT id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima
        FROM prova_questoes
        WHERE avaliacao_id = ?
        ORDER BY id ASC
    """, (avaliacao_id,))
    questoes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"status": "sucesso", "avaliacao": dict(av_row), "questoes": questoes})


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/prorrogar", methods=["POST"])
@login_required_prof
def api_avaliacao_prorrogar(avaliacao_id):
    dados = request.json or {}
    dias = int(dados.get("dias", 7))
    if dias < 1:
        dias = 7

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, data_limite FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404

        agora = datetime.datetime.now()
        base_dt = agora
        dl_raw = (row["data_limite"] or "").strip()
        if dl_raw:
            try:
                parsed = datetime.datetime.strptime(dl_raw[:10], "%Y-%m-%d")
                if parsed > agora:
                    base_dt = parsed
            except Exception:
                pass

        nova_dt = (base_dt + datetime.timedelta(days=dias)).strftime("%Y-%m-%d 23:59:00")
        cursor.execute("UPDATE avaliacoes SET data_limite = ? WHERE id = ?", (nova_dt, avaliacao_id))
        conn.commit()
        return jsonify({
            "status": "sucesso",
            "id": avaliacao_id,
            "nova_data_limite": nova_dt,
            "nova_data_br": nova_dt[:10][8:10] + "/" + nova_dt[:10][5:7] + "/" + nova_dt[:4]
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        conn.close()


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/editar", methods=["POST"])
@login_required_prof
def api_avaliacao_editar(avaliacao_id):
    dados = request.json or {}
    titulo = (dados.get("titulo") or "").strip()
    turma_id = dados.get("turma_id")
    tipo = (dados.get("tipo") or "Prova").strip()
    data_limite = dados.get("data_limite")
    questoes = dados.get("questoes")

    if not titulo or not turma_id:
        return jsonify({"status": "erro", "mensagem": "Título e Turma são obrigatórios."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404

        cursor.execute(
            "UPDATE avaliacoes SET titulo = ?, tipo = ?, data_limite = ?, turma_id = ? WHERE id = ?",
            (titulo, tipo, data_limite, turma_id, avaliacao_id)
        )

        if isinstance(questoes, list) and len(questoes) > 0:
            cursor.execute("SELECT id FROM prova_questoes WHERE avaliacao_id = ? ORDER BY id ASC", (avaliacao_id,))
            existing_ids = [r["id"] for r in cursor.fetchall()]

            for idx, q in enumerate(questoes):
                tipo_q = q.get("tipo_questao", "multipla_escolha")
                enunciado = (q.get("enunciado") or "").strip()
                texto_referencia = q.get("texto_referencia", "")
                pontuacao = float(q.get("pontuacao_maxima", 2.5))
                q_id = q.get("id")

                if q_id and int(q_id) in existing_ids:
                    cursor.execute("""
                        UPDATE prova_questoes
                        SET tipo_questao = ?, enunciado = ?, texto_referencia = ?, pontuacao_maxima = ?
                        WHERE id = ? AND avaliacao_id = ?
                    """, (tipo_q, enunciado, texto_referencia, pontuacao, int(q_id), avaliacao_id))
                elif idx < len(existing_ids) and not q_id:
                    cursor.execute("""
                        UPDATE prova_questoes
                        SET tipo_questao = ?, enunciado = ?, texto_referencia = ?, pontuacao_maxima = ?
                        WHERE id = ? AND avaliacao_id = ?
                    """, (tipo_q, enunciado, texto_referencia, pontuacao, existing_ids[idx], avaliacao_id))
                else:
                    cursor.execute("""
                        INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
                        VALUES (?, ?, ?, ?, ?)
                    """, (avaliacao_id, tipo_q, enunciado, texto_referencia, pontuacao))

        conn.commit()
        return jsonify({"status": "sucesso", "id": avaliacao_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        conn.close()


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/duplicar", methods=["POST"])
@login_required_prof
def api_avaliacao_duplicar(avaliacao_id):
    dados = request.json or {}
    nova_turma_id = dados.get("turma_id")
    novo_titulo = (dados.get("titulo") or "").strip()
    nova_data_limite = dados.get("data_limite")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, titulo, tipo, data_limite, turma_id FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        orig = cursor.fetchone()
        if not orig:
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Avaliação original não encontrada."}), 404

        titulo_final = novo_titulo or f"{orig['titulo']} (Cópia)"
        turma_final = int(nova_turma_id) if nova_turma_id else orig["turma_id"]
        data_final = nova_data_limite if nova_data_limite is not None else orig["data_limite"]

        cursor.execute(
            "INSERT INTO avaliacoes (titulo, tipo, data_limite, turma_id) VALUES (?, ?, ?, ?)",
            (titulo_final, orig["tipo"], data_final, turma_final)
        )
        novo_id = cursor.lastrowid

        cursor.execute("""
            SELECT tipo_questao, enunciado, texto_referencia, pontuacao_maxima
            FROM prova_questoes WHERE avaliacao_id = ? ORDER BY id ASC
        """, (avaliacao_id,))
        for q in cursor.fetchall():
            cursor.execute("""
                INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
                VALUES (?, ?, ?, ?, ?)
            """, (novo_id, q["tipo_questao"], q["enunciado"], q["texto_referencia"], q["pontuacao_maxima"]))

        conn.commit()
        return jsonify({"status": "sucesso", "id": novo_id, "titulo": titulo_final})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        conn.close()


@professor_bp.route("/api/avaliacoes/<int:avaliacao_id>/excluir", methods=["POST", "DELETE"])
@login_required_prof
def api_avaliacao_excluir(avaliacao_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Avaliação não encontrada."}), 404

        cursor.execute("DELETE FROM submissoes WHERE prova_questao_id IN (SELECT id FROM prova_questoes WHERE avaliacao_id = ?)", (avaliacao_id,))
        cursor.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_id,))
        cursor.execute("DELETE FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        conn.commit()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        conn.close()

