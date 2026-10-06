import requests

session = requests.Session()

# 1. Login as teacher
resp = session.post("http://127.0.0.1:5000/login", data={
    "tipo_acesso": "professor",
    "usuario": "admin",
    "senha": "admin"
}, allow_redirects=True)
print(f"Login status: {resp.status_code}, Final URL: {resp.url}")

# 2. Check dashboard
resp_dash = session.get("http://127.0.0.1:5000/dashboard")
print(f"Dashboard status: {resp_dash.status_code}, URL: {resp_dash.url}")
has_copiloto_dash = "secaoCopiloto" in resp_dash.text
print(f"Dashboard has secaoCopiloto: {has_copiloto_dash} (Expected: False)")

# 3. Check professor/avaliacoes
resp_aval = session.get("http://127.0.0.1:5000/professor/avaliacoes")
print(f"Avaliacoes status: {resp_aval.status_code}, URL: {resp_aval.url}")
has_copiloto_aval = "secaoCopiloto" in resp_aval.text
print(f"Avaliacoes has secaoCopiloto: {has_copiloto_aval} (Expected: True)")
has_form_copiloto = "formCopiloto" in resp_aval.text
print(f"Avaliacoes has formCopiloto: {has_form_copiloto} (Expected: True)")
has_js_copiloto = "gerarExerciciosCopiloto" in resp_aval.text
print(f"Avaliacoes has gerarExerciciosCopiloto JS: {has_js_copiloto} (Expected: True)")
has_toast = "toastNotification" in resp_aval.text
print(f"Avaliacoes has toastNotification: {has_toast} (Expected: True)")

# Check if topics are loaded in the select
has_temas = '<select id="copiloto_tema"' in resp_aval.text and "<option value=" in resp_aval.text
print(f"Avaliacoes has topics loaded: {has_temas} (Expected: True)")

assert not has_copiloto_dash, "Error: Dashboard still has secaoCopiloto"
assert has_copiloto_aval, "Error: Avaliacoes missing secaoCopiloto"
assert has_form_copiloto, "Error: Avaliacoes missing formCopiloto"
assert has_js_copiloto, "Error: Avaliacoes missing JS"
assert has_toast, "Error: Avaliacoes missing toastNotification"
assert has_temas, "Error: Avaliacoes missing topic options"
print("\n>>> ALL CHECKS PASSED SUCCESSFULLY! <<<")
