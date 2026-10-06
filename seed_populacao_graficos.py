"""
Script de População Abrangente de Dados para o Assistente Fran
Popula o banco de dados SQLite com dados pedagógicos realistas para testar e validar:
- Gráficos de Rosca (Status Geral)
- Gráficos de Barras Comparativos (Acertos vs Parciais vs Erros por Tópico)
- Filtros por Turma, Nível CEFR e Aluno
- Tabela de Alunos em Risco e Intervenções do Radar
- Painel do Aluno e Gamificação (Badges, Histórico, Missões de Foco)
"""

import sqlite3
import os
import json
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "educacao_ia.db")

def popular_banco():
    print(f"[*] Conectando ao banco de dados: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    senha_padrao = generate_password_hash("123456")
    senha_admin = generate_password_hash("admin")

    # 1. Garante professor administrador
    cursor.execute("SELECT id FROM professores WHERE usuario = 'admin';")
    prof = cursor.fetchone()
    if not prof:
        cursor.execute(
            "INSERT INTO professores (nome, usuario, senha_hash) VALUES (?, ?, ?);",
            ("Professora Françoise (Fran)", "admin", senha_admin)
        )
        prof_id = cursor.lastrowid
    else:
        prof_id = prof[0]
    print(f"[+] Professor ID {prof_id} pronto.")

    # 2. Turmas (A1 a B2)
    turmas_base = [
        ("1º Ano A (Iniciante A1)",),
        ("1º Ano B (Elementar A2)",),
        ("2º Ano A (Intermediário B1)",),
        ("3º Ano A (Avançado B2)",)
    ]
    turma_ids = {}
    for (nome_t,) in turmas_base:
        cursor.execute("SELECT id FROM turmas WHERE nome = ?;", (nome_t,))
        row = cursor.fetchone()
        if row:
            turma_ids[nome_t] = row[0]
        else:
            cursor.execute("INSERT INTO turmas (nome) VALUES (?);", (nome_t,))
            turma_ids[nome_t] = cursor.lastrowid
    print(f"[+] Turmas configuradas: {len(turma_ids)}")

    # 3. Alunos distribuídos por turmas e níveis
    alunos_dados = [
        # 1º Ano A (A1)
        ("Lucas Silva", "202601", turma_ids["1º Ano A (Iniciante A1)"], "A1", "Matutino", "Sala 101"),
        ("Camila Rodrigues", "202602", turma_ids["1º Ano A (Iniciante A1)"], "A1", "Matutino", "Sala 101"),
        ("Matheus Oliveira", "202603", turma_ids["1º Ano A (Iniciante A1)"], "A1", "Matutino", "Sala 101"),
        ("Beatriz Lima", "202604", turma_ids["1º Ano A (Iniciante A1)"], "A2", "Matutino", "Sala 101"),
        ("Enzo Gabriel", "202605", turma_ids["1º Ano A (Iniciante A1)"], "A1", "Matutino", "Sala 101"),
        
        # 1º Ano B (A2)
        ("Gabriel Santos", "202606", turma_ids["1º Ano B (Elementar A2)"], "A2", "Matutino", "Sala 102"),
        ("Juliana Costa", "202607", turma_ids["1º Ano B (Elementar A2)"], "A2", "Matutino", "Sala 102"),
        ("Sofia Ferreira", "202608", turma_ids["1º Ano B (Elementar A2)"], "A1", "Matutino", "Sala 102"),
        ("Thiago Mendes", "202609", turma_ids["1º Ano B (Elementar A2)"], "A2", "Matutino", "Sala 102"),
        ("Larissa Duarte", "202610", turma_ids["1º Ano B (Elementar A2)"], "A2", "Matutino", "Sala 102"),

        # 2º Ano A (B1)
        ("Laura Martins", "202611", turma_ids["2º Ano A (Intermediário B1)"], "B1", "Vespertino", "Sala 201"),
        ("Rafael Barbosa", "202612", turma_ids["2º Ano A (Intermediário B1)"], "B1", "Vespertino", "Sala 201"),
        ("Manuela Ribeiro", "202613", turma_ids["2º Ano A (Intermediário B1)"], "B1", "Vespertino", "Sala 201"),
        ("Felipe Carvalho", "202614", turma_ids["2º Ano A (Intermediário B1)"], "A2", "Vespertino", "Sala 201"),

        # 3º Ano A (B2)
        ("Alice Gonçalves", "202615", turma_ids["3º Ano A (Avançado B2)"], "B2", "Vespertino", "Sala 301"),
        ("Nicolas Souza", "202616", turma_ids["3º Ano A (Avançado B2)"], "B2", "Vespertino", "Sala 301"),
        ("Heloísa Castro", "202617", turma_ids["3º Ano A (Avançado B2)"], "B1", "Vespertino", "Sala 301"),
        ("Arthur Almeida", "202618", turma_ids["3º Ano A (Avançado B2)"], "B2", "Vespertino", "Sala 301")
    ]

    aluno_map = {}
    for nome, mat, t_id, cefr, turno, sala in alunos_dados:
        cursor.execute("SELECT id FROM alunos WHERE matricula = ?;", (mat,))
        row = cursor.fetchone()
        if row:
            aluno_map[mat] = row[0]
            cursor.execute(
                "UPDATE alunos SET nome = ?, turma_id = ?, nivel_cefr = ?, turno = ?, sala = ? WHERE id = ?;",
                (nome, t_id, cefr, turno, sala, row[0])
            )
        else:
            cursor.execute(
                "INSERT INTO alunos (nome, matricula, senha_hash, turma_id, nivel_cefr, turno, sala) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (nome, mat, senha_padrao, t_id, cefr, turno, sala)
            )
            aluno_map[mat] = cursor.lastrowid
    print(f"[+] Alunos cadastrados e vinculados: {len(aluno_map)}")

    # 4. Tópicos Gramaticais (Temas FLE)
    temas_dados = [
        "Les Salutations et Présentations",
        "Les Verbes du 1er groupe au Présent",
        "Les Articles Définis, Indéfinis et Partitifs",
        "La Négation Simple et Complexe",
        "Le Passé Composé: Être vs Avoir",
        "L'Imparfait et la Concordance des Temps",
        "Les Pronoms Personnels (COD et COI)",
        "Le Conditionnel Présent et l'Hypothèse",
        "Le Subjonctif Présent et la Nécessité",
        "Les Prépositions de Lieu et Déplacements"
    ]
    tema_ids = {}
    for t_nome in temas_dados:
        cursor.execute("SELECT id FROM temas WHERE nome_tema = ?;", (t_nome,))
        row = cursor.fetchone()
        if row:
            tema_ids[t_nome] = row[0]
        else:
            cursor.execute("INSERT INTO temas (nome_tema) VALUES (?);", (t_nome,))
            tema_ids[t_nome] = cursor.lastrowid
    print(f"[+] Tópicos gramaticais cadastrados: {len(tema_ids)}")

    # 5. Exercícios Práticos por Tema
    exercicios_lista = [
        # Salutations (A1)
        (tema_ids["Les Salutations et Présentations"], "A1", "Présentez-vous en français en donnant votre prénom, votre nationalité et votre ville d'origine."),
        (tema_ids["Les Salutations et Présentations"], "A1", "Complétez avec le verbe s'appeler au présent: 'Bonjour! Je ___ Pierre et voici mon amie, elle ___ Sophie.'"),
        
        # 1er groupe (A1)
        (tema_ids["Les Verbes du 1er groupe au Présent"], "A1", "Conjuguez le verbe habiter: 'Nous ___ (habiter) à Lyon depuis trois ans.'"),
        (tema_ids["Les Verbes du 1er groupe au Présent"], "A1", "Conjuguez au présent: 'Vous ___ (parler) très bien français.'"),

        # Articles (A1-A2)
        (tema_ids["Les Articles Définis, Indéfinis et Partitifs"], "A2", "Complétez avec l'article partitif ou défini: 'Au petit-déjeuner, je bois ___ café et je mange ___ croissants avec ___ confiture.'"),
        (tema_ids["Les Articles Définis, Indéfinis et Partitifs"], "A2", "Mettez l'article correct: 'Il n'y a pas ___ sucre dans mon thé.'"),

        # Négation (A1-A2)
        (tema_ids["La Négation Simple et Complexe"], "A1", "Transformez à la forme négative simple: 'Paul regarde la télévision tous les soirs.'"),
        (tema_ids["La Négation Simple et Complexe"], "A2", "Complétez avec 'ne... plus' ou 'ne... jamais': 'Je ___ bois ___ d'alcool, j'ai complètement arrêté il y a six mois.'"),

        # Passé Composé (A2)
        (tema_ids["Le Passé Composé: Être vs Avoir"], "A2", "Complétez avec l'auxiliaire être ou avoir et le participe passé: 'Hier soir, nous ___ (aller) au restaurant et nous ___ (manger) une délicieuse crêpe.'"),
        (tema_ids["Le Passé Composé: Être vs Avoir"], "A2", "Faites l'accord si nécessaire: 'Elles ___ (partir) en vacances en Italie la semaine dernière.'"),
        (tema_ids["Le Passé Composé: Être vs Avoir"], "A2", "Mettez au passé composé: 'Marc ___ (perdre) ses clés dans le parc.'"),

        # Imparfait (A2-B1)
        (tema_ids["L'Imparfait et la Concordance des Temps"], "B1", "Complétez avec l'imparfait: 'Quand j'___ (être) petit, nous ___ (vivre) à la campagne.'"),
        (tema_ids["L'Imparfait et la Concordance des Temps"], "B1", "Choisissez entre Passé Composé et Imparfait: 'Pendant qu'il ___ (dormir), le téléphone ___ (sonner).'"),

        # Pronoms COD/COI (B1)
        (tema_ids["Les Pronoms Personnels (COD et COI)"], "B1", "Remplacez le complément par un pronom: 'Tu as envoyé la lettre à ton directeur ? Oui, je ___ ai envoyée ce matin.'"),
        (tema_ids["Les Pronoms Personnels (COD et COI)"], "B1", "Répondez avec le pronom convenable: 'Tu téléphones souvent à tes grands-parents ? Oui, je ___ téléphone tous les dimanches.'"),

        # Conditionnel (B1-B2)
        (tema_ids["Le Conditionnel Présent et l'Hypothèse"], "B1", "Exprimez une demande polie: 'Je ___ (vouloir) réserver une table pour deux personnes, s'il vous plaît.'"),
        (tema_ids["Le Conditionnel Présent et l'Hypothèse"], "B2", "Formulez une hypothèse avec Si + Imparfait: 'Si nous ___ (avoir) plus de temps, nous ___ (voyager) autour du monde.'"),

        # Subjonctif (B2)
        (tema_ids["Le Subjonctif Présent et la Nécessité"], "B2", "Complétez avec le subjonctif: 'Il est impératif que vous ___ (faire) cet exercice avant demain.'"),
        (tema_ids["Le Subjonctif Présent et la Nécessité"], "B2", "Conjuguez au subjonctif: 'Je crains qu'elle ne ___ (venir) pas à la réunion.'"),

        # Prépositions de lieu (A1-A2)
        (tema_ids["Les Prépositions de Lieu et Déplacements"], "A2", "Complétez avec en, au, aux ou à: 'Cet été, je vais ___ France, puis ___ Japon et enfin ___ États-Unis.'"),
        (tema_ids["Les Prépositions de Lieu et Déplacements"], "A1", "Indiquez le lieu exact: 'Le musée est ___ (en face de / à côté) la cathédrale.'")
    ]

    exercicio_ids = []
    for tema_id, nivel_ex, enunciado in exercicios_lista:
        cursor.execute("SELECT id FROM exercicios WHERE enunciado = ?;", (enunciado,))
        row = cursor.fetchone()
        if row:
            exercicio_ids.append((row[0], tema_id, nivel_ex))
        else:
            cursor.execute(
                "INSERT INTO exercicios (tema_id, nivel_exigido, enunciado) VALUES (?, ?, ?);",
                (tema_id, nivel_ex, enunciado)
            )
            exercicio_ids.append((cursor.lastrowid, tema_id, nivel_ex))
    print(f"[+] Banco de exercícios pronto: {len(exercicio_ids)} questões.")

    # 6. Avaliações Formativas / Somativas
    avaliacoes_dados = [
        ("Évaluation Diagnostique FLE - Trimestre 1", "Escrita", turma_ids["1º Ano A (Iniciante A1)"], "2026-09-30 23:59:00"),
        ("Contrôle Continu: Passé Composé & Imparfait", "Mista", turma_ids["1º Ano B (Elementar A2)"], "2026-09-28 23:59:00"),
        ("Épreuve Orale et Écrite: Expression Quotidienne", "Oral", turma_ids["2º Ano A (Intermediário B1)"], "2026-10-05 23:59:00"),
        ("Examen Blanc DELF B2: Structures Complexes", "Mista", turma_ids["3º Ano A (Avançado B2)"], "2026-10-10 23:59:00")
    ]
    avaliacao_ids = []
    for tit, tipo, t_id, d_lim in avaliacoes_dados:
        cursor.execute("SELECT id FROM avaliacoes WHERE titulo = ? AND turma_id = ?;", (tit, t_id))
        row = cursor.fetchone()
        if row:
            avaliacao_ids.append(row[0])
        else:
            cursor.execute(
                "INSERT INTO avaliacoes (titulo, tipo, turma_id, data_limite) VALUES (?, ?, ?, ?);",
                (tit, tipo, t_id, d_lim)
            )
            avaliacao_ids.append(cursor.lastrowid)
    print(f"[+] Avaliações configuradas: {len(avaliacao_ids)}")

    # Questões das avaliações
    questoes_avaliacoes = [
        (avaliacao_ids[0], "escrita", "Rédigez un court texte de présentation (4 à 5 lignes) : nom, âge, nationalité et vos goûts.", 10.0),
        (avaliacao_ids[1], "escrita", "Racontez une journée mémorable en utilisant le Passé Composé et l'Imparfait.", 10.0),
        (avaliacao_ids[2], "oral", "Enregistrez un message audio de 1 minute décrivant votre ville préférée en français.", 10.0),
        (avaliacao_ids[3], "escrita", "Donnez votre avis argumenté sur l'apprentissage des langues à l'ère numérique avec le subjonctif.", 10.0)
    ]
    for av_id, t_q, enunc, pts in questoes_avaliacoes:
        cursor.execute("SELECT id FROM prova_questoes WHERE avaliacao_id = ? AND enunciado = ?;", (av_id, enunc))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO prova_questoes (avaliacao_id, tipo_questao, enunciado, pontuacao_maxima) VALUES (?, ?, ?, ?);",
                (av_id, t_q, enunc, pts)
            )

    # 7. Geração de Submissões Realistas (Para alimentar os Gráficos com perfeição)
    # Limpamos submissões antigas para criar uma base coesa e rica
    cursor.execute("DELETE FROM submissoes;")

    # Modelos de respostas e feedbacks pedagógicos por status
    modelos_respostas = {
        # Correto
        "Correto": [
            ("Je m'appelle Lucas, je suis brésilien et j'habite à São Paulo.", 
             "Très bien ! Prononciation claire, structure grammaticale sans faute.", 
             "Domínio pleno da concordância de gênero e do verbo être no presente."),
            
            ("Nous habitons à Lyon depuis trois ans.", 
             "Excellente conjugaison du verbe habiter au présent pour la première personne du pluriel.", 
             "Terminação 'ons' aplicada corretamente sem erros ortográficos."),
            
            ("Hier soir, nous sommes allés au restaurant et nous avons mangé une délicieuse crêpe.", 
             "Bravo ! Parfaite distinction entre l'auxiliaire être pour le verbe de mouvement et avoir pour le verbe transitif.", 
             "Uso exemplar do Passé Composé com o acordo do particípio 'allés' no plural masculino."),
            
            ("Elles sont parties en vacances en Italie la semaine dernière.", 
             "Parfait ! Accord féminin pluriel (-es) avec l'auxiliaire être correctement respecté.", 
             "Acordo perfeito do particípio passado com sujeito 'elles'."),
            
            ("Quand j'étais petit, nous vivions à la campagne.", 
             "Très bien ! Emploi judicieux de l'imparfait pour évoquer une habitude du passé.", 
             "Morfologia do imperfeito dominada com precisão ('étais' e 'vivions')."),
            
            ("Je voudrais réserver une table pour deux personnes, s'il vous plaît.", 
             "Excellente formule de politesse au conditionnel présent.", 
             "Adequação pragmática e comunicativa excelente no registro formal."),
            
            ("Il est impératif que vous fassiez cet exercice avant demain.", 
             "Magnifique ! Le verbe faire est parfaitement conjugué au subjonctif présent.", 
             "Forma irregular 'fassiez' empregada com correção."),
            
            ("Cet été, je vais en France, puis au Japon et enfin aux États-Unis.", 
             "Parfait respect des prépositions géographiques selon le genre et le nombre des pays.", 
             "Diferenciação clara entre país feminino (en), masculino (au) e plural (aux)."),

            ("Paul ne regarde pas la télévision tous les soirs.",
             "Très bien ! La négation encadre correctement le verbe conjugué.",
             "Estrutura 'ne + verbe + pas' perfeitamente aplicada."),

            ("Oui, je la lui ai envoyée ce matin.",
             "Impressionnant ! Double pronom COD et COI placé dans l'ordre exact avec accord du participe passé.",
             "Domínio avançado da ordem dos pronomes e do acordo com o COD anteposto.")
        ],

        # Parcialmente Correto
        "Parcialmente Correto": [
            ("Au petit-déjeuner, je bois le café et je mange des croissants avec la confiture.",
             "Presque parfait ! Attention à l'utilisation de l'article partitif 'du' café et 'de la' confiture au lieu de l'article défini.",
             "Pequeno desvio no emprego do artigo partitivo em contexto alimentar."),

            ("Pendant qu'il dormait, le téléphone a sonné.",
             "Bonne utilisation globale, mais faites attention à l'accentuation sur les participes.",
             "Conceito temporal correto, pequeno deslize pontual de digitação."),

            ("Hier soir, nous avons allé au restaurant et nous avons mangé.",
             "Attention ! Le verbe 'aller' est un verbe de déplacement et se conjugue avec l'auxiliaire 'être' (nous sommes allés).",
             "Confusão clássica entre os auxiliares être e avoir no Passé Composé."),

            ("Elles sont parti en vacances la semaine dernière.",
             "Bonne conjugaison avec être, mais n'oubliez pas d'accorder le participe passé au féminin pluriel : 'parties'.",
             "Esqueceu a marca de feminino e plural (-es) no particípio passado."),

            ("Il n'y a pas du sucre dans mon thé.",
             "Attention : à la forme négative absolue, les articles partitifs deviennent 'de' : 'Il n'y a pas DE sucre'.",
             "Regra da transformação do partitivo em 'de' na negação necessita de fixação."),

            ("Si nous avions plus de temps, nous voyagerions autour du monde.",
             "Bonne structure, attention au radical du verbe voyager au conditionnel.",
             "Aplicação da regra condicional correta com pequena hesitação ortográfica.")
        ],

        # Incorreto
        "Incorreto": [
            ("Hier soir, nous avons aller au cinéma.",
             "Attention, le Passé Composé nécessite le participe passé et l'auxiliaire être : 'nous sommes allés'.",
             "Não conjugou o particípio passado e errou o verbo auxiliar."),

            ("Paul mange pas la viande.",
             "Attention ! En français écrit standard, la négation nécessite obligatoirement 'ne' : 'Paul NE mange PAS DE viande'.",
             "Omissão da partícula 'ne' e falta de transformação do partitivo em contexto negativo."),

            ("Je vais à la France et après dans le Japon.",
             "Erreur de préposition de lieu : on dit 'en France' (pays féminin) et 'au Japon' (pays masculin).",
             "Desvio recorrente no emprego de preposições para nomes de países."),

            ("Il faut que vous faites attention.",
             "Attention ! L'expression d'obligation 'il faut que' exige le subjonctif : 'que vous FASSIEZ attention'.",
             "Emprego incorreto do indicativo no lugar do modo subjuntivo."),

            ("Marc a perdit ses clés.",
             "Forme erronée du participe passé : le verbe perdre fait 'perdu' au participe passé (Marc a perdu).",
             "Desvio morfológico na formação do particípio de verbos do 3º grupo.")
        ]
    }

    # Geramos aproximadamente 80 a 95 submissões distribuídas
    # Alunos com perfis variados para que os relatórios e filtros mostrem diferenças reais
    status_weights = {
        "A1": ["Correto"] * 4 + ["Parcialmente Correto"] * 3 + ["Incorreto"] * 3,
        "A2": ["Correto"] * 5 + ["Parcialmente Correto"] * 3 + ["Incorreto"] * 2,
        "B1": ["Correto"] * 7 + ["Parcialmente Correto"] * 2 + ["Incorreto"] * 1,
        "B2": ["Correto"] * 8 + ["Parcialmente Correto"] * 2 + ["Incorreto"] * 0
    }

    submissoes_geradas = []
    base_date = datetime(2026, 9, 1, 9, 0, 0)

    # Cada aluno fará entre 4 e 7 exercícios
    for mat, aluno_id in aluno_map.items():
        # Busca o nível CEFR do aluno
        cursor.execute("SELECT nivel_cefr FROM alunos WHERE id = ?;", (aluno_id,))
        nivel_aluno = cursor.fetchone()[0]

        # Quantidade de exercícios para este aluno
        qtd_exercicios = random.randint(4, 7)
        exercicios_escolhidos = random.sample(exercicio_ids, min(qtd_exercicios, len(exercicio_ids)))

        for i, (ex_id, t_id, nivel_ex) in enumerate(exercicios_escolhidos):
            # Seleciona status baseado no peso do nível do aluno
            pool = status_weights.get(nivel_aluno, ["Correto", "Parcialmente Correto", "Incorreto"])
            status = random.choice(pool)

            # Pega modelo compatível
            modelos = modelos_respostas[status]
            resp_texto, feedback_texto, analise_texto = random.choice(modelos)

            # Data realista espaçada nos últimos 18 dias
            dias_delta = random.randint(0, 18)
            horas_delta = random.randint(8, 20)
            minutos_delta = random.randint(0, 59)
            sub_data = (base_date + timedelta(days=dias_delta, hours=horas_delta, minutes=minutos_delta)).strftime("%Y-%m-%d %H:%M:%S")

            tentativa = 1 if status == "Correto" else random.choice([1, 2, 3])
            
            # Nota estimada
            nota = 10.0 if status == "Correto" else (7.0 if status == "Parcialmente Correto" else 4.0)

            submissoes_geradas.append((
                aluno_id,
                ex_id,
                None, # prova_questao_id
                resp_texto,
                None, # audio
                feedback_texto,
                analise_texto,
                nota,
                status,
                tentativa,
                sub_data
            ))

    # Também adicionamos algumas submissões de prova com áudio para habilitar badges orais
    # Aluno Lucas Silva (202601) e Arthur Almeida (202618)
    cursor.execute("SELECT id FROM prova_questoes WHERE tipo_questao = 'oral' LIMIT 1;")
    pq_oral = cursor.fetchone()
    if pq_oral:
        pq_id = pq_oral[0]
        submissoes_geradas.append((
            aluno_map["202601"],
            None,
            pq_id,
            "Bonjour professeur, j'adore ma ville parce qu'il y a beaucoup de parcs.",
            "audios/lucas_oral_202601.webm",
            "Très bonne intonation et articulation fluide en français !",
            "Expressão oral de nível A1 plenamente alcançada.",
            9.5,
            "Correto",
            1,
            "2026-09-18 15:30:00"
        ))
        submissoes_geradas.append((
            aluno_map["202615"],
            None,
            pq_id,
            "À mon avis, l'apprentissage numérique favorise l'autonomie communicative.",
            "audios/alice_oral_202615.webm",
            "Excellente maîtrise du lexique formel et de la syntaxe.",
            "Nível B2 comprovado com fluidez e argumentos bem encadeados.",
            10.0,
            "Correto",
            1,
            "2026-09-18 16:15:00"
        ))

    cursor.executemany("""
        INSERT INTO submissoes (
            aluno_id, exercicio_id, prova_questao_id, resposta_aluno, arquivo_audio_path,
            feedback_ia, analise_professor, nota_professor, status_resposta, tentativa, data_hora
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, submissoes_geradas)
    print(f"[+] Total de submissões pedagógicas geradas: {len(submissoes_geradas)}")

    # 8. Reforços Individuais (Missões do Radar Pedagógico)
    # Identifica alunos com respostas incorretas recentes
    cursor.execute("""
        SELECT s.aluno_id, e.tema_id, COUNT(*) as qtd_erros
        FROM submissoes s
        JOIN exercicios e ON s.exercicio_id = e.id
        WHERE s.status_resposta = 'Incorreto'
        GROUP BY s.aluno_id, e.tema_id
        ORDER BY qtd_erros DESC LIMIT 5;
    """)
    erros_radar = cursor.fetchall()
    
    cursor.execute("DELETE FROM reforcos_individuais;")
    reforcos_dados = []
    for al_id, tm_id, qtd in erros_radar:
        cursor.execute("SELECT nome_tema FROM temas WHERE id = ?;", (tm_id,))
        t_nome = cursor.fetchone()[0]
        
        exercicios_treino = [
            f"Treino 1: Pratique a regra fundamental de {t_nome}.",
            f"Treino 2: Conjugue e formule 3 frases afirmativas e negativas.",
            f"Treino 3: Grave uma leitura pausada aplicando a pronúncia correta."
        ]
        
        reforcos_dados.append((
            al_id,
            tm_id,
            f"Plano de Reforço Tutor FLE: Notamos pequenas dificuldades em '{t_nome}'. Conclua os 3 exercícios práticos guiados para consolidar seu aprendizado!",
            json.dumps(exercicios_treino),
            "Pendente" if random.choice([True, False]) else "Concluido",
            "2026-09-18 10:00:00"
        ))

    # Garante pelo menos um concluído e um pendente para o aluno Lucas (202601) para testar os badges
    lucas_id = aluno_map["202601"]
    reforcos_dados.append((
        lucas_id,
        tema_ids["Le Passé Composé: Être vs Avoir"],
        "Missão de Foco: Domine a diferença entre être e avoir nos verbos de deslocamento.",
        json.dumps(["Complete 5 frases com o auxiliar correto.", "Faça o acordo de gênero e número."]),
        "Concluido",
        "2026-09-17 11:30:00"
    ))

    cursor.executemany("""
        INSERT INTO reforcos_individuais (
            aluno_id, tema_id, mensagem_tutor, exercicios_json, status, data_criacao
        ) VALUES (?, ?, ?, ?, ?, ?);
    """, reforcos_dados)
    print(f"[+] Planos de reforço individual (Radar) criados: {len(reforcos_dados)}")

    # 9. Mensagens na Caixa de Entrada (Inbox)
    cursor.execute("DELETE FROM mensagens_inbox;")
    mensagens_dados = [
        (prof_id, aluno_map["202601"], "Feedback sobre a Prova Oral A1", "Félicitations Lucas ! Votre prononciation en français a beaucoup progressé ce mois-ci. Continuez ainsi !", 1, "2026-09-18 14:00:00"),
        (prof_id, aluno_map["202608"], "Orientações para o Reforço de Artigos", "Bonjour Sofia, deixei uma missão de reforço personalizada sobre os artigos partitivos no seu painel. Qualquer dúvida, estou à disposição.", 0, "2026-09-18 15:00:00"),
        (prof_id, aluno_map["202615"], "Preparação para o Exame DELF B2", "Chère Alice, vos arguments écrits sont très solides. Recommandation : enrichir encore les connecteurs logiques de concession.", 0, "2026-09-19 09:30:00")
    ]
    cursor.executemany("""
        INSERT INTO mensagens_inbox (
            remetente_id, destinatario_id, assunto, corpo, lida_status, data_envio
        ) VALUES (?, ?, ?, ?, ?, ?);
    """, mensagens_dados)
    print(f"[+] Mensagens de recados enviadas: {len(mensagens_dados)}")

    # 10. Tópicos e Mensagens no Fórum
    cursor.execute("DELETE FROM forum_mensagens;")
    cursor.execute("DELETE FROM forum_topicos;")
    
    cursor.execute("""
        INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id, data_criacao)
        VALUES (?, ?, ?, ?, ?);
    """, (
        "Dúvidas sobre o Passé Composé: Quando usar Être?",
        "Espaço para compartilhar dicas mnemônicas (ex: Maison d'Être / DR MRS VANDERTRAMP) e tirar dúvidas de conjugação.",
        prof_id,
        turma_ids["1º Ano B (Elementar A2)"],
        "2026-09-15 10:00:00"
    ))
    topico_1 = cursor.lastrowid

    cursor.execute("""
        INSERT INTO forum_topicos (titulo, descricao, criador_id, turma_id, data_criacao)
        VALUES (?, ?, ?, ?, ?);
    """, (
        "Dicas de Séries e Músicas Francesas para treinar compreensão oral",
        "Recomendações de conteúdos audiovisuais francófonos para enriquecer o vocabulário e a audição.",
        prof_id,
        turma_ids["2º Ano A (Intermediário B1)"],
        "2026-09-16 14:00:00"
    ))
    topico_2 = cursor.lastrowid

    forum_msgs = [
        (topico_1, aluno_map["202606"], "aluno", "Professora, verbos reflexivos como 'se laver' também sempre usam être no Passé Composé?", "2026-09-15 11:20:00"),
        (topico_1, prof_id, "professor", "Exactement Gabriel ! Tous les verbes pronominaux se conjuguent avec l'auxiliaire être : 'je me suis lavé(e)'.", "2026-09-15 11:45:00"),
        (topico_2, aluno_map["202611"], "aluno", "Recomendo muito a série 'Lupin' e as músicas do Stromae, ajudam muito na pronúncia!", "2026-09-16 15:10:00")
    ]
    cursor.executemany("""
        INSERT INTO forum_mensagens (topico_id, autor_id, autor_tipo, conteudo, data_envio)
        VALUES (?, ?, ?, ?, ?);
    """, forum_msgs)
    print(f"[+] Tópicos do fórum e discussões pedagógicas populados.")

    conn.commit()
    conn.close()
    print("\n[OK] BANCO DE DADOS POPULADO COM SUCESSO ABSOLUTO!")

if __name__ == "__main__":
    popular_banco()
