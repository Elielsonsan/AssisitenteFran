from guia_fle_data import VERBOS_CONJUGADOS, TEMAS_GUIA_FLE
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from blueprints.extensions import (
    get_db, login_required, login_required_prof, parse_retorno_gemini_frances,
    genai_model, BASE_DIR, GEMINI_MODEL_NAME, gerar_feedback_frances,
    feedback_demonstracao_frances, analisar_e_transcrever_audio_oral,
    obter_resposta_esperada_exercicio, obter_pista_exercicio,
    validar_magic_bytes_imagem,
    BANCO_PEDAGOGICO_TEMAS, mapear_chave_tema, gerar_questoes_pedagogicas_completas,
    eh_questao_valida, sanitizar_questoes_geradas
)
import sqlite3, json, random, datetime, re, os, csv, io

aluno_bp = Blueprint('aluno', __name__)

def _garantir_coluna_origem_submissao(cursor, conn=None):
    """Garante a coluna origem_submissao ('curso' vs 'pratica_pessoal') na tabela submissoes."""
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(submissoes)").fetchall()]
    if cols and "origem_submissao" not in cols:
        cursor.execute("ALTER TABLE submissoes ADD COLUMN origem_submissao TEXT DEFAULT 'curso'")
        cursor.execute("UPDATE submissoes SET origem_submissao = 'curso' WHERE origem_submissao IS NULL")
        if conn is not None:
            conn.commit()


