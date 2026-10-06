import unittest
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestAlunoPortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cria uma avaliação de teste com questões para testar a tela de prova
        conn = sqlite3.connect("educacao_ia.db")
        c = conn.cursor()
        
        # Garante que temos turma 1
        c.execute("INSERT OR IGNORE INTO turmas (id, nome) VALUES (1, 'Turma Alpha FLE')")
        
        # Insere avaliação de teste
        c.execute("""
            INSERT INTO avaliacoes (id, titulo, tipo, turma_id, data_limite)
            VALUES (9999, 'Avaliação Teste Portal Aluno', 'Exercícios', 1, '2026-12-31 23:59:00')
        """)
        
        # Insere questões
        c.execute("""
            INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
            VALUES (9999, 'exercicio', 'Conjuguez le verbe être au présent: Nous ___ à Paris.', '', 5.0)
        """)
        c.execute("""
            INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, texto_referencia, pontuacao_maxima)
            VALUES (9999, 'ditado', 'Écrivez la phrase entendue.', 'Bonjour tout le monde', 5.0)
        """)
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        conn = sqlite3.connect("educacao_ia.db")
        c = conn.cursor()
        c.execute("DELETE FROM prova_questoes WHERE avaliacao_id = 9999")
        c.execute("DELETE FROM avaliacoes WHERE id = 9999")
        conn.commit()
        conn.close()

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Jean Dupont"
            sess["turma_id"] = 1
            sess["nivel_cefr"] = "A2"

    def test_01_aluno_dashboard(self):
        resp = self.client.get("/aluno/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Container com padding correto para sidebar
        self.assertIn('class="page-container dashboard-page student-page"', html)

        # Barra lateral flutuante
        self.assertIn('class="dash-sidebar no-print" id="dashSidebar"', html)
        self.assertIn('/aluno/atividades', html)
        self.assertIn('Prática Livre', html)
        self.assertIn('scrollToSection(\'secaoNivelXP\')', html)
        self.assertIn('scrollToSection(\'secaoConquistas\')', html)
        self.assertIn('/forum', html)
        self.assertIn('/aluno/perfil', html)

        # Cards e gráficos
        self.assertIn('id="desempenhoChart"', html)
        self.assertIn('id="participacaoChart"', html)
        self.assertIn('id="secaoNivelXP"', html)
        self.assertIn('id="secaoConquistas"', html)
        self.assertIn('Correio do Tutor', html)

    def test_02_aluno_atividades(self):
        resp = self.client.get("/aluno/atividades")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Layout e Barra lateral de filtros
        self.assertIn('class="page-container dashboard-page student-page"', html)
        self.assertIn('class="dash-sidebar no-print" id="dashSidebar"', html)
        self.assertIn('id="popoverFiltros"', html)
        self.assertIn('id="btnToggleFiltrosPopover"', html)

        # Atalhos rápidos de 1 clique
        self.assertIn('id="btnAtalhoPendentes"', html)
        self.assertIn('id="btnAtalhoConcluidas"', html)
        self.assertIn('id="btnAtalhoTestes"', html)
        self.assertIn('id="btnAtalhoExercicios"', html)
        self.assertIn('id="btnAtalhoProvas"', html)

        # Banner de filtro ativo
        self.assertIn('id="bannerFiltroAtivoAtividades"', html)
        self.assertIn('id="bannerTextoFiltro"', html)

        # Cards com atributos de filtragem
        self.assertIn('data-tipo=', html)
        self.assertIn('data-status=', html)
        self.assertIn('Avaliação Teste Portal Aluno', html)
        self.assertIn('/aluno/prova/9999', html)

    def test_03_aluno_prova(self):
        resp = self.client.get("/aluno/prova/9999")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Cronômetro regressivo
        self.assertIn('id="timerCard"', html)
        self.assertIn('id="timerDisplay"', html)

        # Barra de progresso da prova
        self.assertIn('id="barraProgressoProva"', html)
        self.assertIn('id="provaProgressFill"', html)
        self.assertIn('id="progressoContador"', html)
        self.assertIn('id="progressoPorcentagem"', html)

        # Pílulas do navegador de questões
        self.assertIn('id="pillsNavegacaoRow"', html)
        self.assertIn('id="pillQuestao_', html)

        # Cards de questões com botões de síntese e formulários
        self.assertIn('id="cardQuestao_', html)
        self.assertIn('ouvirTexto(', html)
        self.assertIn('aoDigitarResposta(', html)

        # Modal de confirmação para envio
        self.assertIn('id="modalConfirmacaoEnvio"', html)
        self.assertIn('id="btnFinalizarProva"', html)

if __name__ == '__main__':
    unittest.main()
