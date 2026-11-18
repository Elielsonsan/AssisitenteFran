import os
from flask import Flask, send_from_directory, jsonify, request, session
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_compress import Compress
from dotenv import load_dotenv

# Carrega variaveis do arquivo .env
load_dotenv()

app = Flask(__name__)
csrf = CSRFProtect(app)
compress = Compress(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "erro", "mensagem": "Sessão expirada ou token de segurança ausente. Recarregue a página e tente novamente."}), 400
    return e.description, 400

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'assistente_fran_dev_key_2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite máximo de upload: 16 MB
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')

is_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1')
app.config['TEMPLATES_AUTO_RELOAD'] = is_debug
app.jinja_env.auto_reload = is_debug
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if is_debug else 31536000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from blueprints.extensions import close_db_connections, init_schema_migrations, get_db
app.teardown_appcontext(close_db_connections)

# Auto-inicialização do Schema Principal, Planos de Aula e Migrações
try:
    from seed_planos_aula import init_planos_aula
    import sqlite3
    DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    tem_professores = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='professores'"
    ).fetchone()
    if not tem_professores:
        conn.close()
        from database_setup import init_db
        init_db()
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
    init_planos_aula(conn)
    init_schema_migrations(conn)
    conn.close()
except Exception as _e:
    print(f"[!] Aviso ao inicializar banco de dados / migrações: {_e}")

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

@app.context_processor
def inject_nav_badges():
    """Injeta contadores discretos de pendências para a barra de navegação e menu mobile."""
    nav_badges = {
        "aluno_mensagens_nao_lidas": 0,
        "aluno_atividades_pendentes": 0,
        "prof_revisoes_pendentes": 0,
    }
    aluno_id = session.get("aluno_id")
    prof_id = session.get("prof_id")
    if not aluno_id and not prof_id:
        return {"nav_badges": nav_badges}

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        if aluno_id:
            cursor.execute(
                "SELECT COUNT(*) as c FROM mensagens_inbox WHERE destinatario_id = ? AND COALESCE(lida_status, 0) = 0",
                (aluno_id,),
            )
            row_msg = cursor.fetchone()
            nav_badges["aluno_mensagens_nao_lidas"] = (row_msg["c"] or 0) if row_msg else 0

            turma_id = session.get("turma_id")
            if not turma_id:
                cursor.execute("SELECT turma_id FROM alunos WHERE id = ?", (aluno_id,))
                row_al = cursor.fetchone()
                turma_id = row_al["turma_id"] if row_al else None

            pend_av = 0
            if turma_id is not None:
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM prova_questoes pq WHERE pq.avaliacao_id = a.id) as total_q,
                        (SELECT COUNT(DISTINCT s.prova_questao_id)
                         FROM submissoes s
                         JOIN prova_questoes pq ON s.prova_questao_id = pq.id
                         WHERE s.aluno_id = ? AND pq.avaliacao_id = a.id) as resp_q
                    FROM avaliacoes a
                    WHERE a.turma_id = ? OR a.turma_id IS NULL
                """, (aluno_id, turma_id))
            else:
                cursor.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM prova_questoes pq WHERE pq.avaliacao_id = a.id) as total_q,
                        (SELECT COUNT(DISTINCT s.prova_questao_id)
                         FROM submissoes s
                         JOIN prova_questoes pq ON s.prova_questao_id = pq.id
                         WHERE s.aluno_id = ? AND pq.avaliacao_id = a.id) as resp_q
                    FROM avaliacoes a
                    WHERE a.turma_id IS NULL
                """, (aluno_id,))
            for r in cursor.fetchall():
                tq = r["total_q"] or 0
                rq = r["resp_q"] or 0
                if not (rq > 0 and tq > 0 and rq >= tq):
                    pend_av += 1

            cursor.execute(
                "SELECT COUNT(*) as c FROM reforcos_individuais WHERE aluno_id = ? AND LOWER(status) = 'pendente'",
                (aluno_id,),
            )
            row_ref = cursor.fetchone()
            pend_ref = (row_ref["c"] or 0) if row_ref else 0
            nav_badges["aluno_atividades_pendentes"] = pend_av + pend_ref

        if prof_id:
            cursor.execute(
                "SELECT COUNT(*) as c FROM submissoes WHERE status_resposta = 'Aguardando Revisão Manual'"
            )
            row_rev = cursor.fetchone()
            nav_badges["prof_revisoes_pendentes"] = (row_rev["c"] or 0) if row_rev else 0
    except Exception:
        pass
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return {"nav_badges": nav_badges}


# Registrando Blueprints
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.forum import forum_bp
from blueprints.aluno import aluno_bp
from blueprints.professor import professor_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(forum_bp)
app.register_blueprint(aluno_bp)
app.register_blueprint(professor_bp)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=is_debug, port=port)
