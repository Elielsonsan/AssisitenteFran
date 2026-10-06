import sqlite3

conn = sqlite3.connect('educacao_ia.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM prova_questoes WHERE enunciado LIKE '%Quelle terminaison%'")
rows = [dict(r) for r in c.fetchall()]
for r in rows:
    print(r)

if not rows:
    print("Nenhuma questao com 'Quelle terminaison'. Listando as ultimas 10 questoes:")
    c.execute("SELECT id, avaliacao_id, tipo_questao, enunciado, texto_referencia FROM prova_questoes ORDER BY id DESC LIMIT 10")
    for r in c.fetchall():
        print(dict(r))
