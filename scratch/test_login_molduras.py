import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from app import app

class TestLoginMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_01_login_page_renders_with_translucent_molduras(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # 1. Header Hero Card com moldura translúcida
        self.assertIn('id="authHeroCard"', html)
        self.assertIn('hero-card-outer card-moldura-outer auth-hero-outer auth-hero-card', html)
        self.assertIn('class="hero-card-inner auth-hero-inner"', html)
        self.assertIn('Bem-vindo ao Assistente Fran', html)
        self.assertIn('Portail Étudiant • Français FLE', html)

        # 2. Card de Login com Moldura Translúcida (Borda de Vidro Externa)
        self.assertIn('id="authBoxOuter"', html)
        self.assertIn('hero-card-outer card-moldura-outer auth-box-outer', html)
        self.assertIn('id="authCard"', html)
        self.assertIn('auth-card auth-box-inner', html)

        # 3. Elementos do Formulário de Acesso e Contas de Demonstração
        self.assertIn('name="tipo_acesso"', html)
        self.assertIn('name="matricula"', html)
        self.assertIn('name="usuario"', html)
        self.assertIn('name="senha"', html)
        self.assertIn('Lucas Silva', html)
        self.assertIn('Camila Rodrigues', html)
        self.assertIn('Prof. Admin', html)
        self.assertIn('202601', html)
        self.assertIn('123456', html)

        print("[OK] Teste 01: Login page possui Header Hero Card e Moldura Glassmorphic Translúcida no Card de Connexion.")

    def test_02_css_auth_molduras_and_layout(self):
        response = self.client.get('/static/css/style.css?v=20260923_v4')
        self.assertEqual(response.status_code, 200)
        css = response.get_data(as_text=True)

        # Verificação das regras de moldura translúcida
        self.assertIn('.auth-box-outer', css)
        self.assertIn('.auth-hero-outer', css)
        self.assertIn('.auth-box-inner.auth-card', css)
        self.assertIn('border-radius: 24px !important;', css)
        self.assertIn('padding: 12px 14px !important;', css)

        print("[OK] Teste 02: CSS contém todas as regras da moldura translúcida para a tela de autenticação.")

    def test_03_login_flow_preservation(self):
        # Test student login
        resp_aluno = self.client.post('/login', data={'tipo_acesso': 'aluno', 'matricula': '202601', 'senha': '123456'}, follow_redirects=False)
        self.assertEqual(resp_aluno.status_code, 302)
        self.assertEqual(resp_aluno.headers['Location'], '/')

        # Logout before testing teacher login
        self.client.get('/logout')

        # Test teacher login
        resp_prof = self.client.post('/login', data={'tipo_acesso': 'professor', 'usuario': 'admin', 'senha': 'admin'}, follow_redirects=False)
        self.assertEqual(resp_prof.status_code, 302)
        self.assertEqual(resp_prof.headers['Location'], '/dashboard')

        print("[OK] Teste 03: Fluxos de autenticação de aluno e professor preservados integralmente.")

if __name__ == '__main__':
    unittest.main()
