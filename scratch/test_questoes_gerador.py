import unittest
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

class TestQuestoesGerador(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["professor_nome"] = "Professeur Test"
            sess["is_professor"] = True

    def test_gerar_exercicios_possui_frase_real(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Le Passé Composé",
            "nivel": "A2",
            "tipo": "Exercícios",
            "quantidade": 4
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        for q in data["questoes"]:
            enunciado = q["enunciado"]
            # Cada questão de exercício DEVE conter uma frase real (com aspas ou lacuna)
            tem_frase = ('"' in enunciado) or ("'" in enunciado) or ('___' in enunciado)
            self.assertTrue(tem_frase, f"Exercício sem frase para responder: {enunciado}")
            self.assertNotIn("Exercício de fallback 1", enunciado)

    def test_gerar_teste_possui_frase_e_opcoes(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Les Articles Définis et Indéfinis",
            "nivel": "A1",
            "tipo": "Teste",
            "quantidade": 4
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        for q in data["questoes"]:
            enunciado = q["enunciado"]
            tem_frase_ou_opcao = ('"' in enunciado) or ('___' in enunciado) or ('(' in enunciado and ')' in enunciado)
            self.assertTrue(tem_frase_ou_opcao, f"Teste sem frase/opções: {enunciado}")

    def test_gerar_prova_possui_frases_completas(self):
        resp = self.client.post("/api/gerar_prova_completa_ia", json={
            "tema": "La Négation Simple",
            "nivel": "A2",
            "tipo": "Prova"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        for q in data["questoes"]:
            t = q["tipo_questao"]
            if t == "traducao":
                # Tradução deve ter a frase em português para traduzir em texto_referencia ou no enunciado
                ref = q.get("texto_referencia", "").strip()
                enunciado = q["enunciado"]
                self.assertTrue(len(ref) > 5 or ('"' in enunciado), f"Tradução sem frase: {q}")
                self.assertNotEqual(ref, "La phrase")
                self.assertNotEqual(ref, "Tradução contextual")
            elif t == "ditado":
                # Ditado deve ter a frase em francês para a síntese de voz falar
                ref = q.get("texto_referencia", "").strip()
                self.assertTrue(len(ref) > 8, f"Ditado sem áudio de referência: {q}")
            elif t == "leitura_oral":
                # Leitura oral deve ter a frase em francês para o aluno ler
                ref = q.get("texto_referencia", "").strip()
                self.assertTrue(len(ref) > 8, f"Leitura oral sem texto: {q}")
            elif t == "conjugacao":
                enunciado = q["enunciado"]
                tem_verbo_ou_frase = ('___' in enunciado) or ('"' in enunciado) or ('(' in enunciado)
                self.assertTrue(tem_verbo_ou_frase, f"Conjugação sem frase ou verbo especificado: {enunciado}")

    def test_copiloto_gerar_exercicios(self):
        resp = self.client.post("/api/copiloto/gerar_exercicio", json={
            "tema_id": 1,
            "nivel": "A1",
            "quantidade": 3
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "sucesso")
        exercicios = data["exercicios"]
        self.assertGreaterEqual(len(exercicios), 1)
        for ex in exercicios:
            self.assertNotIn("fallback", ex.lower())
            self.assertTrue(('___' in ex) or ('"' in ex) or ("'" in ex) or ('(' in ex), f"Copiloto com exercício sem frase: {ex}")

if __name__ == '__main__':
    unittest.main()
