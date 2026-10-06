import sqlite3

conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()

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
    cur.execute(idx)

conn.commit()

print("Indexes created/verified successfully:")
for row in cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'").fetchall():
    print(f"  {row[0]} ON {row[1]}")

conn.close()
