import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_tab_inside_card():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # Extract hero-card-inner block
    inner_match = re.search(r'<div class="hero-card-inner">(.*?)</div>\s*</div>', html, re.DOTALL)
    assert inner_match is not None, "hero-card-inner not found in HTML"
    inner_content = inner_match.group(1)

    assert 'hero-description' in inner_content, "hero-description should be inside hero-card-inner"
    assert 'id="atividadesTabsTopWrapper"' in inner_content, "atividadesTabsTopWrapper must be INSIDE hero-card-inner!"
    
    desc_pos = inner_content.find('hero-description')
    tabs_pos = inner_content.find('id="atividadesTabsTopWrapper"')
    assert desc_pos < tabs_pos, "atividadesTabsTopWrapper must be BELOW hero-description"

    print("✓ Barra de abas posicionada com perfeição dentro do card central abaixo do texto!")

if __name__ == '__main__':
    test_tab_inside_card()
