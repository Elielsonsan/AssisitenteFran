import unittest
import re

class TestProvaCssFix(unittest.TestCase):
    def test_css_prova_progress_container(self):
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Encontrar a declaração de .prova-progress-container { ... }
        match = re.search(r'\.prova-progress-container\s*\{([^}]+)\}', css)
        self.assertIsNotNone(match, ".prova-progress-container not found in style.css")
        body = match.group(1)

        # Deve conter position: sticky
        self.assertIn("position: sticky", body)
        self.assertIn("top: 76px", body)
        # NÃO deve conter position: relative (que era o bug que deslocava a barra para baixo da questão)
        self.assertNotIn("position: relative", body)

        # Light theme styling
        self.assertIn('[data-theme="light"] .prova-progress-container', css)
        self.assertIn('[data-theme="light"] .question-pill-btn', css)
        self.assertIn('.card-questao-box', css)
        self.assertIn('[data-theme="light"] .card-questao-box', css)
        self.assertIn('scroll-margin-top', css)

    def test_template_aluno_prova_no_dark_inline_style(self):
        with open("templates/aluno_prova.html", "r", encoding="utf-8") as f:
            html = f.read()

        # O card de questão deve ter a classe card-questao-box sem inline dark styling
        self.assertIn('class="card-questao-box"', html)
        self.assertNotIn('background: rgba(255,255,255,0.03)', html)
        self.assertNotIn('border: 1px solid rgba(255,255,255,0.08)', html)

if __name__ == '__main__':
    unittest.main()
