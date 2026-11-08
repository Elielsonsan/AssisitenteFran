# 🚀 Assistente Fran — Contexto de Migração e Handover para Linux

Este documento serve como guia completo e memória técnica do projeto **Assistente Fran** para ser carregado no **Antigravity (Linux)** ou continuado por qualquer nova instância do agente de IA.

---

## 📌 1. Visão Geral do Projeto
- **Nome:** Assistente Fran (Plataforma Educacional e Assistente de Francês / FLE - *Français Langue Étrangère*)
- **Público:** Alunos (prática de conversação, gramática, exercícios com IA) e Professores (gestão pedagógica, planos de aula, notas e frequência).
- **Stack:**
  - **Backend:** Python 3.10+, Flask 3.x (arquitetura modularizada com **Blueprints**)
  - **Banco de Dados:** SQLite3 (`educacao_ia.db` com chaves estrangeiras ativadas: `PRAGMA foreign_keys = ON;`)
  - **Segurança:** `Flask-WTF` (proteção CSRF global com tokens injetados nos formulários e requisições assíncronas)
  - **Performance:** `Flask-Compress` (compressão Gzip/Brotli) e cache HTTP agressivo (`SEND_FILE_MAX_AGE_DEFAULT = 1 ano`)
  - **IA:** Google Generative AI (Gemini Flash/Pro via SDK `google-generativeai`) com mecanismo de retry e fallback
  - **Frontend:** Jinja2 Templates, HTML5 semântico, CSS3 moderno com variáveis nativas e JavaScript Vanilla (sistema de Toasts não-bloqueantes substituindo `alert()`).

---

## 🏗️ 2. Arquitetura Modular (Flask Blueprints)
O projeto anteriormente era um arquivo monolítico de mais de 3.000 linhas (`app.py`). Foi completamente refatorado em Blueprints:

```text
Assistente_Fran/
├── app.py                      # Ponto de entrada enxuto (~90 linhas), inicialização do Flask, CSRF e Compress
├── blueprints/
│   ├── __init__.py
│   ├── extensions.py           # Conexão get_db(), decoradores @login_required/@login_required_prof, helpers do Gemini
│   ├── auth.py                 # Rotas /login, /logout, /trocar_senha
│   ├── main.py                 # Rotas públicas: /, /sobre, /guia, /guia-fle, /api/chat
│   ├── aluno.py                # Rotas do aluno: /pratica, /avaliar, /avaliacoes, /perfil, /historico, /inbox
│   ├── professor.py            # Rotas do professor: /dashboard, /gestao_turmas, /planos_aula, /exportar_boletim...
│   └── forum.py                # Fórum de dúvidas: /forum, /forum/topico/<id>, /forum/novo, /forum/responder
├── templates/                  # Templates Jinja2 (base.html, index.html, dashboard.html, etc.)
├── static/
│   ├── css/style.css           # Estilos globais e componentes da interface (Toasts, Chat bubbles, Modais)
│   └── js/
│       ├── main.js             # Lógica do chat IA, Toasts, envio assíncrono com CSRF
│       └── dashboard.js        # Lógica do painel do professor e modais
├── educacao_ia.db              # Banco de dados SQLite ativo
├── requirements.txt            # Dependências do Python atualizadas
└── .env                        # Chaves de API e variáveis de ambiente
```

---

## 🗄️ 3. Modelo de Dados e Banco de Dados (`educacao_ia.db`)
O banco foi atualizado para um schema padrão **LMS (Learning Management System)**:

### ⚠️ Regras Críticas do Banco:
1. **Nomes de Coluna:** 
   - A coluna `nome` das tabelas `alunos` e `professores` foi renomeada para **`nome_completo`**.
   - A coluna `sala` foi substituída pelo relacionamento com a tabela `turmas` através de **`turma_id`**.
   - *Nota:* Todas as consultas SQL e templates (`dashboard.html`, `perfil.html`, etc.) foram corrigidos para usar `a.nome_completo`. Não reverta para `nome`.
