import sys
import os
import requests

BASE_URL = "http://127.0.0.1:5000"

def test_sidebar_e_filtros():
    print("=" * 65)
    print("TESTE DE VALIDAÇÃO: SIDEBAR GLASSMORPHIC & POPOVER DE FILTROS")
    print("=" * 65)

    session = requests.Session()

    # 1. Autenticação do Professor
    login_resp = session.post(f"{BASE_URL}/login", data={
        "tipo_acesso": "professor",
        "usuario": "admin",
        "senha": "admin"
    }, allow_redirects=True)
    assert login_resp.status_code == 200, "Falha na autenticação do professor"
    print("\n[OK] Professor autenticado com sucesso!")

    # 2. Renderização do Dashboard com a nova Sidebar
    dash_resp = session.get(f"{BASE_URL}/dashboard")
    assert dash_resp.status_code == 200
    html = dash_resp.text

    # Verifica presença da barra lateral e ausência dos antigos menus horizontais
    assert 'id="dashSidebar"' in html, "Sidebar 'dashSidebar' não encontrada"
    assert 'class="dash-sidebar no-print"' in html
    assert 'id="popoverFiltros"' in html, "Modal popover de filtros não encontrado"
    assert 'id="btnToggleFiltrosPopover"' in html, "Botão acionador de filtros não encontrado"
    assert 'class="dashboard-top-menu"' not in html, "Menu horizontal antigo ainda presente!"

    # Verifica os botões de ação e filtros preservados na sidebar
    assert 'id="filtroTurma"' in html, "Select filtroTurma ausente"
    assert 'id="filtroNivel"' in html, "Select filtroNivel ausente"
    assert 'id="filtroAluno"' in html, "Select filtroAluno ausente"
    assert 'id="btnRelatorioText"' in html, "Botão aplicar filtro ausente"
    assert 'id="btnGerenciarTurmas"' in html, "Botão 'Turmas' ausente"
    assert 'id="btnGerenciarAlunos"' in html, "Botão 'Alunos' ausente"
    assert 'id="btnNovoRecado"' in html, "Botão 'Enviar Recado' ausente"
    assert 'id="btnExportarCsv"' in html, "Botão 'Exportar CSV' ausente"
    assert 'id="btnBoletimTurma"' in html, "Botão 'Boletim Escolar' ausente"
    assert 'id="btnExportarPdf"' in html, "Botão 'Exportar PDF' ausente"
    print("[OK] Estrutura da Sidebar, Ícones e Modal Popover de Filtros validados!")

    # 3. Validar se os ícones da sidebar usam traços suaves (SVG stroke) sem emojis nos botões
    assert '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>' in html
    assert 'stroke-width="1.8"' in html
    print("[OK] Ícones em traços suaves vetoriais (stroke 1.8px) validados!")

    # 4. Validar chamada da API de estatísticas do dashboard
    api_resp = session.get(f"{BASE_URL}/api/dashboard/estatisticas?turma_id=todas&nivel_cefr=todos&aluno_id=todos")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["status"] == "sucesso"
    assert "desempenho_geral" in data
    assert "dificuldade_tema" in data
    print("[OK] API /api/dashboard/estatisticas respondendo com sucesso aos filtros!")

    # 5. Validar regras CSS
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".dash-sidebar" in css
    assert ".dash-sidebar:hover" in css
    assert ".popover-filtros-modal" in css
    assert ".popover-filtros-modal.open" in css
    assert "backdrop-filter: blur(24px) saturate(190%)" in css
    print("[OK] Regras CSS de glassmorphism translúcido e animação popout validadas!")

    print("\n" + "=" * 65)
    print(">>> TODOS OS TESTES DA SIDEBAR E FILTROS FORAM APROVADOS! <<<")
    print("=" * 65)

if __name__ == "__main__":
    try:
        test_sidebar_e_filtros()
    except Exception as e:
        print(f"\n[FALHA]: {e}")
        sys.exit(1)
