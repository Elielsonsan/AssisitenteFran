import unittest
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestDashboardMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_teacher_dashboard_hero_card_e_quadro_unificado(self):
        with self.client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["prof_nome"] = "Professora Françoise"
            sess["prof_usuario"] = "admin"

        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Hero Card do Topo com Moldura Glassmorphic e Faixa Tricolor Francesa
        self.assertIn('id="dashboardHeroCard"', html)
        self.assertIn('dashboard-hero-outer', html)
        self.assertIn('dashboard-hero-card', html)
        self.assertIn('Painel Geral do Professor', html)
        self.assertIn('Analytics Pedagógico • FLE & Inteligência Artificial', html)

        # 2. Quadro Unificado de Métricas & Gráficos: APENAS UMA MOLDURA para todos os cards
        self.assertIn('id="dashboardMetricasBoxOuter"', html)
        self.assertIn('dashboard-box-outer', html)
        self.assertIn('dashboard-box-inner', html)
        self.assertIn('Indicadores Globais & Desempenho Gráfico', html)

        # 3. NENHUMA moldura individual em cada card
        kpi_molduras = re.findall(r'class="[^"]*kpi-moldura-outer[^"]*"', html)
        self.assertEqual(len(kpi_molduras), 0, "Não deve haver molduras individuais para cada KPI")
        chart_molduras = re.findall(r'class="[^"]*chart-moldura-outer[^"]*"', html)
        self.assertEqual(len(chart_molduras), 0, "Não deve haver molduras individuais para cada Gráfico")

        # 4. Todos os 4 cards de Métricas presentes dentro do quadro unificado
        self.assertIn('id="cardMetricTotal"', html)
        self.assertIn('id="cardMetricCorretas"', html)
        self.assertIn('id="cardMetricParciais"', html)
        self.assertIn('id="cardMetricIncorretas"', html)

        # 5. Ambos os gráficos presentes dentro do quadro unificado
        self.assertIn('id="graficoStatus"', html)
        self.assertIn('id="graficoTemas"', html)

        # 6. Banner interativo de filtros presente
        self.assertIn('id="bannerFiltroInterativo"', html)

        # 7. Assegurar que os cards e gráficos estão contidos antes do fechamento do quadro
        pos_box_open = html.find('id="dashboardMetricasBoxOuter"')
        pos_box_close = html.find('<!-- FIM DO QUADRO UNIFICADO DE INDICADORES & GRÁFICOS -->')
        self.assertTrue(pos_box_open > 0, "Quadro unificado deve existir")
        self.assertTrue(pos_box_close > pos_box_open, "Comentário de fechamento do quadro deve existir após a abertura")

        box_chunk = html[pos_box_open:pos_box_close]
        self.assertIn('id="cardMetricTotal"', box_chunk)
        self.assertIn('id="cardMetricCorretas"', box_chunk)
        self.assertIn('id="cardMetricParciais"', box_chunk)
        self.assertIn('id="cardMetricIncorretas"', box_chunk)
        self.assertIn('id="graficoStatus"', box_chunk)
        self.assertIn('id="graficoTemas"', box_chunk)
        self.assertIn('id="bannerFiltroInterativo"', box_chunk)

        # 8. Tabela de Alunos com Dificuldade envolvida por Moldura Glassmorphic
        self.assertIn('id="riskBoxOuter"', html)
        self.assertIn('risk-box-outer', html)
        self.assertIn('id="cardTabelaRisco"', html)
        self.assertIn('table-box-inner', html)

        # 9. Tabela de Histórico de Submissões envolvida por Moldura Glassmorphic
        self.assertIn('id="submissoesBoxOuter"', html)
        self.assertIn('submissoes-box-outer', html)
        self.assertIn('id="cardTabelaSubmissoes"', html)

    def test_02_css_dashboard_molduras_e_contraste(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Seletores de moldura externa integrados no Design System
        self.assertIn(".dashboard-hero-outer", css)
        self.assertIn(".dashboard-box-outer", css)
        self.assertIn("[data-theme=\"light\"] .dashboard-hero-outer", css)
        self.assertIn("[data-theme=\"light\"] .dashboard-box-outer", css)
        self.assertIn(".risk-box-outer", css)
        self.assertIn(".submissoes-box-outer", css)
        self.assertIn(".table-box-inner.table-card", css)

        # Classes dedicadas
        self.assertIn(".dashboard-hero-card", css)
        self.assertIn(".dashboard-box-inner", css)

        # Regras de alto contraste em modo claro para os cards dentro da moldura
        self.assertIn('[data-theme="light"] .dashboard-box-inner .metric-card-modern', css)
        self.assertIn('[data-theme="light"] .dashboard-box-inner .chart-card', css)
        self.assertIn('[data-theme="light"] .dashboard-box-inner .metric-value-modern', css)
        self.assertIn('[data-theme="light"] .dashboard-box-inner .metric-title-modern', css)
        self.assertIn('[data-theme="light"] .dashboard-box-inner .chart-title', css)

    def test_03_js_cores_graficos_alto_contraste(self):
        with open("static/js/dashboard.js", "r", encoding="utf-8") as f:
            js = f.read()

        # Cores nítidas e escuras no modo claro (#0f172a, #334155)
        self.assertIn('textColor: isLight ? "#0f172a" : "#cbd5e1"', js)
        self.assertIn('mutedTextColor: isLight ? "#334155" : "#94a3b8"', js)

        with open("templates/aluno_dashboard.html", "r", encoding="utf-8") as f:
            aluno_html = f.read()

        self.assertIn("textColor: isLight ? '#0f172a' : '#cbd5e1'", aluno_html)
        self.assertIn("mutedColor: isLight ? '#334155' : '#94a3b8'", aluno_html)

if __name__ == '__main__':
    unittest.main()
