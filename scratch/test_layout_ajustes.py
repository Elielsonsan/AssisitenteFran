import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_layout_ajustes():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # 1. Barra de Abas no Topo (logo abaixo do cabeçalho)
    assert 'atividadesTabsTopWrapper' in html, "atividadesTabsTopWrapper não encontrado"
    assert 'atividadesHeroCard' in html, "atividadesHeroCard não encontrado"
    header_idx = html.find('id="atividadesHeroCard"')
    tabs_idx = html.find('id="atividadesTabsTopWrapper"')
    split_idx = html.find('id="atividadesSplitContainer"')
    assert header_idx < tabs_idx < split_idx, "As abas não estão posicionadas logo abaixo do texto e antes do split container!"

    # 2. Container Dividido (Pendentes à esquerda, Concluídas à direita)
    assert 'class="atividades-split-container" id="atividadesSplitContainer"' in html
    pendentes_idx = html.find('id="secaoAtividadesPendentes"')
    concluidas_idx = html.find('id="secaoAtividadesConcluidas"')
    assert split_idx < pendentes_idx < concluidas_idx, "Pendentes deve vir antes (lado esquerdo) de Concluídas!"

    # 3. Concluídas no Formato de Linha e quando clicado vira o Card
    assert 'class="concluida-row-view"' in html, "Vista em linha para concluídas não encontrada"
    assert 'class="concluida-card-view"' in html, "Vista em card para concluídas não encontrada"
    assert 'toggleConcluidaCard' in html, "Função toggleConcluidaCard não encontrada"
    assert 'btn-recolher-linha' in html, "Botão para retornar ao modo linha não encontrado"

    # 4. Efeito dos Cards do Fórum
    assert 'forum-card' in html, "Classe forum-card não encontrada nos cards"
    assert 'forum-card-inner' in html, "forum-card-inner não encontrado"
    assert 'forum-card-header' in html, "forum-card-header não encontrado"
    assert 'forum-topic-title' in html, "forum-topic-title não encontrado"
    assert 'forum-card-footer' in html, "forum-card-footer não encontrado"

    print("✓ Todos os 4 ajustes foram validados com 100% de sucesso!")

if __name__ == '__main__':
    test_layout_ajustes()
