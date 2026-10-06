import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_borda_transparente_e_menu():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # 1. Verificar quadro unificado de atividades com efeito hero card (borda de vidro + card interno)
    assert 'atividades-box-outer' in html, "atividades-box-outer não encontrado no HTML"
    assert 'hero-card-outer' in html, "hero-card-outer não encontrado no HTML"
    assert 'atividades-box-inner' in html, "atividades-box-inner não encontrado no HTML"
    assert 'hero-card-inner' in html, "hero-card-inner não encontrado no HTML"

    # Verificar que o split container está DENTRO do box unificado
    match_box = re.search(r'id="atividadesBoxOuter".*?id="atividadesSplitContainer"', html, re.DOTALL)
    assert match_box is not None, "atividadesSplitContainer deve estar DENTRO de atividadesBoxOuter"

    # 2. Verificar efeito de menu nos cabeçalhos de Atividades Pendentes e Concluídas
    assert 'secao-header-menu' in html, "secao-header-menu não encontrado"
    assert 'headerSecaoPendentes' in html, "headerSecaoPendentes não encontrado"
    assert 'headerSecaoConcluidas' in html, "headerSecaoConcluidas não encontrado"
    assert 'toggleMenuStatus' in html, "Função toggleMenuStatus não encontrada no script"

    print("✓ Quadro unificado de atividades com efeito Hero Card e menu em Pendentes e Concluídas validados com 100% de sucesso!")

if __name__ == '__main__':
    test_borda_transparente_e_menu()
