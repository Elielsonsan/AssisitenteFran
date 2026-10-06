import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3

BASE_URL = "http://127.0.0.1:5000"

print("==================================================")
print("TESTE DE VALIDAÇÃO DO PACOTE A (MELHORIAS & CONFIABILIDADE)")
print("==================================================")

# 1. Testar Índices do Banco de Dados
print("\n--- 1. Verificando Índices SQLite de Performance ---")
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
indexes = cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'").fetchall()
print(f"Total de índices de alta performance encontrados: {len(indexes)}")
index_names = [idx[0] for idx in indexes]
for idx in indexes:
    print(f"  [OK] {idx[0]} na tabela '{idx[1]}'")

assert "idx_submissoes_aluno_id" in index_names
assert "idx_submissoes_prova_questao_id" in index_names
assert "idx_alunos_turma_id" in index_names
assert "idx_planos_aula_nivel" in index_names
assert "idx_prova_questoes_avaliacao_id" in index_names
conn.close()

# 2. Testar Carga Automática do Exercício Inicial (Aluno Lucas Silva - Nível B1/A2)
print("\n--- 2. Testando Carga Automática de Exercício na Tela Inicial (Aluno Lucas) ---")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = urllib.parse.urlencode({
    "tipo_acesso": "aluno",
    "matricula": "202601",
    "senha": "123456"
}).encode("utf-8")
req_login = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
resp_login = opener.open(req_login)
assert resp_login.status == 200
print("[OK] Aluno Lucas conectado com sucesso!")

# Acessa a tela inicial /
req_home = urllib.request.Request(f"{BASE_URL}/", method="GET")
html_home = opener.open(req_home).read().decode("utf-8")

assert 'id="tema_aula"' in html_home
assert 'id="pergunta"' in html_home

# Verifica se os campos NÃO estão em branco (estão pré-carregados)
import re
match_tema = re.search(r'id="tema_aula"[^>]*value="([^"]+)"', html_home)
match_pergunta = re.search(r'<textarea[^>]*id="pergunta"[^>]*>(.*?)</textarea>', html_home, re.DOTALL)

assert match_tema is not None and len(match_tema.group(1).strip()) > 0
assert match_pergunta is not None and len(match_pergunta.group(1).strip()) > 0

print(f"[OK] Exercício inicial carregado automaticamente:")
print(f"     Tema: {match_tema.group(1)}")
print(f"     Enunciado: {match_pergunta.group(1)[:60]}...")

# 3. Testar Renderização de Prova com Frase de Ditado com Apóstrofo
print("\n--- 3. Testando Ditado com Frase Francesa com Apóstrofos (aluno_prova.html) ---")
# Criar temporariamente uma questão de ditado com apóstrofo
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
cur.execute("INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES ('Prova Teste Ditado', 'Prova', 1, '2026-12-31 23:59:00')")
av_id = cur.lastrowid
frase_com_apostrofo = "C'est l'ami de Paul qui m'a dit qu'il faisait beau."
cur.execute("""
    INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
    VALUES (?, 'ditado', 'Ouça a frase e escreva:', ?, 10.0)
""", (av_id, frase_com_apostrofo))
conn.commit()

# Acessa /aluno/prova/<av_id>
req_prova = urllib.request.Request(f"{BASE_URL}/aluno/prova/{av_id}", method="GET")
html_prova = opener.open(req_prova).read().decode("utf-8")

# Limpa o teste
cur.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (av_id,))
cur.execute("DELETE FROM avaliacoes WHERE id = ?", (av_id,))
conn.commit()
conn.close()

# Verifica se o data-texto preserva o apóstrofo de forma segura
assert 'data-texto="C&#39;est l&#39;ami de Paul' in html_prova or 'data-texto="C\'est l\'ami de Paul' in html_prova
assert "ouvirTexto(this.getAttribute('data-texto'))" in html_prova
print("[OK] Ditado com apóstrofos renderizado com segurança sem quebrar sintaxe JS!")

# 4. Testar Submissão de Exercício (/avaliar)
print("\n--- 4. Testando Submissão de Resposta do Aluno em /avaliar ---")
# Obter o exercicio_id que veio da tela inicial ou o primeiro exercicio disponivel
conn = sqlite3.connect("educacao_ia.db")
cur = conn.cursor()
ex_row = cur.execute("SELECT id FROM exercicios LIMIT 1").fetchone()
conn.close()
ex_id = ex_row[0]

eval_data = json.dumps({
    "exercicio_id": ex_id,
    "resposta_aluno": "Je m'appelle Lucas et j'apprends le français avec plaisir.",
    "tentativa": 1
}).encode("utf-8")

req_eval = urllib.request.Request(
    f"{BASE_URL}/avaliar",
    data=eval_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_eval = opener.open(req_eval)
assert resp_eval.status == 200
eval_res = json.loads(resp_eval.read().decode("utf-8"))
print(f"[OK] Submissão avaliada com sucesso:")
print(f"     Status: {eval_res.get('status')}")
print(f"     Status Resposta: {eval_res.get('status_resposta')}")
print(f"     Feedback IA: {eval_res.get('feedback_ia')[:80]}...")
assert eval_res.get("status") == "sucesso"
assert "id" in eval_res

print("\n==================================================")
print(">>> TODOS OS TESTES DO PACOTE A FORAM CONCLUÍDOS COM 100% DE SUCESSO! <<<")
print("==================================================")