2. **Tabelas Principais:**
   - `alunos`: `id`, `matricula`, `nome_completo`, `email`, `senha_hash`, `turma_id`, `nivel_cefr`, `status`, `data_cadastro`.
   - `professores`: `id`, `nome_completo`, `email`, `senha_hash`, `departamento`, `status`.
   - `turmas`: `id`, `nome`, `nivel_cefr`, `descricao`.
   - `avaliacoes`: Notas, feedbacks e histórico de tarefas submetidas pelos alunos.
   - `planos_aula`: Planos pedagógicos gerados por IA ou manualmente.
   - `forum_topicos` e `forum_respostas`: Sistema de discussão com resolução de dúvidas.

---

## 🛡️ 4. Segurança e CSRF
- **Flask-WTF** protege todas as requisições `POST`.
- No arquivo `templates/base.html`, o token está presente na meta tag:
  ```html
  <meta name="csrf-token" content="{{ csrf_token() }}">
  ```
- No JavaScript (`main.js` e `dashboard.js`), todas as chamadas `fetch()` injetam automaticamente o header:
  ```javascript
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
  }
  ```

---

## 🎨 5. Melhorias de UX/UI e Acessibilidade (WCAG 2.1 AA / AAA)
1. **Chat de IA Moderno:** O chat na página inicial (`index.html`) utiliza design de balões de mensagens com avatar estilizado da "Fran" e animação de carregamento (typing indicator).
2. **Toasts Interativos:** Não são utilizados `alert()` ou `confirm()` nativos do navegador. Existe a função `showToast(mensagem, tipo)` em `main.js` que renderiza notificações elegantes no topo da tela.
3. **Plano de Acessibilidade Implementado:**
   - **Passo 1 (Síntese e Áudio FLE):** Tags `lang="fr"` semânticas para leitores de tela não misturarem fonética, botões de reproduzir/parar áudio com estado `aria-pressed`, clique para ouvir em trechos citados.
   - **Passo 2 (Navegação por Teclado):** Link "Pular para o conteúdo principal" (`.skip-link`), indicador de foco universal `:focus-visible`, atalho `Ctrl + Enter` para submeter resposta, estados `aria-expanded` em menus e gaveta móvel.
   - **Passo 3 (Conforto Visual & Alto Contraste):** Toolbar com botões `A-` e `A+` para redimensionamento de fonte (87% a 125%), modo Alto Contraste (preto/branco puro com anéis amarelos/azuis), respeito a `prefers-reduced-motion`, persistência em `localStorage` sem FOUC.
   - **Passo 4 (Leitores de Tela e Live Regions):** Regiões `aria-live="polite"` (`#a11y-announcer`) e `role="alert"` (`#a11y-alert`) globais, utilitário `.sr-only`, anúncios automáticos ao gerar exercícios, avaliar resposta, trocar de nível e receber notificações toast.
   - **Passo 5 (Modais, Formulários & Gráficos nos Painéis):** Sistema global de Focus Trap e tecla `Escape` para fechar modais/popovers com restauração de foco no disparador; atributos `role="dialog"` e `aria-labelledby` em todos os modais; acessibilidade em tabelas (`<th scope="col">` e `aria-label` descritivos por aluno/submissão); e `role="img"` com `aria-label` informativo para gráficos Chart.js nos Dashboards Docente e Discente.

---

## 🐧 6. Instruções de Execução no Linux

### 1. Clonar ou Copiar os Arquivos
Copie o diretório do projeto para a sua máquina Linux (ex: `~/projetos/Assistente_Fran`).

### 2. Criar e Ativar o Ambiente Virtual
```bash
cd ~/projetos/Assistente_Fran
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar o `.env`
Garanta que o arquivo `.env` na raiz contenha as chaves necessárias:
```env
GEMINI_API_KEY=sua_chave_do_google_aistudio_aqui
FLASK_SECRET_KEY=sua_chave_secreta_aleatoria
FLASK_ENV=development
```

### 5. Iniciar o Servidor
```bash
python app.py
```
A aplicação iniciará em `http://127.0.0.1:5000`.

---

## 📋 7. Como Iniciar no Antigravity Linux
Quando você abrir o **Antigravity no Linux**, aponte o workspace para o diretório `Assistente_Fran` e envie a seguinte mensagem inicial:

> *"Olá! Acabei de migrar o projeto do Windows para o Linux. Por favor, leia o arquivo CONTEXTO_MIGRACAO.md para entender toda a arquitetura, as alterações recentes nos Blueprints, o schema do banco de dados e as dependências."*

O agente no Linux estará 100% alinhado com o estado atual do desenvolvimento!
