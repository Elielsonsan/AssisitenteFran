import requests

BASE_URL = "http://127.0.0.1:5000"

def test_navbar_structure():
    print("=" * 60)
    print("TESTE DE VALIDAÇÃO: NAVBAR SUPERIOR & DRAWER MOBILE RESPONSIVO")
    print("=" * 60)

    session = requests.Session()

    # 1. Teste Não Logado (Visitante / Guest)
    resp = session.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Status code: {resp.status_code}"
    html = resp.text

    assert 'class="app-navbar"' in html, "Navbar principal não encontrada"
    assert 'class="nav-container"' in html, "Container da navbar não encontrado"
    assert 'class="nav-brand"' in html, "Brand/Logotipo não encontrado"
    assert 'class="nav-links-desktop"' in html, "Links de desktop não encontrados"
    assert 'id="btnHamburger"' in html, "Botão hamburger não encontrado"
    assert 'class="mobile-drawer-backdrop"' in html, "Backdrop do drawer não encontrado"
    assert 'class="mobile-nav-drawer"' in html, "Drawer mobile não encontrado"
    assert 'class="drawer-close-btn"' in html, "Botão fechar do drawer não encontrado"
    assert 'abrirMenuMobile' in html, "Função JS abrirMenuMobile não encontrada"
    assert 'fecharMenuMobile' in html, "Função JS fecharMenuMobile não encontrada"
    print("  [OK] Estrutura HTML e JS da Navbar e Drawer para Visitante verificada!")

    # 2. Teste Logado como Professor
    login_prof = session.post(f"{BASE_URL}/login", data={
        "tipo_acesso": "professor",
        "usuario": "admin",
        "senha": "admin"
    }, allow_redirects=True)
    assert login_prof.status_code == 200, "Falha no login do professor"

    prof_home = session.get(f"{BASE_URL}/dashboard")
    assert prof_home.status_code == 200
    html_prof = prof_home.text

    assert "Painel Docente" in html_prof, "Link Painel Docente não encontrado"
    assert "Avaliações" in html_prof, "Link Avaliações não encontrado"
    assert "Planos de Aula" in html_prof, "Link Planos de Aula não encontrado"
    assert "Fórum" in html_prof, "Link Fórum não encontrado"
    assert "drawer-user-card" in html_prof, "Card de usuário no drawer não encontrado"
    assert "Professor FLE" in html_prof, "Cargo de Professor não exibido no drawer"
    print("  [OK] Links e Drawer do Professor verificados no Dashboard!")

    # 3. Teste Logado como Aluno
    session.get(f"{BASE_URL}/logout")
    login_aluno = session.post(f"{BASE_URL}/login", data={
        "tipo_acesso": "aluno",
        "matricula": "202601",
        "senha": "123456"
    }, allow_redirects=True)
    assert login_aluno.status_code == 200, "Falha no login do aluno"

    aluno_home = session.get(f"{BASE_URL}/aluno/dashboard")
    assert aluno_home.status_code == 200
    html_aluno = aluno_home.text

    assert "Meu Desempenho" in html_aluno, "Link Meu Desempenho não encontrado"
    assert "Atividades" in html_aluno, "Link Atividades não encontrado"
    assert "Lucas Silva" in html_aluno, "Nome do aluno não exibido no drawer"
    print("  [OK] Links e Drawer do Estudante verificados com sucesso!")

    print("\n" + "=" * 60)
    print(">>> TODOS OS TESTES DA NAVBAR & DRAWER PASSARAM COM SUCESSO! <<<")
    print("=" * 60)

if __name__ == "__main__":
    test_navbar_structure()
