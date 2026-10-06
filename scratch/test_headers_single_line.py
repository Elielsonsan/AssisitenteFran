import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_headers_single_line():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # 1. Verificar HTML dos dois cabeçalhos
    assert 'id="headerSecaoPendentes"' in html, "headerSecaoPendentes não encontrado no HTML"
    assert 'id="headerSecaoConcluidas"' in html, "headerSecaoConcluidas não encontrado no HTML"

    # Verificar que o título e badge estão diretamente no secao-header-main
    assert 'secao-header-main' in html, "secao-header-main não encontrado"
    assert 'secao-icon-badge secao-icon-amber' in html, "Ícone de pendentes não encontrado"
    assert 'secao-icon-badge secao-icon-green' in html, "Ícone de concluídas não encontrado"
    assert 'secao-header-menu-indicator' in html, "Indicador de menu não encontrado"

    # 2. Verificar CSS para o formato de linha única
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    assert 'flex-wrap: nowrap !important;' in css, "flex-wrap: nowrap não configurado para cabeçalhos"
    assert 'height: 46px !important;' in css, "height: 46px não configurado para cabeçalhos em linha única"
    assert '.secao-subtitle {\n    display: none !important;\n}' in css, "secao-subtitle deve ser oculto no modo linha"
    assert '.secao-icon-badge {\n    width: 28px !important;\n    height: 28px !important;' in css, "secao-icon-badge deve ter 28px no formato linha"

    print("✓ Teste de cabeçalhos de atividades em formato de linha única aprovado com 100% de sucesso!")

if __name__ == '__main__':
    test_headers_single_line()
