import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_box_atividades_hero_card():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # 1. Verificar container Box com efeito Hero Card envolvendo as seções de atividades
    assert 'id="atividadesBoxOuter"' in html, "id 'atividadesBoxOuter' não encontrado no HTML"
    assert 'atividades-box-outer' in html, "Classe 'atividades-box-outer' não encontrada"
    assert 'atividades-box-inner' in html, "Classe 'atividades-box-inner' não encontrada"
    assert 'hero-card-inner' in html, "Classe 'hero-card-inner' não encontrada"

    # Verificar que o split container está aninhado dentro do box hero card
    box_outer_match = re.search(r'<div class="atividades-box-outer hero-card-outer"[^>]*id="atividadesBoxOuter">.*?<div class="atividades-box-inner hero-card-inner">.*?<div class="atividades-split-container" id="atividadesSplitContainer">', html, re.DOTALL)
    assert box_outer_match is not None, "A hierarquia atividades-box-outer > atividades-box-inner > atividades-split-container não foi encontrada"

    # 2. Verificar que ambas as colunas estão dentro do box unificado
    assert 'secaoAtividadesPendentes' in html, "secaoAtividadesPendentes não encontrada"
    assert 'secaoAtividadesConcluidas' in html, "secaoAtividadesConcluidas não encontrada"

    # 3. Verificar que os cards individuais NÃO têm a classe card-outer-glass redundante
    assert 'card-outer-glass' not in html, "Classe card-outer-glass não deve existir nos cards individuais"

    # 4. Verificar CSS em static/css/style.css
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    assert '.atividades-box-outer' in css, ".atividades-box-outer não encontrado no CSS"
    assert '.atividades-box-inner' in css, ".atividades-box-inner não encontrado no CSS"
    assert '[data-theme="light"]' in css and '.atividades-box-outer' in css, "Tema light para atividades-box-outer não configurado"
    assert '.atividades-box-inner .card-atividade-item' in css, "Estilo de cards dentro do box unificado não configurado"
    assert '.atividades-box-inner .concluida-interactive-card' in css, "Estilo de concluídas dentro do box unificado não configurado"

    print("✓ Teste do Quadro Unificado de Atividades com Efeito Hero Card aprovado com 100% de sucesso!")

if __name__ == '__main__':
    test_box_atividades_hero_card()
