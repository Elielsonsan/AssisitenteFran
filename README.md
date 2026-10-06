# 🇫🇷 Assistente Fran — Tutor Pedagógico Inteligente de Língua Francesa

Aplicação web full-stack desenvolvida em **Python (Flask)**, **SQLite** e **Frontend Moderno (HTML5, Vanilla CSS e JavaScript)** para avaliação diagnóstica e geração de feedback formativo para estudantes brasileiros de **Língua Francesa**, integrada à API do **Google Gemini (gemini-1.5-flash)**.

---

## 🌟 Diretrizes Pedagógicas do Assistente Fran

O assistente foi desenhado com base em princípios da avaliação formativa para o ensino de Francês como Língua Estrangeira (FLE):

1. **Autonomia do Estudante**: A IA **não entrega a frase totalmente corrigida de imediato**, estimulando o aluno a refletir sobre o erro.
2. **Diagnóstico Preciso do Erro**: Identifica exatamente o tipo de falha (ex: escolha do verbo auxiliar no *Passé Composé*, concordância de gênero/número, emprego de artigos partitivos ou falsos cognatos).
3. **Dicas Gramaticais Construtivas**: Fornece a regra esquecida para guiar uma nova tentativa.
4. **Tom Encorajador e Acessível**: Expressões calorosas como *"Salut!"*, *"Très bien!"* e *"Courage!"*.
5. **Comunicação Bilíngue Didática**: Feedback escrito em Português para facilitar a compreensão, destacando termos e regras em Francês com formatação em Markdown.
6. **Visão do Professor**: Separação clara entre o *Feedback para o Aluno* e a *Análise Gramatical Técnica* (para logs e visão docente).
7. **Barra de Caracteres Franceses (Acentos & Ligaturas)**: Teclado virtual integrado (`é`, `è`, `ê`, `ë`, `à`, `â`, `ç`, `ù`, `û`, `î`, `ï`, `ô`, `œ`, `« »`) com botão `a/A` para maiúsculas e inserção no cursor.
8. **Pronúncia em Áudio Nativo (fr-FR)**: Síntese de voz com cadência didática para escutar o texto digitado, a frase submetida e a leitura no painel docente.
9. **Ciclo Formativo com Tentativas (Loop de Correção Guiada)**: Em respostas incorretas ou parciais, o botão *'🔄 Tentar Novamente com a Dica'* ativa um banner fixo com a orientação anterior, e a IA reconhece o progresso na 2ª tentativa.
10. **Seletor de Níveis CEFR (A1, A2, B1, B2)**: Calibra o rigor pedagógico e o vocabulário das explicações segundo o Quadro Europeu Comum de Línguas.
11. **Générateur d'Exercices IA (`/gerar-desafio`)**: Botão *'✨ Gerar Desafio com IA'* que cria exercícios inéditos e contextualizados por nível CEFR (com Google Gemini ou banco pedagógico FLE rico de fallback).
12. **Compréhension Orale no Enunciado (`🔊 Ouvir Enunciado`)**: Permite ao aluno escutar a frase em francês do próprio enunciado antes de responder.
13. **Ditado por Microfone (`🎙️ Falar - Speech-to-Text fr-FR`)**: Prática de produção oral com reconhecimento de fala nativo em francês transcrevendo a resposta em tempo real.
14. **Mémento Gramatical Interativo (`📖 Aide-Mémoire FLE`)**: Guia de consulta rápida com áudio (*La Maison d'Être, Articles Partitifs, Faux Amis, Pronoms Y & EN*).
15. **Filtros em Tempo Real no Dashboard**: Filtragem client-side instantânea por Nível CEFR e por Status de acerto na tabela de submissões.

---

## 📁 Estrutura do Projeto

```
Assistente_Fran/
├── .env.example            # Exemplo de configuração da chave de API do Gemini
├── .gitignore              # Protege chaves, arquivos do banco e ambientes virtuais
├── requirements.txt        # Dependências do projeto (Flask, google-generativeai, python-dotenv, markdown)
├── database_setup.py       # Script SQLite para criar tabelas e dados analíticos em Francês
├── app.py                  # Servidor Flask com gerar_feedback_frances e rotas analíticas
├── educacao_ia.db          # Banco de dados SQLite criado automaticamente
├── templates/
│   ├── base.html           # Layout base com identidade visual, Google Fonts e navbar
│   ├── index.html          # Interface do Aluno com botões rápidos de Francês e feedback
│   └── dashboard.html      # Painel do Professor (Chart.js, tabela com filtros e exportação em PDF)
└── static/
    ├── css/
    │   └── style.css       # Estilo moderno com glassmorphism e tema francês
    └── js/
        ├── main.js         # Lógica do aluno (envio assíncrono e pílulas de exercícios)
        └── dashboard.js    # Inicialização dos gráficos Chart.js e exportação em PDF
```

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.

### 2. Ativar o Ambiente Virtual
No terminal PowerShell ou Prompt de Comando, acesse a pasta do projeto:

```powershell
# Ativar o ambiente virtual existente no projeto
.\venv\Scripts\Activate.ps1
```

*(Se preferir recriar o ambiente virtual a qualquer momento: `python -m venv venv` e `pip install -r requirements.txt`)*.

### 3. Configurar a Chave da API do Google Gemini
1. Obtenha sua chave gratuita em [Google AI Studio](https://aistudio.google.com/).
2. Crie um arquivo chamado `.env` na raiz do projeto (ou copie do `.env.example`):

```env
GEMINI_API_KEY=sua_chave_real_do_gemini_aqui
GEMINI_MODEL=gemini-1.5-flash
FLASK_SECRET_KEY=sua_chave_secreta_local
FLASK_DEBUG=True
```

> **Nota:** Caso execute sem a chave da API definida, a aplicação funciona em **Modo de Demonstração**, simulando a classificação pedagógica e permitindo testar toda a interface, os gráficos do painel e o banco de dados.

### 4. Inicializar o Banco de Dados
```powershell
python database_setup.py
```
Esse comando criará o arquivo `educacao_ia.db` com a tabela `submissoes`, incluindo `analise_professor` e exemplos de exercícios em Francês (*Passé Composé*, *Accord du Participe Passé*, *Articles Partitifs*, *Faux Amis*).

### 5. Iniciar o Servidor Flask
```powershell
python app.py
```

Acesse no seu navegador:
- **Área de Prática do Aluno:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Painel do Professor (Dashboard e PDF):** [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard)
