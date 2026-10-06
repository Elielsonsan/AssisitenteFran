import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3

BASE_URL = "http://127.0.0.1:5000"

print("==================================================")
print("TESTE DO MÓDULO DE PLANOS DE AULA & SEQUÊNCIAS P.P.P.")
print("==================================================")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Testar acesso não autenticado
print("\n--- 1. Testando acesso não autenticado ---")
req = urllib.request.Request(f"{BASE_URL}/professor/planos-aula", method="GET")
resp = urllib.request.urlopen(req)
assert "/login" in resp.geturl()
print(f"[OK] Acesso não autenticado redirecionado para: {resp.geturl()}")

# 2. Login do Professor
print("\n--- 2. Autenticando Professor Admin ---")
login_data = urllib.parse.urlencode({
    "tipo_acesso": "professor",
    "usuario": "admin",
    "senha": "admin"
}).encode("utf-8")
req_login = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
resp_login = opener.open(req_login)
assert "/dashboard" in resp_login.geturl()
print(f"[OK] Login com sucesso: {resp_login.geturl()}")

# 3. Acessar página /professor/planos-aula
print("\n--- 3. Acessando /professor/planos-aula autenticado ---")
req_page = urllib.request.Request(f"{BASE_URL}/professor/planos-aula", method="GET")
resp_page = opener.open(req_page)
html = resp_page.read().decode("utf-8")
assert "Planos de Aula &amp; Sequências Didáticas" in html or "Planos de Aula & Sequências Didáticas" in html
assert "Se présenter" in html
assert "Au restaurant" in html
assert "Raconter au passé" in html
assert "L&#39;art de convaincre" in html or "L'art de convaincre" in html
print("[OK] Página /professor/planos-aula renderizada com sucesso contendo o catálogo de aulas!")

# 4. Testar API de listagem e filtros
print("\n--- 4. Testando /api/planos-aula com filtros ---")
# Todos
req_all = urllib.request.Request(f"{BASE_URL}/api/planos-aula", method="GET")
data_all = json.loads(opener.open(req_all).read().decode("utf-8"))
print(f"[OK] Total geral retornado: {data_all['total']}")
assert data_all["total"] >= 24

# Filtro Iniciante (A1-A2)
req_ini = urllib.request.Request(f"{BASE_URL}/api/planos-aula?nivel=INICIANTE", method="GET")
data_ini = json.loads(opener.open(req_ini).read().decode("utf-8"))
print(f"[OK] Total no ciclo Iniciante: {data_ini['total']}")
assert data_ini["total"] >= 8

# Filtro Intermediário (B1-B2)
req_int = urllib.request.Request(f"{BASE_URL}/api/planos-aula?nivel=INTERMEDIARIO", method="GET")
data_int = json.loads(opener.open(req_int).read().decode("utf-8"))
print(f"[OK] Total no ciclo Intermediário: {data_int['total']}")
assert data_int["total"] >= 8

# Filtro Avançado (C1-C2)
req_av = urllib.request.Request(f"{BASE_URL}/api/planos-aula?nivel=AVANCADO", method="GET")
data_av = json.loads(opener.open(req_av).read().decode("utf-8"))
print(f"[OK] Total no ciclo Avançado: {data_av['total']}")
assert data_av["total"] >= 8

# Busca textual por "restaurant"
req_busca = urllib.request.Request(f"{BASE_URL}/api/planos-aula?busca=restaurant", method="GET")
data_busca = json.loads(opener.open(req_busca).read().decode("utf-8"))
print(f"[OK] Busca por 'restaurant': {data_busca['total']} encontrado(s) -> {data_busca['planos'][0]['tema']}")
assert data_busca["total"] >= 1
assert "restaurant" in data_busca["planos"][0]["tema"].lower()

# 5. Testar obtenção detalhada de um plano (Template e P.P.P.)
print("\n--- 5. Testando /api/planos-aula/<id> detalhado ---")
plano_id_teste = data_busca["planos"][0]["id"]
req_det = urllib.request.Request(f"{BASE_URL}/api/planos-aula/{plano_id_teste}", method="GET")
data_det = json.loads(opener.open(req_det).read().decode("utf-8"))
plano = data_det["plano"]
print(f"Tema: {plano['tema']}")
print(f"Nível: {plano['nivel']}, Duração: {plano['duracao']}")
print(f"Habilidades: {plano['habilidades']}")
print(f"Objetivos: {plano['objetivos'][:60]}...")
print(f"Aquecimento: {plano['etapa_aquecimento'][:40]}...")
print(f"Apresentação: {plano['etapa_apresentacao'][:40]}...")
print(f"Prática: {plano['etapa_pratica'][:40]}...")
print(f"Produção: {plano['etapa_producao'][:40]}...")
print(f"Fechamento: {plano['etapa_fechamento'][:40]}...")
print(f"Formativa: {plano['avaliacao_formativa']}")
assert plano["etapa_aquecimento"] is not None
assert plano["etapa_producao"] is not None

