import sqlite3

conn = sqlite3.connect("educacao_ia.db")
cursor = conn.cursor()

tables = [
    'turmas', 'alunos', 'professores', 'temas', 'exercicios', 
    'submissoes', 'avaliacoes', 'prova_questoes', 'reforcos_individuais', 
    'forum_topicos', 'forum_mensagens', 'mensagens_inbox'
]

print("=" * 60)
print("TOTAL DE REGISTROS POR TABELA:")
print("=" * 60)
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t.ljust(22)}: {cursor.fetchone()[0]}")

print("\n" + "=" * 60)
print("DISTRIBUIÇÃO DE STATUS DAS RESPOSTAS (GRÁFICO DE ROSCA):")
print("=" * 60)
cursor.execute("SELECT status_resposta, COUNT(*) FROM submissoes GROUP BY status_resposta ORDER BY COUNT(*) DESC;")
for row in cursor.fetchall():
    print(f"  {str(row[0]).ljust(22)}: {row[1]} respostas")

print("\n" + "=" * 60)
print("DESEMPENHO POR TÓPICO GRAMATICAL (GRÁFICO DE BARRAS):")
print("=" * 60)
cursor.execute("""
    SELECT COALESCE(t.nome_tema, 'Prova Multimodal') as tema, 
           SUM(CASE WHEN s.status_resposta = 'Correto' THEN 1 ELSE 0 END) as acertos,
           SUM(CASE WHEN s.status_resposta = 'Parcialmente Correto' THEN 1 ELSE 0 END) as parciais,
           SUM(CASE WHEN s.status_resposta = 'Incorreto' THEN 1 ELSE 0 END) as erros,
           COUNT(*) as total
    FROM submissoes s
    LEFT JOIN exercicios e ON s.exercicio_id = e.id
    LEFT JOIN temas t ON e.tema_id = t.id
    GROUP BY tema
    ORDER BY total DESC;
""")
for row in cursor.fetchall():
    print(f"  {row[0][:40].ljust(42)} | Acertos: {str(row[1]).rjust(2)} | Parciais: {str(row[2]).rjust(2)} | Erros: {str(row[3]).rjust(2)} | Total: {str(row[4]).rjust(2)}")

print("\n" + "=" * 60)
print("DISTRIBUIÇÃO DE ALUNOS POR TURMA E NÍVEL:")
print("=" * 60)
cursor.execute("""
    SELECT t.nome, a.nivel_cefr, COUNT(a.id)
    FROM turmas t
    JOIN alunos a ON a.turma_id = t.id
    GROUP BY t.nome, a.nivel_cefr
    ORDER BY t.nome, a.nivel_cefr;
""")
for row in cursor.fetchall():
    print(f"  {row[0].ljust(30)} | Nível {row[1]}: {row[2]} alunos")

conn.close()
