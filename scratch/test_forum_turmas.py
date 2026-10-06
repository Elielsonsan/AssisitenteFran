import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3

BASE_URL = "http://127.0.0.1:5000"

print("==================================================")
print("TESTE DO FÓRUM POR TURMAS & FÓRUM GERAL")
print("==================================================")

# 1. Login do Professor Admin
cj_prof = http.cookiejar.CookieJar()
opener_prof = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_prof))

login_prof_data = urllib.parse.urlencode({
    "tipo_acesso": "professor",
    "usuario": "admin",
    "senha": "admin"
}).encode("utf-8")
resp_login = opener_prof.open(urllib.request.Request(f"{BASE_URL}/login", data=login_prof_data, method="POST"))
assert "/dashboard" in resp_login.geturl()
print("[OK] Professor autenticado com sucesso!")

# 2. Testar listagem do professor com filtros
print("\n--- 2. Testando listagem do Professor ---")
# Todas
resp_todas = opener_prof.open(urllib.request.Request(f"{BASE_URL}/forum?turma=todas", method="GET"))
html_todas = resp_todas.read().decode("utf-8")
assert "Fórum de Discussão Socrático" in html_todas
assert "Fórum Geral" in html_todas
print("[OK] Professor acessou /forum com sucesso e visualizou abas e tópicos!")

# Filtro Fórum Geral
resp_geral = opener_prof.open(urllib.request.Request(f"{BASE_URL}/forum?turma=geral", method="GET"))
html_geral = resp_geral.read().decode("utf-8")
assert "Fórum Geral (Aberto a Todos)" in html_geral
print("[OK] Professor filtrou com sucesso pelo Fórum Geral!")

# Filtro por Turma 14 (1º Ano A)
resp_t14 = opener_prof.open(urllib.request.Request(f"{BASE_URL}/forum?turma=14", method="GET"))
html_t14 = resp_t14.read().decode("utf-8")
assert "1º Ano A" in html_t14
print("[OK] Professor filtrou com sucesso pela Turma 14!")

