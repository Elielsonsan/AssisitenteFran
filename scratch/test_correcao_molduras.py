
from bs4 import BeautifulSoup
import os

def test_correcao_molduras():
    path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'professor_correcao.html')
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')

    # Header deve ter a moldura
    hero_outer = soup.find('div', class_=lambda c: c and 'correcao-hero-outer' in c and 'hero-card-outer' in c)
    assert hero_outer is not None, "Header deve ter correcao-hero-outer e hero-card-outer"
    assert hero_outer.find('div', class_='hero-card-inner') is not None, "Header outer deve conter hero-card-inner"

    # Box do formulário deve ter a moldura
    box_outer = soup.find('div', class_=lambda c: c and 'correcao-box-outer' in c and 'card-moldura-outer' in c)
    assert box_outer is not None, "Formulário deve ter correcao-box-outer e card-moldura-outer"
    assert box_outer.find('div', class_='hero-card-inner') is not None, "Formulário outer deve conter hero-card-inner"
    
    print("Todos os testes de moldura da correção passaram com sucesso.")

if __name__ == '__main__':
    test_correcao_molduras()
