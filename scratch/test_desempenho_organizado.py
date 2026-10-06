import unittest
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestDesempenhoOrganizado(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["turma_id"] = 1
            sess["nivel_cefr"] = "A1"

    def test_01_render_desempenho_novo_layout(self):
        resp = self.client.get("/aluno/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Hero Card do Estudante
        self.assertIn('desempenho-hero-card', html)
        self.assertIn('Bonjour, Lucas Silva!', html)
        self.assertIn('Minhas Atividades', html)
        self.assertIn('Prática Livre', html)

        # 2. Grid de 4 KPIs Principais
        self.assertIn('class="desempenho-kpis-grid"', html)
        self.assertIn('class="desempenho-kpi-card"', html)
        self.assertIn('Nível Atual', html)
        self.assertIn('Precisão Geral', html)
        self.assertIn('Correio do Tutor', html)

        # 3. Grid de Gráficos Analíticos (2 Colunas 50/50)
        self.assertIn('class="desempenho-charts-grid"', html)
        self.assertIn('class="desempenho-chart-card"', html)
        self.assertIn('id="desempenhoChart"', html)
        self.assertIn('id="participacaoChart"', html)
        self.assertIn('chart-pill-stat correto', html)
        self.assertIn('chart-pill-stat parcial', html)
        self.assertIn('chart-pill-stat incorreto', html)

        # 4. Grid de Conquistas & Insígnias FLE
        self.assertIn('class="desempenho-badges-grid"', html)
        self.assertIn('class="desempenho-badge-card', html)

    def test_02_css_rules_desempenho(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Verifica regras de grid e responsividade
        self.assertIn(".desempenho-kpis-grid", css)
        self.assertIn("grid-template-columns: repeat(4, 1fr)", css)
        self.assertIn(".desempenho-charts-grid", css)
        self.assertIn("grid-template-columns: 1fr 1fr", css)
        self.assertIn(".desempenho-badges-grid", css)
        self.assertIn("grid-template-columns: repeat(3, 1fr)", css)

        # Verifica regras para Modo Claro
        self.assertIn('[data-theme="light"] .desempenho-hero-card', css)
        self.assertIn('[data-theme="light"] .desempenho-kpi-card', css)
        self.assertIn('[data-theme="light"] .desempenho-chart-card', css)
        self.assertIn('[data-theme="light"] .desempenho-badge-card', css)

if __name__ == '__main__':
    unittest.main()
