import sqlite3

conn = sqlite3.connect('educacao_ia.db')
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tabelas:", tables)

for t in ['alunos', 'professores']:
    cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"Colunas {t}:", cols)
    rows = c.execute(f"SELECT * FROM {t} LIMIT 3").fetchall()
    print(f"Linhas {t}:", rows)
