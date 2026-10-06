import re

BANCO_PEDAGOGICO_TEMAS = {
    "passe_compose": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase au passé composé avec l'auxiliaire 'avoir' ou 'être' : 'Hier soir, nous ___ (regarder) un documentaire très intéressant sur la France.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase au passé composé : 'Ce matin, Sophie ___ (partir) de la maison à huit heures précises.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Transformez la phrase au passé composé : 'Ils choisissent un bon restaurant en ville.' -> 'Hier, ils ___ (choisir) un bon restaurant en ville.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le participe passé correct : 'Paul et Lucas ont ___ (finir) leur travail avant midi.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la forme correcte au passé composé : 'Hier, mes amis ___ à Paris.'\n(a) sont arrivés\n(b) ont arrivés\n(c) sont arrivé", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle phrase utilise correctement l'auxiliaire 'être' ?\n(a) Elle a descendu la rue\n(b) Elle est allée à la gare\n(c) Elle a allée au marché", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez avec le participe passé du verbe 'prendre' : 'Tu as ___ ton manteau pour sortir.'\n(a) pris\n(b) prendu\n(c) prenant", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Identifiez l'erreur dans la phrase suivante et réécrivez-la correctement : 'Nous avons restés chez nos grands-parents tout le week-end.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au passé composé : 'Hier après-midi, nous ___ (visiter) le musée du Louvre.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o Passé Composé:", "texto_referencia": "Ontem eu comprei um livro muito bom na livraria.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase em francês:", "texto_referencia": "Hier, nous avons mangé dans une boulangerie typique.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia a frase em voz alta com clareza e boa entonação:", "texto_referencia": "Le week-end dernier, je suis allé à la plage avec mes amis et nous avons passé une excellente journée.", "pontuacao_maxima": 2.5}
        ]
    },
    "accord_participe": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Faites l'accord du participe passé si nécessaire : 'Les lettres que j'ai ___ (écrire) sont sur la table.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'accord approprié : 'Elles sont ___ (partir) très tôt pour la gare.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Accordez le participe passé avec le COD placé avant le verbe : 'Quelle belle chanson ! Tu l'as ___ (entendre) à la radio ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Réécrivez la phrase en accordant le verbe : 'Ces pommes, nous les avons ___ (manger) au dessert.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne forme accordée : 'La robe qu'elle a ___ est magnifique.'\n(a) acheté\n(b) achetée\n(c) achetées", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Identifiez la phrase avec un accord correct du participe passé :\n(a) Ils se sont téléphoné hier soir.\n(b) Ils se sont téléphonés hier soir.\n(c) Ils ont téléphonés hier soir.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez l'accord : 'Marie et Claire sont ___ à l'heure au rendez-vous.'\n(a) venue\n(b) venus\n(c) venues", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Justifiez et corrigez l'accord dans : 'Les exercices que le professeur a donné étaient difficiles.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec le participe passé correctement accordé : 'Les photos que nous avons ___ (prendre) pendant le voyage sont superbes.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês, respeitando o acordo do particípio passado:", "texto_referencia": "As cartas que ela escreveu foram enviadas ontem.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e escreva a frase com o acordo correto:", "texto_referencia": "Toutes les fenêtres de la maison sont restées ouvertes cette nuit.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para avaliar pronúncia e ritmo:", "texto_referencia": "Les fleurs que tu as achetées pour mon anniversaire sentent très bon dans le salon.", "pontuacao_maxima": 2.5}
        ]
    },
    "negation": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase à la forme négative avec 'ne ... pas' : 'Alexandre mange de la viande rouge tous les jours.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Transformez à la forme négative en utilisant 'ne ... jamais' : 'Je prends toujours le métro à sept heures.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec les éléments de négation : 'Il ___ parle ___ anglais avec ses collègues.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase au passé composé à la forme négative : 'Nous avons regardé la télévision hier.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle est la négation correcte de la phrase 'Il a encore faim' ?\n(a) Il n'a plus faim.\n(b) Il n'a jamais faim.\n(c) Il n'a rien faim.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne syntaxe négative au passé composé :\n(a) Je n'ai pas compris la leçon.\n(b) Je ai pas ne compris la leçon.\n(c) Je n'ai compris pas la leçon.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la phrase : 'Dans ce café, il ___ y a ___ de sucre.'\n(a) ne / pas\n(b) n' / pas\n(c) ne / rien", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Transformez la phrase affirmative à la négation absolue : 'Il y a quelqu'un dans la salle de classe.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe à la forme négative (ne ... pas) au présent : 'Nous ___ (ne pas aimer) le froid en hiver.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza a seguinte frase para o francês utilizando a negação correta:", "texto_referencia": "Eles não querem viajar sozinhos este ano.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase negativa em francês:", "texto_referencia": "Je ne comprends pas la réponse de cet exercice difficile.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta prestando atenção na elisão do 'ne':", "texto_referencia": "Nous n'avons pas le temps de déjeuner au restaurant aujourd'hui.", "pontuacao_maxima": 2.5}
        ]
    },
    "famille": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase avec le membre de la famille approprié : 'Le père de mon père est mon ___.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le possessif correct : 'J'adore ___ (mon/ma/mes) grand-mère car elle est très gentille.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Rédigez une phrase pour présenter votre frère ou votre sœur en français (prénom, âge, profession).", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez le lien de parenté : 'La fille de ma tante est ma ___.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Comment appelle-t-on le frère de votre mère en français ?\n(a) Le cousin\n(b) L'oncle\n(c) Le neveu", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez le déterminant possessif adéquat : '___ parents habitent dans une grande maison à Bordeaux.'\n(a) Mes\n(b) Mon\n(c) Ma", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "La sœur de mon père est ma :\n(a) Cousine\n(b) Nièce\n(c) Tante", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la phrase : 'Marc et Julie ont deux enfants : un fils et une ___.'\n(a) sœur\n(b) fille\n(c) mère", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent : 'Toute ma famille ___ (se réunir) le dimanche pour le déjeuner.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza a frase a seguir sobre família para o francês:", "texto_referencia": "Meus avós moram em uma casa perto do parque.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase sobre família em francês:", "texto_referencia": "Mon grand-père raconte toujours des histoires intéressantes à ses petits-enfants.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta com entonação clara:", "texto_referencia": "Ma famille est très unie : mes parents, mes deux frères et moi passons toutes nos vacances ensemble en Normandie.", "pontuacao_maxima": 2.5}
        ]
    },
    "verbes_present": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe du 1er groupe au présent : 'Nous ___ (parler) couramment français et portugais.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la terminaison correcte : 'Ils écout___ de la musique classique chaque soir.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au présent de l'indicatif : 'Tu ___ (habiter) dans quel quartier de Paris ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase avec le verbe 'aimer' au présent : 'Vous ___ (aimer) voyager pendant les vacances d'été ?'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle est la forme correcte au présent pour 'nous' avec le verbe 'manger' ?\n(a) mangons\n(b) mangeons\n(c) mangiez", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez la forme correcte : 'Elles ___ à l'université de la Sorbonne.'\n(a) étudient\n(b) étudies\n(c) étudiez", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle terminaison correspond au pronom 'tu' au présent pour les verbes en -er ?\n(a) -e\n(b) -es\n(c) -ent", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Je ___ (travailler) dans une entreprise internationale.'\n(a) travaille\n(b) travailles\n(c) travaillent", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent : 'Chaque matin, vous ___ (commencer) le travail à huit heures.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o presente do indicativo:", "texto_referencia": "Nós moramos em um belo apartamento no centro da cidade.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase em francês:", "texto_referencia": "Les étudiants préparent leurs devoirs de français avec beaucoup de sérieux.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta prestando atenção nas ligações:", "texto_referencia": "Nous habitons ensemble et nous partageons un grand appartement lumineux au centre-ville.", "pontuacao_maxima": 2.5}
        ]
    },
    "articles": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'article défini approprié (le, la, l', les) : '___ soleil brille et ___ oiseaux chantent dans le jardin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec l'article indéfini (un, une, des) : 'J'ai acheté ___ nouveau livre et ___ stylos pour l'école.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec un article partitif (du, de la, de l', des) : 'Au petit-déjeuner, je prends ___ café avec ___ confiture.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez au négatif en observant la règle de l'article : 'J'ai un vélo' -> 'Je n'ai pas ___ vélo.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quel article partitif convient pour : 'Il boit ___ eau minérale fraîche.' ?\n(a) du\n(b) de la\n(c) de l'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez l'article correct : 'C'est ___ amie brésilienne de Pierre.'\n(a) le\n(b) une\n(c) des", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Après une négation absolue, l'article indéfini ou partitif devient généralement :\n(a) du\n(b) des\n(c) de / d'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Vous mangez ___ fromage après le plat principal ?'\n(a) du\n(b) le\n(c) un", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec l'article contracté ou partitif approprié : 'Le professeur parle ___ (à + les) élèves ___ (de + le) prochain examen.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza prestando atenção aos artigos definidos e partitivos:", "texto_referencia": "Eu tomo café com leite e como um pedaço de pão de manhã.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva com os artigos corretos:", "texto_referencia": "Le matin, je bois du thé chaud et je mange des croissants au beurre.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para praticar a fluidez e a pronúncia das vogais nasais:", "texto_referencia": "Dans mon quartier, il y a une boulangerie artisanale, du bon pain frais et des commerces accueillants.", "pontuacao_maxima": 2.5}
        ]
    },
    "imparfait": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe à l'imparfait pour exprimer une habitude : 'Quand nous étions petits, nous ___ (jouer) tous les jours dans le jardin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez à l'imparfait : 'Pendant les vacances, il ___ (faire) toujours un temps magnifique.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Choisissez entre passé composé et imparfait : 'Pendant que je lisais tranquillement, le téléphone ___ (sonner).'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez le verbe 'être' à l'imparfait : 'À cette époque, vous ___ (être) étudiants à Paris.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle terminaison prend l'imparfait avec le pronom 'ils' ?\n(a) -aient\n(b) -ait\n(c) -iez", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle phrase exprime une description ou une habitude dans le passé ?\n(a) Soudain, il a plu.\n(b) Tous les étés, nous allions à la mer.\n(c) Hier, j'ai fini à midi.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez à l'imparfait : 'Tu ___ (finir) toujours tes cours à seize heures.'\n(a) finissais\n(b) finissait\n(c) as fini", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Le radical de l'imparfait se forme à partir de quelle personne du présent ?\n(a) Je\n(b) Nous\n(c) Ils", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez les deux verbes au temps approprié (imparfait vs passé composé) : 'Il ___ (faire) beau quand tout à coup l'orage ___ (éclater).'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês utilizando o Imparfait para expressar hábito passado:", "texto_referencia": "Quando eu era criança, eu lia muitos livros antes de dormir.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e escreva a frase em francês no imperfeito:", "texto_referencia": "Autrefois, le village était calme et les habitants vivaient simplement.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o trecho em voz alta prestando atenção na sonoridade do imperfeito:", "texto_referencia": "Quand j'avais dix ans, ma famille habitait dans un petit village au bord d'un lac magnifique.", "pontuacao_maxima": 2.5}
        ]
    },
    "pronoms": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Remplacez le mot souligné par le pronom COD approprié (le, la, l', les) : 'Je regarde ce film français ce soir' -> 'Je ___ regarde ce soir.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Remplacez le complément par un pronom COI (lui, leur) : 'Elle écrit une lettre à ses parents' -> 'Elle ___ écrit une lettre.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Répondez affirmativement en utilisant le pronom 'y' : 'Tu vas souvent au musée ?' -> 'Oui, j'___ vais souvent.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Répondez avec le pronom 'en' : 'Tu manges des fruits chaque jour ?' -> 'Oui, j'___ mange tous les jours.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quel pronom remplace 'à mon professeur' dans 'Je pose une question à mon professeur' ?\n(a) le\n(b) lui\n(c) leur", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Où se place le pronom personnel au passé composé ?\n(a) Après le participe passé\n(b) Entre l'auxiliaire et le participe\n(c) Avant l'auxiliaire", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Remplacez le complément dans : 'Vous connaissez cette histoire ?'\n(a) Oui, nous la connaissons.\n(b) Oui, nous lui connaissons.\n(c) Oui, nous y connaissons.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Paul a acheté des croissants ? Oui, il ___ a acheté six.'\n(a) les\n(b) en\n(c) y", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Réécrivez la phrase en remplaçant les compléments par les pronoms COD/COI adéquats : 'Nous donnons ces clés à nos voisins.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza utilizando o pronome adequado em francês:", "texto_referencia": "Eu o vejo todos os dias na estação de metrô.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase com pronomes:", "texto_referencia": "Je lui ai expliqué la situation et il m'a écouté attentivement.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta articulando claramente os pronomes:", "texto_referencia": "Si vous avez des questions sur cette leçon, posez-les-moi dès la fin du cours.", "pontuacao_maxima": 2.5}
        ]
    },
    "conditionnel_subjonctif": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Mettez le verbe au conditionnel présent pour exprimer un souhait poli : 'Nous ___ (vouloir) réserver une table pour deux personnes.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la structure de l'hypothèse : 'Si j'avais plus de temps, je ___ (voyager) à travers toute la France.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le verbe au subjonctif présent : 'Il faut absolument que vous ___ (faire) vos exercices.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au subjonctif après l'expression de volonté : 'Je souhaite qu'il ___ (venir) à notre réunion demain.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle forme est au conditionnel présent pour le verbe 'pouvoir' ?\n(a) Je pourrai\n(b) Je pourrais\n(c) Je peux", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle conjonction exige obligatoirement le subjonctif ?\n(a) Pour que\n(b) Parce que\n(c) Pendant que", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez au subjonctif : 'Il est important que nous ___ (être) à l'heure.'\n(a) sommes\n(b) soyons\n(c) serons", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez la formule de politesse : '___ (Aimer)-vous un verre d'eau fraîche ?'\n(a) Aimerez\n(b) Aimeriez\n(c) Aimez", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez au subjonctif présent : 'Le professeur exige que tous les étudiants ___ (apprendre) cette règle.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza utilizando o condicional de polidez:", "texto_referencia": "Eu gostaria de pedir um café e a conta, por favor.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase em francês:", "texto_referencia": "Il faudrait partir plus tôt pour éviter les embouteillages du matin.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta para avaliar a entonação da hipótese:", "texto_referencia": "Si nous avions l'opportunité de vivre à Paris, nous visiterions tous les musées et jardins historiques.", "pontuacao_maxima": 2.5}
        ]
    },
    "prepositions": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de pays appropriée (en, au, aux) : 'Cet été, je vais passer mes vacances ___ France, puis ___ Portugal et enfin ___ États-Unis.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de ville ou de moyen de transport : 'Marie habite ___ Lyon et elle se déplace toujours ___ vélo.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec la préposition de lieu appropriée (sur, sous, devant, derrière, dans) : 'Le chat dort paisiblement ___ la table du salon.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez : 'Nous allons ___ (à + le) cinéma ce soir, puis ___ (à + le) restaurant avec nos amis.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle préposition s'utilise devant un pays féminin comme la France ou l'Italie ?\n(a) à\n(b) en\n(c) au", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Mon frère travaille ___ Brésil depuis deux ans.'\n(a) en\n(b) au\n(c) à", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Devant un nom de ville, on utilise la préposition :\n(a) au\n(b) à\n(c) en", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'La pharmacie se trouve juste ___ face de la gare centrale.'\n(a) en\n(b) à\n(c) de", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Complétez avec la préposition contractée (au, à la, à l', aux) : 'Dimanche, nous allons ___ (à + le) marché et les enfants vont ___ (à + les) manèges.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza com as preposições de lugar e transporte corretas:", "texto_referencia": "Eu moro em Paris e vou ao trabalho de metrô todos os dias.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva a frase sobre deslocamentos:", "texto_referencia": "Nous voyageons en train pour visiter plusieurs villes en France et en Belgique.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta prestando atenção nas preposições e na melodia frasal:", "texto_referencia": "Pour aller au musée depuis l'hôtel, traversez le pont, tournez à droite sur le boulevard et continuez tout droit.", "pontuacao_maxima": 2.5}
        ]
    },
    "salutations": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez le dialogue de salutation : '- Bonjour, comment allez-vous ? - Je vais très bien, ___ (merci / de rien) !'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la présentation personnelle : 'Je m'___ (appeler) Lucas et j'ai vingt-quatre ans.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Associez la formule formelle pour prendre congé : 'Au ___ (revoir / merci) et bonne journée, Monsieur.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez la réponse de nationalité : 'De quelle nationalité êtes-vous ? - Je suis ___ (brésilien / brésilienne).'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Quelle formule de salutation est appropriée pour une rencontre formelle le soir ?\n(a) Salut !\n(b) Bonsoir Monsieur.\n(c) Coucou !", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Pour demander poliment le nom de quelqu'un, on dit :\n(a) Comment vous vous appelez ?\n(b) C'est qui toi ?\n(c) Tu as quel nom ?", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle est la réponse la plus courante à 'Enchanté' ?\n(a) Au revoir.\n(b) Enchanté(e), de même.\n(c) S'il vous plaît.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Comment ça va ? - Ça va ___ , merci !'\n(a) bien\n(b) bon\n(c) beau", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe 's'appeler' au présent : 'Comment vous ___ (s'appeler), Madame ?'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza as saudações e apresentação para o francês:", "texto_referencia": "Bom dia, eu me chamo Jean e sou estudante de francês.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio e transcreva as saudações em francês:", "texto_referencia": "Bonjour madame, enchanté de faire votre connaissance aujourd'hui.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia em voz alta simulando uma apresentação formal e amigável:", "texto_referencia": "Bonjour à toutes et à tous, je m'appelle Julien et je suis très heureux d'être ici avec vous pour ce cours de français.", "pontuacao_maxima": 2.5}
        ]
    },
    "geral": {
        "exercicios": [
            {"tipo_questao": "exercicio", "enunciado": "Complétez la phrase en conjuguant le verbe entre parenthèses au présent : 'Chaque jour, nous ___ (étudier) la langue et la culture françaises.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Complétez avec le pronom ou l'article adéquat : 'Marie a acheté ___ beau bouquet de fleurs pour son amie.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Mettez la phrase suivante à la forme négative : 'Pierre boit toujours du café le matin.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "exercicio", "enunciado": "Conjuguez au passé composé : 'Hier soir, les enfants ___ (dormir) très tôt.'", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "testes": [
            {"tipo_questao": "teste", "enunciado": "Choisissez la bonne forme pour compléter : 'Nous ___ le dîner à vingt heures.'\n(a) préparons\n(b) préparent\n(c) préparez", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Quelle est la phrase correcte au passé composé ?\n(a) Elle est venu hier.\n(b) Elle est venue hier.\n(c) Elle a venue hier.", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Complétez : 'Je ne bois ___ de café après dix-sept heures.'\n(a) pas\n(b) rien\n(c) aucun", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "teste", "enunciado": "Choisissez le mot correct : 'C'est un exercice très ___ pour s'entraîner.'\n(a) utile\n(b) utilise\n(c) utilité", "texto_referencia": "", "pontuacao_maxima": 2.5}
        ],
        "prova": [
            {"tipo_questao": "conjugacao", "enunciado": "Conjuguez le verbe entre parenthèses au présent de l'indicatif : 'Nous ___ (choisir) d'étudier le français avec enthousiasme.'", "texto_referencia": "", "pontuacao_maxima": 2.5},
            {"tipo_questao": "traducao", "enunciado": "Traduza para o francês a seguinte frase com precisão gramatical:", "texto_referencia": "Eu estudo francês todos os dias para viajar pela Europa.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "ditado", "enunciado": "Ouça o áudio com atenção e transcreva a frase em francês:", "texto_referencia": "La pratique régulière est essentielle pour progresser rapidement en français.", "pontuacao_maxima": 2.5},
            {"tipo_questao": "leitura_oral", "enunciado": "Leia o texto em voz alta com boa articulação e fluência:", "texto_referencia": "Apprendre une nouvelle langue permet de découvrir de nouvelles cultures et d'ouvrir son esprit au monde.", "pontuacao_maxima": 2.5}
        ]
    }
}

def mapear_chave_tema(tema: str) -> str:
    t = (tema or "").lower()
    if any(k in t for k in ["accord", "participe"]):
        return "accord_participe"
    if any(k in t for k in ["passé", "passe", "composé", "compose"]):
        return "passe_compose"
    if any(k in t for k in ["négat", "negat", "ne ... pas", "ne pas"]):
        return "negation"
    if any(k in t for k in ["famill", "parent"]):
        return "famille"
    if any(k in t for k in ["1er groupe", "présent", "present", "verbe"]):
        return "verbes_present"
    if any(k in t for k in ["article", "défini", "defini", "indéfini", "indefini", "partitif"]):
        return "articles"
    if any(k in t for k in ["imparfait"]):
        return "imparfait"
    if any(k in t for k in ["pronom", "cod", "coi"]):
        return "pronoms"
    if any(k in t for k in ["conditionnel", "subjonctif", "hypothèse", "hypothese"]):
        return "conditionnel_subjonctif"
    if any(k in t for k in ["préposition", "preposition", "lieu", "déplacement", "deplacement"]):
        return "prepositions"
    if any(k in t for k in ["salutation", "présentation", "presentation"]):
        return "salutations"
    return "geral"

def gerar_questoes_pedagogicas_completas(tema: str, nivel: str = "A2", tipo: str = "Prova", quantidade: int = 4) -> list:
    chave = mapear_chave_tema(tema)
    banco_tema = BANCO_PEDAGOGICO_TEMAS.get(chave, BANCO_PEDAGOGICO_TEMAS["geral"])
    tipo_l = (tipo or "").strip().lower()

    if tipo_l in ["exercicios", "exercício", "exercicio", "exercícios"]:
        pool = banco_tema.get("exercicios", BANCO_PEDAGOGICO_TEMAS["geral"]["exercicios"])
        res = [dict(q) for q in pool]
        while len(res) < quantidade:
            res.extend([dict(q) for q in BANCO_PEDAGOGICO_TEMAS["geral"]["exercicios"]])
        return res[:quantidade]

    elif tipo_l in ["teste", "testes"]:
        pool = banco_tema.get("testes", BANCO_PEDAGOGICO_TEMAS["geral"]["testes"])
        res = [dict(q) for q in pool]
        while len(res) < quantidade:
            res.extend([dict(q) for q in BANCO_PEDAGOGICO_TEMAS["geral"]["testes"]])
        return res[:quantidade]

    else:
        pool = banco_tema.get("prova", BANCO_PEDAGOGICO_TEMAS["geral"]["prova"])
        return [dict(q) for q in pool]

def eh_questao_valida(q: dict) -> bool:
    enunciado = q.get("enunciado", "").strip()
    texto_ref = q.get("texto_referencia", "").strip()
    tipo_q = q.get("tipo_questao", "").strip().lower()

    if not enunciado or len(enunciado) < 10:
        return False

    # Proíbe enunciados puramente abstratos ou de fallback genérico
    proibidos = [
        "complétez les phrases en utilisant la règle",
        "transformez les phrases suivantes en appliquant",
        "rédigez deux phrases correctes",
        "test de connaissance: conjuguez",
        "choisissez ou écrivez la forme correcte en français concernant",
        "identifiez l'erreur dans la phrase et réécrivez-la",
        "question rapide: traduisez en français",
        "exercice de fallback 1",
        "conjuguez au présent ou passé composé selon le sujet",
        "traduisez la phrase suivante pour le français ("
    ]
    if any(p in enunciado.lower() for p in proibidos):
        return False

    if tipo_q == "traducao":
        if texto_ref in ["", "La phrase", "Tradução contextual", "A frase"] and not ('"' in enunciado or "'" in enunciado):
            return False

    if tipo_q in ["ditado", "leitura_oral"]:
        if len(texto_ref) < 8 or texto_ref in ["Le chat mange la souris.", "La phrase"]:
            return False

    # Exercícios e testes precisam de frase de contexto (com aspas, lacunas ou parênteses)
    if tipo_q in ["exercicio", "teste", "conjugacao"]:
        tem_frase = ('___' in enunciado) or ('"' in enunciado) or ("'" in enunciado) or ('(' in enunciado and ')' in enunciado)
        if not tem_frase:
            return False

    return True

def sanitizar_questoes_geradas(questoes: list, tema: str, nivel: str = "A2", tipo: str = "Prova", quantidade: int = 4) -> list:
    questoes_padrao = gerar_questoes_pedagogicas_completas(tema, nivel, tipo, quantidade)
    
    if not questoes:
        return questoes_padrao

    questoes_limpas = []
    for idx, q in enumerate(questoes):
        if eh_questao_valida(q):
            # Garante que campos obrigatórios existam
            questoes_limpas.append({
                "tipo_questao": q.get("tipo_questao", "exercicio"),
                "enunciado": q.get("enunciado", "").strip(),
                "texto_referencia": q.get("texto_referencia", "").strip(),
                "pontuacao_maxima": float(q.get("pontuacao_maxima", 2.5))
            })
        else:
            # Substitui questão inválida pela do banco pedagógico correspondente
            substituta = questoes_padrao[idx % len(questoes_padrao)]
            questoes_limpas.append(dict(substituta))

    # Garante quantidade solicitada
    while len(questoes_limpas) < quantidade and tipo.lower() in ["exercicios", "exercício", "exercicio", "exercícios", "teste", "testes"]:
        questoes_limpas.append(dict(questoes_padrao[len(questoes_limpas) % len(questoes_padrao)]))

    return questoes_limpas

if __name__ == "__main__":
    teste_corrompidas = [
        {"tipo_questao": "exercicio", "enunciado": "Complétez les phrases en utilisant la règle appropriée de 'L'Accord du Participe Passé'.", "texto_referencia": ""},
        {"tipo_questao": "exercicio", "enunciado": "Transformez les phrases suivantes en appliquant le sujet 'L'Accord du Participe Passé'.", "texto_referencia": ""},
        {"tipo_questao": "exercicio", "enunciado": "Traduisez vers le français en respectant 'L'Accord du Participe Passé': 'Eu gosto de estudar francês'.", "texto_referencia": ""},
        {"tipo_questao": "exercicio", "enunciado": "Faites l'accord du participe passé : 'Ces photos, je les ai ___ (prendre) en vacances.'", "texto_referencia": ""}
    ]
    limpas = sanitizar_questoes_geradas(teste_corrompidas, "L'Accord du Participe Passé", "A2", "Exercícios", 4)
    print("Sanitizadas:")
    for q in limpas:
        print(f" -> {q['enunciado']}")
