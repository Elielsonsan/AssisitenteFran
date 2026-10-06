import urllib.request
import urllib.parse
import http.cookiejar
import json
import time
import sqlite3

# Clean up any previous test turmas
conn = sqlite3.connect("educacao_ia.db")
conn.execute("DELETE FROM turmas WHERE nome LIKE 'Turma C1 - %'")
conn.commit()
conn.close()

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

BASE_URL = "http://127.0.0.1:5000"

print("--- 1. Testing Teacher Login ---")
login_data = urllib.parse.urlencode({
    "tipo_acesso": "professor",
    "usuario": "admin",
    "senha": "admin"
}).encode("utf-8")
req = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
resp = opener.open(req)
print(f"Login status: {resp.status}, final url: {resp.geturl()}")
assert "/dashboard" in resp.geturl()

print("\n--- 2. Testing POST /api/turmas/cadastrar ---")
test_turma_name = f"Turma C1 - Test {int(time.time())}"
turma_payload = json.dumps({"nome": test_turma_name}).encode("utf-8")
req_turma = urllib.request.Request(
    f"{BASE_URL}/api/turmas/cadastrar", 
    data=turma_payload, 
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp_turma = opener.open(req_turma)
data_turma = json.loads(resp_turma.read().decode("utf-8"))
print(f"Turma cadastrada com sucesso: {data_turma}")
assert data_turma["status"] == "sucesso"
nova_turma_id = data_turma["turma"]["id"]

try:
    print("\n--- 3. Testing GET /api/relatorio/exportar_csv ---")
    req_csv = urllib.request.Request(f"{BASE_URL}/api/relatorio/exportar_csv?turma_id=1&nivel_cefr=A1", method="GET")
    resp_csv = opener.open(req_csv)
    csv_content = resp_csv.read().decode("utf-8-sig")
    print(f"CSV Content-Type: {resp_csv.headers.get('Content-Type')}")
    print(f"CSV Content-Disposition: {resp_csv.headers.get('Content-Disposition')}")
    print("Linhas do CSV gerado (filtrado Turma 1, Nível A1):")
    for line in csv_content.splitlines()[:6]:
        print("  ", line)
    assert "Nome do Aluno" in csv_content
    assert "Matrícula" in csv_content
    assert "Lucas Silva" in csv_content  # Lucas Silva is A1, Turma 1

    print("\n--- 4. Testing GET /api/avaliacoes/1/submissoes ---")
    req_sub = urllib.request.Request(f"{BASE_URL}/api/avaliacoes/1/submissoes", method="GET")
    resp_sub = opener.open(req_sub)
    data_sub = json.loads(resp_sub.read().decode("utf-8"))
    print(f"Avaliação: {data_sub.get('avaliacao', {}).get('titulo')}")
    print(f"Total submissões encontradas: {len(data_sub.get('submissoes', []))}")
    if data_sub.get('submissoes'):
        print("Amostra de submissão:", data_sub['submissoes'][0]['aluno_nome'], "-", data_sub['submissoes'][0]['status_resposta'])
    assert data_sub["status"] == "sucesso"

finally:
    print("\n--- 5. Clean up test turma ---")
    conn = sqlite3.connect("educacao_ia.db")
    conn.execute("DELETE FROM turmas WHERE id = ?", (nova_turma_id,))
    conn.commit()
    conn.close()
    print("Limpeza da turma de teste concluída. ID:", nova_turma_id)

print("\n>>> ALL PHASE 5 TESTS PASSED SUCCESSFULLY! <<<")
