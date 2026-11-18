import os
import sqlite3
import re
import unicodedata
import difflib
import subprocess
import tempfile
import wave
import struct
import math
import shutil
from functools import wraps
from flask import request, jsonify, redirect, url_for, session, g, has_app_context

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

genai_model = None
if GEMINI_API_KEY and GEMINI_API_KEY != "sua_chave_aqui":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        genai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print(f"[+] Google Gemini conectado com sucesso no modelo: {GEMINI_MODEL_NAME}")
    except Exception as e:
        print(f"[!] Erro ao inicializar Gemini: {e}")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    if has_app_context():
        conns = getattr(g, "_db_connections", None)
        if conns is None:
            conns = []
            g._db_connections = conns
        conns.append(conn)
    return conn


def close_db_connections(exception=None):
    conns = g.pop("_db_connections", None)
    if conns:
        for conn in conns:
            try:
                conn.close()
            except Exception:
                pass


def init_schema_migrations(conn):
    """Garante colunas incrementais, temas essenciais e normalização de status na inicialização."""
    cursor = conn.cursor()

    cols_p = [r[1] for r in cursor.execute("PRAGMA table_info(professores)").fetchall()]
    if cols_p:
        for col_name, col_type in [
            ("foto_perfil", "TEXT"),
            ("email", "TEXT"),
            ("telefone", "TEXT"),
            ("formacao_academica", "TEXT"),
            ("especializacao", "TEXT"),
            ("mini_curriculo", "TEXT"),
            ("link_sala_virtual", "TEXT"),
        ]:
            if col_name not in cols_p:
                cursor.execute(f"ALTER TABLE professores ADD COLUMN {col_name} {col_type}")

    cols_a = [r[1] for r in cursor.execute("PRAGMA table_info(alunos)").fetchall()]
    if cols_a:
        for col_name, col_type in [
            ("foto_url", "TEXT"),
            ("email", "TEXT"),
            ("telefone", "TEXT"),
            ("turno", "TEXT DEFAULT 'Matutino'"),
            ("status_matricula", "TEXT DEFAULT 'Ativo'"),
        ]:
            if col_name not in cols_a:
                cursor.execute(f"ALTER TABLE alunos ADD COLUMN {col_name} {col_type}")

    cols_pl = [r[1] for r in cursor.execute("PRAGMA table_info(planos_aula)").fetchall()]
    if cols_pl:
        if "ministrada" not in cols_pl:
            cursor.execute("ALTER TABLE planos_aula ADD COLUMN ministrada INTEGER DEFAULT 0")
        if "data_ministrada" not in cols_pl:
            cursor.execute("ALTER TABLE planos_aula ADD COLUMN data_ministrada TEXT")

    cols_t = [r[1] for r in cursor.execute("PRAGMA table_info(temas)").fetchall()]
    if cols_t:
        temas_essenciais = [
            "La Maison d'Être",
            "Les Pronoms Adverbiaux (Y et EN)",
            "Les Faux Amis (Falsos Cognatos)",
            "Formules de Courtoisie et Quotidien",
        ]
        for nome_t in temas_essenciais:
            cursor.execute("INSERT OR IGNORE INTO temas (nome_tema) VALUES (?);", (nome_t,))

    cols_ref = [r[1] for r in cursor.execute("PRAGMA table_info(reforcos_individuais)").fetchall()]
    if cols_ref:
        cursor.execute("UPDATE reforcos_individuais SET status = 'Pendente' WHERE LOWER(status) = 'pendente' AND status != 'Pendente'")
        cursor.execute("UPDATE reforcos_individuais SET status = 'Concluido' WHERE LOWER(status) = 'concluido' AND status != 'Concluido'")

    cols_msg = [r[1] for r in cursor.execute("PRAGMA table_info(mensagens_inbox)").fetchall()]
    if cols_msg:
        if "resposta_aluno" not in cols_msg:
            cursor.execute("ALTER TABLE mensagens_inbox ADD COLUMN resposta_aluno TEXT")
        if "data_resposta" not in cols_msg:
            cursor.execute("ALTER TABLE mensagens_inbox ADD COLUMN data_resposta TEXT")

    # Tabela de Diário de Classe / Controle de Frequência vinculada aos Planos de Aula
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presencas_aula (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plano_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            aluno_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Presente',
            observacao TEXT,
            data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(plano_id, aluno_id),
            FOREIGN KEY (plano_id) REFERENCES planos_aula(id) ON DELETE CASCADE,
            FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_presencas_plano_id ON presencas_aula(plano_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_presencas_aluno_id ON presencas_aula(aluno_id);")

    cols_sub = [r[1] for r in cursor.execute("PRAGMA table_info(submissoes)").fetchall()]
    if cols_sub and "origem_submissao" not in cols_sub:
        cursor.execute("ALTER TABLE submissoes ADD COLUMN origem_submissao TEXT DEFAULT 'curso'")
        cursor.execute(
            "UPDATE submissoes SET origem_submissao = 'curso' WHERE origem_submissao IS NULL"
        )

    conn.commit()


def validar_magic_bytes_imagem(file_storage, ext):
    """Verifica a assinatura binária (magic bytes) da imagem enviada."""
    try:
        pos = file_storage.stream.tell()
        header = file_storage.stream.read(16)
        file_storage.stream.seek(pos)
    except Exception:
        return False

    if not header or len(header) < 4:
        return False

    ext = (ext or "").lower()
    if ext == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return header.startswith(b"\xff\xd8\xff")
    if ext == ".gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if ext == ".webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "aluno_id" not in session:
            if request.is_json or request.path == "/avaliar" or request.path.startswith("/api/"):
                return jsonify({"status": "erro", "mensagem": "Sessão expirada."}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def login_required_prof(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "prof_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"status": "erro", "mensagem": "Acesso restrito ao Professor."}), 403
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def parse_retorno_gemini_frances(texto):
    texto = (texto or "").strip()
    status = "Parcialmente Correto"
    match_status = re.search(r"\*{0,2}Status:?\*{0,2}\s*(Parcialmente Correto|Incorreto|Correto)", texto, re.IGNORECASE)
    if match_status:
        status_raw = match_status.group(1).strip().title()
        if "Parcial" in status_raw:
            status = "Parcialmente Correto"
        elif "Incorret" in status_raw:
            status = "Incorreto"
        else:
            status = "Correto"

    analise_professor = "Análise registrada pelo professor virtual."
    match_analise = re.search(
        r"\*\*Análise do Professor:\*\*\s*(.*?)(?=\n-\s*\*\*Feedback|\n\*\*Feedback|$)",
        texto,
        re.DOTALL | re.IGNORECASE
    )
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


def _remover_acentos_fr(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _norm_fr(texto: str, manter_acentos: bool = True) -> str:
    s = (texto or "").replace("’", "'").replace("‘", "'").replace("«", " ").replace("»", " ")
    s = s.replace('"', " ").replace("—", " ")
    s = re.sub(r"[.,!?;:()\[\]{}\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    if not manter_acentos:
        s = _remover_acentos_fr(s)
    return s


def _extrair_trecho_entre_aspas(texto: str) -> str:
    txt = (texto or "").strip()
    if not txt:
        return ""

    # Em enunciados com múltiplas linhas (ex.: V/F e Expressão Oral), a frase-alvo fica no último bloco
    blocos = [b.strip() for b in re.split(r"\n{2,}", txt) if b.strip()]
    alvo = blocos[-1] if len(blocos) > 1 else txt

    # Caso o último bloco seja delimitado por « ... » (mesmo com « tema » interno)
    m_gul_outer = re.search(r"«(.*)»\s*$", alvo)
    if m_gul_outer and m_gul_outer.group(1).strip():
        return m_gul_outer.group(1).strip()

    # Aspas simples após dois-pontos no formato: "Instrução s'appeler: 'Frase em francês.'"
    m_colon_single = re.search(r":\s*'([^'\n]*_{2,}[^'\n]*|[^'\n]+)'\s*$", alvo)
    if m_colon_single and m_colon_single.group(1).strip():
        return m_colon_single.group(1).strip()

    # Aspas simples após dois-pontos contendo apóstrofos franceses dentro (ex.: : 'Il n'y a pas ___ sucre.')
    m_colon_full = re.search(r":\s*'(.+)'\s*$", alvo)
    if m_colon_full and m_colon_full.group(1).strip():
        return m_colon_full.group(1).strip()

    for padrao in (r"«([^»]+)»", r'"([^"\n]+)"'):
        m = re.search(padrao, alvo)
        if m and m.group(1).strip():
            return m.group(1).strip()
        m2 = re.search(padrao, txt)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()
    return txt


_ORTOGRAFIA_FLE_MAP = {
    "coment": ("comment", "falta dobrar a consoante **m** (`comment`)"),
    "francais": ("français", "falta a cedilha em **ç** (`français`)"),
    "francaise": ("française", "falta a cedilha em **ç** (`française`)"),
    "bresilien": ("brésilien", "falta o acento agudo em **é** (`brésilien`)"),
    "bresilienne": ("brésilienne", "falta o acento agudo em **é** (`brésilienne`)"),
    "etudiant": ("étudiant", "falta o acento agudo em **é** (`étudiant`)"),
    "etudiants": ("étudiants", "falta o acento agudo em **é** (`étudiants`)"),
    "etudiante": ("étudiante", "falta o acento agudo em **é** (`étudiante`)"),
    "tres": ("très", "falta o acento grave em **è** (`très`)"),
    "etre": ("être", "falta o acento circunflexo em **ê** (`être`)"),
    "eleve": ("élève", "faltam os acentos gráficos (`élève`)"),
    "eleves": ("élèves", "faltam os acentos gráficos (`élèves`)"),
    "cafe": ("café", "falta o acento agudo em **é** (`café`)"),
    "cinema": ("cinéma", "falta o acento agudo em **é** (`cinéma`)"),
    "theatre": ("théâtre", "faltam os acentos gráficos (`théâtre`)"),
    "television": ("télévision", "faltam os acentos agudos (`télévision`)"),
    "etais": ("étais", "falta o acento agudo em **é** (`étais`)"),
    "etait": ("était", "falta o acento agudo em **é** (`était`)"),
    "etions": ("étions", "falta o acento agudo em **é** (`étions`)"),
    "etiez": ("étiez", "falta o acento agudo em **é** (`étiez`)"),
    "etaient": ("étaient", "falta o acento agudo em **é** (`étaient`)"),
    "etudions": ("étudions", "falta o acento agudo em **é** (`étudions`)"),
    "etudient": ("étudient", "falta o acento agudo em **é** (`étudient`)"),
    "ecrit": ("écrit", "falta o acento agudo em **é** (`écrit`)"),
    "ecrite": ("écrite", "falta o acento agudo em **é** (`écrite`)"),
    "ecrites": ("écrites", "falta o acento agudo em **é** (`écrites`)"),
    "delicieuse": ("délicieuse", "falta o acento agudo em **é** (`délicieuse`)"),
    "bonjour": None,
    "bonjur": ("bonjour", "grafia incorreta (`bonjour` escreve-se com **ou**)"),
    "bonjor": ("bonjour", "grafia incorreta (`bonjour` escreve-se com **ou**)"),
    "mersi": ("merci", "grafia incorreta (`merci` escreve-se com **c**)"),
    "profesieur": ("professeur", "faltam dois **s** (`professeur`)"),
    "profeseur": ("professeur", "faltam dois **s** (`professeur`)"),
    "diferent": ("différent", "dobrar **ff** e acentuar **é** (`différent`)"),
    "different": ("différent", "falta o acento agudo em **é** (`différent`)"),
    "addresse": ("adresse", "em francês `adresse` tem apenas um **d** e dois **s**"),
    "adrese": ("adresse", "faltam dois **s** (`adresse`)"),
    "restorant": ("restaurant", "grafia correta com **au** (`restaurant`)"),
    "aujourdhui": ("aujourd'hui", "falta o apóstrofo em `aujourd'hui`"),
    "toujour": ("toujours", "falta o **s** final (`toujours`)"),
    "jamai": ("jamais", "falta o **s** final (`jamais`)"),
    "baucoup": ("beaucoup", "grafia correta com **eau** (`beaucoup`)"),
    "beacoup": ("beaucoup", "grafia correta com **eau** (`beaucoup`)"),
    "deman": ("demain", "grafia correta com **ai** (`demain`)"),
    "exersice": ("exercice", "grafia correta com **c** (`exercice`)"),
}


def _verificar_desvios_ortograficos_fr(texto: str):
    """Detecta erros de consoantes duplas (ex.: m'apele/s'apelle), acentuação e grafia em francês."""
    desvios = []
    vistas = set()
    s = (texto or "").replace("’", "'").replace("‘", "'")

    # 1. Regra específica para o verbo appeler / s'appeler (pp + ll diante de 'e' mudo)
    for m in re.finditer(r"\b(?:([mtsj])')?(ap{1,2}el{1,2}e?s?)\b", s, re.IGNORECASE):
        pron = (m.group(1) or "").lower()
        rad = m.group(2).lower()
        forma_orig = m.group(0)
        esperado = None
        dica_regra = ""

        if pron in ("m", "s"):
            esperado_rad = "appelle"
            if rad != esperado_rad:
                esperado = f"{pron}'{esperado_rad}"
                dica_regra = f"o verbo *s'appeler* no presente dobra tanto o **p** (**pp**) quanto o **l** (**ll**) -> **`{esperado}`**"
        elif pron == "t":
            esperado_rad = "appelles"
            if rad != esperado_rad:
                esperado = f"{pron}'{esperado_rad}"
                dica_regra = f"com *tu*, dobra **pp** e **ll** e recebe **-es** -> **`{esperado}`**"
        elif rad in ("apele", "apelle", "appele", "apeles", "apelles", "appeles"):
            esperado = "appelle"
            dica_regra = "o verbo *appeler* no singular dobra **p** e **l** -> **`appelle`**"

        if esperado and forma_orig.lower() not in vistas:
            vistas.add(forma_orig.lower())
            desvios.append((forma_orig, esperado, dica_regra))

    # 2. Demais termos comuns com desvio ortográfico ou falta de acento
    for m in re.finditer(r"\b[a-zàâäéèêëïîôùûüç']+\b", s, re.IGNORECASE):
        token = m.group(0)
        low = token.lower()
        if low in vistas:
            continue
        reg = _ORTOGRAFIA_FLE_MAP.get(low)
        if reg is not None:
            esperado, motivo = reg
            vistas.add(low)
            desvios.append((token, esperado, motivo))

    return desvios


def _detectar_modalidade_avaliacao(exercicio: str, tipo_atividade: str = "") -> str:
    t = (tipo_atividade or "").strip().lower()
    if t in ("lacunas", "vf", "multipla_escolha", "ditado", "expressao_oral", "producao_escrita"):
        return t
    ex_low = (exercicio or "").lower()
    if "vrai" in ex_low and "faux" in ex_low:
        return "vf"
    if re.search(r"(?:^|\n)\s*(?:\(?[a-d]\)|[A-D]\))", exercicio or ""):
        return "multipla_escolha"
    if "___" in (exercicio or ""):
        return "lacunas"
    if any(k in ex_low for k in ("traduza", "elabore", "produção textual", "redigir")):
        return "producao_escrita"
    if any(k in ex_low for k in ("pronuncie", "voz alta")):
        return "expressao_oral"
    return "lacunas"


_ERROS_VF_PADROES = [
    (r"\bont\s+arriv[ée]e?s?\b", "Com o verbo 'arriver' (Maison d'Être), o auxiliar deve ser **être** (*sont arrivées*), nunca *avoir* (*ont*)."),
    (r"\ba\s+parti(?:e|s)?\b", "O verbo 'partir' exige o auxiliar **être** (*est partie*), e não *avoir* (*a parti*)."),
    (r"\b(?:avons|avez|ont|as|a)\s+aller\b", "O verbo 'aller' exige o auxiliar **être** e particípio passado (*sommes allés*), nunca o infinitivo com *avoir*."),
    (r"\ba\s+all[ée]e?s?\b", "O verbo 'aller' conjuga com **être** (*est allée*), não com *avoir*."),
    (r"\b(?:avons|avez|ont)\s+rest[ée]s?\b", "O verbo 'rester' pertence à Maison d'Être e exige auxiliar **être** (*sommes restés*)."),
    (r"quand\s+j'[ée]tais[^.!?]*\bnous\s+allons\b", "Quando se descreve um hábito no passado (*Quand j'étais enfant*), o verbo principal deve estar no **Imparfait** (*nous allions*), não no presente."),
    (r"\bne\s+(?:\w+\s+)?pas\s+(?:du|des|de\s+la)\s+(?:caf[ée]|fromage|sucre|amis|viande)\b", "Em frases negativas absolutas, os artigos partitivos/indefinidos mudam para **de / d'** (*pas de café*, *pas de sucre*, *pas d'amis*)."),
    (r"\b(?:des|de\s+la|du)\s+fruits\b[^.!?]*\bj'y\s+mange\b", "Quando substituímos um complemento partitivo ou de quantidade (*des fruits*), usamos o pronome **en** (*j'en mange*), não *y*."),
    (r"\bt[ée]l[ée]phone\s+[àa]\b[^.!?]*\bles\s+t[ée]l[ée]phone\b", "O verbo *téléphoner à* pede pronome indireto (COI: *lui* ou *leur*), e não direto (*les*). Correto: *je leur téléphone*."),
    (r"\b(?:il\s+est\s+n[ée]cessaire|il\s+faut|exige|souhaite)\s+que\s+tu\s+prends\b", "Após expressões de necessidade como *il faut que / il est nécessaire que*, deve-se empregar o **Subjonctif** (*que tu prennes*), não o indicativo."),
    (r"\b(?:marie\s+et\s+sophie|elles)\s+sont\s+arriv[ée]\b(?!e?s)", "Falta a concordância feminino plural no particípio passado com **être**: *sont arrivées*."),
]


def _analisar_erro_frase_vf(frase: str):
    f_low = (frase or "").lower()
    for padrao, explicacao in _ERROS_VF_PADROES:
        if re.search(padrao, f_low):
            return explicacao
    return None


_CORRECOES_VF_PADROES = [
    (re.compile(r"\bont\s+arriv[ée]e?s?\b", re.IGNORECASE), "sont arrivées"),
    (re.compile(r"\ba\s+parti(?:e|s)?\b", re.IGNORECASE), "est partie"),
    (re.compile(r"\bavons\s+aller\b", re.IGNORECASE), "sommes allés"),
    (re.compile(r"\bont\s+aller\b", re.IGNORECASE), "sont allés"),
    (re.compile(r"\ba\s+all[ée]e?s?\b", re.IGNORECASE), "est allée"),
    (re.compile(r"\bavons\s+rest[ée]s?\b", re.IGNORECASE), "sommes restés"),
    (re.compile(r"\bnous\s+allons\b", re.IGNORECASE), "nous allions"),
    (re.compile(r"\bpas\s+(?:du|des|de\s+la)\s+(caf[ée]|fromage|sucre|viande)\b", re.IGNORECASE), r"pas de \1"),
    (re.compile(r"\bpas\s+des\s+(amis)\b", re.IGNORECASE), r"pas d'\1"),
    (re.compile(r"\bj'y\s+mange\b", re.IGNORECASE), "j'en mange"),
    (re.compile(r"\bles\s+t[ée]l[ée]phone\b", re.IGNORECASE), "leur téléphone"),
    (re.compile(r"\bque\s+tu\s+prends\b", re.IGNORECASE), "que tu prennes"),
]


def _corrigir_frase_vf_modelo(frase: str) -> str:
    txt = (frase or "").strip()
    if not txt:
        return ""
    corrigida = txt
    for padrao_rx, subst in _CORRECOES_VF_PADROES:
        corrigida = padrao_rx.sub(subst, corrigida)
    return corrigida if corrigida != txt else ""


_GABARITOS_MC = [
    ("marie et sophie", "sont arrivees", "Com *Marie et Sophie* (feminino plural) e o verbo *arriver* (Maison d'Être), o correto é o auxiliar **être** com acordo **-ées**: *sont arrivées*."),
    ("mes amis", "sont arrives", "Com *mes amis* (masculino plural) e *arriver*, utiliza-se **être** com acordo plural: *sont arrivés*."),
    ("mes soeurs", "sont", "Na Maison d'Être (*naître*), com *mes sœurs* (3ª pessoa plural), o auxiliar é **être**: *sont* (*Mes sœurs sont nées*)."),
    ("elle ___ nées", "sont", "O correto é utilizar o auxiliar *être*."),
    ("autrefois", "habitaient", "O marcador temporal *autrefois* pede o **Imparfait** na 3ª pessoa do plural (*ils habitaient*)."),
    ("ne prends pas", "de", "Na frase negativa absoluta, o artigo partitivo muda para **de**: *Je ne prends pas de sucre*."),
    ("d'amis", "je n'ai pas d'amis", "Em negação absoluta, *des* vira **d'** diante de vogal: *Je n'ai pas d'amis à Lyon*."),
    ("a lyon", "j'y vais demain", "Substituindo um complemento de lugar introduzido por *à* (*à Lyon*), emprega-se o pronome **y**: *J'y vais demain*."),
    ("a sophie", "je lui parle", "Com o verbo *parler à* + pessoa singular (*à Sophie*), usa-se o pronome COI **lui**: *Je lui parle*."),
    ("a l'heure", "soyons", "Após *exige que* / *il est important que*, é obrigatório o **Subjonctif Présent** de *être* com *nous*: *soyons*."),
    ("les etudiants", "finissent", "Com *les étudiants* (3ª pessoa do plural), o verbo *finir* (2º grupo) conjuga **finissent**."),
    ("manger", "mangeons", "Com *nous*, verbos terminados em *-ger* mantêm o **e** antes de *-ons* para preservar o som: *mangeons*."),
    ("sorbonne", "etudient", "Com *elles* (3ª pessoa plural), o verbo *étudier* recebe a terminação **-ent**: *étudient*."),
    ("eau minerale", "de l'", "*Eau* começa por vogal, exigindo o partitivo **de l'**."),
    ("mon pere est", "tante", "A irmã do meu pai é minha **tante** (*Tante*)."),
    ("frere de votre mere", "l'oncle", "O irmão da sua mãe é **L'oncle**."),
]


def _extrair_opcoes_e_correta_mc(exercicio: str):
    opcoes = {}
    for line in (exercicio or "").splitlines():
        m = re.match(r"^\s*\(?([A-Da-d])[\)\.\-]\s*(.+)$", line.strip())
        if m:
            opcoes[m.group(1).upper()] = m.group(2).strip()
    if not opcoes:
        return {}, None, ""

    ex_norm = _norm_fr(exercicio, manter_acentos=False)
    for chave_enunc, alvo_op, exp in _GABARITOS_MC:
        if chave_enunc in ex_norm:
            for l_cand, t_cand in opcoes.items():
                if alvo_op in _norm_fr(t_cand, manter_acentos=False):
                    return opcoes, l_cand, exp
    return opcoes, None, "Revise a concordância verbal, o auxiliar e a regência da frase."


def _avaliar_multipla_escolha(exercicio: str, resposta: str):
    opcoes, letra_correta, explicacao = _extrair_opcoes_e_correta_mc(exercicio)
    if not opcoes:
        return None

    resp_trim = (resposta or "").strip()
    letra_escolhida = None
    m_letra = re.match(r"^\(?([A-Da-d])(?:[\)\.\-\s]|$)", resp_trim)
    if m_letra:
        letra_escolhida = m_letra.group(1).upper()
    else:
        resp_norm = _norm_fr(resp_trim, manter_acentos=False)
        for letra, texto_op in opcoes.items():
            if resp_norm == _norm_fr(texto_op, manter_acentos=False):
                letra_escolhida = letra
                break

    if not letra_escolhida or letra_escolhida not in opcoes:
        return (
            "Incorreto",
            "A resposta enviada não corresponde a uma das alternativas (A, B, C ou D).",
            "### *Attention !*\n\nSua resposta não corresponde às alternativas propostas. Selecione ou informe a letra **A**, **B**, **C** ou **D** (ex.: `B`).\n\n**Dica:** Analise atentamente o verbo, auxiliar ou pronome pedido antes de escolher."
        )

    if not letra_correta:
        # Heurística gramatical caso a questão venha da IA com opções inéditas
        erro_na_escolha = _analisar_erro_frase_vf(opcoes[letra_escolhida])
        if erro_na_escolha:
            return (
                "Incorreto",
                f"Alternativa {letra_escolhida} incorreta: {erro_na_escolha}",
                f"### *Pas tout à fait !*\n\nA alternativa **{letra_escolhida}) {opcoes[letra_escolhida]}** não está correta.\n\n**Dica:** {erro_na_escolha}"
            )
        return (
            "Correto",
            f"Alternativa {letra_escolhida} selecionada ({opcoes[letra_escolhida]}).",
            f"### *Très bien !*\n\nVocê escolheu **{letra_escolhida}) {opcoes[letra_escolhida]}**, que atende adequadamente à estrutura pedida na questão."
        )

    if letra_escolhida == letra_correta:
        return (
            "Correto",
            f"O aluno escolheu corretamente a alternativa {letra_correta}) {opcoes[letra_correta]}.",
            f"### *Très bien !*\n\nAlternativa correta: **{letra_correta}) {opcoes[letra_correta]}**.\n\n{explicacao}"
        )

    return (
        "Incorreto",
        f"O aluno marcou {letra_escolhida}) {opcoes[letra_escolhida]}, mas a correta era {letra_correta}) {opcoes[letra_correta]}.",
        f"### *Attention !*\n\nVocê marcou **{letra_escolhida}) {opcoes[letra_escolhida]}**, porém essa opção apresenta um desvio gramatical.\n\n**Dica:** {explicacao}"
    )


def _avaliar_vf(exercicio: str, resposta: str):
    resp_trim = (resposta or "").strip()
    m_vf = re.match(r"^(vrai|faux)\b(?:\s*[—\-:]\s*(.*))?$", resp_trim, re.IGNORECASE | re.DOTALL)
    if not m_vf:
        return (
            "Incorreto",
            "Não foi informado o julgamento 'Vrai' ou 'Faux'.",
            "### *Attention !*\n\nPara essa modalidade, indique primeiro se a frase é **Vrai** (verdadeira) ou **Faux** (falsa) e, se for falsa, reescreva a correção.\n\n**Dica:** Observe com cuidado o auxiliar (*être/avoir*), a concordância e as preposições."
        )

    julgamento = m_vf.group(1).title()
    reescrita = (m_vf.group(2) or "").strip()
    frase_proposta = _extrair_trecho_entre_aspas(exercicio)
    erro_frase = _analisar_erro_frase_vf(frase_proposta)

    if erro_frase:
        # A frase proposta É FALSA
        if julgamento == "Vrai":
            return (
                "Incorreto",
                f"O aluno julgou a frase como Vrai, mas ela contém erro: {erro_frase}",
                f"### *Pas tout à fait !*\n\nNa verdade, a frase proposta contém uma incorreção gramatical (**Faux**).\n\n**Dica:** {erro_frase}"
            )
        # Julgou Faux! Verificar se reescreveu corretamente
        if not reescrita or _norm_fr(reescrita, False) == _norm_fr(frase_proposta, False):
            return (
                "Parcialmente Correto",
                f"O aluno identificou corretamente que a frase é Faux, mas não apresentou a frase corrigida.",
                f"### *Presque !*\n\nVocê acertou ao identificar que a frase é **Faux**! Para completar a pontuação máxima, reescreva a frase corrigida no campo abaixo.\n\n**Dica:** {erro_frase}"
            )
        erro_reescrita = _analisar_erro_frase_vf(reescrita)
        if erro_reescrita:
            return (
                "Parcialmente Correto",
                f"O aluno julgou Faux corretamente, mas a reescrita ainda mantém incorreção: {erro_reescrita}",
                f"### *Presque !*\n\nVocê acertou ao marcar **Faux**, porém sua reescrita (*« {reescrita} »*) ainda precisa de ajuste.\n\n**Dica:** {erro_reescrita}"
            )
        sim = difflib.SequenceMatcher(None, _norm_fr(reescrita, False), _norm_fr(frase_proposta, False)).ratio()
        if sim < 0.45:
            return (
                "Parcialmente Correto",
                "O julgamento Faux está correto, mas a reescrita fugiu muito da frase original.",
                "### *Presque !*\n\nVocê marcou **Faux** corretamente, mas tente manter a mesma estrutura da frase original corrigindo apenas o verbo/elemento incorreto."
            )
        desvios_vf = _verificar_desvios_ortograficos_fr(reescrita)
        if desvios_vf:
            return _formatar_feedback_ortografia(desvios_vf, contexto=" na reescrita de Vrai ou Faux")
        return (
            "Correto",
            "O aluno identificou corretamente Faux e reescreveu a frase aplicando a norma culta do francês.",
            f"### *Très bien !*\n\nExcelente! Você identificou corretamente que a sentença era **Faux** e fez a correção adequada (*« {reescrita} »*)."
        )

    # A frase proposta É VERDADEIRA
    if julgamento == "Vrai":
        return (
            "Correto",
            "O aluno identificou corretamente que a sentença é Vrai.",
            f"### *Très bien !*\n\nCorreto! A frase *« {frase_proposta} »* está gramaticalmente bem construída (**Vrai**)."
        )
    return (
        "Incorreto",
        "A frase proposta está gramaticalmente correta (Vrai), mas o aluno a classificou como Faux.",
        f"### *Attention !*\n\nNa verdade, a frase *« {frase_proposta} »* já está **correta (Vrai)** — os verbos, auxiliares e concordâncias estão em conformidade com o francês padrão.\n\n**Dica:** Releia o auxiliar e o particípio ou pronome da frase original: não há erro oculto nela."
    )


def _avaliar_ditado_ou_oral(exercicio: str, resposta: str, modalidade: str):
    alvo = _extrair_trecho_entre_aspas(exercicio)
    alvo_norm = re.sub(r"'\s+", "'", _norm_fr(alvo, manter_acentos=True))
    resp_norm = re.sub(r"'\s+", "'", _norm_fr(resposta, manter_acentos=True))

    alvo_sem = re.sub(r"'\s+", "'", _norm_fr(alvo, manter_acentos=False))
    resp_sem = re.sub(r"'\s+", "'", _norm_fr(resposta, manter_acentos=False))

    if not resp_sem or len(resp_sem) < 2:
        msg_vazio = (
            "### *Attention !*\n\nNão foi possível identificar palavras em francês na gravação. Clique em **\"Tentar Novamente com a Dica\"** para gravar novamente falando perto do microfone."
            if modalidade == "expressao_oral"
            else "### *Attention !*\n\nDigite ou dite a frase completa em francês antes de enviar."
        )
        return ("Incorreto", "Resposta vazia ou insuficiente.", msg_vazio)

    if modalidade == "expressao_oral":
        if resp_sem == alvo_sem:
            return (
                "Correto",
                f"Pronúncia transcrita corresponde integralmente à frase proposta: '{alvo}'.",
                f"### *Excellent !*\n\nPronúncia clara e fiel à sentença proposta: *« {alvo} »*."
            )

        ratio_oral = difflib.SequenceMatcher(None, resp_sem, alvo_sem).ratio()
        palavras_alvo_l = alvo_sem.split()
        palavras_resp_l = resp_sem.split()
        faltantes = [w for w in palavras_alvo_l if w not in palavras_resp_l]
        trocadas = [w for w in palavras_resp_l if w not in palavras_alvo_l]

        detalhes = []
        if trocadas:
            detalhes.append(f"compreendido como `{', '.join(trocadas[:4])}`")
        if faltantes:
            detalhes.append(f"esperado `{', '.join(faltantes[:4])}`")
        resumo_dif = (" (" + " → ".join(detalhes) + ")") if detalhes else ""

        if ratio_oral >= 0.72:
            return (
                "Parcialmente Correto",
                f"Expressão oral com correspondência parcial ({round(ratio_oral * 100)}%){resumo_dif}.",
                f"### *Presque !*\n\nA maior parte da sua pronúncia foi reconhecida, mas houve pequenas diferenças nas palavras captadas{resumo_dif}.\n\n"
                f"**Dica:** Ouça a pronúncia modelo no botão **Ouvir** do exercício (frase-alvo: *« {alvo} »*) e clique em **\"Tentar Novamente com a Dica\"** para gravar novamente."
            )

        return (
            "Incorreto",
            f"Baixa correspondência oral com a frase esperada ({round(ratio_oral * 100)}%){resumo_dif}.",
            f"### *Attention !*\n\nO que foi compreendido no áudio divergiu bastante da frase proposta (*« {alvo} »*){resumo_dif}.\n\n"
            f"**Dica:** Ouça o enunciado no botão **Ouvir**, articule cada sílaba em francês com calma e clique em **\"Tentar Novamente com a Dica\"** para regravar."
        )

    # Modalidade: Compreensão Auditiva (Ditado) — rigor ortográfico total
    desvios_ort = _verificar_desvios_ortograficos_fr(resposta)

    if resp_norm == alvo_norm:
        if desvios_ort:
            return _formatar_feedback_ortografia(desvios_ort, contexto=f" em {modalidade}")
        return (
            "Correto",
            f"Transcrição exata: '{alvo}'.",
            f"### *Excellent !*\n\nTranscrição exata! Você reproduziu com precisão a frase: *« {alvo} »*."
        )

    if desvios_ort and difflib.SequenceMatcher(None, resp_sem, alvo_sem).ratio() >= 0.75:
        return _formatar_feedback_ortografia(desvios_ort, contexto=f" em {modalidade}")

    if resp_sem == alvo_sem:
        palavras_alvo = alvo_norm.split()
        palavras_resp = resp_norm.split()
        faltando_acento = [pa for pa, pr in zip(palavras_alvo, palavras_resp) if pa != pr]
        detalhe = f" ({', '.join(faltando_acento[:4])})" if faltando_acento else ""
        return (
            "Parcialmente Correto",
            f"A estrutura lexical está correta, porém faltaram/divergiram acentos franceses{detalhe}.",
            f"### *Presque parfait !*\n\nVocê acertou todas as palavras da frase! Fique atento apenas à acentuação em francês{detalhe}.\n\n**Dica:** Utilize a barra de caracteres especiais (`é`, `è`, `ê`, `à`, `ç`) para revisar os acentos."
        )

    ratio = difflib.SequenceMatcher(None, resp_sem, alvo_sem).ratio()
    palavras_alvo_l = alvo_sem.split()
    palavras_resp_l = resp_sem.split()
    faltantes = [w for w in palavras_alvo_l if w not in palavras_resp_l]

    if ratio >= 0.78:
        dica_falta = f" Revise especialmente os trechos com: `{', '.join(faltantes[:4])}`." if faltantes else ""
        return (
            "Parcialmente Correto",
            f"Similaridade de {round(ratio * 100)}% com a frase esperada.",
            f"### *Bien essayé, presque !*\n\nVocê compreendeu a maior parte da frase, mas houve pequenas diferenças na grafia ou omissão de palavras.{dica_falta}\n\n**Dica:** Ouça novamente em ritmo calmo prestando atenção às terminações e artigos."
        )

    return (
        "Incorreto",
        f"Baixa correspondência com o texto-alvo ({round(ratio * 100)}%).",
        f"### *Attention !*\n\nSua resposta ainda está distante da frase proposta ({len(palavras_resp_l)} palavras registradas contra {len(palavras_alvo_l)} no áudio).\n\n**Dica:** Utilize os botões de **Voltar trecho** e **Ritmo Calmo** no player para ouvir palavra por palavra com calma."
    )


def _obter_gabaritos_lacuna(exercicio: str, tema: str):
    """Retorna lista de preenchimentos aceitos para a lacuna com base no exercício."""
    ex_norm = _norm_fr(exercicio, manter_acentos=False)
    respostas_map = [
        ("hier, nous ___ (aller) au cinema", ["sommes allés"]),
        ("marie et sophie ___ (arriver)", ["sont arrivées"]),
        ("nous ___ (aller) au cinema", ["sommes allés"]),
        ("sophie ___ (partir) de la maison", ["est partie"]),
        ("elle ___ (partir) tres tot", ["est partie"]),
        ("ils ___ (choisir) un bon restaurant", ["ont choisi"]),
        ("ont ___ (finir) leur travail", ["fini"]),
        ("au petit-dejeuner, je bois ___ cafe", ["du"]),
        ("elles ___ (arriver) a paris", ["sont arrivées"]),
        ("elles ___ (partir) en vacances", ["sont parties"]),
        ("quand j'etais enfant, nous ___ (aller)", ["allions"]),
        ("cafe, mais je ne mets pas ___ sucre", ["du", "de"]),
        ("il n'y a pas ___ sucre", ["de"]),
        ("je prends ___ cafe", ["du"]),
        ("tu prends du cafe", ["en"]),
        ("combien", ["en"]),
        ("je ___ ecris chaque semaine", ["leur"]),
        ("je ___ telephone tous les dimanches", ["leur"]),
        ("oui, je ___ ai envoyee ce matin", ["la lui", "l'"]),
        ("vous ___ (faire) attention", ["fassiez"]),
        ("il est imperatif que vous ___ (faire)", ["fassiez"]),
        ("qu'elle ne ___ (venir) pas", ["vienne"]),
        ("nous ___ (habiter) a lyon", ["habitons"]),
        ("vous ___ (parler) tres bien", ["parlez"]),
        ("nous ___ (parler) couramment", ["parlons"]),
        ("ils ecout___", ["ent"]),
        ("tu ___ (habiter)", ["habites"]),
        ("vous ___ (aimer)", ["aimez"]),
        ("vous ___ (commencer)", ["commencez"]),
        ("nous ___ (etudier)", ["étudions"]),
        ("nous ___ (choisir)", ["choisissons"]),
        ("les lettres que j'ai ___ (ecrire)", ["écrites"]),
        ("elles sont ___ (partir)", ["parties"]),
        ("tu l'as ___ (entendre)", ["entendue"]),
        ("nous les avons ___ (manger)", ["mangées"]),
        ("marc ___ (perdre) ses cles", ["a perdu"]),
        ("le musee est ___ (en face de / a cote)", ["en face de", "à côté de", "a cote de"]),
        ("elle ___ boit ___ de cafe", ["ne ... pas", "ne pas", "ne", "n'"]),
        ("le pere de mon pere est mon ___", ["grand-père", "grand père"]),
        ("j'adore ___ (mon/ma/mes) grand-mere", ["ma"]),
        ("la fille de ma tante est ma ___", ["cousine"]),
        ("vous ___ (etre) etudiants a paris", ["étiez"]),
        ("le telephone ___ (sonner)", ["a sonné"]),
        ("je ___ regarde ce soir", ["le"]),
        ("j'___ vais souvent", ["y"]),
        ("j'___ mange tous les jours", ["en"]),
        ("je ___ (vouloir) reserver", ["voudrais"]),
        ("nous ___ (vouloir) reserver", ["voudrions"]),
        ("je ___ (voyager) a travers", ["voyagerais"]),
        ("qu'il ___ (venir)", ["vienne"]),
        ("m'___ (appeler)", ["appelle"]),
        ("je suis ___ (bresilien / bresilienne)", ["brésilien", "brésilienne"]),
        ("nous ___ (regarder) un documentaire", ["avons regardé"]),
        ("les enfants ___ (dormir)", ["ont dormi"]),
    ]
    for chave, cands in respostas_map:
        if _norm_fr(chave, manter_acentos=False) in ex_norm:
            return cands

    # Fallback inteligente via sujeito + verbo entre parênteses quando existir "(verbo)"
    m_verb = re.search(r"([a-zàâäéèêëïîôùûüç']+)\s+___\s*\(([^)]+)\)", exercicio or "", re.IGNORECASE)
    if m_verb:
        suj = m_verb.group(1).lower()
        verbo = m_verb.group(2).strip().lower()
        t_low = (tema or "").lower()
        eh_passe = "passé" in t_low or "passe" in t_low or "hier" in ex_norm
        eh_imparf = "imparfait" in t_low or "quand j'etais" in ex_norm
        eh_subj = "subjonctif" in t_low or "il faut que" in ex_norm
        if verbo == "étudier" and suj == "nous":
            return ["étudions"]
        if verbo == "aller" and eh_passe:
            if suj in ("nous", "vous"):
                return ["sommes allés" if suj == "nous" else "êtes allés"]
        if verbo == "aller" and eh_imparf and suj == "nous":
            return ["allions"]
        if verbo == "faire" and eh_subj and suj == "vous":
            return ["fassiez"]
        # Presente regular 1o grupo
        if verbo.endswith("er") and not eh_passe and not eh_imparf and not eh_subj:
            rad = verbo[:-2]
            termin = {"je": "e", "tu": "es", "il": "e", "elle": "e", "on": "e", "nous": "ons", "vous": "ez", "ils": "ent", "elles": "ent"}.get(suj)
            if termin:
                return [rad + termin]
    return []


def _formatar_feedback_ortografia(desvios_ort, contexto=""):
    itens = [f"- **`{orig}`** → **`{esp}`** ({motivo})" for orig, esp, motivo in desvios_ort]
    analise = f"Estrutura/ideia adequada{contexto}, porém com desvio(s) ortográfico(s): " + "; ".join(f"{o} -> {e}" for o, e, _ in desvios_ort) + "."
    feedback = (
        "### *Presque ! Atenção à ortografia*\n\n"
        "Sua frase está bem encaminhada na estrutura gramatical, mas encontramos detalhes ortográficos para ajustar antes de atingir 100%:\n\n"
        + "\n".join(itens)
        + "\n\n**Dica:** Revise as consoantes duplas e os acentos franceses e tente novamente!"
    )
    return "Parcialmente Correto", analise, feedback


_REGRAS_MULTIPLAS_LACUNAS = [
    {
        "chave": "bonjour je ___ pierre et voici mon amie elle ___ sophie",
        "partes_esperadas": ["m'appelle", "s'appelle"],
        "frase_modelo": "Bonjour! Je m'appelle Pierre et voici mon amie, elle s'appelle Sophie.",
        "dica": "O verbo pronominal *s'appeler* no presente exige **dois p (`pp`)** e **dois l (`ll`)** com *je/il/elle*: `m'appelle` e `s'appelle`."
    },
    {
        "chave": "je bois ___ cafe et je mange ___ croissants avec ___ confiture",
        "partes_esperadas": ["du", "des", "de la"],
        "frase_modelo": "Au petit-déjeuner, je bois du café et je mange des croissants avec de la confiture.",
        "dica": "Use os artigos partitivos conforme gênero e número: `du café` (masc.), `des croissants` (plural) e `de la confiture` (fem.)."
    },
    {
        "chave": "je ___ bois ___ d'alcool",
        "partes_esperadas": ["ne", "plus"],
        "alt_aceitas": [["ne", "jamais"]],
        "frase_modelo": "Je ne bois plus d'alcool.",
        "dica": "Como o enunciado diz 'j'ai complètement arrêté' (parei completamente), utilize a estrutura `ne ... plus`."
    },
    {
        "chave": "hier soir nous ___ aller au restaurant et nous ___ manger",
        "partes_esperadas": ["sommes allés", "avons mangé"],
        "frase_modelo": "Hier soir, nous sommes allés au restaurant et nous avons mangé une délicieuse crêpe.",
        "dica": "Use **être** com acordo plural para *aller* (`sommes allés`) e **avoir** para *manger* (`avons mangé`)."
    },
    {
        "chave": "quand j'___ etre petit nous ___ vivre",
        "partes_esperadas": ["étais", "vivions"],
        "frase_modelo": "Quand j'étais petit, nous vivions à la campagne.",
        "dica": "No **Imparfait**, *être* faz `étais` e *vivre* com *nous* faz `vivions`."
    },
    {
        "chave": "pendant qu'il ___ dormir le telephone ___ sonner",
        "partes_esperadas": ["dormait", "a sonné"],
        "frase_modelo": "Pendant qu'il dormait, le téléphone a sonné.",
        "dica": "Ação contínua de fundo no **Imparfait** (`dormait`) interrompida por ação pontual no **Passé Composé** (`a sonné`)."
    },
    {
        "chave": "si nous ___ avoir plus de temps nous ___ voyager",
        "partes_esperadas": ["avions", "voyagerions"],
        "frase_modelo": "Si nous avions plus de temps, nous voyagerions autour du monde.",
        "dica": "Estrutura de hipótese: *Si + Imparfait* (`avions`) + *Conditionnel Présent* (`voyagerions`)."
    },
    {
        "chave": "cet ete je vais ___ france puis ___ japon et enfin ___ etats unis",
        "partes_esperadas": ["en", "au", "aux"],
        "frase_modelo": "Cet été, je vais en France, puis au Japon et enfin aux États-Unis.",
        "dica": "País feminino (`en France`), masculino (`au Japon`) e plural (`aux États-Unis`)."
    },
    {
        "chave": "le matin je prends ___ cafe mais je ne mets pas ___ sucre",
        "partes_esperadas": ["du", "de"],
        "frase_modelo": "Le matin, je prends du café, mais je ne mets pas de sucre.",
        "dica": "Na frase afirmativa usa-se o partitivo **du** (`du café`), e na negativa absoluta substitui-se por **de** (`pas de sucre`)."
    },
]


def _avaliar_multiplas_lacunas_ou_transformacao(exercicio: str, resposta: str, tema: str):
    """Avalia exercícios de 2+ lacunas ou transformação do banco considerando ortografia à risca."""
    ex_norm = _norm_fr(exercicio, manter_acentos=False)
    resp_norm = _norm_fr(resposta, manter_acentos=True)
    resp_sem = _norm_fr(resposta, manter_acentos=False)
    desvios_ort = _verificar_desvios_ortograficos_fr(resposta)

    for reg in _REGRAS_MULTIPLAS_LACUNAS:
        if reg["chave"] in ex_norm:
            modelo_sem = _norm_fr(reg["frase_modelo"], manter_acentos=False)
            modelo_com = _norm_fr(reg["frase_modelo"], manter_acentos=True)

            # Verifica se o aluno acertou todas as partes esperadas (com acento exato e sem desvios ortográficos)
            partes = reg["partes_esperadas"]
            alts = reg.get("alt_aceitas", [])
            conjuntos_validos = [partes] + alts

            acertou_com_acento = False
            acertou_sem_acento = False
            for cj in conjuntos_validos:
                if all(_norm_fr(p, True) in resp_norm for p in cj):
                    acertou_com_acento = True
                    break
                if all(_norm_fr(p, False) in resp_sem for p in cj):
                    acertou_sem_acento = True

            if desvios_ort:
                # Verifica se a frase tem alta semelhança com o modelo mesmo tendo desvios como m'apele/s'apelle
                sim = difflib.SequenceMatcher(None, resp_sem, modelo_sem).ratio()
                if sim >= 0.75 or acertou_sem_acento:
                    return _formatar_feedback_ortografia(desvios_ort, contexto=f" em '{tema}'")

            if acertou_com_acento and not desvios_ort:
                return (
                    "Correto",
                    f"Todas as lacunas preenchidas corretamente em '{tema}'.",
                    f"### *Très bien !*\n\nExcelente domínio de conjugação, ortografia e estrutura: *« {reg['frase_modelo']} »*."
                )

            if acertou_sem_acento:
                return (
                    "Parcialmente Correto",
                    f"As formas esperadas foram identificadas, porém faltou acentuação gráfica exata ({', '.join(partes)}).",
                    f"### *Presque !*\n\nVocê acertou os termos principais, mas revise a acentuação em francês (`{', '.join(partes)}`).\n\n**Dica:** {reg['dica']}"
                )

            # Verifica acerto parcial (acertou pelo menos 1 das lacunas)
            acertos_parciais = sum(1 for p in partes if _norm_fr(p, True) in resp_norm)
            if acertos_parciais > 0 and acertos_parciais < len(partes):
                return (
                    "Parcialmente Correto",
                    f"Acertou {acertos_parciais} de {len(partes)} lacuna(s) esperada(s) ({', '.join(partes)}).",
                    f"### *Presque !*\n\nVocê acertou parte das lacunas, mas uma delas ainda precisa de ajuste.\n\n**Dica:** {reg['dica']}"
                )

            return (
                "Incorreto",
                f"Preenchimento incorreto para '{tema}' (esperado: {', '.join(partes)}).",
                f"### *Pas tout à fait !*\n\nRevise as lacunas da sentença.\n\n**Dica:** {reg['dica']}"
            )

    # Transformações para forma negativa
    if "paul mange de la viande" in ex_norm:
        alvo = "paul ne mange pas de viande"
        if alvo in resp_sem:
            if desvios_ort:
                return _formatar_feedback_ortografia(desvios_ort, " na negação")
            return ("Correto", "Negação absoluta aplicada corretamente ('ne ... pas de').", "### *Très bien !*\n\nTransformação perfeita: **Paul ne mange pas de viande.**")
        if "ne mange pas de la viande" in resp_sem:
            return ("Parcialmente Correto", "Aplicou 'ne ... pas', mas esqueceu de converter o partitivo 'de la' para 'de'.", "### *Presque !*\n\nVocê posicionou corretamente **ne ... pas**, mas lembre-se da regra: na negação absoluta, *du / de la* torna-se **`de`** (*Paul ne mange pas **de** viande*).")
        return ("Incorreto", "Transformação negativa esperada: 'Paul ne mange pas de viande.'", "### *Attention !*\n\nUse `ne` antes e `pas` depois do verbo, convertendo `de la` em `de`: *ne ... pas de viande*.")

    if "paul regarde la television tous les soirs" in ex_norm:
        if "paul ne regarde pas la television tous les soirs" in resp_sem:
            if desvios_ort:
                return _formatar_feedback_ortografia(desvios_ort, " na frase negativa")
            return ("Correto", "Negação simples aplicada perfeitamente.", "### *Très bien !*\n\nNegação correta: **Paul ne regarde pas la télévision tous les soirs.**")
        if "ne regarde pas" in resp_sem:
            return ("Parcialmente Correto", "Estrutura 'ne regarde pas' presente, mas revise o restante da frase.", "### *Presque !*\n\nA negação do verbo está certa (`ne regarde pas`), confira apenas a grafia completa da sentença.")
        return ("Incorreto", "Forma negativa incorreta para 'Paul regarde la télévision...'", "### *Attention !*\n\nPara negar no presente em francês, envolva o verbo conjugado com **`ne ... pas`**: *Paul **ne** regarde **pas**...*")

    return None


_TRADS_CONHECIDAS = [
    ("ontem a noite, nos fomos ao cinema juntos", ["hier soir nous sommes alles au cinema ensemble", "hier nous sommes alles au cinema"], "Hier soir, nous sommes allés au cinéma ensemble.", "Lembre-se de usar o Passé Composé com auxiliar **être** (*nous sommes allés*) para o verbo *aller*."),
    ("ela subiu pelas escadas e entrou na sala", ["elle est montee par les escaliers et est entree dans la salle", "elle est montee", "elle est entree"], "Elle est montée par les escaliers et est entrée dans la salle.", "Tanto *monter* quanto *entrer* pertencem à **Maison d'Être**, portanto usam **être** com concordância feminina (*montée*, *entrée*)."),
    ("quando eu morava em paris, tomava cafe", ["quand j'habitais a paris je prenais du cafe", "quand j'habitais a paris je buvais du cafe"], "Quand j'habitais à Paris, je prenais du café à la boulangerie tous les matins.", "Para hábitos contínuos no passado, empregue o **Imparfait** (*j'habitais*, *je prenais/buvais*) e o partitivo *du café*."),
    ("eu gosto de queijo, mas hoje nao comprei queijo", ["j'aime le fromage mais aujourd'hui je n'ai pas achete de fromage"], "J'aime le fromage, mais aujourd'hui je n'ai pas acheté de fromage.", "Em *gosto*, use artigo definido (*le fromage*); na negação absoluta após *pas*, troque para **de** (*pas de fromage*)."),
    ("tenho dois", ["j'en ai deux"], "J'en ai deux.", "Para substituir quantidades ou elementos indefinidos com números, utilize o pronome **en**: *J'en ai deux*."),
    ("eu o vejo todos os dias e lhe falo em frances", ["je le vois tous les jours et je lui parle en francais"], "Je le vois tous les jours et je lui parle en français.", "Use **le** (COD) para *o vejo* e **lui** (COI) para *lhe falo*."),
    ("e preciso que voce venha conosco amanha", ["il faut que tu viennes avec nous demain", "il faut que vous veniez avec nous demain"], "Il faut que vous veniez avec nous demain.", "Após *il faut que*, conjugue *venir* no **Subjonctif** (*que tu viennes* / *que vous veniez*)."),
    ("nos aprendemos frances todos os dias para viajar", ["nous apprenons le francais tous les jours pour voyager en france"], "Nous apprenons le français tous les jours pour voyager en France.", "Verifique a conjugação de *apprendre* com *nous* (*nous apprenons*) e o uso de **en France**."),
]


def _avaliar_lacunas_ou_producao(tema: str, exercicio: str, resposta: str, modalidade: str):
    resp_norm = _norm_fr(resposta, manter_acentos=True)
    resp_sem = _norm_fr(resposta, manter_acentos=False)

    if not resp_sem or "___" in resposta:
        return (
            "Incorreto",
            "O aluno não substituiu a lacuna.",
            "### *Attention !*\n\nVocê deixou a lacuna (`___`) em branco. Substitua o espaço pela forma verbal ou gramatical correta em francês."
        )

    frase_base = _extrair_trecho_entre_aspas(exercicio)
    frase_sem_lacuna = re.sub(r"_{2,}\s*(?:\([^)]*\))?", "", frase_base)
    frase_sem_lacuna_norm = _norm_fr(frase_sem_lacuna, False)
    if frase_sem_lacuna_norm == resp_sem or (
        modalidade == "lacunas"
        and len(resp_sem.split()) >= 3
        and set(resp_sem.split()) <= set(frase_sem_lacuna_norm.split())
    ):
        return (
            "Incorreto",
            "O texto enviado não preencheu o termo faltante na frase.",
            "### *Attention !*\n\nA resposta foi enviada sem preencher o termo faltante na frase proposta.\n\n**Dica:** Observe o verbo ou pista entre parênteses e escreva a palavra/conjugação no local da lacuna."
        )

    # Verifica sinais claros de português ou resposta muito curta/aleatória
    palavras_pt = {"eu", "voce", "você", "ontem", "nao", "não", "estou", "gosto", "fui", "nos", "nós", "moro", "trabalho", "amigos"}
    tokens_resp = set(resp_sem.split())
    if tokens_resp & palavras_pt:
        return (
            "Incorreto",
            "A resposta contém palavras em português em vez de francês.",
            "### *Attention !*\n\nSua resposta parece conter palavras em português. Tente escrever toda a resposta em **francês**.\n\n**Dica:** Utilize o Mémento Gramatical FLE no menu para consultar pronomes e verbos."
        )

    desvios_ort = _verificar_desvios_ortograficos_fr(resposta)

    # 1. Verifica exercícios com múltiplas lacunas ou transformações específicas do banco
    res_multi = _avaliar_multiplas_lacunas_ou_transformacao(exercicio, resposta, tema)
    if res_multi:
        return res_multi

    # 2. Verifica exercícios de lacuna simples
    if modalidade == "lacunas":
        gabaritos = _obter_gabaritos_lacuna(exercicio, tema)
        if gabaritos:
            acertou_exato = False
            acertou_sem_acento = False
            frase_template = re.sub(r"_{2,}\s*(?:\([^)]*\))?", " xxgaptokenxx ", frase_base)
            frase_template = _norm_fr(frase_template, manter_acentos=True)

            for gab in gabaritos:
                gab_c = _norm_fr(gab, manter_acentos=True)
                gab_s = _norm_fr(gab, manter_acentos=False)
                if resp_norm == gab_c or ("xxgaptokenxx" in frase_template and resp_norm == re.sub(r"\s+", " ", frase_template.replace("xxgaptokenxx", gab_c)).strip()):
                    acertou_exato = True
                    break
                if gab_c in resp_norm.split() or (len(gab_c.split()) > 1 and gab_c in resp_norm):
                    if len(resp_norm.split()) <= len(gab_c.split()) + 12:
                        acertou_exato = True
                        break
                if resp_sem == gab_s or gab_s in resp_sem:
                    acertou_sem_acento = True

            if acertou_exato:
                if desvios_ort:
                    return _formatar_feedback_ortografia(desvios_ort, contexto=f" em '{tema}'")
                return (
                    "Correto",
                    f"Lacuna preenchida corretamente conforme a regra de '{tema}'.",
                    f"### *Très bien !*\n\nExcelente precisão gramatical! A forma **{gabaritos[0]}** completa perfeitamente a frase dentro do tema *{tema}*."
                )
            if acertou_sem_acento:
                return (
                    "Parcialmente Correto",
                    f"Estrutura correta, porém faltou acentuação gráfica ({gabaritos[0]}).",
                    f"### *Presque !*\n\nA sua conjugação/estrutura está correta, mas faltou observar a acentuação em francês (`{gabaritos[0]}`).\n\n**Dica:** Use os botões de acento (`é`, `è`, `ê`) logo abaixo do campo de resposta."
                )
            if desvios_ort:
                return _formatar_feedback_ortografia(desvios_ort, contexto=f" na lacuna de '{tema}'")

            # Checa concordância faltante comum
            dica_especifica = f"Revise a regra de *{tema}* para o sujeito da frase."
            if "arriver" in exercicio.lower() or "partir" in exercicio.lower() or "aller" in exercicio.lower():
                dica_especifica = "Lembre-se da **Maison d'Être**: esse verbo utiliza o auxiliar **être** (não *avoir*) e o particípio deve concordar em gênero e número com o sujeito!"
            return (
                "Incorreto",
                f"Forma esperada não identificada para '{tema}' (esperado: {', '.join(gabaritos[:2])}).",
                f"### *Pas tout à fait !*\n\nA forma informada (*{resposta}*) não corresponde à estrutura esperada para esta lacuna.\n\n**Dica:** {dica_especifica}"
            )

    # 3. Produção escrita / tradução / frase aberta em francês
    ex_norm = _norm_fr(exercicio, manter_acentos=False)
    for chave_trad, alvos_trad, _modelo_trad, dica_trad in _TRADS_CONHECIDAS:
        if chave_trad in ex_norm:
            melhor_sim = max(difflib.SequenceMatcher(None, resp_sem, alvo_t).ratio() for alvo_t in alvos_trad)
            if melhor_sim >= 0.88:
                if desvios_ort:
                    return _formatar_feedback_ortografia(desvios_ort, contexto=f" em '{tema}'")
                return (
                    "Correto",
                    "Produção escrita em francês correta e fiel à proposta.",
                    f"### *Très bien !*\n\nExcelente tradução/produção em francês (*« {resposta} »*). Estrutura gramatical e vocabulário precisos!"
                )
            if melhor_sim >= 0.65:
                return (
                    "Parcialmente Correto",
                    f"Produção próxima da estrutura esperada (similaridade {round(melhor_sim * 100)}%).",
                    f"### *Presque !*\n\nBoa tentativa! Sua frase já comunica a ideia principal, mas precisa de pequenos ajustes gramaticais.\n\n**Dica:** {dica_trad}"
                )
            return (
                "Incorreto",
                f"Tradução/produção insuficiente ou com erro estrutural importante.",
                f"### *Attention !*\n\nSua frase ainda não atende corretamente à estrutura pedida na proposta.\n\n**Dica:** {dica_trad}"
            )

    # Caso seja uma frase aberta inédita em francês (ou lacuna sem gabarito fixo)
    palavras_qtd = len(resp_sem.split())
    tem_marcador_fr = bool(re.search(r"\b(je|j'|tu|il|elle|nous|vous|ils|elles|on|le|la|les|un|une|des|du|de|est|suis|sont|ai|avons|pas|que|qui|dans|pour|avec|en|au|aux)\b", resp_sem))
    if palavras_qtd < 2 or not tem_marcador_fr:
        return (
            "Incorreto",
            "Resposta curta demais ou sem estrutura reconhecida em francês.",
            "### *Attention !*\n\nEscreva uma frase completa em **francês** (com sujeito, verbo conjugado e complemento) respeitando o tema proposto.\n\n**Dica:** Evite responder apenas com uma palavra solta em produção escrita."
        )

    erro_geral = _analisar_erro_frase_vf(resposta)
    if erro_geral:
        return (
            "Incorreto",
            f"Desvio gramatical detectado na produção: {erro_geral}",
            f"### *Pas tout à fait !*\n\nEncontramos um erro gramatical na sua frase.\n\n**Dica:** {erro_geral}"
        )

    if desvios_ort:
        return _formatar_feedback_ortografia(desvios_ort, contexto=f" na resposta em '{tema}'")

    return (
        "Correto",
        "Produção escrita validada sem desvios gramaticais ou ortográficos detectados.",
        f"### *Très bien !*\n\nBoa construção em francês (*« {resposta} »*) alinhada ao tema *{tema}*."
    )


def gerar_feedback_frances(tema, exercicio, resposta_aluno, tentativa=1, dica_anterior="", nivel_cefr="A2", tipo_atividade=""):
    nivel = (nivel_cefr or "A2").strip().upper()
    modalidade = _detectar_modalidade_avaliacao(exercicio, tipo_atividade)
    contexto_tentativa = f"\nNúmero da tentativa do aluno: {tentativa}." if tentativa and int(tentativa) > 1 else ""
    if dica_anterior:
        contexto_tentativa += f"\nDica anterior fornecida ao aluno: {dica_anterior}"

    prompt_sistema = f"""Você é um examinador nativo e rigoroso de Francês Língua Estrangeira (FLE) do quadro europeu CEFR, corrigindo respostas de estudantes brasileiros palavra por palavra e letra por letra.
Nível CEFR do aluno: {nivel}.
Modalidade da atividade: {modalidade}.
Tema: {tema}
Exercício proposto: {exercicio}
Resposta do aluno: {resposta_aluno}{contexto_tentativa}

CRITÉRIOS RIGOROSOS DE CORREÇÃO (SIGA À RISCA):
1. Revise TODA a ortografia francesa caractere por caractere antes de definir o status:
   - Consoantes duplas obrigatórias (ex.: `m'appelle`, `s'appelle`, `t'appelles` exigem **pp** e **ll** — se o aluno escrever `m'apele`, `m'appele`, `m'apelle` ou `s'apelle`, NÃO pode ser `Correto`!).
   - Acentos gráficos (`é`, `è`, `ê`, `à`, `ç`), apóstrofos (`j'`, `m'`, `s'`, `n'`, `l'`) e concordâncias de gênero/número.
2. Classificação obrigatória:
   - **Correto**: SOMENTE quando conjugação, auxiliar, concordância, vocabulário E ortografia estiverem 100% exatos (zero erros de grafia ou acento).
   - **Parcialmente Correto**: quando o sentido, verbo ou estrutura estiverem reconhecíveis e na direção certa, MAS houver qualquer desvio ortográfico (como `m'apele` ou `s'apelle` faltando `p`/`l`), falta de acento, falta de concordância simples ou V/F marcado `Faux` sem a frase corrigida. Aponte EXATAMENTE cada palavra grafada errado e mostre a grafia correta!
   - **Incorreto**: quando o verbo, tempo verbal, auxiliar (ex.: *avoir* em vez de *être*), pronome ou alternativa estiverem errados, se a lacuna não foi preenchida, ou se houver mistura com português.

Responda EXATAMENTE neste formato:
- **Status:** (Correto / Parcialmente Correto / Incorreto)
- **Análise do Professor:** (Diagnóstico técnico detalhando exatamente cada acerto, erro gramatical ou desvio ortográfico)
- **Feedback para o Aluno:** (Feedback formativo claro em português, destacando em negrito as palavras com erro ortográfico ou gramatical e a forma correta em francês)"""

    if genai_model:
        try:
            response = genai_model.generate_content(prompt_sistema)
            return parse_retorno_gemini_frances(response.text)
        except Exception as e:
            print(f"[!] Fallback de avaliação ativado ({e})")
            return feedback_demonstracao_frances(tema, exercicio, resposta_aluno, nivel_cefr=nivel, tipo_atividade=modalidade)

    return feedback_demonstracao_frances(tema, exercicio, resposta_aluno, nivel_cefr=nivel, tipo_atividade=modalidade)


def feedback_demonstracao_frances(tema, exercicio, resposta_aluno, nivel_cefr="A2", tipo_atividade=""):
    """Avaliador pedagógico determinístico para todas as modalidades FLE (sempre que a IA externa não estiver ativa)."""
    resp = (resposta_aluno or "").strip()
    if not resp or len(re.sub(r"[\W_]+", "", resp)) == 0:
        return (
            "Incorreto",
            "Resposta em branco ou inválida.",
            "### *Attention !*\n\nDigite, selecione ou fale uma resposta em francês antes de solicitar a correção."
        )

    modalidade = _detectar_modalidade_avaliacao(exercicio, tipo_atividade)

    if modalidade == "multipla_escolha":
        res_mc = _avaliar_multipla_escolha(exercicio, resp)
        if res_mc:
            return res_mc

    if modalidade == "vf":
        return _avaliar_vf(exercicio, resp)

    if modalidade in ("ditado", "expressao_oral"):
        return _avaliar_ditado_ou_oral(exercicio, resp, modalidade)

    return _avaliar_lacunas_ou_producao(tema, exercicio, resp, modalidade)


def obter_resposta_esperada_exercicio(tema: str, exercicio: str, tipo_atividade: str = "") -> str:
    """Retorna a forma/frase modelo esperada em francês para comparação formativa no feedback."""
    modalidade = _detectar_modalidade_avaliacao(exercicio, tipo_atividade)
    ex_norm = _norm_fr(exercicio, manter_acentos=False)

    if modalidade == "multipla_escolha":
        opcoes, letra_correta, _ = _extrair_opcoes_e_correta_mc(exercicio)
        if letra_correta and letra_correta in opcoes:
            return f"{letra_correta}) {opcoes[letra_correta]}"
        return ""

    if modalidade == "vf":
        frase = _extrair_trecho_entre_aspas(exercicio)
        if not frase:
            return ""
        erro = _analisar_erro_frase_vf(frase)
        if not erro:
            return f"Vrai — {frase}"
        corrigida = _corrigir_frase_vf_modelo(frase)
        return f"Faux — {corrigida}" if corrigida else "Faux (corrigir o desvio apontado)"

    if modalidade in ("ditado", "expressao_oral"):
        return _extrair_trecho_entre_aspas(exercicio)

    # Lacunas, transformações e produção escrita
    for reg in _REGRAS_MULTIPLAS_LACUNAS:
        if reg["chave"] in ex_norm:
            return reg["frase_modelo"]

    if "paul mange de la viande" in ex_norm:
        return "Paul ne mange pas de viande."
    if "paul regarde la television tous les soirs" in ex_norm:
        return "Paul ne regarde pas la télévision tous les soirs."

    if modalidade == "lacunas":
        gabs = _obter_gabaritos_lacuna(exercicio, tema)
        if gabs:
            frase_base = _extrair_trecho_entre_aspas(exercicio)
            if "___" in frase_base:
                preenchida = re.sub(r"_{2,}\s*(?:\([^)]*\))?", gabs[0], frase_base, count=1)
                preenchida = re.sub(r"(['’])\s+", r"\1", preenchida)
                return preenchida.strip()
            return gabs[0]

    for chave_trad, _alvos, modelo_trad, _dica in _TRADS_CONHECIDAS:
        if chave_trad in ex_norm:
            return modelo_trad

    return ""


def obter_pista_exercicio(tema: str, exercicio: str, tipo_atividade: str = "") -> str:
    """Fornece uma pista pedagógica objetiva sobre a regra envolvida sem entregar a resposta pronta."""
    modalidade = _detectar_modalidade_avaliacao(exercicio, tipo_atividade)
    t_low = (tema or "").lower()
    ex_low = (exercicio or "").lower()

    if modalidade == "ditado":
        return "Escute primeiro no ritmo normal, depois use o modo **Calmo (0.65x)** ou **Voltar trecho** para conferir terminações mudas e acentos (`é`, `è`, `ê`, `ç`)."
    if modalidade == "expressao_oral":
        return "Ouça a frase no botão **🐢 0.65x** antes de gravar, observe as ligações entre palavras (*liaisons*) e pronuncie com clareza."
    if any(k in t_low or k in ex_low for k in ("maison d'être", "arriver", "partir", "aller", "venir", "monter", "entrer", "rester")):
        return "Atenção à **Maison d'Être**: verbos de movimento/estado no Passé Composé usam o auxiliar **être** e fazem acordo de gênero e número no particípio."
    if "passé" in t_low or "passe" in t_low:
        return "No **Passé Composé**, identifique primeiro se o verbo pede **avoir** ou **être** e verifique o particípio passado."
    if "imparfait" in t_low:
        return "O **Imparfait** usa o radical da 1ª pessoa do plural do presente + `-ais, -ais, -ait, -ions, -iez, -aient` (exceção: *être* → `ét-`)."
    if "négat" in t_low or "negat" in t_low or "negação" in ex_low:
        return "Envolva o verbo conjugado com `ne ... pas` (ou `n'` antes de vogal). Na negação absoluta, os partitivos `du / de la / des` viram **`de / d'`**."
    if "article" in t_low or "partitif" in t_low:
        return "Partitivos: **`du`** (masc. sing.), **`de la`** (fem. sing.), **`de l'`** (vogal/h mudo) e **`des`** (plural); após negação absoluta com *pas*, use **`de / d'`**."
    if "subjonctif" in t_low or "il faut" in ex_low:
        return "Após expressões de necessidade/obrigação (*il faut que*, *il est nécessaire que*), o verbo vai para o **Subjonctif Présent**."
    if "pronom" in t_low or "y " in ex_low or "en " in ex_low or "cod" in t_low or "coi" in t_low:
        return "Regência pronominal: **`y`** substitui lugar (*à/en + local*); **`en`** substitui *de + coisa/quantidade*; **`lui / leur`** substituem *à + pessoa*."
    if "salutation" in t_low or "appeler" in ex_low:
        return "No presente do indicativo, *s'appeler* dobra **`pp`** e **`ll`** com *je / tu / il / elle* (`je m'appelle`, `elle s'appelle`), mas com *nous / vous* mantém apenas 1 **`l`**."
    return f"Analise o sujeito, o tempo verbal e a ortografia francesa ligados ao tema **{tema or 'Francês FLE'}** antes de enviar."


def _analisar_e_transcrever_wav(filepath_audio: str):
    """Converte áudio .webm para WAV 16kHz mono, mede energia acústica e transcreve em fr-FR."""
    metricas = {"duracao": 0.0, "rms": 0.0, "silencio": False, "stt_erro": None}
    if not filepath_audio or not os.path.exists(filepath_audio):
        metricas["silencio"] = True
        return "", metricas

    ffmpeg_bin = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
    if not os.path.exists(ffmpeg_bin):
        return "", metricas

    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name

        subprocess.run(
            [ffmpeg_bin, "-y", "-i", filepath_audio, "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )

        with wave.open(wav_path, "rb") as wf:
            nframes = wf.getnframes()
            framerate = wf.getframerate() or 16000
            duracao = nframes / float(framerate)
            raw = wf.readframes(nframes)
            total_amostras = len(raw) // 2
            rms = 0.0
            if total_amostras > 0:
                samples = struct.unpack("<" + ("h" * total_amostras), raw[: total_amostras * 2])
                rms = math.sqrt(sum(s * s for s in samples) / float(total_amostras))

        metricas["duracao"] = round(duracao, 2)
        metricas["rms"] = round(rms, 1)

        if duracao < 0.6 or rms < 120.0:
            metricas["silencio"] = True
            return "", metricas

        try:
            import speech_recognition as sr

            recon = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recon.record(source)
            texto_stt = (recon.recognize_google(audio_data, language="fr-FR") or "").strip()
            return texto_stt, metricas
        except Exception as err_stt:
            metricas["stt_erro"] = type(err_stt).__name__
            return "", metricas
    except Exception as err_conv:
        metricas["stt_erro"] = type(err_conv).__name__
        return "", metricas
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass


def _garantir_cabecalho_oral(feedback_ia: str, status_resposta: str, transcricao: str) -> str:
    rotulo_ouvido = f"*« {transcricao} »*" if transcricao else "*(Nenhuma palavra em francês pôde ser reconhecida com clareza na gravação)*"
    if "O que o Assistente Fran entendeu" not in (feedback_ia or ""):
        feedback_ia = f"**🎙️ O que o Assistente Fran entendeu do seu áudio:** {rotulo_ouvido}\n\n" + (feedback_ia or "")
    if status_resposta != "Correto" and "Tentar Novamente" not in feedback_ia:
        feedback_ia += '\n\n🔄 **Próximo passo:** Ouça o enunciado no botão **Ouvir** acima e clique em **"Tentar Novamente com a Dica"** para gravar novamente.'
    return feedback_ia


def analisar_e_transcrever_audio_oral(
    tema: str,
    exercicio: str,
    transcricao_cliente: str = "",
    filepath_audio: str = None,
    tentativa: int = 1,
    dica_anterior: str = "",
    nivel_cefr: str = "A2",
):
    """Transcreve áudio de Expressão Oral (Gemini ou ffmpeg + STT fr-FR) e avalia com fluxo de nova tentativa."""
    nivel = (nivel_cefr or "A2").strip().upper()
    transcricao_cli = (transcricao_cliente or "").strip()
    if transcricao_cli.startswith("[") and transcricao_cli.endswith("]"):
        transcricao_cli = ""

    transcricao_srv, metricas = _analisar_e_transcrever_wav(filepath_audio) if filepath_audio else ("", {"silencio": False})

    if filepath_audio and metricas.get("silencio") and not transcricao_cli:
        dur = metricas.get("duracao", 0)
        msg_silencio = _garantir_cabecalho_oral(
            f"### *Attention !*\n\n"
            f"O áudio enviado está muito curto ou silencioso ({dur:.1f}s), não sendo possível identificar sua pronúncia em francês.\n\n"
            f"**Dica:** Fale próximo ao microfone pronunciando a frase completa pausadamente e depois clique em **Parar Gravação**.",
            "Incorreto",
            "",
        )
        return (
            "Incorreto",
            f"Áudio oral sem fala detectada (duração={dur:.2f}s, rms={metricas.get('rms', 0)}).",
            msg_silencio,
            "[Áudio sem fala detectada]",
        )

    if genai_model and filepath_audio and os.path.exists(filepath_audio):
        try:
            with open(filepath_audio, "rb") as f_aud:
                audio_bytes = f_aud.read()
            audio_blob = {"mime_type": "audio/webm", "data": audio_bytes}
            prompt_oral = (
                f"Você é um examinador nativo e rigoroso de Francês (FLE) nível {nivel}.\n"
                f"Tema: {tema}\n"
                f"Exercício oral proposto: {exercicio}\n"
                f"Tentativa do aluno: {tentativa}. {('Dica anterior: ' + dica_anterior) if dica_anterior else ''}\n\n"
                f"INSTRUÇÕES OBRIGATÓRIAS:\n"
                f"1. Transcreva LITERALMENTE o que o aluno pronunciou em francês no áudio anexo.\n"
                f"2. Se houver silêncio, ruído sem fala ou frase diferente/errada, NÃO aprove como Correto — indique claramente o que foi entendido e peça para o aluno tentar novamente.\n"
                f"Responda EXATAMENTE:\n"
                f"- **Transcrição:** (texto exato ouvido em francês ou [Nenhuma fala reconhecida])\n"
                f"- **Status:** (Correto / Parcialmente Correto / Incorreto)\n"
                f"- **Análise do Professor:** (Avaliação objetiva da transcrição, pronúncia e fidelidade à frase)\n"
                f"- **Feedback para o Aluno:** (Retorno detalhado em português; quando não for Correto, peça para clicar em Tentar Novamente com a Dica)"
            )
            resp_gemini = genai_model.generate_content([prompt_oral, audio_blob])
            txt_gem = resp_gemini.text or ""
            m_tr = re.search(r"\*{0,2}Transcrição:?\*{0,2}\s*(.+)", txt_gem, re.IGNORECASE)
            transcricao_gem = m_tr.group(1).strip() if m_tr else (transcricao_srv or transcricao_cli)
            if transcricao_gem.startswith("[") and transcricao_gem.endswith("]"):
                transcricao_exibida = ""
            else:
                transcricao_exibida = transcricao_gem
            status_r, analise_r, feedback_r = parse_retorno_gemini_frances(txt_gem)
            feedback_r = _garantir_cabecalho_oral(feedback_r, status_r, transcricao_exibida)
            return status_r, analise_r, feedback_r, (transcricao_exibida or "[Áudio sem fala reconhecida]")
        except Exception as e:
            print(f"[!] Fallback de transcrição/avaliação oral ativado ({e})")

    transcricao_final = transcricao_srv or transcricao_cli
    if not transcricao_final:
        msg_nao_entendido = _garantir_cabecalho_oral(
            "### *Attention !*\n\n"
            "Não foi possível transcrever palavras claras em francês a partir da sua gravação.\n\n"
            "**Dica:** Ouça o áudio modelo clicando no botão **Ouvir** do exercício acima, pronuncie a frase com voz firme próximo ao microfone e grave novamente.",
            "Incorreto",
            "",
        )
        return (
            "Incorreto",
            f"Gravação oral salva ({filepath_audio or 'memória'}), mas sem transcrição em francês reconhecida ({metricas.get('stt_erro') or 'UnknownValue'}).",
            msg_nao_entendido,
            "[Áudio sem fala reconhecida]",
        )

    status_r, analise_base, feedback_base = _avaliar_ditado_ou_oral(exercicio, transcricao_final, "expressao_oral")
    analise_completa = f"Transcrição do áudio (fr-FR): « {transcricao_final} ». {analise_base}"
    feedback_completo = _garantir_cabecalho_oral(feedback_base, status_r, transcricao_final)
    return status_r, analise_completa, feedback_completo, transcricao_final


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
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec les éléments de négation : 'Elle ___ boit ___ de café après dix-huit heures.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Répondez négativement à la question : 'As-tu déjà visité le musée d'Orsay ?'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle est la forme négative correcte de 'J'ai des amis à Lyon' ?\n(a) Je n'ai pas des amis à Lyon.\n(b) Je n'ai pas d'amis à Lyon.\n(c) Je ne ai pas d'amis à Lyon.\n(d) Je n'ai plus des amis à Lyon.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la négation au passé composé : 'Hier, il ___ a ___ plu du tout.'\n(a) ne ... pas\n(b) n' ... pas\n(c) n'a ... pas\n(d) ne ... rien", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quel mot exprime l'opposé négatif de 'toujours' ?\n(a) personne\n(b) rien\n(c) jamais\n(d) aucun", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Corrigez l'erreur de négation dans la phrase : 'Marie ne mange pas du fromage le soir.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
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
            {"tipo_questao": "exercicio", "enunciado": "Rédigez une phrase pour présenter votre frère ou votre sœur en français (prénom, âge, profession).", "texto_referencia": "", "pontuacao_maxima": 2.5},
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
        tem_frase = (
            ('___' in enunciado) or ('"' in enunciado) or ("'" in enunciado)
            or ('(' in enunciado and ')' in enunciado) or ('\n' in enunciado)
            or ('vrai' in enunciado.lower()) or ('?' in enunciado) or ('(a)' in enunciado.lower())
        )
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

    while len(questoes_limpas) < quantidade:
        questoes_limpas.append(dict(questoes_padrao[len(questoes_limpas) % len(questoes_padrao)]))

    if len(questoes_limpas) > quantidade:
        questoes_limpas = questoes_limpas[:quantidade]

    if questoes_limpas:
        n_q = len(questoes_limpas)
        base_pts = round(10.0 / n_q, 1)
        soma_pts = 0.0
        for q in questoes_limpas[:-1]:
            q["pontuacao_maxima"] = base_pts
            soma_pts += base_pts
        questoes_limpas[-1]["pontuacao_maxima"] = round(10.0 - soma_pts, 1)

    return questoes_limpas
