import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json

from app import app, get_db

def test_gerador_questoes_variados():
    with app.test_client() as client:
        # Autentica como professor
        with client.session_transaction() as sess:
            sess["prof_id"] = 1
            sess["usuario"] = "prof_teste"

        # 1. Teste Múltipla Escolha com 5 perguntas
        res1 = client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Passé Composé",
            "nivel": "A2",
            "tipo": "Exercícios",
            "quantidade": 5,
            "formato_questoes": "multipla_escolha"
        })
        assert res1.status_code == 200
        d1 = res1.get_json()
        print("1. Qtd Múltipla Escolha retornada:", len(d1["questoes"]))
        assert len(d1["questoes"]) == 5
        soma1 = sum(q.get("pontuacao_maxima", 0) for q in d1["questoes"])
        print(f"   Soma de pontos (deve ser 10.0): {soma1:.1f}")
        assert abs(soma1 - 10.0) < 0.1

        # 2. Teste Verdadeiro ou Falso com 3 perguntas
        res2 = client.post("/api/gerar_prova_completa_ia", json={
            "tema": "L'Accord du Participe Passé",
            "nivel": "B1",
            "tipo": "Teste",
            "quantidade": 3,
            "formato_questoes": "verdadeiro_falso"
        })
        assert res2.status_code == 200
        d2 = res2.get_json()
        print("2. Qtd Verdadeiro/Falso retornada:", len(d2["questoes"]))
        assert len(d2["questoes"]) == 3
        soma2 = sum(q.get("pontuacao_maxima", 0) for q in d2["questoes"])
        print(f"   Soma de pontos (deve ser 10.0): {soma2:.1f}")
        assert abs(soma2 - 10.0) < 0.1

        # 3. Teste Aleatório / Misto com 4 perguntas
        res3 = client.post("/api/gerar_prova_completa_ia", json={
            "tema": "Les Pronoms Y et EN",
            "nivel": "A2",
            "tipo": "Prova",
            "quantidade": 4,
            "formato_questoes": "aleatorio"
        })
        assert res3.status_code == 200
        d3 = res3.get_json()
        print("3. Qtd Aleatório / Misto retornada:", len(d3["questoes"]))
        assert len(d3["questoes"]) == 4
        soma3 = sum(q.get("pontuacao_maxima", 0) for q in d3["questoes"])
        print(f"   Soma de pontos (deve ser 10.0): {soma3:.1f}")
        assert abs(soma3 - 10.0) < 0.1

        # 4. Teste Salvar Avaliação com Pontuação Customizada
        questoes_custom = [
            {"tipo_questao": "multipla_escolha", "enunciado": "Choisissez la bonne réponse (a) ou (b)", "texto_referencia": "", "pontuacao_maxima": 3.0},
            {"tipo_questao": "verdadeiro_falso", "enunciado": "Vrai ou Faux : le français est facile", "texto_referencia": "", "pontuacao_maxima": 3.0},
            {"tipo_questao": "complete", "enunciado": "Complétez : Je ___ étudiant.", "texto_referencia": "", "pontuacao_maxima": 4.0}
        ]
        res4 = client.post("/api/salvar_avaliacao", json={
            "titulo": "Prova Teste Automatizado",
            "tipo": "Prova",
            "turma_id": 1,
            "data_limite": "2026-12-31 23:59:00",
            "questoes": questoes_custom
        })
        assert res4.status_code == 200
        d4 = res4.get_json()
        av_id = d4.get("avaliacao_id")
        assert av_id is not None
        print("4. Avaliação salva com ID:", av_id)

        # Verifica no banco de dados SQLite se as pontuações e tipos foram persistidos
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT tipo_questao, pontuacao_maxima FROM prova_questoes WHERE avaliacao_id = ?", (av_id,))
        rows = cursor.fetchall()
        print("   Questões no banco:", [dict(r) for r in rows])
        assert len(rows) == 3
        assert rows[0]["pontuacao_maxima"] == 3.0
        assert rows[1]["pontuacao_maxima"] == 3.0
        assert rows[2]["pontuacao_maxima"] == 4.0
        assert rows[0]["tipo_questao"] == "multipla_escolha"
        assert rows[1]["tipo_questao"] == "verdadeiro_falso"
        assert rows[2]["tipo_questao"] == "complete"

        # Limpeza do teste
        cursor.execute("DELETE FROM prova_questoes WHERE avaliacao_id = ?", (av_id,))
        cursor.execute("DELETE FROM avaliacoes WHERE id = ?", (av_id,))
        conn.commit()
        conn.close()
        print("   Limpeza de teste concluída.")

def test_render_templates():
    with app.test_request_context():
        from flask import render_template
        # Render professor_avaliacoes
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM turmas LIMIT 5")
        turmas = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM temas LIMIT 5")
        temas = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT a.*, t.nome as turma_nome FROM avaliacoes a JOIN turmas t ON a.turma_id = t.id ORDER BY a.id DESC LIMIT 5")
        avaliacoes = [dict(r) for r in cursor.fetchall()]
        conn.close()

        res_prof = render_template("professor_avaliacoes.html", turmas=turmas, temas=temas, avaliacoes=avaliacoes, active_page="prof_avaliacoes")
        assert "na_quantidade" in res_prof
        assert "na_formato_questoes" in res_prof
        assert "barraPontuacaoAvaliacao" in res_prof
        assert "Distribuir 10.0 pts igualmente" in res_prof
        assert "🎲 Aleatório / Misto" in res_prof
        print("Template professor_avaliacoes.html renderizado com sucesso com todos os novos campos!")

        # Render aluno_prova
        res_aluno = render_template("aluno_prova.html", avaliacao={"id": 999, "titulo": "Simulado FLE", "tipo": "Prova"}, questoes=[
            {"id": 1, "tipo_questao": "multipla_escolha", "enunciado": "Choisissez (a) ou (b)", "pontuacao_maxima": 5.0},
            {"id": 2, "tipo_questao": "verdadeiro_falso", "enunciado": "Vrai ou Faux", "pontuacao_maxima": 5.0}
        ], active_page="aluno_atividades")
        assert "Valor Total:" in res_aluno
        assert "10.0 pts" in res_aluno
        assert "Vrai (Verdadeiro)" in res_aluno
        assert "Alternativa:" in res_aluno
        print("Template aluno_prova.html renderizado com sucesso com botões interativos e valor total!")

if __name__ == "__main__":
    print("=== INICIANDO TESTES DOS NOVOS RECURSOS DE AVALIAÇÃO ===")
    test_gerador_questoes_variados()
    test_render_templates()
    print("=== TODOS OS TESTES PASSARAM COM SUCESSO! ===")
