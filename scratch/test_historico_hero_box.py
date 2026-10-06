import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_historico_hero_box():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # 1. Verificar container Box com efeito Hero Card envolvendo o Histórico de Prática Recente
    assert 'id="historicoBoxOuter"' in html, "id 'historicoBoxOuter' não encontrado no HTML"
    assert 'historico-box-outer' in html, "Classe 'historico-box-outer' não encontrada"
    assert 'historico-box-inner' in html, "Classe 'historico-box-inner' não encontrada"
    assert 'historico-header-section' in html, "Classe 'historico-header-section' não encontrada"

    # Verificar que o header do histórico está aninhado dentro do box hero card
    match_box = re.search(r'<div class="historico-box-outer hero-card-outer"[^>]*id="historicoBoxOuter">.*?<div class="historico-box-inner hero-card-inner">.*?<div class="historico-header-section">.*?Histórico de Prática Recente', html, re.DOTALL)
    assert match_box is not None, "A hierarquia historico-box-outer > historico-box-inner > historico-header-section não foi encontrada"

    # 2. Verificar CSS em static/css/style.css
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    assert '.historico-box-outer' in css, ".historico-box-outer não encontrado no CSS"
    assert '.historico-box-inner' in css, ".historico-box-inner não encontrado no CSS"
    assert '[data-theme="light"]' in css and '.historico-box-outer' in css, "Tema light para historico-box-outer não configurado"
    assert '.historico-item-card' in css, "Estilo de cards de histórico dentro do box unificado não configurado"

    print("✓ Teste do Quadro Unificado de Histórico com Efeito Hero Card aprovado com 100% de sucesso!")

if __name__ == '__main__':
    test_historico_hero_box()
