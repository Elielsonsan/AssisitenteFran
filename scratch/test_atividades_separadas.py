import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import re

def test_separacao_atividades():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['aluno_id'] = 1
        sess['aluno_nome'] = 'Eliel'
        sess['tipo_usuario'] = 'aluno'
        sess['turma_id'] = 14

    res = client.get('/aluno/atividades')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.get_data(as_text=True)

    # Verifica estrutura das abas
    assert 'atividades-tab-bar' in html, "Tab bar not found"
    assert 'tabStatusTodas' in html, "tabStatusTodas not found"
    assert 'tabStatusPendentes' in html, "tabStatusPendentes not found"
    assert 'tabStatusConcluidas' in html, "tabStatusConcluidas not found"

    # Verifica seções separadas
    assert 'secaoAtividadesPendentes' in html, "secaoAtividadesPendentes not found"
    assert 'secaoAtividadesConcluidas' in html, "secaoAtividadesConcluidas not found"
    assert 'gridAtividadesPendentes' in html, "gridAtividadesPendentes not found"
    assert 'gridAtividadesConcluidas' in html, "gridAtividadesConcluidas not found"

    # Verifica contagem de cards
    pend_count = html.count('data-status="pendente"')
    conc_count = html.count('data-status="concluida"')
    print(f"Cards pendentes encontrados: {pend_count}")
    print(f"Cards concluídos encontrados: {conc_count}")

    assert pend_count >= 1, f"Esperado ao menos 1 pendente, encontrado {pend_count}"
    assert conc_count >= 1, f"Esperado ao menos 1 concluído, encontrado {conc_count}"
    assert pend_count + conc_count == 8, f"Esperado total de 8 atividades, encontrado {pend_count + conc_count}"

    print("✓ Teste de separação de pendentes e concluídas aprovado com 100% de sucesso!")

if __name__ == '__main__':
    test_separacao_atividades()
