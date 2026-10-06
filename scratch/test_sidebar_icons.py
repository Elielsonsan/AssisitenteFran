import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestSidebarIcons(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["turma_id"] = 1
            sess["nivel_cefr"] = "A1"

    def test_sidebar_icons_present(self):
        resp = self.client.get("/aluno/atividades")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Verifica que os ícones substituíram os antigos spans com pontos
        self.assertNotIn("box-shadow: 0 0 6px rgba(245, 158, 11, 0.8)", html)
        self.assertNotIn("box-shadow: 0 0 6px rgba(16, 185, 129, 0.8)", html)

        # Verifica a presença dos ícones SVG estilizados para cada atalho
        self.assertIn("sidebar-icon-amber", html)
        self.assertIn("sidebar-icon-green", html)
        self.assertIn("sidebar-icon-blue", html)
        self.assertIn("sidebar-icon-purple", html)
        self.assertIn("sidebar-icon-red", html)

    def test_css_sidebar_icons(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".sidebar-icon-amber", css)
        self.assertIn(".sidebar-icon-green", css)
        self.assertIn(".sidebar-icon-blue", css)
        self.assertIn(".sidebar-icon-purple", css)
        self.assertIn(".sidebar-icon-red", css)
        self.assertIn('[data-theme="light"] .sidebar-icon-amber', css)

if __name__ == '__main__':
    unittest.main()
