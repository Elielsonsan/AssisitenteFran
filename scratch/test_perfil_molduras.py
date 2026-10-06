import sys
import os
import unittest
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

class TestPerfilMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_perfil_aluno_hero_card_e_moldura_unificada(self):
        with self.client.session_transaction() as sess:
            sess['aluno_id'] = 1
            sess['aluno_nome'] = 'Lucas Silva'
            sess['tipo_usuario'] = 'aluno'
            sess['turma_id'] = 14

        res = self.client.get('/aluno/perfil')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Verificar Hero Card
        self.assertIn('id="perfilHeroCard"', html)
        self.assertIn('perfil-hero-outer', html)
        self.assertIn('perfil-hero-inner', html)
        self.assertIn('Perfil &amp; Caixa de Mensagens', html)
        self.assertIn('FLE - Mon Profil Académique', html)

        # 2. Verificar Quadro Unificado (Moldura única envolvendo info e mensagens)
        self.assertIn('id="perfilBoxOuter"', html)
        self.assertIn('perfil-box-outer', html)
        self.assertIn('perfil-box-inner', html)
        self.assertIn('card-moldura-outer', html)
        self.assertIn('perfil-split-grid', html)
        self.assertIn('perfil-info-card', html)
        self.assertIn('perfil-mensagens-card', html)

        # 3. Verificar que o split grid está aninhado dentro do box unificado
        match_box = re.search(
            r'id="perfilBoxOuter"[^>]*>.*?class="[^"]*perfil-box-inner[^"]*".*?class="perfil-split-grid".*?class="[^"]*perfil-info-card[^"]*".*?class="[^"]*perfil-mensagens-card[^"]*"',
            html,
            re.DOTALL
        )
        self.assertIsNotNone(match_box, "A hierarquia perfilBoxOuter > perfil-box-inner > perfil-split-grid > info e mensagens não foi respeitada")

        # 4. Verificar dados acadêmicos e logout
        self.assertIn('Lucas Silva', html)
        self.assertIn('Matrícula:', html)
        self.assertIn('btn-perfil-logout', html)
        self.assertIn('/logout', html)

    def test_css_perfil_molduras(self):
        css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        self.assertIn('.perfil-hero-outer', css)
        self.assertIn('.perfil-hero-inner', css)
        self.assertIn('.perfil-box-outer', css)
        self.assertIn('.perfil-box-inner', css)
        self.assertIn('.perfil-split-grid', css)
        self.assertIn('.perfil-card-box', css)
        self.assertIn('.btn-perfil-logout', css)
        self.assertIn('[data-theme="light"] .perfil-hero-outer', css)
        self.assertIn('[data-theme="light"] .perfil-box-outer', css)
        self.assertIn('[data-theme="light"] .perfil-card-box', css)
        self.assertIn('[data-theme="light"] .btn-perfil-logout', css)

if __name__ == '__main__':
    unittest.main()