# 6. Testar Cadastro Manual de Plano
print("\n--- 6. Testando POST /api/planos-aula/cadastrar ---")
payload_novo = {
    "tema": "Exprimer la condition avec Si",
    "nivel": "B1",
    "duracao": "50 min",
    "objetivos": "Formular hipóteses no presente e futuro usando a estrutura 'Si + présent, futur'.",
    "habilidades": "PO, PE, GR",
    "conteudos": "A conjunção 'Si', alternância entre Présent e Futur Simple/Impératif.",
    "metodologia": "Abordagem indutiva com jogo de cartas condicionais.",
    "recursos": "Baralho de situações hipotéticas, tiras de frases.",
    "etapa_aquecimento": "5-10 min: Jogo rápido: 'Si vous gagnez au loto, que faites-vous?'.",
    "etapa_apresentacao": "15 min: Regra da condição tipo 1 (Si + présent = futur).",
    "etapa_pratica": "15 min: Exercícios de conexão de frases em duplas.",
    "etapa_producao": "15 min: Criação de um conselho em cadeia: 'Si tu viens à Paris, tu dois...'.",
    "etapa_fechamento": "5 min: Alerta contra o erro comum 'Si j'aurai' e recapitulação.",
    "avaliacao_formativa": "Observação dos encadeamentos lógicos durante a produção em cadeia.",
    "avaliacao_somativa": "Questões de transformação condicional na prova B1.",
    "dever_casa": "Escrever 6 previsões ou conselhos para um amigo usando 'Si'.",
    "reforco": "Treino no assistente Fran de hipótese e tempos verbais."
}
req_cad = urllib.request.Request(
    f"{BASE_URL}/api/planos-aula/cadastrar",
    data=json.dumps(payload_novo).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_cad = json.loads(opener.open(req_cad).read().decode("utf-8"))
assert resp_cad["status"] == "sucesso"
plano_cadastrado_id = resp_cad["plano_id"]
print(f"[OK] Novo plano manual cadastrado com ID: {plano_cadastrado_id}")

# 7. Testar Geração de Plano com IA
print("\n--- 7. Testando POST /api/planos-aula/gerar-ia ---")
payload_ia = {
    "tema": "Commander à la boulangerie",
    "nivel": "A1",
    "duracao": "50 min",
    "foco": "Situações da vida real e compras diárias"
}
req_ia = urllib.request.Request(
    f"{BASE_URL}/api/planos-aula/gerar-ia",
    data=json.dumps(payload_ia).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_ia = json.loads(opener.open(req_ia).read().decode("utf-8"))
assert resp_ia["status"] == "sucesso"
plano_ia = resp_ia["plano"]
print(f"[OK] Plano gerado com IA com sucesso! ID: {plano_ia.get('id')}")
print(f"  Tema: {plano_ia.get('tema')}")
print(f"  Objetivos: {plano_ia.get('objetivos')[:70]}...")
print(f"  Produção: {plano_ia.get('etapa_producao')[:60]}...")
plano_ia_id = plano_ia.get("id")

# 8. Testar Geração de Avaliação Alinhada ao Plano
print("\n--- 8. Testando POST /api/planos-aula/<id>/gerar-prova ---")
req_prova = urllib.request.Request(
    f"{BASE_URL}/api/planos-aula/{plano_cadastrado_id}/gerar-prova",
    data=json.dumps({"turma_id": 1, "data_limite": "2026-12-31 23:59:00"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_prova = json.loads(opener.open(req_prova).read().decode("utf-8"))
assert resp_prova["status"] == "sucesso"
avaliacao_gerada_id = resp_prova["avaliacao_id"]
print(f"[OK] Prova criada com sucesso a partir do plano! ID Avaliação: {avaliacao_gerada_id}")

# Verificar se as 4 questões foram criadas no banco
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
cur.execute("SELECT tipo_questao, enunciado FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_gerada_id,))
questoes = cur.fetchall()
print(f"[OK] Total de questões geradas para a prova: {len(questoes)}")
for q in questoes:
    print(f"  - [{q[0]}] {q[1][:50]}...")
assert len(questoes) == 4

# 9. Limpeza dos registros de teste
print("\n--- 9. Limpeza dos dados de teste ---")
cur.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_gerada_id,))
cur.execute("DELETE FROM avaliacoes WHERE id = ?", (avaliacao_gerada_id,))
cur.execute("DELETE FROM planos_aula WHERE id IN (?, ?)", (plano_cadastrado_id, plano_ia_id))
conn.commit()
conn.close()
print("[OK] Limpeza concluída com sucesso.")

print("\n==================================================")
print(">>> TODOS OS TESTES DO MÓDULO PASSARAM COM 100% DE SUCESSO! <<<")
print("==================================================")
