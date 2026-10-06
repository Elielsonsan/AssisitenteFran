import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")

print(f"Iniciando migração do Fórum em: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Verificar colunas atuais de forum_topicos
cursor.execute("PRAGMA table_info(forum_topicos)")
cols = {row[1]: row for row in cursor.fetchall()}
print("Colunas atuais:", list(cols.keys()))

# 2. Habilitar foreign keys
cursor.execute("PRAGMA foreign_keys = OFF;")

# 3. Criar nova tabela com turma_id NULLABLE e categoria
cursor.execute("""
    CREATE TABLE IF NOT EXISTS forum_topicos_novo (
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

# 4. Copiar dados existentes
if 'categoria' in cols:
    cursor.execute("""
        INSERT INTO forum_topicos_novo (id, titulo, descricao, criador_id, turma_id, categoria, data_criacao)
        SELECT id, titulo, descricao, criador_id, turma_id, categoria, data_criacao FROM forum_topicos;
    """)
else:
    cursor.execute("""
        INSERT INTO forum_topicos_novo (id, titulo, descricao, criador_id, turma_id, categoria, data_criacao)
        SELECT id, titulo, descricao, criador_id, turma_id, 'geral', data_criacao FROM forum_topicos;
    """)

# 5. Substituir tabela antiga
cursor.execute("DROP TABLE forum_topicos;")
cursor.execute("ALTER TABLE forum_topicos_novo RENAME TO forum_topicos;")

# 6. Atualizar categorias dos tópicos pré-existentes
cursor.execute("UPDATE forum_topicos SET categoria = 'gramatica' WHERE titulo LIKE '%Passé Composé%';")
cursor.execute("UPDATE forum_topicos SET categoria = 'cultura' WHERE titulo LIKE '%Séries e Músicas%';")

# 7. Inserir tópicos para o Fórum Geral e para as demais turmas se não existirem
cursor.execute("SELECT id FROM professores LIMIT 1")
prof_row = cursor.fetchone()
prof_id = prof_row[0] if prof_row else 1

topicos_iniciais = [
    # Fórum Geral (turma_id = None)
    (
        "Cinema & Séries em Francês: Recomendações e Debates",
        "Compartilhe filmes, curtas, séries e animações francófonas que você está assistindo. Que tal praticar uma resenha curta em francês?",
        prof_id,
        None,
        "cultura",
        "2026-09-15 10:00:00"
    ),
    (
        "Pronúncia & Fonética: Dicas para o som do 'R' e vogais nasais",
        "Espaço para dúvidas e exercícios de pronúncia. Conte como você superou as dificuldades fonéticas no início do aprendizado.",
        prof_id,
        None,
        "dicas",
        "2026-09-16 14:30:00"
    ),
    (
        "Café Literário FLE: Livros, Poemas e Quadrinhos (BD)",
        "Dicas de leituras acessíveis para quem está nos níveis A1 a B2: histórias em quadrinhos (Astérix, Tintin), fábulas de La Fontaine e contos curtos.",
        prof_id,
        None,
        "cultura",
        "2026-09-17 09:15:00"
    ),
    (
        "Dúvidas Gerais & Estratégias de Estudo Diário",
        "Como você organiza seus estudos? Dicas de aplicativos, rotinas de escuta matinal, flashcards e anotações ativas em francês.",
        prof_id,
        None,
        "duvidas",
        "2026-09-18 11:00:00"
    ),
    # Tópico Turma 14: 1º Ano A (Iniciante A1)
    (
        "Prática de Apresentação Pessoal: Se présenter en français",
        "Olá alunos do 1º Ano A! Escreva um pequeno parágrafo dizendo seu nome, nacionalidade, profissão/estudos e o que gosta de fazer.",
        prof_id,
        14,
        "vocabulario",
        "2026-09-19 08:30:00"
    ),
    # Tópico Turma 17: 3º Ano A (Avançado B2)
    (
        "Débat B2: L'intelligence artificielle dans l'apprentissage des langues",
        "Pour les étudiants de 3º Ano A: selon vous, comment l'IA transforme-t-elle l'enseignement des langues vivantes? Quels en sont les avantages et les limites?",
        prof_id,
        17,
        "debate",
        "2026-09-19 16:45:00"
    )
]

for tit, desc, c_id, t_id, cat, dt in topicos_iniciais:
    cursor.execute("SELECT id FROM forum_topicos WHERE titulo = ?", (tit,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id, categoria, data_criacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tit, desc, c_id, t_id, cat, dt))
        novo_id = cursor.lastrowid
        print(f"[OK] Criado tópico: {tit} (ID: {novo_id}, Turma: {t_id})")

        # Inserir primeira mensagem da Assistente Fran de incentivo
        if t_id is None and "Cinema" in tit:
            cursor.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo, data_envio)
                VALUES (?, NULL, 'IA', 'Bonjour à tous ! J''adore le cinéma français ! Vous avez déjà regardé "Le Fabuleux Destin d''Amélie Poulain" ou la série "Lupin" ? Qu''en avez-vous pensé ?', ?)
            """, (novo_id, dt))
        elif t_id is None and "Pronúncia" in tit:
            cursor.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo, data_envio)
                VALUES (?, NULL, 'IA', 'Une astuce essentielle pour le "R" français : détendez la langue et faites vibrer légèrement l''arrière du palais, sans forcer. Avez-vous essayé ?', ?)
            """, (novo_id, dt))
        elif t_id == 14:
            cursor.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo, data_envio)
                VALUES (?, NULL, 'IA', 'Bienvenue aux débutants ! N''hésitez pas à vous lancer, les erreurs font partie de l''apprentissage. "Bonjour, je m''appelle Fran..." !', ?)
            """, (novo_id, dt))
        elif t_id == 17:
            cursor.execute("""
                INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo, data_envio)
                VALUES (?, NULL, 'IA', 'C''est un sujet passionnant pour le niveau B2 ! Pensez à utiliser des connecteurs logiques comme "d''une part... d''autre part", "toutefois", "en outre".', ?)
            """, (novo_id, dt))

conn.commit()
cursor.execute("PRAGMA foreign_keys = ON;")
conn.close()

print("[OK] Migração concluída com sucesso!")