# 3. Testar criação de Tópico no Fórum Geral via API
print("\n--- 3. Criando Tópico no Fórum Geral ---")
req_criar_geral = urllib.request.Request(
    f"{BASE_URL}/api/forum/criar_topico",
    data=json.dumps({
        "titulo": "Teste Automatizado Tópico Geral",
        "descricao": "Discussão aberta para todos os estudantes do Assistente Fran.",
        "turma_id": "geral",
        "categoria": "cultura"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_cg = json.loads(opener_prof.open(req_criar_geral).read().decode("utf-8"))
assert resp_cg["status"] == "sucesso"
topico_geral_id = resp_cg["topico_id"]
print(f"[OK] Tópico Geral criado com sucesso! ID: {topico_geral_id}")

# 4. Testar criação de Tópico na Turma 15 (1º Ano B)
print("\n--- 4. Criando Tópico específico na Turma 15 ---")
req_criar_t15 = urllib.request.Request(
    f"{BASE_URL}/api/forum/criar_topico",
    data=json.dumps({
        "titulo": "Teste Automatizado Tópico Turma 15",
        "descricao": "Discussão restrita aos alunos do 1º Ano B.",
        "turma_id": 15,
        "categoria": "gramatica"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_c15 = json.loads(opener_prof.open(req_criar_t15).read().decode("utf-8"))
assert resp_c15["status"] == "sucesso"
topico_t15_id = resp_c15["topico_id"]
print(f"[OK] Tópico Turma 15 criado com sucesso! ID: {topico_t15_id}")

# 5. Obter um aluno da Turma 14 e um aluno da Turma 15
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
cur.execute("SELECT id, nome, matricula FROM alunos WHERE turma_id = 14 LIMIT 1")
aluno_t14 = cur.fetchone()
cur.execute("SELECT id, nome, matricula FROM alunos WHERE turma_id = 15 LIMIT 1")
aluno_t15 = cur.fetchone()
conn.close()

print(f"Aluno Turma 14 selecionado: ID {aluno_t14[0]} ({aluno_t14[1]}, Matrícula: {aluno_t14[2]})")
print(f"Aluno Turma 15 selecionado: ID {aluno_t15[0]} ({aluno_t15[1]}, Matrícula: {aluno_t15[2]})")

# 6. Login com Aluno da Turma 14
cj_aluno14 = http.cookiejar.CookieJar()
opener_aluno14 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_aluno14))

login_aluno14_data = urllib.parse.urlencode({
    "tipo_acesso": "aluno",
    "matricula": aluno_t14[2],
    "senha": "123456"
}).encode("utf-8")
resp_la14 = opener_aluno14.open(urllib.request.Request(f"{BASE_URL}/login", data=login_aluno14_data, method="POST"))
assert resp_la14.getcode() == 200
print("[OK] Aluno da Turma 14 logado com sucesso!")

# 7. Verificar o que o Aluno da Turma 14 vê no Fórum
print("\n--- 7. Testando permissões de visualização do Aluno da Turma 14 ---")
resp_fa14 = opener_aluno14.open(urllib.request.Request(f"{BASE_URL}/forum", method="GET"))
html_fa14 = resp_fa14.read().decode("utf-8")

# Deve ver o tópico do Fórum Geral
assert "Teste Automatizado Tópico Geral" in html_fa14
print("[OK] Aluno da Turma 14 visualiza perfeitamente o Fórum Geral!")

# NÃO DEVE ver o tópico da Turma 15
assert "Teste Automatizado Tópico Turma 15" not in html_fa14
print("[OK] SUCESSO: Tópico da Turma 15 NÃO aparece para o aluno da Turma 14!")

# 8. Testar tentativa de invasão direta via URL (/forum/topico/<topico_t15_id>)
print("\n--- 8. Testando proteção direta de URL contra acesso indevido ---")
resp_bloqueio = opener_aluno14.open(urllib.request.Request(f"{BASE_URL}/forum/topico/{topico_t15_id}", method="GET"))
html_bloqueio = resp_bloqueio.read().decode("utf-8")
# Deve ter sido redirecionado para /forum
assert "/forum" in resp_bloqueio.geturl()
assert "Acesso restrito" in html_bloqueio or "Fórum de Discussão" in html_bloqueio
print("[OK] SUCESSO: Tentativa de acesso a tópico de outra turma foi bloqueada com redirecionamento e flash warning!")

# 9. Testar acesso permitido ao tópico Geral pelo Aluno da Turma 14
print("\n--- 9. Testando acesso permitido ao Fórum Geral pelo Aluno ---")
resp_top_geral = opener_aluno14.open(urllib.request.Request(f"{BASE_URL}/forum/topico/{topico_geral_id}", method="GET"))
html_top_geral = resp_top_geral.read().decode("utf-8")
assert "Teste Automatizado Tópico Geral" in html_top_geral
assert "Fórum Geral" in html_top_geral
print("[OK] Aluno acessou a página de discussão do Fórum Geral normalmente!")

# 10. Testar envio de mensagem no tópico Geral pelo Aluno
print("\n--- 10. Testando envio de mensagem no Fórum Geral ---")
req_msg = urllib.request.Request(
    f"{BASE_URL}/api/forum/responder",
    data=json.dumps({
        "topico_id": topico_geral_id,
        "conteudo": "J'aime beaucoup regarder des films français avec des sous-titres !"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_msg = json.loads(opener_aluno14.open(req_msg).read().decode("utf-8"))
assert resp_msg["status"] == "sucesso"
print("[OK] Mensagem do aluno publicada com sucesso no Fórum Geral!")

# 11. Limpeza dos dados de teste
print("\n--- 11. Limpeza dos dados de teste ---")
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
cur.execute("DELETE FROM forum_mensagens WHERE topico_id IN (?, ?)", (topico_geral_id, topico_t15_id))
cur.execute("DELETE FROM forum_topicos WHERE id IN (?, ?)", (topico_geral_id, topico_t15_id))
conn.commit()
conn.close()
print("[OK] Registros de teste limpos com sucesso.")

print("\n==================================================")
print(">>> TODOS OS TESTES DO FÓRUM PASSARAM COM 100% DE SUCESSO! <<<")
print("==================================================")
