import sys
import os
import unittest
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

class TestForumMolduras(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_forum_aluno_hero_card_e_moldura_unificada(self):
        with self.client.session_transaction() as sess:
            sess['aluno_id'] = 1
            sess['aluno_nome'] = 'Lucas Silva'
            sess['tipo_usuario'] = 'aluno'
            sess['turma_id'] = 14

        res = self.client.get('/forum')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Verificar Hero Card
        self.assertIn('id="forumHeroCard"', html)
        self.assertIn('forum-hero-outer', html)
        self.assertIn('forum-hero-inner', html)
        self.assertIn('Fórum de Discussão Socrático', html)
        self.assertIn("FLE - Espace d'Échange Socratique", html)

        # 2. Verificar Quadro Unificado (Moldura única envolvendo filtros e tópicos)
        self.assertIn('id="forumBoxOuter"', html)
        self.assertIn('forum-box-outer', html)
        self.assertIn('forum-box-inner', html)
        self.assertIn('card-moldura-outer', html)

        # 3. Verificar que #bannerFiltroAtivoForum e #gridTopicosForum estão aninhados dentro do box unificado
        match_box = re.search(
            r'id="forumBoxOuter"[^>]*>.*?class="[^"]*forum-box-inner[^"]*".*?id="bannerFiltroAtivoForum".*?id="gridTopicosForum"',
            html,
            re.DOTALL
        )
        self.assertIsNotNone(match_box, "A hierarquia forumBoxOuter > forum-box-inner > bannerFiltroAtivoForum > gridTopicosForum não foi respeitada")

    def test_forum_professor_hero_card_e_botao(self):
        with self.client.session_transaction() as sess:
            sess['prof_id'] = 1
            sess['prof_nome'] = 'Professeur Test'
            sess['tipo_usuario'] = 'professor'

        res = self.client.get('/forum')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="forumHeroCard"', html)
        self.assertIn('id="forumBoxOuter"', html)
        self.assertIn('abrirModalCriarTopico()', html)

    def test_forum_topico_detalhe_hero_card(self):
        with self.client.session_transaction() as sess:
            sess['aluno_id'] = 1
            sess['aluno_nome'] = 'Lucas Silva'
            sess['tipo_usuario'] = 'aluno'
            sess['turma_id'] = 14

        # Busca um tópico geral ou da turma 14 existente com app_context
        with app.app_context():
            from app import get_db
            db = get_db()
            t = db.execute("SELECT id FROM forum_topicos WHERE turma_id IS NULL OR turma_id = 14 LIMIT 1").fetchone()

        if t:
            res = self.client.get(f'/forum/topico/{t["id"]}')
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)

            self.assertIn('id="topicoHeroOuter"', html)
            self.assertIn('topic-detail-hero-outer', html)
            self.assertIn('topic-detail-hero-inner', html)
            self.assertIn('card-moldura-outer', html)

    def test_css_forum_molduras(self):
        css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        self.assertIn('.forum-hero-outer', css)
        self.assertIn('.forum-hero-inner', css)
        self.assertIn('.forum-box-outer', css)
        self.assertIn('.forum-box-inner', css)
        self.assertIn('[data-theme="light"] .forum-hero-outer', css)
        self.assertIn('[data-theme="light"] .forum-box-outer', css)
        self.assertIn('[data-theme="light"] .forum-box-inner .forum-card', css)

if __name__ == '__main__':
    unittest.main()
