import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from app import app

class TestHomeHeroCard(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_home_page_layout(self):
        with self.client.session_transaction() as sess:
            sess['aluno_id'] = 1
            sess['aluno_nome'] = 'Lucas Silva'
            sess['tipo_usuario'] = 'aluno'
            sess['turma_id'] = 1
            sess['turma_nome'] = '1º Ano A (Iniciante A1)'
            sess['matricula'] = '202601'
            sess['nivel_cefr'] = 'A1'

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # 1. Header Hero Card
        self.assertIn('id="homeHeroCard"', html)
        self.assertIn('class="hero-card-outer home-hero-card"', html)
        self.assertIn('class="hero-card-inner"', html)
        self.assertIn('Pratique seu Francês com Feedback Inteligente', html)
        self.assertIn('Tuteur Pédagogique Virtuel', html)

        # 2. Form Box com Moldura Hero Card (Primeira Imagem)
        self.assertIn('id="formBoxOuter"', html)
        self.assertIn('class="hero-card-outer form-box-outer"', html)
        self.assertIn('class="form-card form-box-inner"', html)

        # 3. Quadro de Bonjour
        self.assertIn('class="student-profile-bar"', html)
        self.assertIn('Lucas Silva', html)

        # 4. Pílula de Desafios (Segunda Imagem) inserida abaixo do quadro de bonjour
        self.assertIn('class="examples-container form-examples-bar"', html)
        self.assertIn('id="btnGerarDesafio"', html)
        self.assertIn('id="btnGerarNivel"', html)

        # Verificar ordem: student-profile-bar deve vir antes de examples-container
        pos_bonjour = html.find('class="student-profile-bar"')
        pos_examples = html.find('class="examples-container form-examples-bar"')
        pos_form_actions = html.find('class="form-actions"')

        self.assertTrue(pos_bonjour > 0, "Quadro de bonjour não encontrado")
        self.assertTrue(pos_examples > 0, "Quadro de exemplos/desafios não encontrado")
        self.assertTrue(pos_bonjour < pos_examples, "Quadro de exemplos deve estar ABAIXO do quadro de bonjour")
        self.assertTrue(pos_examples < pos_form_actions, "Quadro de exemplos deve estar antes das ações do formulário")

        print("SUCCESS: Moldura no quadro principal e barra de desafios abaixo do Bonjour validados 100%!")

if __name__ == '__main__':
    unittest.main()
