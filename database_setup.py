import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")

def init_db():
    print(f"[*] Conectando ao banco de dados SQLite em: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Habilita integridade referencial de chaves estrangeiras
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Remove tabelas existentes para garantir schema limpo
    cursor.execute("DROP TABLE IF EXISTS prova_questoes;")
    cursor.execute("DROP TABLE IF EXISTS mensagens_inbox;")
    cursor.execute("DROP TABLE IF EXISTS forum_mensagens;")
    cursor.execute("DROP TABLE IF EXISTS forum_topicos;")
    cursor.execute("DROP TABLE IF EXISTS avaliacoes;")
    cursor.execute("DROP TABLE IF EXISTS reforcos_individuais;")
    cursor.execute("DROP TABLE IF EXISTS submissoes;")
    cursor.execute("DROP TABLE IF EXISTS exercicios;")
    cursor.execute("DROP TABLE IF EXISTS temas;")
    cursor.execute("DROP TABLE IF EXISTS alunos;")
    cursor.execute("DROP TABLE IF EXISTS professor_turmas;")
    cursor.execute("DROP TABLE IF EXISTS professor_disciplinas;")
    cursor.execute("DROP TABLE IF EXISTS professores;")
    cursor.execute("DROP TABLE IF EXISTS turmas;")

    # 1. Tabela: turmas
    cursor.execute("""
        CREATE TABLE turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        );
    """)

    # 2. Tabela: professores
    cursor.execute("""
        CREATE TABLE professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            nome_social TEXT,
            cpf TEXT UNIQUE,
            rg TEXT,
            data_nascimento TEXT,
            email TEXT,
            telefone TEXT,
            endereco TEXT,
            cidade_uf TEXT,
            foto_perfil TEXT,
            codigo_professor TEXT UNIQUE,
            formacao_academica TEXT,
            especializacao TEXT,
            areas_atuacao TEXT,
            mini_curriculo TEXT,
            experiencia_profissional TEXT,
            certificados_links TEXT,
            email_acesso TEXT UNIQUE NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil_acesso TEXT DEFAULT 'Professor',
            tipo_professor TEXT DEFAULT 'Bilíngue',
            link_sala_virtual TEXT,
            perm_lancar_notas BOOLEAN DEFAULT 1,
            perm_registrar_freq BOOLEAN DEFAULT 1,
            perm_visualizar_alunos BOOLEAN DEFAULT 1,
            status_acesso TEXT DEFAULT 'Ativo'
        );
    """)

    # Tabelas Relacionais N:N para Professor
    cursor.execute("""
        CREATE TABLE professor_disciplinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            disciplina TEXT NOT NULL,
            FOREIGN KEY (professor_id) REFERENCES professores(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE professor_turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL,
            FOREIGN KEY (professor_id) REFERENCES professores(id) ON DELETE CASCADE,
            FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE
        );
    """)

    # 3. Tabela: alunos
    cursor.execute("""
        CREATE TABLE alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            matricula TEXT UNIQUE NOT NULL,
            data_nascimento TEXT,
            cpf TEXT UNIQUE,
            telefone TEXT,
            is_whatsapp BOOLEAN DEFAULT 0,
            email TEXT,
            endereco TEXT,
            data_matricula TEXT DEFAULT CURRENT_TIMESTAMP,
            resp_legal_nome TEXT,
            resp_legal_parentesco TEXT,
            resp_legal_cpf TEXT,
            resp_legal_telefone TEXT,
            contato_emergencia TEXT,
            resp_financeiro TEXT,
            aceite_contrato BOOLEAN DEFAULT 0,
            aceite_politica_privacidade BOOLEAN DEFAULT 0,
            consentimento_ia_voz BOOLEAN DEFAULT 0,
            senha_hash TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            nivel_cefr TEXT DEFAULT 'A2',
            turno TEXT DEFAULT 'Matutino',
            status_matricula TEXT DEFAULT 'Ativo',
            FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE
        );
    """)

    # Tabela: avaliacoes
    cursor.execute("""
        CREATE TABLE avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            data_limite TEXT NOT NULL,
            FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE
        );
    """)

    # Tabela: prova_questoes
    cursor.execute("""
        CREATE TABLE prova_questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            avaliacao_id INTEGER NOT NULL,
            tipo_questao TEXT NOT NULL,
            enunciado TEXT NOT NULL,
            texto_referencia TEXT,
            pontuacao_maxima REAL DEFAULT 10.0,
            FOREIGN KEY (avaliacao_id) REFERENCES avaliacoes(id) ON DELETE CASCADE
        );
    """)

    # Tabela: forum_topicos
    cursor.execute("""
        CREATE TABLE forum_topicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            criador_id INTEGER NOT NULL,
            turma_id INTEGER,
            categoria TEXT DEFAULT 'geral',
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (criador_id) REFERENCES professores(id) ON DELETE CASCADE,
            FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE SET NULL
        );
    """)

    # Tabela: forum_mensagens
    cursor.execute("""
        CREATE TABLE forum_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topico_id INTEGER NOT NULL,
            autor_id INTEGER,
            autor_tipo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            data_envio TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topico_id) REFERENCES forum_topicos(id) ON DELETE CASCADE
        );
    """)

    # Tabela: mensagens_inbox
    cursor.execute("""
        CREATE TABLE mensagens_inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remetente_id INTEGER NOT NULL,
            destinatario_id INTEGER NOT NULL,
            assunto TEXT NOT NULL,
            corpo TEXT NOT NULL,
            lida_status INTEGER DEFAULT 0,
            data_envio TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tabela: temas
    cursor.execute("""
        CREATE TABLE temas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_tema TEXT NOT NULL UNIQUE
        );
    """)

    # Tabela: exercicios
    cursor.execute("""
        CREATE TABLE exercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema_id INTEGER NOT NULL,
            nivel_exigido TEXT NOT NULL,
            enunciado TEXT NOT NULL,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE
        );
    """)

    # Tabela: submissoes
    cursor.execute("""
        CREATE TABLE submissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            exercicio_id INTEGER,
            prova_questao_id INTEGER,
            resposta_aluno TEXT,
            arquivo_audio_path TEXT,
            feedback_ia TEXT NOT NULL,
            analise_professor TEXT,
            nota_professor REAL,
            status_resposta TEXT NOT NULL,
            tentativa INTEGER DEFAULT 1,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
            FOREIGN KEY (exercicio_id) REFERENCES exercicios(id) ON DELETE CASCADE,
            FOREIGN KEY (prova_questao_id) REFERENCES prova_questoes(id) ON DELETE CASCADE
        );
    """)

    # Tabela: reforcos_individuais
    cursor.execute("""
        CREATE TABLE reforcos_individuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            tema_id INTEGER NOT NULL,
            mensagem_tutor TEXT NOT NULL,
            exercicios_json TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
            FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE
        );
    """)

    # POPULAÇÃO COM DADOS DE TESTE (SEEDS)
    
    # Inserção das turmas
    turmas_dados = [
        ("1º Ano A",),
        ("1º Ano B",)
    ]
    cursor.executemany("INSERT INTO turmas (nome) VALUES (?);", turmas_dados)

    # Inserção dos alunos
    senha_padrao_hash = generate_password_hash("123456")
    alunos_dados = [
        ("Lucas Silva", "202601", senha_padrao_hash, 1, "B1", "Matutino"),
        ("Camila Rodrigues", "202602", senha_padrao_hash, 1, "A1", "Matutino"),
        ("Gabriel Santos", "202603", senha_padrao_hash, 2, "A2", "Vespertino")
    ]
    cursor.executemany("INSERT INTO alunos (nome_completo, matricula, senha_hash, turma_id, nivel_cefr, turno) VALUES (?, ?, ?, ?, ?, ?);", alunos_dados)

    # Inserção do professor
    professores_dados = [
        ("Professor Admin", "admin@escola.com", "admin", generate_password_hash("admin"))
    ]
    cursor.executemany("INSERT INTO professores (nome_completo, email_acesso, usuario, senha_hash) VALUES (?, ?, ?, ?);", professores_dados)

    # Lincando o professor admin às turmas (M:N)
    # Admin tem id=1, turmas tem id=1 e 2
    professor_turmas_dados = [(1, 1), (1, 2)]
    cursor.executemany("INSERT INTO professor_turmas (professor_id, turma_id) VALUES (?, ?);", professor_turmas_dados)

    # Inserção de temas
    temas_lista = [
        "Les Salutations et Présentations",
        "Les Verbes du 1er groupe au Présent",
        "Les Articles Définis et Indéfinis",
        "Le Passé Composé: Être vs Avoir",
        "L'Imparfait",
        "Les Prépositions de Lieu",
        "Le Vocabulaire de la Famille",
        "La Négation Simple (ne ... pas)"
    ]
    cursor.executemany("INSERT INTO temas (nome_tema) VALUES (?);", [(t,) for t in temas_lista])

    # Inserção de exercícios
    exercicios_dados = [
        (4, "A2", "Complete com o auxiliar correto e particípio de aller: 'Hier, nous ___ (aller) au cinéma ensemble.'"),
        (3, "A2", "Preencha com o artigo partitivo adequado: 'Au petit-déjeuner, je bois ___ café et je mange ___ confiture.'"),
        (4, "A2", "Conjugue com concordância no Passé Composé: 'Elles ___ (arriver) à Paris hier soir.'"),
        (8, "A1", "Transforme a frase afirmativa em negação: 'Paul mange de la viande.'")
    ]
    cursor.executemany("INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?);", exercicios_dados)

    # Inserção de submissões de teste pedagógicas
    submissoes_dados = [
        (1, 1, "Hier, nous sommes allés au cinéma ensemble.", "**Très bien, Lucas !** ...", "Perfeita utilização...", "Correto", 1, "2026-09-17 14:10:00"),
        (1, 2, "Au petit-déjeuner, je bois le café et je mange la confiture.", "**Attention, Lucas !** ...", "Erro no uso de artigos...", "Incorreto", 1, "2026-09-17 15:35:00"),
        (2, 3, "Elles sont arrivées à Paris hier soir.", "**Excellent, Camila !** ...", "Acordo correto...", "Correto", 1, "2026-09-17 14:40:00"),
        (3, 4, "Paul ne mange pas de la viande.", "**Presque, Gabriel !** ...", "Desvio de regra...", "Parcialmente Correto", 1, "2026-09-17 16:30:00")
    ]
    cursor.executemany("""
        INSERT INTO submissoes (
            aluno_id, exercicio_id, resposta_aluno, feedback_ia, 
            analise_professor, status_resposta, tentativa, data_hora
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, submissoes_dados)

    conn.commit()

    # Seed de Avaliações, Fórum e Mensagens
    avaliacoes_dados = [
        ("Prova Multimodal A2", "Prova", 1, "2026-11-30 23:59:00"),
        ("Teste de Conjugação", "Teste", 2, "2026-10-15 23:59:00")
    ]
    cursor.executemany("INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES (?, ?, ?, ?);", avaliacoes_dados)

    prova_questoes_dados = [
        (1, "leitura_oral", "Leia o texto a seguir em voz alta:", "Bonjour, je m'appelle Lucas et j'habite à Paris.", 10.0),
        (1, "ditado", "Ouça o áudio e escreva a frase em francês:", "Il fait très beau aujourd'hui.", 10.0),
        (1, "conjugacao", "Conjugue o verbo Être na 1ª pessoa do plural:", "Nous sommes", 10.0)
    ]
    cursor.executemany("INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima) VALUES (?, ?, ?, ?, ?);", prova_questoes_dados)

    forum_dados = [
        ("Dúvidas sobre o Passé Composé", "Espaço reservado para dúvidas sobre os auxiliares Être e Avoir.", 1, 1),
        ("Faux Amis - Vamos compartilhar exemplos!", "Quais falsos cognatos vocês acharam mais interessantes?", 1, 2)
    ]
    cursor.executemany("INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id) VALUES (?, ?, ?, ?);", forum_dados)

    mensagens_dados = [
        (1, 1, "Bem-vindo ao LMS", "Olá Lucas, não se esqueça de revisar os verbos do 1º grupo!"),
        (1, 2, "Aviso de Prova", "Camila, a prova será na próxima semana.")
    ]
    cursor.executemany("INSERT INTO mensagens_inbox (remetente_id, destinatario_id, assunto, corpo) VALUES (?, ?, ?, ?);", mensagens_dados)

    try:
        from seed_planos_aula import init_planos_aula
        init_planos_aula(conn)
    except Exception as e:
        print(f"[!] Aviso: Nao foi possivel inicializar planos_aula: {e}")

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_submissoes_aluno_id ON submissoes(aluno_id);",
        "CREATE INDEX IF NOT EXISTS idx_submissoes_prova_questao_id ON submissoes(prova_questao_id);",
        "CREATE INDEX IF NOT EXISTS idx_submissoes_exercicio_id ON submissoes(exercicio_id);",
        "CREATE INDEX IF NOT EXISTS idx_alunos_turma_id ON alunos(turma_id);",
        "CREATE INDEX IF NOT EXISTS idx_alunos_matricula ON alunos(matricula);",
        "CREATE INDEX IF NOT EXISTS idx_planos_aula_nivel ON planos_aula(nivel);",
        "CREATE INDEX IF NOT EXISTS idx_prova_questoes_avaliacao_id ON prova_questoes(avaliacao_id);",
        "CREATE INDEX IF NOT EXISTS idx_mensagens_destinatario ON mensagens_inbox(destinatario_id);",
        "CREATE INDEX IF NOT EXISTS idx_forum_mensagens_topico ON forum_mensagens(topico_id);"
    ]
    for idx in indexes:
        cursor.execute(idx)

    conn.commit()
    conn.close()
    print("[OK] Banco de dados relacional 'educacao_ia.db' inicializado com sucesso com nova arquitetura e índices!")

    try:
        from seed_populacao_graficos import popular_banco
        popular_banco()
    except Exception as e:
        print(f"[!] Aviso ao executar população de gráficos: {e}")

if __name__ == "__main__":
    init_db()
