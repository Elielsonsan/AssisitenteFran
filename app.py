import os
from flask import Flask, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress
from dotenv import load_dotenv

# Carrega variaveis do arquivo .env
load_dotenv()

app = Flask(__name__)
csrf = CSRFProtect(app)
compress = Compress(app)

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'assistente_fran_dev_key_2026')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000 # Cache de 1 ano para arquivos estáticos (Performance)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-inicialização dos Planos de Aula
try:
    from seed_planos_aula import init_planos_aula
    import sqlite3
    DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")
    conn = sqlite3.connect(DB_PATH)
    init_planos_aula(conn)
    conn.close()
except Exception as _e:
    print(f"[!] Aviso ao inicializar planos de aula: {_e}")

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
    app.run(debug=True, port=5000)
