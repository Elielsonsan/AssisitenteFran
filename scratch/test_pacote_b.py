import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3

BASE_URL = "http://127.0.0.1:5000"

print("==================================================")
print("TESTE DE VALIDAÇÃO DO PACOTE B (EXTENSÕES PEDAGÓGICAS)")
print("==================================================")

# Autenticar Professor Admin
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = urllib.parse.urlencode({
    "tipo_acesso": "professor",
    "usuario": "admin",
    "senha": "admin"
}).encode("utf-8")
req_login = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
resp_login = opener.open(req_login)
assert resp_login.status == 200
print("\n[OK] Professor Admin conectado com sucesso!")

# 1. Testar Filtro de Competências na API de Planos de Aula (/api/planos-aula?habilidade=...)
print("\n--- 1. Testando Filtros por Competência Comunicativa FLE ---")

for hab in ["PO", "CO", "CE", "PE", "IO", "GR"]:
    req = urllib.request.Request(f"{BASE_URL}/api/planos-aula?habilidade={hab}", method="GET")
    resp = opener.open(req)
    assert resp.status == 200
    dados = json.loads(resp.read().decode("utf-8"))
    assert dados.get("status") == "sucesso"
    planos = dados.get("planos", [])
    print(f"  [OK] Competência '{hab}': {len(planos)} planos encontrados.")
    assert len(planos) > 0
    # Verifica que todos os planos contêm a habilidade pesquisada
    for p in planos:
        assert hab in p["habilidades"].upper()

# Teste combinado: Ciclo INICIANTE + Competência PO
req_comb = urllib.request.Request(f"{BASE_URL}/api/planos-aula?nivel=INICIANTE&habilidade=PO", method="GET")
resp_comb = opener.open(req_comb)
dados_comb = json.loads(resp_comb.read().decode("utf-8"))
assert dados_comb.get("status") == "sucesso"
print(f"  [OK] Filtro Combinado (Iniciante + PO): {len(dados_comb.get('planos', []))} planos encontrados.")

# 2. Testar Endpoint de Dados do Boletim Escolar (/api/relatorio/boletim_dados)
print("\n--- 2. Testando API do Boletim Escolar Consolidado ---")

req_boletim = urllib.request.Request(f"{BASE_URL}/api/relatorio/boletim_dados", method="GET")
resp_boletim = opener.open(req_boletim)
assert resp_boletim.status == 200
b_data = json.loads(resp_boletim.read().decode("utf-8"))
assert b_data.get("status") == "sucesso"
print(f"[OK] Boletim Geral carregado com sucesso:")
print(f"     Turma: {b_data.get('turma_nome')}")
print(f"     Data de Emissão: {b_data.get('data_emissao')}")
print(f"     Total de Alunos: {b_data.get('total_alunos')}")
print(f"     Média de Aproveitamento: {b_data.get('media_aproveitamento_turma')}%")
print(f"     Média de Provas: {b_data.get('media_provas_turma')}")
print(f"     Taxa de Aprovação: {b_data.get('taxa_aprovacao_turma')}%")

assert b_data.get("total_alunos") >= 3
alunos = b_data.get("alunos", [])
lucas = next((a for a in alunos if a["matricula"] == "202601"), None)
assert lucas is not None
print(f"[OK] Aluno Lucas Silva identificado no boletim:")
print(f"     Turma: {lucas['turma_nome']}, Nível CEFR: {lucas['nivel_cefr']}")
print(f"     Atividades: {lucas['total_atividades']}, Aproveitamento: {lucas['taxa_aproveitamento']}%")
print(f"     Conceito FLE: {lucas['conceito']}")

# Testar Boletim com filtro de Turma 1
req_b_turma = urllib.request.Request(f"{BASE_URL}/api/relatorio/boletim_dados?turma_id=1", method="GET")
resp_b_turma = opener.open(req_b_turma)
b_turma_data = json.loads(resp_b_turma.read().decode("utf-8"))
assert b_turma_data.get("status") == "sucesso"
assert b_turma_data.get("turma_nome") == "1º Ano A"
print(f"[OK] Filtro de Boletim por Turma ('1º Ano A'): {b_turma_data.get('total_alunos')} alunos")

# 3. Testar Renderização do Cronômetro na Prova do Aluno
print("\n--- 3. Testando Cronômetro Regressivo em aluno_prova.html ---")
# Criar prova temporária
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
cur.execute("INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES ('Prova Timer Test', 'Teste', 1, '2026-12-31 23:59:00')")
av_id = cur.lastrowid
cur.execute("INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, pontuacao_maxima) VALUES (?, 'traducao', 'Traduza Bonjour', 10.0)", (av_id,))
conn.commit()

# Autenticar Aluno Lucas
cj_aluno = http.cookiejar.CookieJar()
opener_aluno = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_aluno))
login_aluno = urllib.parse.urlencode({"tipo_acesso": "aluno", "matricula": "202601", "senha": "123456"}).encode("utf-8")
opener_aluno.open(urllib.request.Request(f"{BASE_URL}/login", data=login_aluno, method="POST"))

# Acessa /aluno/prova/<av_id>
req_prova = urllib.request.Request(f"{BASE_URL}/aluno/prova/{av_id}", method="GET")
html_prova = opener_aluno.open(req_prova).read().decode("utf-8")

# Limpa o teste
cur.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (av_id,))
cur.execute("DELETE FROM avaliacoes WHERE id = ?", (av_id,))
conn.commit()
conn.close()

assert 'id="timerCard"' in html_prova
assert 'id="timerDisplay"' in html_prova
assert 'id="timerAlertBanner"' in html_prova
assert 'formatarTempo' in html_prova
assert 'tempoEsgotado' in html_prova
print("[OK] Elementos do Cronômetro Regressivo renderizados com sucesso no exame!")

# 4. Testar Renderização do Botão e Modal de Boletim no Dashboard do Professor
print("\n--- 4. Testando Modal e Botão de Boletim Escolar no Dashboard ---")
req_dash = urllib.request.Request(f"{BASE_URL}/dashboard", method="GET")
html_dash = opener.open(req_dash).read().decode("utf-8")

assert 'id="btnBoletimTurma"' in html_dash
assert 'id="modalBoletim"' in html_dash
assert 'id="areaBoletimImpressao"' in html_dash
assert 'abrirBoletimEscolar' in html_dash
assert 'imprimirBoletim' in html_dash
print("[OK] Botão, Modal e Script de Impressão do Boletim Escolar renderizados no Dashboard!")

# 5. Testar Renderização dos Filtros de Habilidade em professor_planos_aula.html
print("\n--- 5. Testando Filtros de Habilidades no Catálogo Docente ---")
req_planos = urllib.request.Request(f"{BASE_URL}/professor/planos-aula", method="GET")
html_planos = opener.open(req_planos).read().decode("utf-8")

assert 'id="tabHabilidades"' in html_planos
assert 'data-skill="CO"' in html_planos
assert 'data-skill="PO"' in html_planos
assert 'data-skills=' in html_planos
assert 'setFiltroSkill' in html_planos
print("[OK] Barra de Competências FLE e atributos data-skills renderizados no Catálogo!")

print("\n==================================================")
print(">>> TODOS OS TESTES DO PACOTE B PASSARAM COM 100% DE SUCESSO! <<<")
print("==================================================")
