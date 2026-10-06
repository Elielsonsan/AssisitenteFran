# -*- coding: utf-8 -*-
"""
test_guia_fle.py - Testes Automatizados para a Página Completa /guia-fle
Verifica rotas, dados de conjugação, barra lateral, navbar e API de verbos.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from guia_fle_data import VERBOS_CONJUGADOS, TEMAS_GUIA_FLE


class TestGuiaFLE(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_guia_fle_public_access(self):
        """Verifica se /guia-fle é acessível publicamente (200 OK)."""
        res = self.client.get("/guia-fle")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Título e Header
        self.assertIn("Guia Gramatical & Mémento FLE", html)
        self.assertIn("Référence Pédagogique FLE", html)

        # Barra Lateral com 10 Temas
        self.assertIn('id="guiaSidebar"', html)
        self.assertIn("Maison d'Être", html)
        self.assertIn("Conjugação", html)
        self.assertIn("Partitivos", html)
        self.assertIn("Falsos Cognatos", html)
        self.assertIn("Pronomes Y & EN", html)
        self.assertIn("COD & COI", html)
        self.assertIn("Negação", html)
        self.assertIn("Preposições", html)
        self.assertIn("Cortesia", html)
        self.assertIn("Subjonctif", html)

        # Verbos da Maison d'Être presentes
        for v_id in ["aller", "venir", "arriver", "partir", "entrer", "sortir", "monter", "descendre", "naitre", "mourir", "rester", "tomber", "retourner", "passer"]:
            v = VERBOS_CONJUGADOS[v_id]
            self.assertIn(f"abrirConjugadorVerbo('{v_id}')", html)
            self.assertIn(v["verbo"], html)

        # Verbos essenciais
        for v_id in ["etre", "avoir", "faire", "prendre", "pouvoir", "vouloir", "devoir", "savoir", "dire", "voir"]:
            self.assertIn(f"abrirConjugadorVerbo('{v_id}')", html)

        # Modal de conjugação e abas de tempos verbais
        self.assertIn('id="modalConjugador"', html)
        self.assertIn('id="tabBtn-present"', html)
        self.assertIn('id="tabBtn-passe_compose"', html)
        self.assertIn('id="tabBtn-imparfait"', html)
        self.assertIn('id="tabBtn-futur_simple"', html)
        self.assertIn('id="tabBtn-conditionnel"', html)
        self.assertIn('id="tabBtn-imperatif"', html)

        # JSON embutido com todos os verbos
        self.assertIn('id="dadosVerbosJSON"', html)

    def test_guia_fle_aluno_logado(self):
        """Verifica se /guia-fle renderiza perfeitamente com sessão de aluno."""
        with self.client.session_transaction() as sess:
            sess["aluno_id"] = 1
            sess["aluno_nome"] = "Lucas Silva"
            sess["nivel_cefr"] = "B1"

        res = self.client.get("/guia-fle")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Guia Gramatical & Mémento FLE", html)
        self.assertIn('href="/guia-fle"', html)

    def test_guia_fle_professor_logado(self):
        """Verifica se /guia-fle renderiza perfeitamente com sessão de professor."""
        with self.client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["prof_nome"] = "Prof. Dupont"

        res = self.client.get("/guia-fle")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Guia Gramatical & Mémento FLE", html)

    def test_api_verbo_valido(self):
        """Testa API de busca de conjugação de verbo."""
        res = self.client.get("/api/guia-fle/verbo/aller")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["verbo"]["verbo"], "Aller")
        self.assertEqual(data["verbo"]["auxiliaire"], "Être")
        self.assertIn("vais", data["verbo"]["present"]["je"])
        self.assertIn("suis allé(e)", data["verbo"]["passe_compose"]["je"])
        self.assertTrue(len(data["verbo"]["exemplos"]) >= 2)

    def test_api_verbo_inexistente(self):
        """Testa API com verbo inexistente (esperado 404)."""
        res = self.client.get("/api/guia-fle/verbo/verbo_ficticio_123")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["status"], "erro")

    def test_navbar_links_and_no_modal_in_base(self):
        """Garante que base.html aponta para /guia-fle e não tem modal embutido."""
        res = self.client.get("/")
        # O base deve ter o link para /guia-fle
        with open("templates/base.html", "r", encoding="utf-8") as f:
            base_html = f.read()
        self.assertIn('href="/guia-fle"', base_html)
        self.assertNotIn('id="mementoModal"', base_html)

    def test_aluno_dashboard_sidebar_link(self):
        """Garante que a barra lateral de aluno_dashboard aponta para /guia-fle."""
        with open("templates/aluno_dashboard.html", "r", encoding="utf-8") as f:
            dash_html = f.read()
        self.assertIn('href="/guia-fle"', dash_html)


if __name__ == "__main__":
    unittest.main()
