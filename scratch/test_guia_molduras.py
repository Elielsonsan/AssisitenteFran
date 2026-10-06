import sys
import os
import unittest
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

class TestGuiaFLEMolduras(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_guia_hero_card_e_quadro_unificado(self):
        res = self.client.get('/guia-fle')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Verificar Hero Card
        self.assertIn('id="guiaHeroCard"', html)
        self.assertIn('guia-hero-outer', html)
        self.assertIn('guia-hero-inner', html)
        self.assertIn('hero-card-outer', html)
        self.assertIn('hero-card-inner', html)
        self.assertIn('Guia Gramatical & Mémento FLE', html)
        self.assertIn('Référence Pédagogique FLE', html)
        self.assertIn('id="guiaSearchInput"', html)

        # 2. Verificar Quadro Unificado dos Temas (moldura única envolvendo todas as seções)
        self.assertIn('id="guiaBoxOuter"', html)
        self.assertIn('guia-box-outer', html)
        self.assertIn('guia-box-inner', html)
        self.assertIn('card-moldura-outer', html)
        self.assertIn('guia-sections-wrap', html)

        # 3. Hierarquia rigorosa: guiaBoxOuter > guia-box-inner > guia-sections-wrap > seções
        match_hierarchy = re.search(
            r'id="guiaBoxOuter"[^>]*>.*?class="[^"]*guia-box-inner[^"]*".*?class="[^"]*guia-sections-wrap[^"]*".*?id="tema-maison-etre"',
            html,
            re.DOTALL
        )
        self.assertIsNotNone(match_hierarchy, "A hierarquia guiaBoxOuter > guia-box-inner > guia-sections-wrap > seções não foi respeitada")

        # 4. Todos os 10 capítulos presentes dentro do quadro
        temas_esperados = [
            'maison-etre', 'conjugacao-verbos', 'articles-partitifs', 'faux-amis',
            'pronoms-y-en', 'pronoms-cod-coi', 'negation-complexe', 'prepositions-lieu',
            'courtoisie-quotidien', 'subjonctif-indicatif'
        ]
        for t in temas_esperados:
            self.assertIn(f'id="tema-{t}"', html)
            self.assertIn(f'data-tema="{t}"', html)

        # 5. Sidebar de navegação
        self.assertIn('id="guiaSidebar"', html)

    def test_css_guia_molduras_e_contraste(self):
        css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        # Verifica integração ao Design System de molduras
        self.assertIn('.guia-hero-outer', css)
        self.assertIn('.guia-hero-card', css)
        self.assertIn('.guia-box-outer', css)
        self.assertIn('.guia-hero-inner', css)
        self.assertIn('.guia-box-inner', css)

        # Verifica tema claro
        self.assertIn('[data-theme="light"] .guia-hero-outer', css)
        self.assertIn('[data-theme="light"] .guia-hero-card', css)
        self.assertIn('[data-theme="light"] .guia-box-outer', css)

    def test_guia_fle_aluno_logado(self):
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["nivel_cefr"] = "B1"

        res = self.client.get('/guia-fle')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="guiaHeroCard"', html)
        self.assertIn('id="guiaBoxOuter"', html)

    def test_guia_fle_centralizado(self):
        res = self.client.get('/guia-fle')
        html = res.get_data(as_text=True)

        # Garantir que o container está centralizado (margin: 0 auto) e não empurrado para a esquerda com 90px
        self.assertIn('.guia-fle-container', html)
        self.assertIn('margin: 0 auto', html)
        self.assertNotIn('margin-left: 90px', html)

        # Garantir que os atalhos e busca estão centralizados
        self.assertIn('justify-content: center', html)
        self.assertIn('.guia-search-box', html)

if __name__ == '__main__':
    unittest.main()
