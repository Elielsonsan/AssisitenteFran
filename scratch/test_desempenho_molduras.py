import unittest
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestDesempenhoMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["turma_id"] = 1
            sess["nivel_cefr"] = "A1"

    def test_01_quadros_unificados_meu_desempenho(self):
        resp = self.client.get("/aluno/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Hero Card do Topo com Moldura Glassmorphic
        self.assertIn('id="desempenhoHeroCard"', html)
        self.assertIn('desempenho-hero-outer', html)
        self.assertIn('desempenho-hero-card', html)

        # 2. Quadro Unificado de Métricas: APENAS UMA MOLDURA para todos os cards de métricas
        self.assertIn('id="desempenhoMetricasBoxOuter"', html)
        self.assertIn('desempenho-box-outer', html)
        self.assertIn('desempenho-box-inner', html)

        # 3. NENHUMA moldura individual em cada card (removidos kpi-moldura-outer e chart-moldura-outer)
        kpi_molduras = re.findall(r'class="[^"]*kpi-moldura-outer[^"]*"', html)
        self.assertEqual(len(kpi_molduras), 0, "Não deve haver molduras individuais para cada KPI")
        chart_molduras = re.findall(r'class="[^"]*chart-moldura-outer[^"]*"', html)
        self.assertEqual(len(chart_molduras), 0, "Não deve haver molduras individuais para cada Gráfico")

        # 4. Todos os 4 cards de KPIs presentes dentro do quadro unificado
        kpi_cards = re.findall(r'class="[^"]*desempenho-kpi-card[^"]*"', html)
        self.assertEqual(len(kpi_cards), 4, f"Esperado 4 cards de KPI dentro do quadro, encontrado {len(kpi_cards)}")

        # 5. Ambos os 2 cards de Gráficos presentes dentro do quadro unificado
        chart_cards = re.findall(r'class="[^"]*desempenho-chart-card[^"]*"', html)
        self.assertEqual(len(chart_cards), 2, f"Esperado 2 cards de Gráfico dentro do quadro, encontrado {len(chart_cards)}")
        self.assertIn('id="desempenhoChart"', html)
        self.assertIn('id="participacaoChart"', html)

        # 6. Quadro Unificado de Conquistas: APENAS UMA MOLDURA para todos os cards de conquistas
        self.assertIn('id="desempenhoConquistasBoxOuter"', html)
        self.assertIn('conquistas-box-outer', html)
        self.assertIn('conquistas-box-inner', html)
        self.assertIn('Minhas Conquistas & Insígnias FLE', html)

        # 7. Todos os 6 cards de badges presentes dentro do quadro unificado de conquistas
        badge_cards = re.findall(r'class="[^"]*desempenho-badge-card[^"]*"', html)
        self.assertEqual(len(badge_cards), 6, f"Esperado 6 cards de insígnias FLE, encontrado {len(badge_cards)}")

    def test_02_css_quadros_unificados(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Quadros registrados no efeito de vidro glassmorphic
        self.assertIn(".desempenho-hero-outer", css)
        self.assertIn(".desempenho-box-outer", css)
        self.assertIn(".conquistas-box-outer", css)
        self.assertIn(".desempenho-box-inner", css)
        self.assertIn(".conquistas-box-inner", css)

        # Cards com estilização interna elegante no modo claro
        self.assertIn('[data-theme="light"] .desempenho-box-inner .desempenho-kpi-card', css)
        self.assertIn('[data-theme="light"] .conquistas-box-inner .desempenho-badge-card', css)

if __name__ == '__main__':
    unittest.main()
