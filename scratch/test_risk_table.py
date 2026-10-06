import re, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

client = app.test_client()
with client.session_transaction() as sess:
    sess['prof_id'] = 1
    sess['prof_nome'] = 'Prof. Fran'

res = client.get('/dashboard')
print('Dashboard status:', res.status_code)
assert res.status_code == 200

html = res.data.decode('utf-8')

# Tabela 1: Alunos em Dificuldade (Risco)
assert 'id="tabelaAlunosRisco"' in html
assert 'id="paginacaoRiscoFooter"' in html
assert 'id="selectRiscoPageSize"' in html
assert 'id="infoPaginacaoRisco"' in html
assert 'id="btnRiscoPrev"' in html
assert 'id="btnRiscoNext"' in html
assert 'id="numerosPaginaRisco"' in html

# Tabela 2: Histórico de Atividades Avaliadas (Submissões)
assert 'id="tabelaSubmissoes"' in html
assert 'id="paginacaoSubmissoesFooter"' in html
assert 'id="selectSubmissoesPageSize"' in html
assert 'id="infoPaginacaoSubmissoes"' in html
assert 'id="btnSubmissoesPrev"' in html
assert 'id="btnSubmissoesNext"' in html
assert 'id="numerosPaginaSubmissoes"' in html

# Req 3: Date formatting (dd/mm/yyyy in text, title with full date/time)
assert 'class="date-display"' in html
assert re.search(r'\d{2}/\d{2}/\d{4}', html), 'Formatted date not found in HTML'

# Req 4: Turma plain text (no turma-chip in tables)
assert 'class="turma-plain-text' in html

# Req 5: Tema plain text (no topic-chip in tables)
assert 'class="tema-plain-text"' in html

# Check CSS
css_res = client.get('/static/css/style.css')
css = css_res.data.decode('utf-8')
assert css_res.status_code == 200

# CSS checks - Risk Table
assert '.risk-table th' in css
assert '.risk-table tbody tr.risk-row-odd' in css
assert '.risk-table tbody tr.risk-row-even' in css
assert '.risk-pagination-footer' in css

# CSS checks - Submissions Table
assert '.submissions-table th' in css
assert '.submissions-table tbody tr.sub-row-odd' in css
assert '.submissions-table tbody tr.sub-row-even' in css
assert '.submissoes-pagination-footer' in css or '.table-pagination-footer' in css

# General Pagination CSS
assert '.pagination-size-select' in css
assert '.btn-pagination-nav' in css
assert '.btn-page-number' in css

print('ALL TESTS ON BOTH TABLES PASSED WITH 100% SUCCESS!')
