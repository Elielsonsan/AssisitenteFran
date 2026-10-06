import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import eh_questao_valida, gerar_questoes_pedagogicas_completas

def run_cleanup():
    conn = sqlite3.connect('educacao_ia.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pq.id as questao_id, pq.avaliacao_id, pq.tipo_questao, pq.enunciado, pq.texto_referencia,
               a.titulo, a.tipo
        FROM prova_questoes pq
        JOIN avaliacoes a ON pq.avaliacao_id = a.id
    """)
    rows = cursor.fetchall()

    corrigidas = 0
    # Group by avaliacao_id
    from collections import defaultdict
    by_av = defaultdict(list)
    for r in rows:
        by_av[r["avaliacao_id"]].append(dict(r))

    for av_id, q_list in by_av.items():
        av_titulo = q_list[0]["titulo"]
        av_tipo = q_list[0]["tipo"]
        
        # Extrai tema do titulo
        tema = av_titulo
        if ":" in av_titulo:
            tema = av_titulo.split(":", 1)[1].strip()
        elif "-" in av_titulo:
            tema = av_titulo.split("-", 1)[1].strip()

        if not tema:
            tema = "Grammaire Française"

        questoes_ped = gerar_questoes_pedagogicas_completas(tema, "A2", av_tipo, len(q_list))

        for idx, q in enumerate(q_list):
            if not eh_questao_valida(q):
                subst = questoes_ped[idx % len(questoes_ped)]
                print(f"Corrigindo questão {q['questao_id']} da avaliação '{av_titulo}':")
                print(f"  Antes : [{q['tipo_questao']}] {q['enunciado']} (ref: '{q['texto_referencia']}')")
                print(f"  Depois: [{subst['tipo_questao']}] {subst['enunciado']} (ref: '{subst['texto_referencia']}')")

                cursor.execute("""
                    UPDATE prova_questoes
                    SET tipo_questao = ?, enunciado = ?, texto_referencia = ?
                    WHERE id = ?
                """, (subst["tipo_questao"], subst["enunciado"], subst["texto_referencia"], q["questao_id"]))
                corrigidas += 1

    conn.commit()
    conn.close()
    print(f"\n[OK] Limpeza concluída! Total de questões atualizadas: {corrigidas}")

if __name__ == "__main__":
    run_cleanup()
