from flask import Blueprint, request, redirect, url_for, session, render_template, jsonify
from werkzeug.security import check_password_hash
from blueprints.extensions import get_db
import time

auth_bp = Blueprint('auth', __name__)

# Controle básico de tentativas de login por IP (proteção contra força bruta)
_LOGIN_ATTEMPTS = {}
_MAX_ATTEMPTS = 10
_LOCKOUT_SECONDS = 300

def _verificar_rate_limit(ip):
    agora = time.time()
    registro = _LOGIN_ATTEMPTS.get(ip)
    if not registro:
        return True
    tentativas, primeiro_ts = registro
    if agora - primeiro_ts > _LOCKOUT_SECONDS:
        _LOGIN_ATTEMPTS.pop(ip, None)
        return True
    return tentativas < _MAX_ATTEMPTS

def _registrar_falha_login(ip):
    agora = time.time()
    registro = _LOGIN_ATTEMPTS.get(ip)
    if not registro or (agora - registro[1] > _LOCKOUT_SECONDS):
        _LOGIN_ATTEMPTS[ip] = (1, agora)
    else:
        _LOGIN_ATTEMPTS[ip] = (registro[0] + 1, registro[1])

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "aluno_id" in session:
        return redirect(url_for("aluno.index"))
    if "prof_id" in session:
        return redirect(url_for("professor.dashboard"))
        
    erro = None
    if request.method == "POST":
        ip_cliente = request.remote_addr or "unknown"
        if not _verificar_rate_limit(ip_cliente):
            erro = "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente."
            return render_template("login.html", erro=erro, active_page="login"), 429

        login_val = (request.form.get("login") or request.form.get("matricula") or request.form.get("usuario") or "").strip()
        senha = request.form.get("senha", "").strip()
        
        if not login_val or not senha:
            erro = "Preencha login e senha."
        else:
            conn = get_db()
            cursor = conn.cursor()
            
            # 1. Verifica se é Professor (por usuario)
            cursor.execute("SELECT id, nome_completo as nome, usuario, senha_hash FROM professores WHERE usuario = ?;", (login_val,))
            prof = cursor.fetchone()
            if prof and check_password_hash(prof["senha_hash"], senha):
                _LOGIN_ATTEMPTS.pop(ip_cliente, None)
                session["prof_id"] = prof["id"]
                session["prof_nome"] = prof["nome"]
                session["prof_usuario"] = prof["usuario"]
                conn.close()
                return redirect(url_for("professor.dashboard"))
            
            # 2. Verifica se é Aluno (por matricula)
            cursor.execute("""
                SELECT a.id, a.nome_completo as nome, a.matricula, a.senha_hash, a.turma_id, a.nivel_cefr, a.foto_url, t.nome as turma_nome
                FROM alunos a LEFT JOIN turmas t ON a.turma_id = t.id WHERE a.matricula = ?;
            """, (login_val,))
            aluno = cursor.fetchone()
            if aluno and check_password_hash(aluno["senha_hash"], senha):
                _LOGIN_ATTEMPTS.pop(ip_cliente, None)
                session["aluno_id"] = aluno["id"]
                session["aluno_nome"] = aluno["nome"]
                session["matricula"] = aluno["matricula"]
                session["turma_id"] = aluno["turma_id"]
                session["turma_nome"] = aluno["turma_nome"]
                session["nivel_cefr"] = aluno["nivel_cefr"] or "A2"
                session["foto_url"] = aluno["foto_url"]
                conn.close()
                return redirect(url_for("aluno.index"))
                
            conn.close()
            _registrar_falha_login(ip_cliente)
            erro = "Login ou senha incorretos."
    return render_template("login.html", erro=erro, active_page="login")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