@aluno_bp.route("/pratica", methods=["GET"])
@login_required
def index():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()
    _garantir_coluna_origem_submissao(cursor, conn)
    cursor.execute("SELECT nivel_cefr FROM alunos WHERE id = ?;", (aluno_id,))
    row = cursor.fetchone()
    nivel_aluno = row["nivel_cefr"] if row and row["nivel_cefr"] else "A2"
    session["nivel_cefr"] = nivel_aluno
        
    # Buscar reforço pendente
    cursor.execute("SELECT id, mensagem_tutor, tema_id FROM reforcos_individuais WHERE aluno_id=? AND LOWER(status)='pendente' ORDER BY id DESC LIMIT 1", (aluno_id,))
    reforco = cursor.fetchone()

    cursor.execute("SELECT id, nome_tema FROM temas ORDER BY nome_tema ASC;")
    lista_temas = [dict(r) for r in cursor.fetchall()]

    # XP Pessoal exclusivo da Prática Guiada (separado do aprendizado do curso)
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais
        FROM submissoes
        WHERE aluno_id = ? AND origem_submissao = 'pratica_pessoal'
    """, (aluno_id,))
    stats_pratica = cursor.fetchone()
    xp_pessoal = ((stats_pratica["acertos"] or 0) * 10 + (stats_pratica["parciais"] or 0) * 5) if stats_pratica else 0
    total_pratica_pessoal = (stats_pratica["total"] or 0) if stats_pratica else 0

    # Exercício inicial recomendado automático de acordo com o nível ou tema selecionado
    tema_param = (request.args.get("tema") or "").strip()
    exercicio_inicial = None
    if not reforco:
        ex_row = None
        if tema_param:
            cursor.execute("""
                SELECT e.id, e.enunciado, t.nome_tema
                FROM exercicios e
                JOIN temas t ON e.tema_id = t.id
                WHERE LOWER(t.nome_tema) = LOWER(?)
                ORDER BY RANDOM()
                LIMIT 1;
            """, (tema_param,))
            ex_row = cursor.fetchone()
        if not ex_row:
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
            exercicio_inicial["pista_gramatical"] = obter_pista_exercicio(
                exercicio_inicial.get("nome_tema", ""),
                exercicio_inicial.get("enunciado", ""),
                "lacunas",
            )
    
    conn.close()
    return render_template(
        "index.html", 
        active_page="student", 
        aluno_nivel=nivel_aluno, 
        reforco=reforco,
        exercicio_inicial=exercicio_inicial,
        lista_temas=lista_temas,
        xp_pessoal=xp_pessoal,
        total_pratica_pessoal=total_pratica_pessoal
    )

# ===================== ROTAS DE ALUNO (GERAR E AVALIAR) =====================

def _calcular_serie_5_dias(cursor, aluno_id, filtro_sql, total_ref, dias_iso):
    cursor.execute(f"""
        SELECT substr(data_hora, 1, 10) as dia, COUNT(*) as qtd
        FROM submissoes
        WHERE aluno_id = ? AND ({filtro_sql}) AND substr(data_hora, 1, 10) >= ?
        GROUP BY dia
    """, (aluno_id, dias_iso[0]))
    mapa = {r["dia"]: r["qtd"] for r in cursor.fetchall()}
    serie = [mapa.get(d, 0) for d in dias_iso]
    if sum(serie) == 0 and total_ref > 0:
        cursor.execute(f"""
            SELECT substr(data_hora, 1, 10) as dia, COUNT(*) as qtd
            FROM submissoes
            WHERE aluno_id = ? AND ({filtro_sql})
            GROUP BY dia
            ORDER BY dia DESC
            LIMIT 5
        """, (aluno_id,))
        ultimos = [r["qtd"] for r in cursor.fetchall()][::-1]
        serie = ([0] * (5 - len(ultimos))) + ultimos
    return serie


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
    _garantir_coluna_origem_submissao(cursor, conn)
    
    # Buscar atividades e acertos do APRENDIZADO NO CURSO (separado da prática livre pessoal)
    cursor.execute("""
        SELECT 
            COUNT(*) as total_atividades,
            SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
            SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
            SUM(CASE WHEN status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros
        FROM submissoes 
        WHERE aluno_id = ? AND COALESCE(origem_submissao, 'curso') != 'pratica_pessoal'
    """, (aluno_id,))
    stats = cursor.fetchone()
    
    total = stats["total_atividades"] or 0
    acertos = stats["acertos"] or 0
    parciais = stats["parciais"] or 0
    erros = stats["erros"] or 0
    
    xp_curso = (acertos * 10) + (parciais * 5)
    progresso_xp = 0 if total == 0 else (xp_curso % 100 if xp_curso > 100 else xp_curso)

    # Métricas separadas da Prática Pessoal (Prática Guiada autônoma)
    cursor.execute("""
        SELECT
            COUNT(*) as total_pratica,
            SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos_pratica,
            SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais_pratica,
            SUM(CASE WHEN status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros_pratica
        FROM submissoes
        WHERE aluno_id = ? AND origem_submissao = 'pratica_pessoal'
    """, (aluno_id,))
    stats_pessoal = cursor.fetchone()
    total_pratica_pessoal = (stats_pessoal["total_pratica"] or 0) if stats_pessoal else 0
    acertos_pratica_pessoal = (stats_pessoal["acertos_pratica"] or 0) if stats_pessoal else 0
    parciais_pratica_pessoal = (stats_pessoal["parciais_pratica"] or 0) if stats_pessoal else 0
    erros_pratica_pessoal = (stats_pessoal["erros_pratica"] or 0) if stats_pessoal else 0
    xp_pessoal = (acertos_pratica_pessoal * 10) + (parciais_pratica_pessoal * 5)

    total_geral = total + total_pratica_pessoal
    acertos_geral = acertos + acertos_pratica_pessoal
    parciais_geral = parciais + parciais_pratica_pessoal
    erros_geral = erros + erros_pratica_pessoal
    
    # Participação semanal (últimos 5 dias) para Curso, Prática Pessoal e Geral
    hoje = datetime.date.today()
    dias_objs = [hoje - datetime.timedelta(days=i) for i in range(4, -1, -1)]
    dias_iso = [d.strftime("%Y-%m-%d") for d in dias_objs]
    nomes_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dias_semana_labels = [nomes_semana[d.weekday()] for d in dias_objs]

    participacao_semanal = _calcular_serie_5_dias(
        cursor, aluno_id, "COALESCE(origem_submissao, 'curso') != 'pratica_pessoal'", total, dias_iso
    )
    participacao_semanal_pratica = _calcular_serie_5_dias(
        cursor, aluno_id, "origem_submissao = 'pratica_pessoal'", total_pratica_pessoal, dias_iso
    )
    participacao_semanal_geral = [c + p for c, p in zip(participacao_semanal, participacao_semanal_pratica)]
    
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

    # Domínio por Tema Gramatical Francês (Mapa de Tópicos FLE)
    cursor.execute("""
        SELECT t.nome_tema as nome_tema,
               COUNT(*) as total,
               SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
               SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais
        FROM submissoes s
        JOIN exercicios e ON s.exercicio_id = e.id
        JOIN temas t ON e.tema_id = t.id
        WHERE s.aluno_id = ?
        GROUP BY t.id, t.nome_tema
    """, (aluno_id,))
    dominio_temas = []
    for rt in cursor.fetchall():
        t_qtd = rt["total"] or 0
        if t_qtd <= 0:
            continue
        t_ac = rt["acertos"] or 0
        t_pa = rt["parciais"] or 0
        precisao_tema = min(100, round(((t_ac + t_pa * 0.5) / t_qtd) * 100))
        if precisao_tema >= 75:
            status_tema, cor_classe = "Dominado", "dominado"
        elif precisao_tema >= 50:
            status_tema, cor_classe = "Em evolução", "evolucao"
        else:
            status_tema, cor_classe = "Revisar", "revisar"
        dominio_temas.append({
            "nome_tema": rt["nome_tema"],
            "total": t_qtd,
            "acertos": t_ac,
            "parciais": t_pa,
            "precisao": precisao_tema,
            "status": status_tema,
            "cor_classe": cor_classe,
        })
    dominio_temas.sort(key=lambda item: (item["precisao"], -item["total"], item["nome_tema"]))

    # Caderno de Revisão Rápida (últimas 4 respostas com desvio/revisão)
    cursor.execute("""
        SELECT s.id, s.resposta_aluno, s.status_resposta, s.data_hora,
               COALESCE(e.enunciado, pq.enunciado, '') as enunciado,
               COALESCE(t.nome_tema, a.titulo, 'Prática de Francês') as tema
        FROM submissoes s
        LEFT JOIN exercicios e ON s.exercicio_id = e.id
        LEFT JOIN temas t ON e.tema_id = t.id
        LEFT JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        LEFT JOIN avaliacoes a ON pq.avaliacao_id = a.id
        WHERE s.aluno_id = ? AND s.status_resposta IN ('Parcialmente Correto', 'Incorreto')
        ORDER BY s.id DESC
        LIMIT 4
    """, (aluno_id,))
    revisoes_recentes = [dict(r) for r in cursor.fetchall()]

    # Sistema de Medalhas Gamificadas (Badges FLE) com barra de evolução
    badges = [
        {
            "id": "premier_pas",
            "nome": "Premier Pas",
            "icone": "star",
            "descricao": "Concluiu sua primeira atividade de francês.",
            "desbloqueado": total_geral >= 1,
            "atual": min(total_geral, 1),
            "meta": 1,
            "progresso_pct": 100 if total_geral >= 1 else 0
        },
        {
            "id": "tir_precis",
            "nome": "Tir Précis",
            "icone": "target",
            "descricao": "Alcançou 5 acertos perfeitos nas atividades.",
            "desbloqueado": acertos_geral >= 5,
            "atual": min(acertos_geral, 5),
            "meta": 5,
            "progresso_pct": min(100, round((acertos_geral / 5) * 100))
        },
        {
            "id": "erudit_fle",
            "nome": "Érudit du FLE",
            "icone": "book",
            "descricao": "Praticou pelo menos 10 exercícios na plataforma.",
            "desbloqueado": total_geral >= 10,
            "atual": min(total_geral, 10),
            "meta": 10,
            "progresso_pct": min(100, round((total_geral / 10) * 100))
        },
        {
            "id": "voix_paris",
            "nome": "Voix de Paris",
            "icone": "mic",
            "descricao": "Gravou e enviou áudio em uma avaliação ou expressão oral.",
            "desbloqueado": tem_audio,
            "atual": 1 if tem_audio else 0,
            "meta": 1,
            "progresso_pct": 100 if tem_audio else 0
        },
        {
            "id": "niveau_avance",
            "nome": "Niveau Avancé",
            "icone": "award",
            "descricao": "Alcançou o nível intermediário B1 ou superior.",
            "desbloqueado": aluno_nivel in ["B1", "B2", "C1", "C2"],
            "atual": min(idx + 1, 3),
            "meta": 3,
            "progresso_pct": 100 if aluno_nivel in ["B1", "B2", "C1", "C2"] else min(95, round(((idx + 1) / 3) * 100))
        },
        {
            "id": "perseverance",
            "nome": "Persévérance",
            "icone": "shield",
            "descricao": "Concluiu uma missão de reforço guiada pelo tutor.",
            "desbloqueado": tem_reforco,
            "atual": 1 if tem_reforco else 0,
            "meta": 1,
            "progresso_pct": 100 if tem_reforco else 0
        }
    ]
    
    conn.close()
    
    return render_template(
        "aluno_dashboard.html",
        active_page="aluno_dashboard",
        aluno_nivel=aluno_nivel,
        niveis_cefr=niveis,
        cefr_idx=idx,
        proximo_nivel=proximo_nivel,
        progresso_xp=progresso_xp,
        xp_curso=xp_curso,
        xp_pessoal=xp_pessoal,
        total_pratica_pessoal=total_pratica_pessoal,
        acertos_pratica_pessoal=acertos_pratica_pessoal,
        parciais_pratica_pessoal=parciais_pratica_pessoal,
        erros_pratica_pessoal=erros_pratica_pessoal,
        total_atividades=total,
        acertos=acertos,
        parciais=parciais,
        erros=erros,
        total_geral=total_geral,
        acertos_geral=acertos_geral,
        parciais_geral=parciais_geral,
        erros_geral=erros_geral,
        participacao_semanal=participacao_semanal,
        participacao_semanal_pratica=participacao_semanal_pratica,
        participacao_semanal_geral=participacao_semanal_geral,
        dias_semana_labels=dias_semana_labels,
        reforco=reforco,
        badges=badges,
        dominio_temas=dominio_temas,
        revisoes_recentes=revisoes_recentes,
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
                "correta": "Hier, c'était l'anniversaire de ma mère ; je lui ai téléphoné pour la féliciter.",
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
                f"Pronuncie em voz alta utilizando o botão 'Gravar Áudio' abaixo a seguinte frase em francês:\n\n"
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
            "dica_inicial": dica_inicial,
            "pista_gramatical": obter_pista_exercicio(tema_nome, exercicio_gerado, tipo_atividade)
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
    dados = request.get_json(silent=True) if request.is_json else request.form

    exercicio_id = dados.get("exercicio_id")
    resposta = (dados.get("resposta_aluno") or "").strip()
    transcricao_oral = (dados.get("transcricao_oral") or resposta or "").strip()
    tentativa = int(dados.get("tentativa") or 1)
    dica_anterior = (dados.get("dica_anterior") or "").strip()
    tipo_atividade = (dados.get("tipo_atividade") or "").strip().lower()
    files_dict = getattr(request, "files", None) or {}
    audio_oral_file = files_dict.get("audio_oral")
    tem_arquivo_audio = bool(audio_oral_file and getattr(audio_oral_file, "filename", ""))

    if not exercicio_id or (not resposta and not tem_arquivo_audio):
        return jsonify({"status": "erro", "mensagem": "Preencha a resposta ou grave seu áudio antes de enviar."}), 400

    conn = get_db()
    cursor = conn.cursor()
    _garantir_coluna_origem_submissao(cursor, conn)

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

    arquivo_audio_path = None
    filepath = None
    if tem_arquivo_audio:
        upload_dir = os.path.join(BASE_DIR, "static", "uploads", "audios")
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(f"oral_pratica_{aluno_id or 0}_{int(datetime.datetime.now().timestamp())}.webm")
        filepath = os.path.join(upload_dir, filename)
        audio_oral_file.save(filepath)
        arquivo_audio_path = f"static/uploads/audios/{filename}"

    if arquivo_audio_path or tipo_atividade == "expressao_oral":
        status_resposta, analise_prof, feedback_ia, resposta = analisar_e_transcrever_audio_oral(
            tema=tema,
            exercicio=exercicio,
            transcricao_cliente=transcricao_oral,
            filepath_audio=filepath,
            tentativa=tentativa,
            dica_anterior=dica_anterior,
            nivel_cefr=nivel_cefr,
        )
    else:
        status_resposta, analise_prof, feedback_ia = gerar_feedback_frances(
            tema,
            exercicio,
            resposta,
            tentativa=tentativa,
            dica_anterior=dica_anterior,
            nivel_cefr=nivel_cefr,
            tipo_atividade=tipo_atividade,
        )

    data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cols_sub = [r[1] for r in cursor.execute("PRAGMA table_info(submissoes)").fetchall()]
    if "arquivo_audio_path" in cols_sub:
        cursor.execute("""
            INSERT INTO submissoes (
                aluno_id, exercicio_id, resposta_aluno, arquivo_audio_path,
                feedback_ia, analise_professor, status_resposta, tentativa, data_hora, origem_submissao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pratica_pessoal')
        """, (aluno_id, exercicio_id, resposta, arquivo_audio_path, feedback_ia, analise_prof, status_resposta, tentativa, data_hora))
    else:
        cursor.execute("""
            INSERT INTO submissoes (
                aluno_id, exercicio_id, resposta_aluno,
                feedback_ia, analise_professor, status_resposta, tentativa, data_hora, origem_submissao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pratica_pessoal')
        """, (aluno_id, exercicio_id, resposta, feedback_ia, analise_prof, status_resposta, tentativa, data_hora))
    conn.commit()
    novo_id = cursor.lastrowid

    # Gamificação pessoal em tempo real (separada do XP de aprendizado no curso)
    xp_ganho = 10 if status_resposta == "Correto" else (5 if status_resposta == "Parcialmente Correto" else 0)
    progresso_xp = xp_ganho
    total_atividades = 1
    xp_curso = 0
    conquista_desbloqueada = None

    if aluno_id:
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
                   SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais
            FROM submissoes
            WHERE aluno_id = ? AND origem_submissao = 'pratica_pessoal'
            """,
            (aluno_id,),
        )
        stats_xp = cursor.fetchone()
        if stats_xp:
            total_atividades = stats_xp["total"] or 0
            acertos_totais = stats_xp["acertos"] or 0
            parciais_totais = stats_xp["parciais"] or 0
            progresso_xp = (acertos_totais * 10) + (parciais_totais * 5)
            if total_atividades == 1:
                conquista_desbloqueada = "Premier Pas na Prática (1ª Atividade Pessoal)"
            elif acertos_totais == 5 and status_resposta == "Correto":
                conquista_desbloqueada = "Tir Précis na Prática (5 Acertos Perfeitos)"
            elif total_atividades == 10:
                conquista_desbloqueada = "Érudit du FLE (10 Práticas Pessoais)"

        cursor.execute(
            """
            SELECT SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
                   SUM(CASE WHEN status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais
            FROM submissoes
            WHERE aluno_id = ? AND COALESCE(origem_submissao, 'curso') != 'pratica_pessoal'
            """,
            (aluno_id,),
        )
        stats_curso = cursor.fetchone()
        if stats_curso:
            xp_curso = ((stats_curso["acertos"] or 0) * 10) + ((stats_curso["parciais"] or 0) * 5)

    resposta_esperada = obter_resposta_esperada_exercicio(tema, exercicio, tipo_atividade)

    conn.close()

    return jsonify({
        "status": "sucesso",
        "id": novo_id,
        "tema": tema,
        "exercicio": exercicio,
        "resposta_aluno": resposta,
        "resposta_esperada": resposta_esperada,
        "transcricao_audio": resposta if (arquivo_audio_path or tipo_atividade == "expressao_oral") else None,
        "status_resposta": status_resposta,
        "feedback_ia": feedback_ia,
        "analise_professor": analise_prof,
        "tentativa": tentativa,
        "xp_ganho": xp_ganho,
        "progresso_xp": progresso_xp,
        "xp_pessoal": progresso_xp,
        "xp_curso": xp_curso,
        "total_atividades": total_atividades,
        "conquista_desbloqueada": conquista_desbloqueada,
    })

# ===================== DASHBOARD DO PROFESSOR =====================

def _classificar_prazo_avaliacao(data_limite_str):
    """Classifica o prazo da avaliação para exibir urgência real na UI."""
    raw = str(data_limite_str or "").strip()
    if not raw:
        return {"status_prazo": "em_dia", "label_prazo": "Prazo aberto"}

    data_obj = None
    parte_data = raw.split(" ")[0].strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            data_obj = datetime.datetime.strptime(parte_data, fmt).date()
            break
        except ValueError:
            continue

    if not data_obj:
        return {"status_prazo": "em_dia", "label_prazo": "Prazo aberto"}

    hoje = datetime.date.today()
    delta = (data_obj - hoje).days
    if delta < 0:
        return {"status_prazo": "atrasada", "label_prazo": "Prazo encerrado"}
    if delta == 0:
        return {"status_prazo": "urgente", "label_prazo": "Vence hoje"}
    if delta <= 3:
        return {"status_prazo": "urgente", "label_prazo": f"Vence em {delta} dia(s)"}
    return {"status_prazo": "em_dia", "label_prazo": f"Faltam {delta} dias"}


def _mapear_habilidade_fle(tipo_questao):
    """Mapeia tipo interno de questão para rótulo pedagógico FLE."""
    t = str(tipo_questao or "").strip().lower()
    if t == "ditado":
        return "🎧 Dictée"
    if t in ("leitura_oral", "expressao_oral"):
        return "🗣️ Leitura Oral"
    if t in ("multipla_escolha", "teste", "verdadeiro_falso"):
        return "☑️ QCM / V-F"
    return "✍️ Escrita FLE"


@aluno_bp.route("/aluno/atividades", methods=["GET"])
@login_required
def aluno_atividades():
    aluno_id = session.get("aluno_id")
    turma_id = session.get("turma_id")
    conn = get_db()
    cursor = conn.cursor()
    _garantir_coluna_origem_submissao(cursor, conn)

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

    escala_formativa = {
        "Correto": 10.0,
        "Parcialmente Correto": 5.0,
        "Aguardando Revisão Manual": 7.5,
        "Incorreto": 0.0,
    }

    avaliacoes_pendentes = []
    avaliacoes_concluidas = []
    for a in avaliacoes:
        total = a.get("total_questoes") or 0
        resp = a.get("questoes_respondidas") or 0
        a["progresso_pct"] = min(100, round((resp / total) * 100)) if total > 0 else 0
        a.update(_classificar_prazo_avaliacao(a.get("data_limite")))

        cursor.execute("""
            SELECT id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima
            FROM prova_questoes
            WHERE avaliacao_id = ?
            ORDER BY id ASC
        """, (a["id"],))
        q_rows = [dict(q) for q in cursor.fetchall()]

        habilidades = []
        questoes_espelho = []
        notas_formativas = []

        for q in q_rows:
            hab = _mapear_habilidade_fle(q.get("tipo_questao"))
            if hab not in habilidades:
                habilidades.append(hab)

            cursor.execute("""
                SELECT id, resposta_aluno, arquivo_audio_path, status_resposta,
                       feedback_ia, analise_professor, nota_professor, data_hora
                FROM submissoes
                WHERE aluno_id = ? AND prova_questao_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (aluno_id, q["id"]))
            sub_row = cursor.fetchone()
            sub_dict = dict(sub_row) if sub_row else None
            if sub_dict and sub_dict.get("status_resposta") in escala_formativa:
                notas_formativas.append(escala_formativa[sub_dict["status_resposta"]])

            q["submissao"] = sub_dict
            questoes_espelho.append(q)

        a["habilidades_fle"] = habilidades
        a["questoes_espelho"] = questoes_espelho
        a["nota_formativa"] = (
            round(sum(notas_formativas) / len(notas_formativas), 1)
            if (a.get("media_nota") is None and notas_formativas)
            else None
        )

        conc = (resp is not None and resp > 0 and resp >= total and total > 0)
        a["concluida"] = conc
        if conc:
            avaliacoes_concluidas.append(a)
        else:
            avaliacoes_pendentes.append(a)

    # Histórico recente de exercícios e feedbacks para consulta do aluno
    cursor.execute("""
        SELECT s.id, s.resposta_aluno, s.arquivo_audio_path, s.status_resposta,
               s.feedback_ia, s.analise_professor, s.data_hora, s.prova_questao_id,
               COALESCE(s.origem_submissao, 'curso') as origem_submissao,
               COALESCE(e.enunciado, pq.enunciado) as enunciado,
               COALESCE(te.nome_tema, a.titulo, 'Exercício de Avaliação') as tema,
               a.id as avaliacao_id, a.titulo as avaliacao_titulo
        FROM submissoes s
        LEFT JOIN exercicios e ON s.exercicio_id = e.id
        LEFT JOIN temas te ON e.tema_id = te.id
        LEFT JOIN prova_questoes pq ON s.prova_questao_id = pq.id
        LEFT JOIN avaliacoes a ON pq.avaliacao_id = a.id
        WHERE s.aluno_id = ?
        ORDER BY s.id DESC
        LIMIT 20;
    """, (aluno_id,))
    historico = [dict(row) for row in cursor.fetchall()]

    total_historico = len(historico)
    acertos_historico = sum(1 for h in historico if h.get("status_resposta") == "Correto")
    parciais_historico = sum(1 for h in historico if h.get("status_resposta") == "Parcialmente Correto")
    revisar_historico = sum(1 for h in historico if h.get("status_resposta") not in ("Correto", "Parcialmente Correto"))
    taxa_acerto_historico = round((acertos_historico / total_historico) * 100) if total_historico > 0 else 0

    conn.close()
    return render_template(
        "aluno_atividades.html",
        avaliacoes=avaliacoes,
        avaliacoes_pendentes=avaliacoes_pendentes,
        avaliacoes_concluidas=avaliacoes_concluidas,
        historico=historico,
        total_historico=total_historico,
        acertos_historico=acertos_historico,
        parciais_historico=parciais_historico,
        revisar_historico=revisar_historico,
        taxa_acerto_historico=taxa_acerto_historico,
        active_page="aluno_atividades"
    )

def _garantir_colunas_resposta_inbox(cursor, conn=None):
    """Garante colunas incrementais de resposta rápida do aluno na tabela mensagens_inbox."""
    cols_msg = [r[1] for r in cursor.execute("PRAGMA table_info(mensagens_inbox)").fetchall()]
    alterou = False
    if cols_msg:
        if "resposta_aluno" not in cols_msg:
            cursor.execute("ALTER TABLE mensagens_inbox ADD COLUMN resposta_aluno TEXT")
            alterou = True
        if "data_resposta" not in cols_msg:
            cursor.execute("ALTER TABLE mensagens_inbox ADD COLUMN data_resposta TEXT")
            alterou = True
    if alterou and conn is not None:
        conn.commit()


def _garantir_colunas_perfil_fle(cursor, conn=None):
    """Garante colunas de perfil completo e identidade linguística FLE na tabela alunos."""
    cols_al = [r[1] for r in cursor.execute("PRAGMA table_info(alunos)").fetchall()]
    alterou = False
    if cols_al:
        if "data_nascimento" not in cols_al:
            cursor.execute("ALTER TABLE alunos ADD COLUMN data_nascimento TEXT")
            alterou = True
        if "endereco" not in cols_al:
            cursor.execute("ALTER TABLE alunos ADD COLUMN endereco TEXT")
            alterou = True
        if "foto_url" not in cols_al:
            cursor.execute("ALTER TABLE alunos ADD COLUMN foto_url TEXT")
            alterou = True
        if "bio_frances" not in cols_al:
            cursor.execute("ALTER TABLE alunos ADD COLUMN bio_frances TEXT")
            alterou = True
        if "objetivo_fle" not in cols_al:
            cursor.execute("ALTER TABLE alunos ADD COLUMN objetivo_fle TEXT DEFAULT 'Conversação & Fluência'")
            alterou = True
    if alterou and conn is not None:
        conn.commit()


@aluno_bp.route("/aluno/perfil", methods=["GET"])
@login_required
def aluno_perfil():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()

    _garantir_colunas_resposta_inbox(cursor, conn)
    _garantir_colunas_perfil_fle(cursor, conn)
    _garantir_coluna_origem_submissao(cursor, conn)

    cursor.execute("""
        SELECT a.id, a.nome_completo, a.nome_completo as nome, a.matricula,
               a.nivel_cefr, a.turno, a.email, a.telefone, a.data_nascimento,
               a.endereco, a.foto_url, a.bio_frances, a.objetivo_fle, t.nome as turma_nome
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
        SELECT m.id, m.assunto, m.corpo, m.data_envio, COALESCE(m.lida_status, 0) as lida_status,
               m.resposta_aluno, m.data_resposta, p.nome_completo as remetente_nome
        FROM mensagens_inbox m
        LEFT JOIN professores p ON m.remetente_id = p.id
        WHERE m.destinatario_id = ?
        ORDER BY m.id DESC
    """, (aluno_id,))
    mensagens = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM submissoes WHERE aluno_id = ?", (aluno_id,))
    sub_row = cursor.fetchone()
    total_submissoes = sub_row["total"] if sub_row else 0

    # Métricas do Passaporte Linguístico CEFR
    cursor.execute("""
        SELECT
            SUM(CASE WHEN COALESCE(origem_submissao, 'curso') != 'pratica_pessoal' THEN 1 ELSE 0 END) as total_curso,
            SUM(CASE WHEN COALESCE(origem_submissao, 'curso') != 'pratica_pessoal' AND status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos_curso,
            SUM(CASE WHEN COALESCE(origem_submissao, 'curso') != 'pratica_pessoal' AND status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais_curso,
            SUM(CASE WHEN origem_submissao = 'pratica_pessoal' AND status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos_pessoal,
            SUM(CASE WHEN origem_submissao = 'pratica_pessoal' AND status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais_pessoal,
            SUM(CASE WHEN status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos_geral,
            SUM(CASE WHEN arquivo_audio_path IS NOT NULL AND arquivo_audio_path != '' THEN 1 ELSE 0 END) as total_audio
        FROM submissoes
        WHERE aluno_id = ?
    """, (aluno_id,))
    st_sub = cursor.fetchone()
    xp_curso = (((st_sub["acertos_curso"] or 0) * 10) + ((st_sub["parciais_curso"] or 0) * 5)) if st_sub else 0
    xp_pessoal = (((st_sub["acertos_pessoal"] or 0) * 10) + ((st_sub["parciais_pessoal"] or 0) * 5)) if st_sub else 0
    acertos_geral = (st_sub["acertos_geral"] or 0) if st_sub else 0
    tem_audio = ((st_sub["total_audio"] or 0) > 0) if st_sub else False

    cursor.execute("""
        SELECT COUNT(*) as total_aulas,
               SUM(CASE WHEN status IN ('Presente', 'Justificado') THEN 1 ELSE 0 END) as presencas
        FROM presencas_aula
        WHERE aluno_id = ?
    """, (aluno_id,))
    freq_row = cursor.fetchone()
    total_aulas = (freq_row["total_aulas"] or 0) if freq_row else 0
    presencas = (freq_row["presencas"] or 0) if freq_row else 0
    taxa_frequencia = round((presencas / total_aulas) * 100) if total_aulas > 0 else 100

    cursor.execute("SELECT COUNT(*) as c FROM reforcos_individuais WHERE aluno_id = ? AND LOWER(status) = 'concluido'", (aluno_id,))
    ref_row = cursor.fetchone()
    tem_reforco = ((ref_row["c"] or 0) > 0) if ref_row else False

    nivel_cefr = aluno.get("nivel_cefr") or session.get("nivel_cefr", "A2")
    cefr_meta = {
        "A1": ("Découverte", "Compreende e utiliza expressões cotidianas familiares e apresentações simples."),
        "A2": ("Survie", "Comunica-se em situações simples do dia a dia e descreve rotinas e experiências."),
        "B1": ("Seuil", "Sustenta conversas sobre interesses pessoais, viagens e justifica opiniões em francês."),
        "B2": ("Avancé", "Argumenta com fluidez, compreende textos complexos e interage com espontaneidade."),
        "C1": ("Autonome", "Expressa ideias complexas com precisão estilística e domínio gramatical avançado."),
        "C2": ("Maîtrise", "Compreende praticamente tudo com facilidade e se expressa com rigor próximo ao nativo."),
    }
    titulo_cefr, descricao_cefr = cefr_meta.get(nivel_cefr, cefr_meta["A2"])
    conquistas_desbloqueadas = sum([
        total_submissoes >= 1,
        acertos_geral >= 5,
        total_submissoes >= 10,
        tem_audio,
        nivel_cefr in ["B1", "B2", "C1", "C2"],
        tem_reforco,
    ])
    primeiro_nome = ((aluno.get("nome_completo") or session.get("aluno_nome") or "Étudiant").strip().split()[0])
    sugestao_bio_frances = f"Bonjour ! Je m'appelle {primeiro_nome}. J'étudie le français (niveau {nivel_cefr}) pour progresser à l'oral et à l'écrit."

    passeport_fle = {
        "nivel_cefr": nivel_cefr,
        "titulo_cefr": titulo_cefr,
        "descricao_cefr": descricao_cefr,
        "xp_curso": xp_curso,
        "xp_pessoal": xp_pessoal,
        "taxa_frequencia": taxa_frequencia,
        "conquistas_desbloqueadas": conquistas_desbloqueadas,
        "sugestao_bio_frances": sugestao_bio_frances,
    }

    conn.close()
    return render_template(
        "aluno_perfil.html",
        aluno=aluno,
        mensagens=mensagens,
        total_submissoes=total_submissoes,
        passeport_fle=passeport_fle,
        active_page="aluno_perfil"
    )


@aluno_bp.route("/api/aluno/atualizar_perfil", methods=["POST"])
@login_required
def api_atualizar_perfil():
    aluno_id = session.get("aluno_id")
    conn = get_db()
    cursor = conn.cursor()
    _garantir_colunas_perfil_fle(cursor, conn)

    cursor.execute("""
        SELECT nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url, bio_frances, objetivo_fle
        FROM alunos WHERE id = ?
    """, (aluno_id,))
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
    bio_frances = (dados.get("bio_frances") if "bio_frances" in dados else (atual["bio_frances"] or "")).strip()[:400]
    objetivo_fle = (dados.get("objetivo_fle") if "objetivo_fle" in dados else (atual["objetivo_fle"] or "Conversação & Fluência")).strip()[:120] or "Conversação & Fluência"
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
                    endereco = ?, turno = ?, foto_url = ?, bio_frances = ?, objetivo_fle = ?, senha_hash = ?
                WHERE id = ?
            """, (nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url, bio_frances, objetivo_fle, senha_hash, aluno_id))
        else:
            cursor.execute("""
                UPDATE alunos
                SET nome_completo = ?, email = ?, telefone = ?, data_nascimento = ?,
                    endereco = ?, turno = ?, foto_url = ?, bio_frances = ?, objetivo_fle = ?
                WHERE id = ?
            """, (nome_completo, email, telefone, data_nascimento, endereco, turno, foto_url, bio_frances, objetivo_fle, aluno_id))

        conn.commit()
        conn.close()

        session["aluno_nome"] = nome_completo
        session["foto_url"] = foto_url

        return jsonify({
            "status": "sucesso",
            "mensagem": "Dados do perfil atualizados com sucesso!",
            "nome": nome_completo,
            "foto_url": foto_url,
            "bio_frances": bio_frances,
            "objetivo_fle": objetivo_fle
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao atualizar perfil: {e}"}), 500


@aluno_bp.route("/api/aluno/mensagem/marcar_lida", methods=["POST"])
@login_required
def api_aluno_marcar_mensagem_lida():
    aluno_id = session.get("aluno_id")
    dados = request.get_json(silent=True) if request.is_json else request.form
    marcar_todas = str(dados.get("todas", "")).strip().lower() in ("true", "1", "sim")
    mensagem_id = dados.get("mensagem_id")

    conn = get_db()
    cursor = conn.cursor()
    try:
        if marcar_todas:
            cursor.execute(
                "UPDATE mensagens_inbox SET lida_status = 1 WHERE destinatario_id = ?",
                (aluno_id,),
            )
        else:
            if not mensagem_id:
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Mensagem não informada."}), 400
            cursor.execute(
                "SELECT id FROM mensagens_inbox WHERE id = ? AND destinatario_id = ?",
                (mensagem_id, aluno_id),
            )
            if not cursor.fetchone():
                conn.close()
                return jsonify({"status": "erro", "mensagem": "Recado não encontrado."}), 404
            cursor.execute(
                "UPDATE mensagens_inbox SET lida_status = 1 WHERE id = ? AND destinatario_id = ?",
                (mensagem_id, aluno_id),
            )

        conn.commit()
        cursor.execute(
            "SELECT COUNT(*) as c FROM mensagens_inbox WHERE destinatario_id = ? AND COALESCE(lida_status, 0) = 0",
            (aluno_id,),
        )
        nao_lidas = (cursor.fetchone()["c"] or 0)
        conn.close()
        return jsonify({"status": "sucesso", "nao_lidas": nao_lidas})
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao atualizar leitura: {e}"}), 500


@aluno_bp.route("/api/aluno/mensagem/responder", methods=["POST"])
@login_required
def api_aluno_responder_mensagem():
    aluno_id = session.get("aluno_id")
    dados = request.get_json(silent=True) if request.is_json else request.form
    mensagem_id = dados.get("mensagem_id")
    resposta = (dados.get("resposta") or "").strip()

    if not mensagem_id or not resposta:
        return jsonify({"status": "erro", "mensagem": "Informe a mensagem e o texto da resposta."}), 400
    if len(resposta) > 1000:
        return jsonify({"status": "erro", "mensagem": "A resposta deve ter no máximo 1000 caracteres."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        _garantir_colunas_resposta_inbox(cursor, conn)
        cursor.execute(
            "SELECT id FROM mensagens_inbox WHERE id = ? AND destinatario_id = ?",
            (mensagem_id, aluno_id),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"status": "erro", "mensagem": "Recado não encontrado."}), 404

        data_resp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("""
            UPDATE mensagens_inbox
            SET lida_status = 1, resposta_aluno = ?, data_resposta = ?
            WHERE id = ? AND destinatario_id = ?
        """, (resposta, data_resp, mensagem_id, aluno_id))
        conn.commit()

        cursor.execute(
            "SELECT COUNT(*) as c FROM mensagens_inbox WHERE destinatario_id = ? AND COALESCE(lida_status, 0) = 0",
            (aluno_id,),
        )
        nao_lidas = (cursor.fetchone()["c"] or 0)
        conn.close()
        return jsonify({
            "status": "sucesso",
            "mensagem": "Resposta enviada com sucesso ao professor!",
            "resposta_aluno": resposta,
            "data_resposta": data_resp,
            "nao_lidas": nao_lidas,
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "erro", "mensagem": f"Erro ao enviar resposta: {e}"}), 500

# ===================== MÓDULO DE PROVAS MULTIMODAIS =====================
@aluno_bp.route("/aluno/prova/<int:avaliacao_id>", methods=["GET"])
@login_required
def aluno_prova(avaliacao_id):
    aluno_id = session.get("aluno_id")
    turma_id = session.get("turma_id")
    refazer = request.args.get("refazer") == "1"
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

    cursor.execute("SELECT * FROM prova_questoes WHERE avaliacao_id = ? ORDER BY id ASC", (avaliacao_id,))
    questoes = [dict(r) for r in cursor.fetchall()]
    for q in questoes:
        cursor.execute("""
            SELECT id, resposta_aluno, arquivo_audio_path, status_resposta,
                   feedback_ia, analise_professor, nota_professor, data_hora
            FROM submissoes
            WHERE aluno_id = ? AND prova_questao_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (aluno_id, q["id"]))
        sub_row = cursor.fetchone()
        q["submissao"] = dict(sub_row) if sub_row else None

    questoes_respondidas_count = sum(1 for q in questoes if q.get("submissao"))
    modo_revisao = (questoes_respondidas_count > 0 and not refazer)

    conn.close()
    return render_template(
        "aluno_prova.html",
        avaliacao=avaliacao,
        questoes=questoes,
        modo_revisao=modo_revisao,
        questoes_respondidas_count=questoes_respondidas_count,
        active_page="aluno_atividades"
    )

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
    _garantir_coluna_origem_submissao(cursor, conn)

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
                    feedback_ia, analise_professor, status_resposta, data_hora, origem_submissao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'curso')
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

                status_oral = "Aguardando Revisão Manual"
                analise_oral = ""
                feedback_ia = "Análise pendente."
                transcricao_oral = None
                try:
                    if not genai_model:
                        raise RuntimeError("Modelo Gemini não configurado")

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
                    print(f"[i] Usando motor de transcrição local na prova oral ({e})")
                    status_oral, analise_oral, feedback_ia, transcricao_oral = analisar_e_transcrever_audio_oral(
                        tema=av_row["titulo"] or "Avaliação Oral",
                        exercicio=texto_ref or "",
                        transcricao_cliente="",
                        filepath_audio=filepath,
                        tentativa=1,
                        nivel_cefr=session.get("nivel_cefr", "A2"),
                    )

                cursor.execute("""
                    INSERT INTO submissoes (
                        aluno_id, prova_questao_id, resposta_aluno, arquivo_audio_path,
                        status_resposta, feedback_ia, analise_professor, data_hora, origem_submissao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'curso')
                """, (
                    aluno_id,
                    q_id,
                    transcricao_oral,
                    f"static/uploads/audios/{filename}",
                    status_oral,
                    feedback_ia,
                    analise_oral,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ))
    
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


