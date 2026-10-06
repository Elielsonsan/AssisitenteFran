import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestAvaliacoesMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_professor_avaliacoes_hero_card_e_molduras(self):
        with self.client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["prof_nome"] = "Professora Françoise"
            sess["is_professor"] = True

        resp = self.client.get("/professor/avaliacoes")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Hero Card do Topo com Moldura Glassmorphic e Faixa Francesa
        self.assertIn('id="avaliacoesHeroCard"', html)
        self.assertIn('dashboard-hero-outer', html)
        self.assertIn('card-moldura-outer', html)
        self.assertIn('avaliacoes-hero-outer', html)
        self.assertIn('dashboard-hero-card', html)
        self.assertIn('hero-card-inner', html)
        self.assertIn('Évaluations &amp; Examens • FLE', html.replace('&', '&amp;'))
        self.assertIn('Gestão de Avaliações', html)

        # 2. Tabela de Submissões Pendentes envolvida por Moldura
        self.assertIn('id="pendentesBoxOuter"', html)
        self.assertIn('pendentes-box-outer', html)
        self.assertIn('id="cardTabelaPendentes"', html)
        self.assertIn('table-box-inner', html)

        # 3. Tabela de Avaliações Ativas envolvida por Moldura
        self.assertIn('id="avaliacoesBoxOuter"', html)
        self.assertIn('avaliacoes-box-outer', html)
        self.assertIn('id="secaoTabelaAvaliacoes"', html)
        self.assertIn('table-box-inner', html)
        self.assertIn('id="tabelaAvaliacoes"', html)
        self.assertIn('id="paginacaoAvaliacoes"', html)

    def test_02_css_avaliacoes_molduras_e_regras(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Seletores de moldura externa integrados no Design System
        self.assertIn(".avaliacoes-hero-outer", css)
        self.assertIn(".avaliacoes-box-outer", css)
        self.assertIn(".pendentes-box-outer", css)
        self.assertIn('[data-theme="light"] .avaliacoes-hero-outer', css)
        self.assertIn('[data-theme="light"] .avaliacoes-box-outer', css)
        self.assertIn('[data-theme="light"] .pendentes-box-outer', css)

        # Regras de cabeçalho e tabela
        self.assertIn(".pendentes-table-header", css)
        self.assertIn(".avaliacoes-table-header", css)
        self.assertIn(".dash-table-zebra th", css)
        self.assertIn(".dash-table-zebra td", css)

if __name__ == '__main__':
    unittest.main()
