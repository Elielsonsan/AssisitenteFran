import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, iniciais_filter

def test_iniciais_filter():
    print("[1] Testando filtro de iniciais...")
    assert iniciais_filter("Professor Admin") == "PA", f"Esperado PA, obteve {iniciais_filter('Professor Admin')}"
    assert iniciais_filter("Lucas Silva") == "LS"
    assert iniciais_filter("Jean Dupont") == "JD"
    assert iniciais_filter("Fran") == "FR"
    assert iniciais_filter("") == "U"
    assert iniciais_filter(None) == "U"
    print("  -> Filtro de iniciais OK!")

def test_dashboard_navbar_rendering():
    print("[2] Testando renderização da navbar no dashboard...")
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['prof_id'] = 1
        sess['prof_nome'] = "Professor Admin"
        sess['prof_usuario'] = "admin"

    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Verifica se os ícones SVG de linha estão presentes
    assert 'class="theme-icon icon-moon"' in html
    assert 'class="theme-icon icon-sun"' in html
    assert '<circle cx="12" cy="12" r="4">' in html  # SVG sun outline

    # Verifica se as iniciais aparecem no badge
    assert 'PA' in html
    assert 'nav-avatar-badge' in html
    assert '👨‍🏫' not in html, "Emoji de professor ainda presente na navbar!"

    print("  -> Ícones SVG e Iniciais do Usuário renderizados corretamente!")

def test_css_rules():
    print("[3] Testando regras CSS para remoção da faixa e linha discreta...")
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".nav-link::after" in css
    assert "background: transparent !important" in css
    assert ".avatar-initials" in css
    assert ".nav-icon-btn" in css
    print("  -> Regras CSS validadas com sucesso!")

if __name__ == "__main__":
    try:
        test_iniciais_filter()
        test_dashboard_navbar_rendering()
        test_css_rules()
        print("\n>>> TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! <<<")
    except Exception as e:
        print(f"\n[FALHA]: {e}")
        sys.exit(1)
