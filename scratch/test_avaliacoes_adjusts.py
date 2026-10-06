import unittest
import json
import sqlite3
from app import app

class TestAvaliacoesAdjusts(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Login as professor (session mock)
        with self.client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["professor_nome"] = "Professeur Test"
            sess["is_professor"] = True

    def test_01_gerar_prova_ia_exercicios(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Le Passé Composé",
            "nivel": "A2",
            "tipo": "Exercícios",
            "quantidade": 3
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        self.assertIn("questoes", data)
        self.assertGreaterEqual(len(data["questoes"]), 1)
        self.assertEqual(data["questoes"][0]["tipo_questao"], "exercicio")

    def test_02_gerar_prova_ia_teste(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Les Pronoms Relatifs",
            "nivel": "B1",
            "tipo": "Teste",
            "quantidade": 3
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        self.assertIn("questoes", data)
        self.assertEqual(data["questoes"][0]["tipo_questao"], "teste")

    def test_03_gerar_prova_ia_prova_multimodal(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Le Subjonctif Présent",
            "nivel": "B2",
            "tipo": "Prova"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        self.assertIn("questoes", data)
        tipos = [q["tipo_questao"] for q in data["questoes"]]
        self.assertIn("conjugacao", tipos)
        self.assertIn("ditado", tipos)

    def test_04_salvar_avaliacao_exercicios_e_visualizacao_aluno(self):
        # 1. Professor salva uma avaliação do tipo Exercícios
        payload = {
            "titulo": "Exercícios Teste Automatizado: Pronoms",
            "tipo": "Exercícios",
            "turma_id": 14,
            "data_limite": "2026-12-31 23:59:00",
            "questoes": [
                {
                    "tipo_questao": "exercicio",
                    "enunciado": "Complétez avec le pronom COD approprié: 'Tu regardes la télévision? Oui, je ... regarde.'",
                    "texto_referencia": "",
                    "pontuacao_maxima": 5.0
                },
                {
                    "tipo_questao": "exercicio",
                    "enunciado": "Répondez à la question: 'Avez-vous compris la leçon?'",
                    "texto_referencia": "",
                    "pontuacao_maxima": 5.0
                }
            ]
        }
        resp = self.client.post("/api/salvar_avaliacao", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        avaliacao_id = data["avaliacao_id"]
        self.assertIsNotNone(avaliacao_id)

        # 2. Login como aluno da turma 14
        client_aluno = app.test_client()
        with client_aluno.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["turma_id"] = 14
            sess["nivel_cefr"] = "A2"

        # 3. Aluno acessa a lista de atividades
        resp_ativ = client_aluno.get("/aluno/atividades")
        self.assertEqual(resp_ativ.status_code, 200)
        html_ativ = resp_ativ.get_data(as_text=True)
        self.assertIn("Exercícios Teste Automatizado: Pronoms", html_ativ)
        self.assertIn(f"/aluno/prova/{avaliacao_id}", html_ativ)

        # 4. Aluno abre o formulário da atividade
        resp_prova = client_aluno.get(f"/aluno/prova/{avaliacao_id}")
        self.assertEqual(resp_prova.status_code, 200)
        html_prova = resp_prova.get_data(as_text=True)
        self.assertIn("Complétez avec le pronom COD", html_prova)
        self.assertIn("Formulário de Resposta do Aluno:", html_prova)
        self.assertIn("questao_", html_prova)
        self.assertIn("Finalizar e Enviar Exercícios", html_prova)

        # 5. Limpeza no banco
        conn = sqlite3.connect("educacao_ia.db")
        c = conn.cursor()
        c.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (avaliacao_id,))
        c.execute("DELETE FROM avaliacoes WHERE id = ?", (avaliacao_id,))
        conn.commit()
        conn.close()

    def test_05_professor_avaliacoes_template_sidebar_e_modais(self):
        resp = self.client.get("/professor/avaliacoes")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Barra lateral e popover de filtros
        self.assertIn('class="dash-sidebar no-print"', html)
        self.assertIn('id="popoverFiltros"', html)
        self.assertIn('id="btnToggleFiltrosPopover"', html)
        self.assertIn('id="btnNovaAvaliacaoSidebar"', html)
        self.assertIn('id="btnCopilotoSidebar"', html)

        # Modal Nova Avaliação com os 3 tipos
        self.assertIn('id="modalNovaAvaliacao"', html)
        self.assertIn('id="cardTipoTeste"', html)
        self.assertIn('id="cardTipoExercicios"', html)
        self.assertIn('id="cardTipoProva"', html)

        # Copiloto com botão de publicar para a turma
        self.assertIn('id="btnPublicarTurmaExercicios"', html)
        self.assertIn('id="copiloto_turma"', html)

        # Tabela e Paginação
        self.assertIn('class="dash-table-zebra"', html)
        self.assertIn('id="paginacaoAvaliacoes"', html)
        self.assertIn('id="seletorQtdLinhas"', html)

if __name__ == '__main__':
    unittest.main()
