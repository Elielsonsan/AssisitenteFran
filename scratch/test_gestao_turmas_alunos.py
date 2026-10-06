import requests

BASE_URL = "http://127.0.0.1:5000"

def test_gestao_turmas_e_alunos():
    print("=" * 65)
    print("TESTE DE VALIDAÇÃO: GESTÃO DE TURMAS & ALUNOS NO MENU DOCENTE")
    print("=" * 65)

    session = requests.Session()

    # 1. Autenticação do Professor Admin
    login_resp = session.post(f"{BASE_URL}/login", data={
        "tipo_acesso": "professor",
        "usuario": "admin",
        "senha": "admin"
    }, allow_redirects=True)
    assert login_resp.status_code == 200, "Falha na autenticação do professor"
    print("\n[OK] Professor autenticado com sucesso!")

    # 2. Verificar Renderização no Dashboard (Botões no Menu e Modais)
    dash_resp = session.get(f"{BASE_URL}/dashboard")
    assert dash_resp.status_code == 200
    html = dash_resp.text

    assert 'id="btnGerenciarTurmas"' in html, "Botão 'Turmas' não encontrado no menu"
    assert 'id="btnGerenciarAlunos"' in html, "Botão 'Alunos' não encontrado no menu"
    assert 'id="modalGestaoTurmas"' in html, "Modal de Gestão de Turmas não encontrado"
    assert 'id="modalAluno"' in html, "Modal de Gestão de Alunos não encontrado"
    assert 'id="tabBtnListaAlunos"' in html, "Aba de Lista de Alunos não encontrada"
    assert 'id="tabBtnFormAluno"' in html, "Aba de Formulário de Aluno não encontrada"
    assert 'id="listaTurmasContainer"' in html, "Container de Lista de Turmas não encontrado"
    print("[OK] Elementos visuais (Botões 'Turmas' e 'Alunos', Modais e Abas) renderizados no Dashboard!")

    # 3. Testar API de Listagem de Turmas (GET /api/turmas)
    resp_turmas = session.get(f"{BASE_URL}/api/turmas")
    assert resp_turmas.status_code == 200
    data_turmas = resp_turmas.json()
    assert data_turmas["status"] == "sucesso"
    assert len(data_turmas["turmas"]) > 0
    print(f"[OK] GET /api/turmas retornou {len(data_turmas['turmas'])} turmas cadastradas.")

    # 4. Testar Criação de Nova Turma (POST /api/turmas/cadastrar)
    nome_turma_teste = "Turma Teste Automatizado B2"
    resp_cria_turma = session.post(f"{BASE_URL}/api/turmas/cadastrar", json={"nome": nome_turma_teste})
    assert resp_cria_turma.status_code == 200
    dados_cria = resp_cria_turma.json()
    assert dados_cria["status"] == "sucesso"
    turma_id = dados_cria["turma"]["id"]
    print(f"[OK] POST /api/turmas/cadastrar criou a turma ID {turma_id} ('{nome_turma_teste}').")

    # 5. Testar Edição da Turma (POST /api/turmas/<id>/editar)
    nome_turma_editado = "Turma Teste Automatizado B2 - Renomeada"
    resp_edit_turma = session.post(f"{BASE_URL}/api/turmas/{turma_id}/editar", json={"nome": nome_turma_editado})
    assert resp_edit_turma.status_code == 200
    assert resp_edit_turma.json()["status"] == "sucesso"
    print(f"[OK] POST /api/turmas/{turma_id}/editar renomeou com sucesso para '{nome_turma_editado}'.")

    # 6. Testar Listagem de Alunos (GET /api/alunos)
    resp_alunos = session.get(f"{BASE_URL}/api/alunos")
    assert resp_alunos.status_code == 200
    data_alunos = resp_alunos.json()
    assert data_alunos["status"] == "sucesso"
    print(f"[OK] GET /api/alunos retornou {len(data_alunos['alunos'])} alunos.")

    # 7. Testar Criação de Novo Aluno (POST /api/alunos/cadastrar)
    mat_teste = "999901"
    nome_aluno_teste = "Estudante Teste Automatizado"
    resp_cria_aluno = session.post(f"{BASE_URL}/api/alunos/cadastrar", json={
        "nome": nome_aluno_teste,
        "matricula": mat_teste,
        "senha": "senha123",
        "turma_id": turma_id,
        "nivel_cefr": "B1"
    })
    assert resp_cria_aluno.status_code == 200
    dados_aluno = resp_cria_aluno.json()
    assert dados_aluno["status"] == "sucesso"
    aluno_id = dados_aluno["aluno"]["id"]
    print(f"[OK] POST /api/alunos/cadastrar criou o aluno ID {aluno_id} ('{nome_aluno_teste}').")

    # 8. Testar Bloqueio de Exclusão de Turma com Alunos
    resp_bloqueio = session.post(f"{BASE_URL}/api/turmas/{turma_id}/excluir")
    assert resp_bloqueio.status_code == 400
    assert "existem" in resp_bloqueio.json()["mensagem"]
    print("[OK] Proteção de exclusão validada: turma com alunos vinculados não pode ser apagada.")

    # 9. Testar Edição de Aluno com Troca de Senha (POST /api/alunos/<id>/editar)
    nome_aluno_editado = "Estudante Teste Editado"
    resp_edit_aluno = session.post(f"{BASE_URL}/api/alunos/{aluno_id}/editar", json={
        "nome": nome_aluno_editado,
        "matricula": mat_teste,
        "senha": "nova_senha456",
        "turma_id": turma_id,
        "nivel_cefr": "B2"
    })
    assert resp_edit_aluno.status_code == 200
    assert resp_edit_aluno.json()["status"] == "sucesso"
    print(f"[OK] POST /api/alunos/{aluno_id}/editar atualizou dados e senha com sucesso.")

    # 10. Testar Exclusão do Aluno Teste (POST /api/alunos/<id>/excluir)
    resp_del_aluno = session.post(f"{BASE_URL}/api/alunos/{aluno_id}/excluir")
    assert resp_del_aluno.status_code == 200
    assert resp_del_aluno.json()["status"] == "sucesso"
    print(f"[OK] POST /api/alunos/{aluno_id}/excluir removeu o aluno com sucesso.")

    # 11. Testar Exclusão da Turma Teste Vazia (POST /api/turmas/<id>/excluir)
    resp_del_turma = session.post(f"{BASE_URL}/api/turmas/{turma_id}/excluir")
    assert resp_del_turma.status_code == 200
    assert resp_del_turma.json()["status"] == "sucesso"
    print(f"[OK] POST /api/turmas/{turma_id}/excluir removeu a turma vazia com sucesso.")

    print("\n" + "=" * 65)
    print(">>> TODOS OS TESTES DE GESTÃO DE TURMAS & ALUNOS FORAM APROVADOS COM 100%! <<<")
    print("=" * 65)

if __name__ == "__main__":
    test_gestao_turmas_e_alunos()
