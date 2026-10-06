# -*- coding: utf-8 -*-
"""
guia_fle_data.py - Base de Dados Pedagógica Completa para o Guia FLE
Contém dados estruturados de conjugação de verbos (Maison d'Être e Essenciais)
e os 10 temas gramaticais com dezenas de exemplos enriquecidos, traduções e explicações.
"""

VERBOS_CONJUGADOS = {
    "aller": {
        "verbo": "Aller",
        "traducao": "Ir",
        "auxiliaire": "Être",
        "participe_passe": "allé (allée, allés, allées)",
        "grupo": "3º Grupo (Irregular / Maison d'Être)",
        "dica_uso": "Verbo de movimento por excelência. No Passé Composé, concorda sempre em gênero e número com o sujeito.",
        "present": {
            "je": "vais", "tu": "vas", "il/elle/on": "va",
            "nous": "allons", "vous": "allez", "ils/elles": "vont"
        },
        "passe_compose": {
            "je": "suis allé(e)", "tu": "es allé(e)", "il/elle": "est allé(e)",
            "nous": "sommes allé(e)s", "vous": "êtes allé(e)(s)", "ils/elles": "sont allé(e)s"
        },
        "imparfait": {
            "je": "allais", "tu": "allais", "il/elle": "allait",
            "nous": "allions", "vous": "alliez", "ils/elles": "allaient"
        },
        "futur_simple": {
            "je": "irai", "tu": "iras", "il/elle": "ira",
            "nous": "irons", "vous": "irez", "ils/elles": "iront"
        },
        "conditionnel": {
            "je": "irais", "tu": "irais", "il/elle": "irait",
            "nous": "irions", "vous": "iriez", "ils/elles": "iraient"
        },
        "imperatif": ["Va !", "Allons !", "Allez !"],
        "exemplos": [
            {"fr": "Je vais à la boulangerie chercher des croissants chauds.", "pt": "Vou à padaria buscar croissants quentes."},
            {"fr": "Elle est allée à Paris pour son stage professionnel.", "pt": "Ela foi a Paris para seu estágio profissional."},
            {"fr": "Demain, nous irons visiter le musée du Louvre.", "pt": "Amanhã iremos visitar o museu do Louvre."}
        ]
    },
    "venir": {
        "verbo": "Venir",
        "traducao": "Vir",
        "auxiliaire": "Être",
        "participe_passe": "venu (venue, venus, venues)",
        "grupo": "3º Grupo (Irregular / Maison d'Être)",
        "dica_uso": "Indica movimento de proveniência ou aproximação. Usado também no Passé Récent: venir de + infinitif.",
        "present": {
            "je": "viens", "tu": "viens", "il/elle/on": "vient",
            "nous": "venons", "vous": "venez", "ils/elles": "viennent"
        },
        "passe_compose": {
            "je": "suis venu(e)", "tu": "es venu(e)", "il/elle": "est venu(e)",
            "nous": "sommes venu(e)s", "vous": "êtes venu(e)(s)", "ils/elles": "sont venu(e)s"
        },
        "imparfait": {
            "je": "venais", "tu": "venais", "il/elle": "venait",
            "nous": "venions", "vous": "veniez", "ils/elles": "venaient"
        },
        "futur_simple": {
            "je": "viendrai", "tu": "viendras", "il/elle": "viendra",
            "nous": "viendrons", "vous": "viendrez", "ils/elles": "viendront"
        },
        "conditionnel": {
            "je": "viendrais", "tu": "viendrais", "il/elle": "viendrait",
            "nous": "viendrions", "vous": "viendriez", "ils/elles": "viendraient"
        },
        "imperatif": ["Viens !", "Venons !", "Venez !"],
        "exemplos": [
            {"fr": "Tu viens avec nous au cinéma ce soir ?", "pt": "Você vem conosco ao cinema hoje à noite?"},
            {"fr": "Ils sont venus de Marseille en train à grande vitesse.", "pt": "Eles vieram de Marselha no trem de alta velocidade."},
            {"fr": "Je viens de terminer mes devoirs de français.", "pt": "Acabei de terminar minha lição de francês (Passé Récent)."}
        ]
    },
    "arriver": {
        "verbo": "Arriver",
        "traducao": "Chegar",
        "auxiliaire": "Être",
        "participe_passe": "arrivé (arrivée, arrivés, arrivées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Verbo regular em -er conjugado com Être no Passé Composé.",
        "present": {
            "je": "arrive", "tu": "arrives", "il/elle/on": "arrive",
            "nous": "arrivons", "vous": "arrivez", "ils/elles": "arrivent"
        },
        "passe_compose": {
            "je": "suis arrivé(e)", "tu": "es arrivé(e)", "il/elle": "est arrivé(e)",
            "nous": "sommes arrivé(e)s", "vous": "êtes arrivé(e)(s)", "ils/elles": "sont arrivé(e)s"
        },
        "imparfait": {
            "je": "arrivais", "tu": "arrivais", "il/elle": "arrivait",
            "nous": "arrivions", "vous": "arriviez", "ils/elles": "arrivaient"
        },
        "futur_simple": {
            "je": "arriverai", "tu": "arriveras", "il/elle": "arrivera",
            "nous": "arriverons", "vous": "arriverez", "ils/elles": "arriveront"
        },
        "conditionnel": {
            "je": "arriverais", "tu": "arriverais", "il/elle": "arriverait",
            "nous": "arriverions", "vous": "arriveriez", "ils/elles": "arriveraient"
        },
        "imperatif": ["Arrive !", "Arrivons !", "Arrivez !"],
        "exemplos": [
            {"fr": "Le train arrive à quai à 14h15 précises.", "pt": "O trem chega à plataforma às 14h15 em ponto."},
            {"fr": "Marie est arrivée en retard à cause de la pluie.", "pt": "Marie chegou atrasada por causa da chuva."}
        ]
    },
    "partir": {
        "verbo": "Partir",
        "traducao": "Partir / Ir embora / Sair em viagem",
        "auxiliaire": "Être",
        "participe_passe": "parti (partie, partis, parties)",
        "grupo": "3º Grupo (Maison d'Être)",
        "dica_uso": "Oposto de arriver/venir. Cuidado: partir de = partir de algum lugar; partir pour = partir com destino a.",
        "present": {
            "je": "pars", "tu": "pars", "il/elle/on": "part",
            "nous": "partons", "vous": "partez", "ils/elles": "partent"
        },
        "passe_compose": {
            "je": "suis parti(e)", "tu": "es parti(e)", "il/elle": "est parti(e)",
            "nous": "sommes parti(e)s", "vous": "êtes parti(e)(s)", "ils/elles": "sont parti(e)s"
        },
        "imparfait": {
            "je": "partais", "tu": "partais", "il/elle": "partait",
            "nous": "partions", "vous": "partiez", "ils/elles": "partaient"
        },
        "futur_simple": {
            "je": "partirai", "tu": "partiras", "il/elle": "partira",
            "nous": "partirons", "vous": "partirez", "ils/elles": "partiront"
        },
        "conditionnel": {
            "je": "partirais", "tu": "partirais", "il/elle": "partirait",
            "nous": "partirions", "vous": "partiriez", "ils/elles": "partiraient"
        },
        "imperatif": ["Pars !", "Partons !", "Partez !"],
        "exemplos": [
            {"fr": "Nous partons en vacances en Bretagne vendredi.", "pt": "Partimos em férias para a Bretanha na sexta-feira."},
            {"fr": "Mes collègues sont déjà partis du bureau.", "pt": "Meus colegas já foram embora do escritório."}
        ]
    },
    "entrer": {
        "verbo": "Entrer",
        "traducao": "Entrar",
        "auxiliaire": "Être",
        "participe_passe": "entré (entrée, entrés, entrées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Geralmente acompanhado de dans: entrer dans la pièce.",
        "present": {
            "je": "entre", "tu": "entres", "il/elle/on": "entre",
            "nous": "entrons", "vous": "entrez", "ils/elles": "entrent"
        },
        "passe_compose": {
            "je": "suis entré(e)", "tu": "es entré(e)", "il/elle": "est entré(e)",
            "nous": "sommes entré(e)s", "vous": "êtes entré(e)(s)", "ils/elles": "sont entré(e)s"
        },
        "imparfait": {
            "je": "entrais", "tu": "entrais", "il/elle": "entrait",
            "nous": "entrions", "vous": "entriez", "ils/elles": "entraient"
        },
        "futur_simple": {
            "je": "entrerai", "tu": "entreras", "il/elle": "entrera",
            "nous": "entrerons", "vous": "entrerez", "ils/elles": "entreront"
        },
        "conditionnel": {
            "je": "entrerais", "tu": "entrerais", "il/elle": "entrerait",
            "nous": "entrerions", "vous": "entreriez", "ils/elles": "entreraient"
        },
        "imperatif": ["Entre !", "Entrons !", "Entrez !"],
        "exemplos": [
            {"fr": "Entrez, je vous en prie, faites comme chez vous !", "pt": "Entre, por favor, fique à vontade!"},
            {"fr": "Elle est entrée discrètement dans la salle de classe.", "pt": "Ela entrou discretamente na sala de aula."}
        ]
    },
    "sortir": {
        "verbo": "Sortir",
        "traducao": "Sair (Maison d'Être) / Tirar (com Avoir)",
        "auxiliaire": "Être (intransitivo) / Avoir (transitivo direto)",
        "participe_passe": "sorti (sortie, sortis, sorties)",
        "grupo": "3º Grupo (Maison d'Être)",
        "dica_uso": "Atenção: Je suis sorti(e) = Eu saí; J'ai sorti mon passeport = Tirei meu passaporte da bolsa (com COD usa AVOIR).",
        "present": {
            "je": "sors", "tu": "sors", "il/elle/on": "sort",
            "nous": "sortons", "vous": "sortez", "ils/elles": "sortent"
        },
        "passe_compose": {
            "je": "suis sorti(e)", "tu": "es sorti(e)", "il/elle": "est sorti(e)",
            "nous": "sommes sorti(e)s", "vous": "êtes sorti(e)(s)", "ils/elles": "sont sorti(e)s"
        },
        "imparfait": {
            "je": "sortais", "tu": "sortais", "il/elle": "sortait",
            "nous": "sortions", "vous": "sortiez", "ils/elles": "sortaient"
        },
        "futur_simple": {
            "je": "sortirai", "tu": "sortiras", "il/elle": "sortira",
            "nous": "sortirons", "vous": "sortirez", "ils/elles": "sortiront"
        },
        "conditionnel": {
            "je": "sortirais", "tu": "sortirais", "il/elle": "sortirait",
            "nous": "sortirions", "vous": "sortiriez", "ils/elles": "sortiraient"
        },
        "imperatif": ["Sors !", "Sortons !", "Sortez !"],
        "exemplos": [
            {"fr": "Nous sommes sortis dîner dans un bistrot parisien.", "pt": "Saímos para jantar num bistrô parisiense."},
            {"fr": "Il a sorti son carnet pour noter l'adresse.", "pt": "Ele tirou o bloco de notas para anotar o endereço."}
        ]
    },
    "monter": {
        "verbo": "Monter",
        "traducao": "Subir (Maison d'Être) / Subir algo (com Avoir)",
        "auxiliaire": "Être (intransitivo) / Avoir (transitivo)",
        "participe_passe": "monté (montée, montés, montées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Je suis monté(e) au 4e étage (Être). J'ai monté les valises (Avoir, pois há objeto direto).",
        "present": {
            "je": "monte", "tu": "montes", "il/elle/on": "monte",
            "nous": "montons", "vous": "montez", "ils/elles": "montent"
        },
        "passe_compose": {
            "je": "suis monté(e)", "tu": "es monté(e)", "il/elle": "est monté(e)",
            "nous": "sommes monté(e)s", "vous": "êtes monté(e)(s)", "ils/elles": "sont monté(e)s"
        },
        "imparfait": {
            "je": "montais", "tu": "montais", "il/elle": "montait",
            "nous": "montions", "vous": "montiez", "ils/elles": "montoient"
        },
        "futur_simple": {
            "je": "monterai", "tu": "monteras", "il/elle": "montera",
            "nous": "monterons", "vous": "monterez", "ils/elles": "monteront"
        },
        "conditionnel": {
            "je": "monterais", "tu": "monterais", "il/elle": "monterait",
            "nous": "monterions", "vous": "monteriez", "ils/elles": "monteraient"
        },
        "imperatif": ["Monte !", "Montons !", "Montez !"],
        "exemplos": [
            {"fr": "Elle est montée par les escaliers car l'ascenseur est en panne.", "pt": "Ela subiu pelas escadas porque o elevador está quebrado."},
            {"fr": "J'ai monté les valises dans la chambre.", "pt": "Subi as malas para o quarto (uso com AVOIR)."}
        ]
    },
    "descendre": {
        "verbo": "Descendre",
        "traducao": "Descer (Maison d'Être) / Baixar algo (com Avoir)",
        "auxiliaire": "Être (intransitivo) / Avoir (transitivo)",
        "participe_passe": "descendu (descendue, descendus, descendues)",
        "grupo": "3º Grupo (-re / Maison d'Être)",
        "dica_uso": "Oposto de monter. Ex: Je suis descendu du bus (Être) vs J'ai descendu la poubelle (Avoir).",
        "present": {
            "je": "descends", "tu": "descends", "il/elle/on": "descend",
            "nous": "descendons", "vous": "descendez", "ils/elles": "descendent"
        },
        "passe_compose": {
            "je": "suis descendu(e)", "tu": "es descendu(e)", "il/elle": "est descendu(e)",
            "nous": "sommes descendu(e)s", "vous": "êtes descendu(e)(s)", "ils/elles": "sont descendu(e)s"
        },
        "imparfait": {
            "je": "descendais", "tu": "descendais", "il/elle": "descendait",
            "nous": "descendions", "vous": "descendiez", "ils/elles": "descendaient"
        },
        "futur_simple": {
            "je": "descendrai", "tu": "descendras", "il/elle": "descendra",
            "nous": "descendrons", "vous": "descendrez", "ils/elles": "descendront"
        },
        "conditionnel": {
            "je": "descendrais", "tu": "descendrais", "il/elle": "descendrait",
            "nous": "descendrions", "vous": "descendriez", "ils/elles": "descendraient"
        },
        "imperatif": ["Descends !", "Descendons !", "Descendez !"],
        "exemplos": [
            {"fr": "À quelle station de métro descendez-vous ?", "pt": "Em qual estação de metrô vocês descem?"},
            {"fr": "Ils sont descendus au rez-de-chaussée.", "pt": "Eles desceram ao térreo."}
        ]
    },
    "naitre": {
        "verbo": "Naître",
        "traducao": "Nascer",
        "auxiliaire": "Être",
        "participe_passe": "né (née, nés, nées)",
        "grupo": "3º Grupo (Maison d'Être)",
        "dica_uso": "Atenção ao particípio irregular né. Concordância: Je suis né(e), elle est née.",
        "present": {
            "je": "nais", "tu": "nais", "il/elle/on": "naît",
            "nous": "naissons", "vous": "naissez", "ils/elles": "naissent"
        },
        "passe_compose": {
            "je": "suis né(e)", "tu": "es né(e)", "il/elle": "est né(e)",
            "nous": "sommes né(e)s", "vous": "êtes né(e)(s)", "ils/elles": "sont né(e)s"
        },
        "imparfait": {
            "je": "naissais", "tu": "naissais", "il/elle": "naissait",
            "nous": "naissions", "vous": "naissiez", "ils/elles": "naissaient"
        },
        "futur_simple": {
            "je": "naîtrai", "tu": "naîtras", "il/elle": "naîtra",
            "nous": "naîtrons", "vous": "naîtrez", "ils/elles": "naîtront"
        },
        "conditionnel": {
            "je": "naîtrais", "tu": "naîtrais", "il/elle": "naîtrait",
            "nous": "naîtrions", "vous": "naîtriez", "ils/elles": "naîtraient"
        },
        "imperatif": ["Nais !", "Naissons !", "Naissez !"],
        "exemplos": [
            {"fr": "Victor Hugo est né à Besançon en 1802.", "pt": "Victor Hugo nasceu em Besançon em 1802."},
            {"fr": "Je suis né au Brésil, mais j'ai grandi en France.", "pt": "Nasci no Brasil, mas cresci na França."}
        ]
    },
    "mourir": {
        "verbo": "Mourir",
        "traducao": "Morrer",
        "auxiliaire": "Être",
        "participe_passe": "mort (morte, morts, mortes)",
        "grupo": "3º Grupo (Maison d'Être)",
        "dica_uso": "Particípio irregular: mort / morte. Ex: Elle est morte l'an dernier.",
        "present": {
            "je": "meurs", "tu": "meurs", "il/elle/on": "meurt",
            "nous": "mourons", "vous": "mourez", "ils/elles": "meurent"
        },
        "passe_compose": {
            "je": "suis mort(e)", "tu": "es mort(e)", "il/elle": "est mort(e)",
            "nous": "sommes mort(e)s", "vous": "êtes mort(e)(s)", "ils/elles": "sont mort(e)s"
        },
        "imparfait": {
            "je": "mourais", "tu": "mourais", "il/elle": "mourait",
            "nous": "mourions", "vous": "mouriez", "ils/elles": "mouraient"
        },
        "futur_simple": {
            "je": "mourrai", "tu": "mourras", "il/elle": "mourra",
            "nous": "mourrons", "vous": "mourrez", "ils/elles": "mourront"
        },
        "conditionnel": {
            "je": "mourrais", "tu": "mourrais", "il/elle": "mourrait",
            "nous": "mourrions", "vous": "mourriez", "ils/elles": "mourraient"
        },
        "imperatif": ["Meurs !", "Mourons !", "Mourez !"],
        "exemplos": [
            {"fr": "Molière est mort après la quatrième représentation du Malade imaginaire.", "pt": "Molière morreu após a quarta apresentação de O Doente Imaginário."},
            {"fr": "Les feuilles mortes tombent en automne.", "pt": "As folhas secas caem no outono."}
        ]
    },
    "rester": {
        "verbo": "Rester",
        "traducao": "Ficar / Permanecer",
        "auxiliaire": "Être",
        "participe_passe": "resté (restée, restés, restées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Falso cognato: NÃO significa 'restar' apenas, significa principalmente 'ficar em algum lugar'.",
        "present": {
            "je": "reste", "tu": "restes", "il/elle/on": "reste",
            "nous": "restons", "vous": "restez", "ils/elles": "restent"
        },
        "passe_compose": {
            "je": "suis resté(e)", "tu": "es resté(e)", "il/elle": "est resté(e)",
            "nous": "sommes resté(e)s", "vous": "êtes resté(e)(s)", "ils/elles": "sont resté(e)s"
        },
        "imparfait": {
            "je": "restais", "tu": "restais", "il/elle": "restait",
            "nous": "restions", "vous": "restiez", "ils/elles": "restaient"
        },
        "futur_simple": {
            "je": "resterai", "tu": "resteras", "il/elle": "restera",
            "nous": "resterons", "vous": "resterez", "ils/elles": "resteront"
        },
        "conditionnel": {
            "je": "resterais", "tu": "resterais", "il/elle": "resterait",
            "nous": "resterions", "vous": "resteriez", "ils/elles": "resteraient"
        },
        "imperatif": ["Reste !", "Restons !", "Restez !"],
        "exemplos": [
            {"fr": "Dimanche dernier, nous sommes restés à la maison à cause du froid.", "pt": "No domingo passado, ficamos em casa por causa do frio."},
            {"fr": "Reste calme, tout va bien se passer !", "pt": "Fique calmo, tudo vai dar certo!"}
        ]
    },
    "tomber": {
        "verbo": "Tomber",
        "traducao": "Cair",
        "auxiliaire": "Être",
        "participe_passe": "tombé (tombée, tombés, tombées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Usado para quedas físicas e expressões como: tomber amoureux (apaixonar-se), tomber malade (adoecer).",
        "present": {
            "je": "tombe", "tu": "tombes", "il/elle/on": "tombe",
            "nous": "tombons", "vous": "tombez", "ils/elles": "tombent"
        },
        "passe_compose": {
            "je": "suis tombé(e)", "tu": "es tombé(e)", "il/elle": "est tombé(e)",
            "nous": "sommes tombé(e)s", "vous": "êtes tombé(e)(s)", "ils/elles": "sont tombé(e)s"
        },
        "imparfait": {
            "je": "tombais", "tu": "tombais", "il/elle": "tombait",
            "nous": "tombions", "vous": "tombiez", "ils/elles": "tombaient"
        },
        "futur_simple": {
            "je": "tomberai", "tu": "tomberas", "il/elle": "tombera",
            "nous": "tomberons", "vous": "tomberez", "ils/elles": "tomberont"
        },
        "conditionnel": {
            "je": "tomberais", "tu": "tomberais", "il/elle": "tomberait",
            "nous": "tomberions", "vous": "tomberiez", "ils/elles": "tomberaient"
        },
        "imperatif": ["Tombe !", "Tombons !", "Tombez !"],
        "exemplos": [
            {"fr": "La neige est tombée toute la nuit sur les Alpes.", "pt": "A neve caiu a noite toda sobre os Alpes."},
            {"fr": "Il est tombé amoureux au premier regard.", "pt": "Ele se apaixonou à primeira vista."}
        ]
    },
    "retourner": {
        "verbo": "Retourner",
        "traducao": "Retornar / Voltar",
        "auxiliaire": "Être (intransitivo) / Avoir (transitivo)",
        "participe_passe": "retourné (retournée, retournés, retournées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Je suis retourné en France (retornei). J'ai retourné la crêpe (virei a panqueca - com Avoir).",
        "present": {
            "je": "retourne", "tu": "retournes", "il/elle/on": "retourne",
            "nous": "retournons", "vous": "retournez", "ils/elles": "retournent"
        },
        "passe_compose": {
            "je": "suis retourné(e)", "tu": "es retourné(e)", "il/elle": "est retourné(e)",
            "nous": "sommes retourné(e)s", "vous": "êtes retourné(e)(s)", "ils/elles": "sont retourné(e)s"
        },
        "imparfait": {
            "je": "retournais", "tu": "retournais", "il/elle": "retournait",
            "nous": "retournions", "vous": "retourniez", "ils/elles": "retournaient"
        },
        "futur_simple": {
            "je": "retournerai", "tu": "retourneras", "il/elle": "retournera",
            "nous": "retournerons", "vous": "retournerez", "ils/elles": "retourneront"
        },
        "conditionnel": {
            "je": "retournerais", "tu": "retournerais", "il/elle": "retournerait",
            "nous": "retournerions", "vous": "retourneriez", "ils/elles": "retourneraient"
        },
        "imperatif": ["Retourne !", "Retournons !", "Retournez !"],
        "exemplos": [
            {"fr": "Après cinq ans, elle est retournée dans sa ville natale.", "pt": "Após cinco anos, ela retornou à sua cidade natal."},
            {"fr": "Nous y retournerons l'année prochaine.", "pt": "Retornaremos lá no próximo ano."}
        ]
    },
    "passer": {
        "verbo": "Passer",
        "traducao": "Passar",
        "auxiliaire": "Être (intransitivo) / Avoir (transitivo)",
        "participe_passe": "passé (passée, passés, passées)",
        "grupo": "1º Grupo (-er / Maison d'Être)",
        "dica_uso": "Je suis passé chez le médecin (passei pelo médico - Être). J'ai passé un examen (fiz uma prova - Avoir).",
        "present": {
            "je": "passe", "tu": "passes", "il/elle/on": "passe",
            "nous": "passons", "vous": "passez", "ils/elles": "passent"
        },
        "passe_compose": {
            "je": "suis passé(e)", "tu": "es passé(e)", "il/elle": "est passé(e)",
            "nous": "sommes passé(e)s", "vous": "êtes passé(e)(s)", "ils/elles": "sont passé(e)s"
        },
        "imparfait": {
            "je": "passais", "tu": "passais", "il/elle": "passait",
            "nous": "passions", "vous": "passiez", "ils/elles": "passaient"
        },
        "futur_simple": {
            "je": "passerai", "tu": "passeras", "il/elle": "passera",
            "nous": "passerons", "vous": "passerez", "ils/elles": "passeront"
        },
        "conditionnel": {
            "je": "passerais", "tu": "passerais", "il/elle": "passerait",
            "nous": "passerions", "vous": "passeriez", "ils/elles": "passeraient"
        },
        "imperatif": ["Passe !", "Passons !", "Passez !"],
        "exemplos": [
            {"fr": "Je suis passé te voir hier, mais tu n'étais pas là.", "pt": "Passei para te ver ontem, mas você não estava."},
            {"fr": "Nous avons passé d'excellentes vacances en Normandie.", "pt": "Passamos excelentes férias na Normandia (com AVOIR)."}
        ]
    },
    # VERBOS ESSENCIAIS IRREGULARES E REGULARES
    "etre": {
        "verbo": "Être",
        "traducao": "Ser / Estar",
        "auxiliaire": "Avoir",
        "participe_passe": "été (invariável)",
        "grupo": "Auxiliar Fundamental (Irregular)",
        "dica_uso": "Verbo basilar. O particípio passado été é invariável e seu auxiliar no Passé Composé é AVOIR (J'ai été).",
        "present": {
            "je": "suis", "tu": "es", "il/elle/on": "est",
            "nous": "sommes", "vous": "êtes", "ils/elles": "sont"
        },
        "passe_compose": {
            "je": "ai été", "tu": "as été", "il/elle": "a été",
            "nous": "avons été", "vous": "avez été", "ils/elles": "ont été"
        },
        "imparfait": {
            "je": "étais", "tu": "étais", "il/elle": "était",
            "nous": "étions", "vous": "étiez", "ils/elles": "étaient"
        },
        "futur_simple": {
            "je": "serai", "tu": "seras", "il/elle": "sera",
            "nous": "serons", "vous": "serez", "ils/elles": "seront"
        },
        "conditionnel": {
            "je": "serais", "tu": "serais", "il/elle": "serait",
            "nous": "serions", "vous": "seriez", "ils/elles": "seraient"
        },
        "imperatif": ["Sois !", "Soyons !", "Soyez !"],
        "exemplos": [
            {"fr": "Je suis ravi de faire votre connaissance.", "pt": "Estou encantado em conhecê-lo(a)."},
            {"fr": "Hier, elle a été très occupée avec ses révisions.", "pt": "Ontem ela esteve muito ocupada com suas revisões."},
            {"fr": "Si j'avais le temps, je serais plus détendu.", "pt": "Se eu tivesse tempo, estaria mais relaxado."}
        ]
    },
    "avoir": {
        "verbo": "Avoir",
        "traducao": "Ter / Haver",
        "auxiliaire": "Avoir",
        "participe_passe": "eu (pronuncia-se 'u')",
        "grupo": "Auxiliar Fundamental (Irregular)",
        "dica_uso": "Auxiliar da imensa maioria dos verbos franceses no Passé Composé. Usado para idade: J'ai 25 ans.",
        "present": {
            "je": "ai", "tu": "as", "il/elle/on": "a",
            "nous": "avons", "vous": "avez", "ils/elles": "ont"
        },
        "passe_compose": {
            "je": "ai eu", "tu": "as eu", "il/elle": "a eu",
            "nous": "avons eu", "vous": "avez eu", "ils/elles": "ont eu"
        },
        "imparfait": {
            "je": "avais", "tu": "avais", "il/elle": "avait",
            "nous": "avions", "vous": "aviez", "ils/elles": "avaient"
        },
        "futur_simple": {
            "je": "aurai", "tu": "auras", "il/elle": "aura",
            "nous": "aurons", "vous": "aurez", "ils/elles": "auront"
        },
        "conditionnel": {
            "je": "aurais", "tu": "aurais", "il/elle": "aurait",
            "nous": "aurions", "vous": "auriez", "ils/elles": "auraient"
        },
        "imperatif": ["Aie !", "Ayons !", "Ayez !"],
        "exemplos": [
            {"fr": "J'ai faim et j'ai soif après cette longue marche.", "pt": "Estou com fome e com sede após essa longa caminhada."},
            {"fr": "Nous avons eu la chance de trouver une place assise.", "pt": "Tivemos a sorte de encontrar um assento."},
            {"fr": "Il y a un bon café juste au coin de la rue.", "pt": "Há um bom café bem na esquina da rua."}
        ]
    },
    "faire": {
        "verbo": "Faire",
        "traducao": "Fazer",
        "auxiliaire": "Avoir",
        "participe_passe": "fait",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Usado também para o clima: Il fait beau, il fait chaud, il fait froid.",
        "present": {
            "je": "fais", "tu": "fais", "il/elle/on": "fait",
            "nous": "faisons", "vous": "faites", "ils/elles": "font"
        },
        "passe_compose": {
            "je": "ai fait", "tu": "as fait", "il/elle": "a fait",
            "nous": "avons fait", "vous": "avez fait", "ils/elles": "ont fait"
        },
        "imparfait": {
            "je": "faisais", "tu": "faisais", "il/elle": "faisait",
            "nous": "faisions", "vous": "faisiez", "ils/elles": "faisaient"
        },
        "futur_simple": {
            "je": "ferai", "tu": "feras", "il/elle": "fera",
            "nous": "ferons", "vous": "ferez", "ils/elles": "feront"
        },
        "conditionnel": {
            "je": "ferais", "tu": "ferais", "il/elle": "ferait",
            "nous": "ferions", "vous": "feriez", "ils/elles": "feraient"
        },
        "imperatif": ["Fais !", "Faisons !", "Faites !"],
        "exemplos": [
            {"fr": "Qu'est-ce que vous faites dans la vie ?", "pt": "O que você faz da vida?"},
            {"fr": "Aujourd'hui, il fait un soleil magnifique à Nice.", "pt": "Hoje faz um sol magnífico em Nice."},
            {"fr": "J'ai fait une tarte aux pommes pour le dessert.", "pt": "Fiz uma torta de maçã para a sobremesa."}
        ]
    },
    "prendre": {
        "verbo": "Prendre",
        "traducao": "Pegar / Tomar",
        "auxiliaire": "Avoir",
        "participe_passe": "pris",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Usado para transporte (prendre le métro) e refeições (prendre un café, prendre le petit-déjeuner).",
        "present": {
            "je": "prends", "tu": "prends", "il/elle/on": "prend",
            "nous": "prenons", "vous": "prenez", "ils/elles": "prennent"
        },
        "passe_compose": {
            "je": "ai pris", "tu": "as pris", "il/elle": "a pris",
            "nous": "avons pris", "vous": "avez pris", "ils/elles": "ont pris"
        },
        "imparfait": {
            "je": "prenais", "tu": "prenais", "il/elle": "prenait",
            "nous": "prenions", "vous": "preniez", "ils/elles": "prenaient"
        },
        "futur_simple": {
            "je": "prendrai", "tu": "prendras", "il/elle": "prendra",
            "nous": "prendrons", "vous": "prendrez", "ils/elles": "prendront"
        },
        "conditionnel": {
            "je": "prendrais", "tu": "prendrais", "il/elle": "prendrait",
            "nous": "prendrions", "vous": "prendriez", "ils/elles": "prendraient"
        },
        "imperatif": ["Prends !", "Prenons !", "Prenez !"],
        "exemplos": [
            {"fr": "Je prends un espresso et un croissant, s'il vous plaît.", "pt": "Vou tomar um expresso e um croissant, por favor."},
            {"fr": "Nous avons pris le train de huit heures.", "pt": "Pegamos o trem das oito horas."}
        ]
    },
    "pouvoir": {
        "verbo": "Pouvoir",
        "traducao": "Poder / Conseguir",
        "auxiliaire": "Avoir",
        "participe_passe": "pu",
        "grupo": "3º Grupo (Modal Irregular)",
        "dica_uso": "Verbo modal. No Conditionnel (Pourriez-vous...), expressa cortesia refinada.",
        "present": {
            "je": "peux", "tu": "peux", "il/elle/on": "peut",
            "nous": "pouvons", "vous": "pouvez", "ils/elles": "peuvent"
        },
        "passe_compose": {
            "je": "ai pu", "tu": "as pu", "il/elle": "a pu",
            "nous": "avons pu", "vous": "avez pu", "ils/elles": "ont pu"
        },
        "imparfait": {
            "je": "pouvais", "tu": "pouvais", "il/elle": "pouvait",
            "nous": "pouvions", "vous": "pouviez", "ils/elles": "pouvaient"
        },
        "futur_simple": {
            "je": "pourrai", "tu": "pourras", "il/elle": "pourra",
            "nous": "pourrons", "vous": "pourrez", "ils/elles": "pourront"
        },
        "conditionnel": {
            "je": "pourrais", "tu": "pourrais", "il/elle": "pourrait",
            "nous": "pourrions", "vous": "pourriez", "ils/elles": "pourraient"
        },
        "imperatif": ["(Inusitado)"],
        "exemplos": [
            {"fr": "Pourriez-vous m'indiquer le chemin de la gare ?", "pt": "Poderia me indicar o caminho da estação? (Cortesia)"},
            {"fr": "Je peux vous aider à porter ces sacs.", "pt": "Posso ajudar você a carregar estas sacolas."}
        ]
    },
    "vouloir": {
        "verbo": "Vouloir",
        "traducao": "Querer",
        "auxiliaire": "Avoir",
        "participe_passe": "voulu",
        "grupo": "3º Grupo (Modal Irregular)",
        "dica_uso": "Je voudrais (Conditionnel) é a fórmula essencial de polidez para pedidos: Je voudrais un café.",
        "present": {
            "je": "veux", "tu": "veux", "il/elle/on": "veut",
            "nous": "voulons", "vous": "voulez", "ils/elles": "veulent"
        },
        "passe_compose": {
            "je": "ai voulu", "tu": "as voulu", "il/elle": "a voulu",
            "nous": "avons voulu", "vous": "avez voulu", "ils/elles": "ont voulu"
        },
        "imparfait": {
            "je": "voulais", "tu": "voulais", "il/elle": "voulait",
            "nous": "voulions", "vous": "vouliez", "ils/elles": "voulaient"
        },
        "futur_simple": {
            "je": "voudrai", "tu": "voudras", "il/elle": "voudra",
            "nous": "voudrons", "vous": "voudrez", "ils/elles": "voudront"
        },
        "conditionnel": {
            "je": "voudrais", "tu": "voudrais", "il/elle": "voudrait",
            "nous": "voudrions", "vous": "voudriez", "ils/elles": "voudraient"
        },
        "imperatif": ["Veuille !", "Veuillons !", "Veuillez !"],
        "exemplos": [
            {"fr": "Je voudrais réserver une table pour deux personnes.", "pt": "Gostaria de reservar uma mesa para duas pessoas."},
            {"fr": "Veuillez patienter un instant, s'il vous plaît.", "pt": "Tenha a bondade de aguardar um instante, por favor."}
        ]
    },
    "devoir": {
        "verbo": "Devoir",
        "traducao": "Dever / Ter que",
        "auxiliaire": "Avoir",
        "participe_passe": "dû (due, dus, dues)",
        "grupo": "3º Grupo (Modal Irregular)",
        "dica_uso": "Particípio com acento circunflexo no masculino singular (dû) para diferenciar do artigo partitivo du.",
        "present": {
            "je": "dois", "tu": "dois", "il/elle/on": "doit",
            "nous": "devons", "vous": "devez", "ils/elles": "doivent"
        },
        "passe_compose": {
            "je": "ai dû", "tu": "as dû", "il/elle": "a dû",
            "nous": "avons dû", "vous": "avez dû", "ils/elles": "ont dû"
        },
        "imparfait": {
            "je": "devais", "tu": "devais", "il/elle": "devait",
            "nous": "devions", "vous": "deviez", "ils/elles": "devaient"
        },
        "futur_simple": {
            "je": "devrai", "tu": "devras", "il/elle": "devra",
            "nous": "devrons", "vous": "devrez", "ils/elles": "devront"
        },
        "conditionnel": {
            "je": "devrais", "tu": "devrais", "il/elle": "devrait",
            "nous": "devrions", "vous": "devriez", "ils/elles": "devraient"
        },
        "imperatif": ["Dois !", "Devons !", "Devez !"],
        "exemplos": [
            {"fr": "Nous devons partir tôt pour éviter les embouteillages.", "pt": "Devemos sair cedo para evitar os engarrafamentos."},
            {"fr": "Tu devrais te reposer un peu, tu as l'air fatigué.", "pt": "Você deveria descansar um pouco, parece cansado (conselho)."}
        ]
    },
    "savoir": {
        "verbo": "Savoir",
        "traducao": "Saber",
        "auxiliaire": "Avoir",
        "participe_passe": "su",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Savoir = saber fatos ou habilidades aprendidas (savoir nager). Connaître = conhecer pessoas ou lugares.",
        "present": {
            "je": "sais", "tu": "sais", "il/elle/on": "sait",
            "nous": "savons", "vous": "savez", "ils/elles": "savent"
        },
        "passe_compose": {
            "je": "ai su", "tu": "as su", "il/elle": "a su",
            "nous": "avons su", "vous": "avez su", "ils/elles": "ont su"
        },
        "imparfait": {
            "je": "savais", "tu": "savais", "il/elle": "savait",
            "nous": "savions", "vous": "saviez", "ils/elles": "savaient"
        },
        "futur_simple": {
            "je": "saurai", "tu": "sauras", "il/elle": "saura",
            "nous": "saurons", "vous": "saurez", "ils/elles": "sauront"
        },
        "conditionnel": {
            "je": "saurais", "tu": "saurais", "il/elle": "saurait",
            "nous": "saurions", "vous": "sauriez", "ils/elles": "sauraient"
        },
        "imperatif": ["Sache !", "Sachons !", "Sachez !"],
        "exemplos": [
            {"fr": "Je sais parler français et anglais couramment.", "pt": "Sei falar francês e inglês fluentemente."},
            {"fr": "Savez-vous à quelle heure commence la conférence ?", "pt": "Você sabe a que horas começa a conferência?"}
        ]
    },
    "dire": {
        "verbo": "Dire",
        "traducao": "Dizer",
        "auxiliaire": "Avoir",
        "participe_passe": "dit",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Cuidado com o vous no presente: vous DITES (e não disez).",
        "present": {
            "je": "dis", "tu": "dis", "il/elle/on": "dit",
            "nous": "disons", "vous": "dites", "ils/elles": "disent"
        },
        "passe_compose": {
            "je": "ai dit", "tu": "as dit", "il/elle": "a dit",
            "nous": "avons dit", "vous": "avez dit", "ils/elles": "ont dit"
        },
        "imparfait": {
            "je": "disais", "tu": "disais", "il/elle": "disait",
            "nous": "disions", "vous": "disiez", "ils/elles": "disaient"
        },
        "futur_simple": {
            "je": "dirai", "tu": "diras", "il/elle": "dira",
            "nous": "dirons", "vous": "direz", "ils/elles": "diront"
        },
        "conditionnel": {
            "je": "dirais", "tu": "dirais", "il/elle": "dirait",
            "nous": "dirions", "vous": "diriez", "ils/elles": "diraient"
        },
        "imperatif": ["Dis !", "Disons !", "Dites !"],
        "exemplos": [
            {"fr": "Qu'est-ce que vous dites ?", "pt": "O que o senhor / a senhora está dizendo?"},
            {"fr": "Elle a dit la vérité dès le début.", "pt": "Ela disse a verdade desde o início."}
        ]
    },
    "voir": {
        "verbo": "Voir",
        "traducao": "Ver",
        "auxiliaire": "Avoir",
        "participe_passe": "vu",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "No futuro e condicional a raiz é com dois r's: je verrai, je verrais.",
        "present": {
            "je": "vois", "tu": "vois", "il/elle/on": "voit",
            "nous": "voyons", "vous": "voyez", "ils/elles": "voient"
        },
        "passe_compose": {
            "je": "ai vu", "tu": "as vu", "il/elle": "a vu",
            "nous": "avons vu", "vous": "avez vu", "ils/elles": "ont vu"
        },
        "imparfait": {
            "je": "voyais", "tu": "voyais", "il/elle": "voyait",
            "nous": "voyions", "vous": "voyiez", "ils/elles": "voyaient"
        },
        "futur_simple": {
            "je": "verrai", "tu": "verras", "il/elle": "verra",
            "nous": "verrons", "vous": "verrez", "ils/elles": "verront"
        },
        "conditionnel": {
            "je": "verrais", "tu": "verrais", "il/elle": "verrait",
            "nous": "verrions", "vous": "verriez", "ils/elles": "verraient"
        },
        "imperatif": ["Vois !", "Voyons !", "Voyez !"],
        "exemplos": [
            {"fr": "Tu as vu ce nouveau film français ?", "pt": "Você viu esse novo filme francês?"},
            {"fr": "On se voit demain à midi pour déjeuner.", "pt": "A gente se vê amanhã ao meio-dia para almoçar."}
        ]
    },
    "parler": {
        "verbo": "Parler",
        "traducao": "Falar",
        "auxiliaire": "Avoir",
        "participe_passe": "parlé",
        "grupo": "1º Grupo (-er Regular)",
        "dica_uso": "Modelo perfeito dos verbos regulares do 1º grupo. No Passé Composé: j'ai parlé, tu as parlé.",
        "present": {
            "je": "parle", "tu": "parles", "il/elle/on": "parle",
            "nous": "parlons", "vous": "parlez", "ils/elles": "parlent"
        },
        "passe_compose": {
            "je": "ai parlé", "tu": "as parlé", "il/elle": "a parlé",
            "nous": "avons parlé", "vous": "avez parlé", "ils/elles": "ont parlé"
        },
        "imparfait": {
            "je": "parlais", "tu": "parlais", "il/elle": "parlait",
            "nous": "parlions", "vous": "parliez", "ils/elles": "parlaient"
        },
        "futur_simple": {
            "je": "parlerai", "tu": "parleras", "il/elle": "parlera",
            "nous": "parlerons", "vous": "parlerez", "ils/elles": "parleront"
        },
        "conditionnel": {
            "je": "parlerais", "tu": "parlerais", "il/elle": "parlerait",
            "nous": "parlerions", "vous": "parleriez", "ils/elles": "parleraient"
        },
        "imperatif": ["Parle !", "Parlons !", "Parlez !"],
        "exemplos": [
            {"fr": "Elle parle couramment français et portugais.", "pt": "Ela fala francês e português fluentemente."},
            {"fr": "Nous avons parlé de notre avenir pendant des heures.", "pt": "Conversamos sobre nosso futuro durante horas."}
        ]
    },
    "finir": {
        "verbo": "Finir",
        "traducao": "Terminar / Concluir",
        "auxiliaire": "Avoir",
        "participe_passe": "fini",
        "grupo": "2º Grupo (-ir Regular com -iss-)",
        "dica_uso": "Modelo dos verbos do 2º grupo: ganha o infixo -iss- nas pessoas do plural (finissons, finissez, finissent).",
        "present": {
            "je": "finis", "tu": "finis", "il/elle/on": "finit",
            "nous": "finissons", "vous": "finissez", "ils/elles": "finissent"
        },
        "passe_compose": {
            "je": "ai fini", "tu": "as fini", "il/elle": "a fini",
            "nous": "avons fini", "vous": "avez fini", "ils/elles": "ont fini"
        },
        "imparfait": {
            "je": "finissais", "tu": "finissais", "il/elle": "finissait",
            "nous": "finissions", "vous": "finissiez", "ils/elles": "finissaient"
        },
        "futur_simple": {
            "je": "finirai", "tu": "finiras", "il/elle": "finira",
            "nous": "finirons", "vous": "finirez", "ils/elles": "finiront"
        },
        "conditionnel": {
            "je": "finirais", "tu": "finirais", "il/elle": "finirait",
            "nous": "finirions", "vous": "finiriez", "ils/elles": "finiraient"
        },
        "imperatif": ["Finis !", "Finissons !", "Finissez !"],
        "exemplos": [
            {"fr": "Je finis ma tasse de café et je te rejoins.", "pt": "Termino minha xícara de café e me junto a você."},
            {"fr": "Les étudiants ont fini l'examen avant l'heure.", "pt": "Os estudantes terminaram o exame antes da hora."}
        ]
    },
    "comprendre": {
        "verbo": "Comprendre",
        "traducao": "Compreender / Entender",
        "auxiliaire": "Avoir",
        "participe_passe": "compris",
        "grupo": "3º Grupo (Derivado de Prendre)",
        "dica_uso": "Segue exatamente o padrão de 'prendre': je comprends, nous comprenons, ils comprennent.",
        "present": {
            "je": "comprends", "tu": "comprends", "il/elle/on": "comprend",
            "nous": "comprenons", "vous": "comprenez", "ils/elles": "comprennent"
        },
        "passe_compose": {
            "je": "ai compris", "tu": "as compris", "il/elle": "a compris",
            "nous": "avons compris", "vous": "avez compris", "ils/elles": "ont compris"
        },
        "imparfait": {
            "je": "comprenais", "tu": "comprenais", "il/elle": "comprenait",
            "nous": "comprenions", "vous": "compreniez", "ils/elles": "comprenaient"
        },
        "futur_simple": {
            "je": "comprendrai", "tu": "comprendras", "il/elle": "comprendra",
            "nous": "comprendrons", "vous": "comprendrez", "ils/elles": "comprendront"
        },
        "conditionnel": {
            "je": "comprendrais", "tu": "comprendrais", "il/elle": "comprendrait",
            "nous": "comprendrions", "vous": "comprendriez", "ils/elles": "comprendraient"
        },
        "imperatif": ["Comprends !", "Comprenons !", "Comprenez !"],
        "exemplos": [
            {"fr": "Est-ce que vous comprenez quand les Français parlent vite ?", "pt": "Você compreende quando os franceses falam rápido?"},
            {"fr": "C'est bon, j'ai tout compris !", "pt": "Tudo bem, compreendi tudo!"}
        ]
    },
    "boire": {
        "verbo": "Boire",
        "traducao": "Beber",
        "auxiliaire": "Avoir",
        "participe_passe": "bu",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Atenção à alternância de radicais: je bois, nous buvons, ils boivent. Particípio: bu.",
        "present": {
            "je": "bois", "tu": "bois", "il/elle/on": "boit",
            "nous": "buvons", "vous": "buvez", "ils/elles": "boivent"
        },
        "passe_compose": {
            "je": "ai bu", "tu": "as bu", "il/elle": "a bu",
            "nous": "avons bu", "vous": "avez bu", "ils/elles": "ont bu"
        },
        "imparfait": {
            "je": "buvais", "tu": "buvais", "il/elle": "buvait",
            "nous": "buvions", "vous": "buviez", "ils/elles": "buvaient"
        },
        "futur_simple": {
            "je": "boirai", "tu": "boiras", "il/elle": "boira",
            "nous": "boirons", "vous": "boirez", "ils/elles": "boiront"
        },
        "conditionnel": {
            "je": "boirais", "tu": "boirais", "il/elle": "boirait",
            "nous": "boirions", "vous": "boiriez", "ils/elles": "boiraient"
        },
        "imperatif": ["Bois !", "Buvons !", "Buvez !"],
        "exemplos": [
            {"fr": "Je bois toujours un verre d'eau au réveil.", "pt": "Sempre bebo um copo de água ao acordar."},
            {"fr": "Nous avons bu un délicieux vin de Bordeaux.", "pt": "Bebemos um delicioso vinho de Bordeaux."}
        ]
    },
    "mettre": {
        "verbo": "Mettre",
        "traducao": "Colocar / Pôr / Vestir",
        "auxiliaire": "Avoir",
        "participe_passe": "mis",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "Usado para pôr objetos, vestir roupas (mettre un manteau) e tempo gasto (mettre deux heures).",
        "present": {
            "je": "mets", "tu": "mets", "il/elle/on": "met",
            "nous": "mettons", "vous": "mettez", "ils/elles": "mettent"
        },
        "passe_compose": {
            "je": "ai mis", "tu": "as mis", "il/elle": "a mis",
            "nous": "avons mis", "vous": "avez mis", "ils/elles": "ont mis"
        },
        "imparfait": {
            "je": "mettais", "tu": "mettais", "il/elle": "mettait",
            "nous": "mettions", "vous": "mettiez", "ils/elles": "mettaient"
        },
        "futur_simple": {
            "je": "mettrai", "tu": "mettras", "il/elle": "mettra",
            "nous": "mettrons", "vous": "mettrez", "ils/elles": "mettront"
        },
        "conditionnel": {
            "je": "mettrais", "tu": "mettrais", "il/elle": "mettrait",
            "nous": "mettrions", "vous": "mettriez", "ils/elles": "mettraient"
        },
        "imperatif": ["Mets !", "Mettons !", "Mettez !"],
        "exemplos": [
            {"fr": "Mets ton manteau, il fait froid dehors !", "pt": "Vista seu casaco, está frio lá fora!"},
            {"fr": "Où as-tu mis les clés de la maison ?", "pt": "Onde você colocou as chaves de casa?"}
        ]
    },
    "ecrire": {
        "verbo": "Écrire",
        "traducao": "Escrever",
        "auxiliaire": "Avoir",
        "participe_passe": "écrit",
        "grupo": "3º Grupo (Irregular)",
        "dica_uso": "No plural ganha som de 'v': nous écrivons, vous écrivez, ils écrivent.",
        "present": {
            "je": "écris", "tu": "écris", "il/elle/on": "écrit",
            "nous": "écrivons", "vous": "écrivez", "ils/elles": "écrivent"
        },
        "passe_compose": {
            "je": "ai écrit", "tu": "as écrit", "il/elle": "a écrit",
            "nous": "avons écrit", "vous": "avez écrit", "ils/elles": "ont écrit"
        },
        "imparfait": {
            "je": "écrivais", "tu": "écrivais", "il/elle": "écrivait",
            "nous": "écrivions", "vous": "écriviez", "ils/elles": "écrivaient"
        },
        "futur_simple": {
            "je": "écrirai", "tu": "écriras", "il/elle": "écrira",
            "nous": "écrirons", "vous": "écrirez", "ils/elles": "écriront"
        },
        "conditionnel": {
            "je": "écrirais", "tu": "écrirais", "il/elle": "écrirait",
            "nous": "écririons", "vous": "écririez", "ils/elles": "écriraient"
        },
        "imperatif": ["Écris !", "Écrivons !", "Écrivez !"],
        "exemplos": [
            {"fr": "J'écris un courriel à mon professeur de français.", "pt": "Estou escrevendo um e-mail para meu professor de francês."},
            {"fr": "Albert Camus a écrit 'L'Étranger' en 1942.", "pt": "Albert Camus escreveu 'O Estrangeiro' em 1942."}
        ]
    }
}

# 10 TEMAS GRAMATICAIS EXPANDIDOS COM RIQUEZA DE EXEMPLOS E DIÁLOGOS
TEMAS_GUIA_FLE = [
    {
        "id": "maison-etre",
        "icone": "home",
        "titulo": "1. La Maison d'Être",
        "subtitulo": "14 Verbos de Movimento e Estado + Verbos Pronominais",
        "descricao": "No Passé Composé, a maioria dos verbos usa o auxiliar AVOIR. No entanto, 14 verbos fundamentais de deslocamento e mudança de estado (e seus compostos) + TODOS os verbos pronominais exigem o auxiliar ÊTRE, concordando obrigatoriamente com o sujeito em gênero (-e) e número (-s).",
        "regra_chave": "Sujeito Feminino: +e | Sujeito Plural: +s | Sujeito Feminino Plural: +es. Ex: Elle est partie, Elles sont parties.",
        "verbos_ids": ["aller", "venir", "arriver", "partir", "entrer", "sortir", "monter", "descendre", "naitre", "mourir", "rester", "tomber", "retourner", "passer"],
        "pares_opostos": [
            {"v1": "Aller (Ir)", "v2": "Venir (Vir)", "ex": "Il est allé au marché / Elle est venue chez moi."},
            {"v1": "Arriver (Chegar)", "v2": "Partir (Partir)", "ex": "Le train est arrivé / Les invités sont partis."},
            {"v1": "Entrer (Entrar)", "v2": "Sortir (Sair)", "ex": "Elle est entrée dans la pièce / Il est sorti sous la pluie."},
            {"v1": "Monter (Subir)", "v2": "Descendre (Descer)", "ex": "Nous sommes montés au sommet / Ils sont descendus à la cave."},
            {"v1": "Naître (Nascer)", "v2": "Mourir (Morrer)", "ex": "Elle est née en mai / L'écrivain est mort en 1980."},
            {"v1": "Tomber (Cair)", "v2": "Rester (Ficar)", "ex": "La feuille est tombée / Sophie est restée calme."},
            {"v1": "Passer (Passar)", "v2": "Retourner (Voltar)", "ex": "Il est passé me dire bonjour / Elle est retournée au Brésil."}
        ],
        "atencao_especial": "Atenção: Monter, Descendre, Sortir, Passer e Retourner usam AVOIR quando têm objeto direto (COD)! Ex: 'J'ai monté mes valises' (Avoir) vs 'Je suis monté par l'escalier' (Être)."
    },
    {
        "id": "conjugacao-verbos",
        "icone": "clock",
        "titulo": "2. Conjugação de Verbos Essenciais",
        "subtitulo": "Tabelas e Modelos dos Principais Grupos e Modos",
        "descricao": "O francês divide os verbos em 3 grupos: 1º Grupo (-er, regular e produtivo), 2º Grupo (-ir com terminação -issons no nous, regular) e 3º Grupo (verbos irregulares em -ir, -re, -oir e o verbo aller). Clique em qualquer card de verbo para abrir o conjugador instantâneo.",
        "regra_chave": "Terminações no Presente do Indicativo: 1º Grupo: -e, -es, -e, -ons, -ez, -ent | 2º/3º Grupos regulares: -s, -s, -t/d, -ons, -ez, -ent.",
        "verbos_ids": ["etre", "avoir", "faire", "prendre", "pouvoir", "vouloir", "devoir", "savoir", "dire", "voir", "parler", "finir", "comprendre", "boire", "mettre", "ecrire"],
        "exemplos_adicionais": [
            {"titulo": "Parler (1º Grupo Regular)", "fr": "Je parle français avec mes collègues tous les jours.", "pt": "Falo francês com meus colegas todos os dias."},
            {"titulo": "Finir (2º Grupo Regular em -ir)", "fr": "Nous finissons notre rapport avant la réunion de demain.", "pt": "Terminamos nosso relatório antes da reunião de amanhã."},
            {"titulo": "Comprendre (3º Grupo)", "fr": "Tu comprends parfaitement les explications du professeur.", "pt": "Você compreende perfeitamente as explicações do professor."}
        ]
    },
    {
        "id": "articles-partitifs",
        "icone": "coffee",
        "titulo": "3. Articles Partitifs (du, de la, de l', des)",
        "subtitulo": "Quantidades Indeterminadas, Bebidas, Alimentos e a Regra do 'DE'",
        "descricao": "Os artigos partitivos indicam uma parte ou porção não contável de uma matéria, alimento ou conceito abstrato. Em português frequentemente omitimos ('Quero café'), mas em francês o partitivo é obrigatório ('Je veux du café').",
        "regra_chave": "Masculino: DU | Feminino: DE LA | Antes de vogal/h mudo: DE L' | Plural: DES. Na NEGAÇÃO absoluta e após expressões de quantidade, todos viram DE ou D'!",
        "tabela": [
            {"forma": "DU", "genero": "Masculino singular", "ex_fr": "Je bois du thé le matin.", "ex_pt": "Bebo chá pela manhã."},
            {"forma": "DE LA", "genero": "Feminino singular", "ex_fr": "Elle mange de la salade fraîche.", "ex_pt": "Ela come salada fresca."},
            {"forma": "DE L'", "genero": "Vogal ou 'h' mudo", "ex_fr": "Il faut boire de l'eau tous les jours.", "ex_pt": "É preciso beber água todos os dias."},
            {"forma": "DES", "genero": "Plural indiferenciado", "ex_fr": "J'achète des fruits au marché.", "ex_pt": "Compro frutas na feira."}
        ],
        "armadilhas": [
            {
                "titulo": "Regra de Ouro da Negação Absoluta (Vira 'DE' / 'D')",
                "regra": "Na frase negativa com 'ne... pas', du / de la / de l' / des viram simplesmente 'de' ou 'd''.",
                "correto": "Je n'ai pas de sucre. / Je ne bois pas d'alcool.",
                "incorreto": "Je n'ai pas du sucre. (ERRADO)"
            },
            {
                "titulo": "Exceção do Verbo Être na Negação",
                "regra": "Com o verbo Être, o artigo partitivo NÃO vira 'de'!",
                "correto": "Ce n'est pas du café, c'est du thé.",
                "incorreto": "Ce n'est pas de café. (Inadequado)"
            },
            {
                "titulo": "Verbos de Preferência Exigem Artigo Definido (le, la, les)",
                "regra": "Com aimer, adorer, préférer e détester usa-se LE, LA, L', LES (gosto da ideia como um todo).",
                "correto": "J'aime LE fromage (gosto de queijo), mas: Je mange DU fromage (como um pedaço de queijo).",
                "incorreto": "J'aime du fromage. (ERRADO)"
            },
            {
                "titulo": "Expressões de Quantidade Fixa Usam 'DE'",
                "regra": "beaucoup de, un peu de, un kilo de, un verre de, une bouteille de, trop de, assez de.",
                "correto": "Un kilo de pommes / Une bouteille d'eau minérale / Beaucoup de travail.",
                "incorreto": "Un kilo des pommes (ERRADO)"
            }
        ]
    },
    {
        "id": "faux-amis",
        "icone": "alert-triangle",
        "titulo": "4. Faux Amis (Falsos Cognatos Clássicos)",
        "subtitulo": "Palavras que parecem português mas possuem significados completamente diferentes",
        "descricao": "Devido à raiz latina comum, muitas palavras francesas se assemelham ao português na grafia ou pronúncia, mas possuem acepções distintas. Dominar os falsos cognatos evita gafes sociais e erros de interpretação em exames DELF/DALF.",
        "regra_chave": "Desconfie de palavras com som idêntico e verifique o contexto sintático!",
        "itens": [
            {
                "termo": "Attendre",
                "parece": "Atender",
                "significa": "ESPERAR / AGUARDAR",
                "como_dizer_atender": "Répondre (au téléphone) / Servir (un client)",
                "exemplo_fr": "J'attends le bus depuis vingt minutes.",
                "exemplo_pt": "Estou esperando o ônibus há vinte minutos."
            },
            {
                "termo": "Entendre",
                "parece": "Entender",
                "significa": "OUVIR / ESCUTAR",
                "como_dizer_atender": "Comprendre (compreender)",
                "exemplo_fr": "Parlez plus fort, s'il vous plaît, je n'entends rien !",
                "exemplo_pt": "Fale mais alto, por favor, não ouço nada!"
            },
            {
                "termo": "Prétendre",
                "parece": "Pretender (ter a intenção)",
                "significa": "AFIRMAR / ALEGAR (muitas vezes sem provas)",
                "como_dizer_atender": "Avoir l'intention de / Compter faire",
                "exemplo_fr": "Il prétend avoir tout compris sans réviser.",
                "exemplo_pt": "Ele afirma/alega ter entendido tudo sem revisar."
            },
            {
                "termo": "Actuellement",
                "parece": "Na verdade / realmente (Actually do inglês)",
                "significa": "ATUALMENTE / AGORA / NO MOMENTO",
                "como_dizer_atender": "En fait / En réalité (Na verdade)",
                "exemplo_fr": "Actuellement, j'habite à Lyon et j'étudie la linguistique.",
                "exemplo_pt": "Atualmente moro em Lyon e estudo linguística."
            },
            {
                "termo": "Décevoir",
                "parece": "Descrever",
                "significa": "DECEPCIONAR / DESAPONTAR",
                "como_dizer_atender": "Décrire (descrever)",
                "exemplo_fr": "Le résultat du match a déçu tous les supporters.",
                "exemplo_pt": "O resultado do jogo decepcionou todos os torcedores."
            },
            {
                "termo": "Bénéfice",
                "parece": "Benefício (vantagem social)",
                "significa": "LUCRO (financeiro / empresarial)",
                "como_dizer_atender": "Avantage / Allocation (benefício social)",
                "exemplo_fr": "L'entreprise a réalisé un beau bénéfice ce trimestre.",
                "exemplo_pt": "A empresa obteve um belo lucro neste trimestre."
            },
            {
                "termo": "Blesser",
                "parece": "Abençoar (Bless do inglês)",
                "significa": "FERIR / MACHUCAR",
                "como_dizer_atender": "Bénir (abençoar)",
                "exemplo_fr": "Il s'est blessé au genou pendant la randonnée.",
                "exemplo_pt": "Ele se machucou no joelho durante a caminhada."
            },
            {
                "termo": "Journée",
                "parece": "Jornada de trabalho / Viagem",
                "significa": "O DIA INTEIRO (da manhã à noite)",
                "como_dizer_atender": "Voyage (viagem), Journée de travail (expediente)",
                "exemplo_fr": "Passe une excellente journée !",
                "exemplo_pt": "Tenha um excelente dia (o dia todo)!"
            },
            {
                "termo": "Habit",
                "parece": "Hábito / Costume",
                "significa": "TRAJE / ROUPA (no plural 'habits')",
                "como_dizer_atender": "Habitude (hábito/costume)",
                "exemplo_fr": "L'habit ne fait pas le moine (ditado).",
                "exemplo_pt": "O hábito não faz o monge (as roupas não revelam o caráter)."
            },
            {
                "termo": "Librairie",
                "parece": "Biblioteca",
                "significa": "LIVRARIA (onde se compra livros)",
                "como_dizer_atender": "Bibliothèque (onde se empresta livros)",
                "exemplo_fr": "J'ai acheté ce dictionnaire dans une librairie du Quartier Latin.",
                "exemplo_pt": "Comprei este dicionário em uma livraria do Quartier Latin."
            },
            {
                "termo": "Mépris",
                "parece": "Empresa / Negócio",
                "significa": "DESPREZO / DESDÉM",
                "como_dizer_atender": "Entreprise (empresa)",
                "exemplo_fr": "Son regard était plein de mépris.",
                "exemplo_pt": "O olhar dele estava cheio de desprezo."
            },
            {
                "termo": "Sensible",
                "parece": "Sensato / Razoável",
                "significa": "SENSÍVEL / EMOTIVO",
                "como_dizer_atender": "Sensé / Raisonnable (sensato)",
                "exemplo_fr": "C'est une personne très sensible et bienveillante.",
                "exemplo_pt": "É uma pessoa muito sensível e acolhedora."
            }
        ]
    },
    {
        "id": "pronoms-y-en",
        "icone": "git-merge",
        "titulo": "5. Pronoms Adverbiaux Y & EN",
        "subtitulo": "Substituição Elegante de Lugares, Quantidades e Preposições",
        "descricao": "Os pronomes Y e EN são elementos estilísticos vitais no francês para evitar repetições pesadas. Dominá-los é o maior salto de fluência entre o nível A2 e B1/B2.",
        "regra_chave": "Y substitui: [à / en / dans / chez + LUGAR] ou [à + COISA] | EN substitui: [de / du / de la / des + COISA/LUGAR] ou [QUANTIDADE NUMÉRICA].",
        "secoes": [
            {
                "nome": "O Pronome 'Y'",
                "pontos": [
                    "Substitui preposição de LUGAR (à, en, dans, sur, chez, sous + lugar). Ex: Je vais à Paris -> J'y vais.",
                    "Substitui preposição 'à + coisa/ideia' (verbos transitivos indiretos como penser à, s'intéresser à, faire attention à). Ex: Tu penses à ton avenir ? -> Oui, j'y pense souvent.",
                    "Atenção: NÃO use Y para pessoas! Para 'penser à une personne', usa-se pronome tônico: 'Je pense à Pierre -> Je pense à LUI' (e NÃO j'y pense)."
                ],
                "dialogos": [
                    {"pergunta": "— Tu habites toujours à Marseille ?", "resposta": "— Oui, j'y habite depuis trois ans.", "pt": "— Você ainda mora em Marselha? — Sim, moro lá há três anos."},
                    {"pergunta": "— Est-ce que tu vas chez le médecin cet après-midi ?", "resposta": "— Oui, j'y vais à seize heures.", "pt": "— Você vai ao médico hoje à tarde? — Sim, vou lá às 16h."},
                    {"pergunta": "— Tu participes à ce projet ?", "resposta": "— Oui, j'y participe avec enthousiasme.", "pt": "— Você participa deste projeto? — Sim, participo dele com entusiasmo."}
                ]
            },
            {
                "nome": "O Pronome 'EN'",
                "pontos": [
                    "Substitui substantivo precedido por artigo partitivo (du, de la, des) ou indefinido (un, une). Ex: Tu bois du café ? -> J'en bois.",
                    "Substitui preposição 'de + coisa' (verbos como parler de, avoir besoin de, avoir peur de, se souvenir de). Ex: Tu te souviens de cette histoire ? -> Je m'en souviens.",
                    "Substitui substantivos com quantidades numéricas (mantém o número no final!). Ex: Tu as deux dictionnaires ? -> Oui, j'en ai deux.",
                    "Substitui proveniência de lugar (venir de, sortir de). Ex: Tu sors du bureau ? -> Oui, j'en sors tout juste."
                ],
                "dialogos": [
                    {"pergunta": "— Tu manges de la viande ?", "resposta": "— Non, je n'en mange plus du tout.", "pt": "— Você come carne? — Não, não como nada disso."},
                    {"pergunta": "— Combien de frères as-tu ?", "resposta": "— J'en ai trois.", "pt": "— Quantos irmãos você tem? — Tenho três."},
                    {"pergunta": "— As-tu besoin de ce document ?", "resposta": "— Oui, j'en ai grandement besoin.", "pt": "— Você precisa deste documento? — Sim, preciso muito dele."}
                ]
            }
        ]
    },
    {
        "id": "pronoms-cod-coi",
        "icone": "target",
        "titulo": "6. Pronomes COD & COI",
        "subtitulo": "Complément d'Objet Direct (le, la, les) & Indirect (lui, leur)",
        "descricao": "Os pronomes complemento direto (COD) respondem à pergunta 'qui ?' (quem?) ou 'quoi ?' (o quê?), sem preposição. Os pronomes indiretos (COI) respondem à pergunta 'à qui ?' (a quem?), com a preposição 'à'.",
        "regra_chave": "COD: me, te, le/la, nous, vous, les | COI: me, te, LUI, nous, vous, LEUR. Ficam ANTES do verbo conjugado (ex: Je le vois, Je lui parle).",
        "comparativo": [
            {
                "tipo": "COD (Direto)",
                "formas": "le (masc), la (fem), l' (vogal), les (plural)",
                "pergunta": "Verbo + QUEM ? / O QUÊ ?",
                "ex_fr": "Je regarde ce film -> Je le regarde. / J'attends Marie -> Je l'attends.",
                "ex_pt": "Assisto a este filme -> Eu o assisto. / Espero a Marie -> Eu a espero."
            },
            {
                "tipo": "COI (Indireto)",
                "formas": "lui (a ele / a ela), leur (a eles / a elas)",
                "pergunta": "Verbo + À QUI ? (a quem?)",
                "ex_fr": "Je téléphone à Paul -> Je lui téléphone. / J'écris à mes parents -> Je leur écris.",
                "ex_pt": "Telefono para o Paul -> Telefono para ele. / Escrevo aos meus pais -> Escrevo para eles."
            }
        ],
        "posicao_passado": "No Passé Composé: o pronome fica antes do auxiliar! Ex: 'Je l'ai vu hier', 'Je lui ai parlé ce matin'. Se o COD estiver antes do particípio no Passé Composé com AVOIR, o particípio concorda com o COD: 'Ces fleurs ? Je les ai achetées' (fem. pl. -> +es)."
    },
    {
        "id": "negation-complexe",
        "icone": "slash",
        "titulo": "7. Negação Simples & Complexa",
        "subtitulo": "Além do 'ne... pas': nuances de tempo, restrição e ausência",
        "descricao": "A estrutura de negação em francês abraça o verbo conjugado: ne + [verbo] + [palavra negativa]. No registro coloquial e oral, os franceses costumam omitir o 'ne' ('J'sais pas'), mas na escrita e em exames o 'ne' é indispensável.",
        "regra_chave": "No Passé Composé: ne + auxiliar + pas/jamais/rien/plus + particípio. EXCEÇÃO: 'personne' e 'nulle part' ficam DEPOIS do particípio! Ex: Je n'ai vu personne.",
        "pares_transformacao": [
            {"afirmacao": "Toujours / Souvent (Sempre/Frequentemente)", "negacao": "Ne... JAMAIS (Nunca)", "ex_fr": "Je ne prends jamais l'avion.", "ex_pt": "Nunca viajo de avião."},
            {"afirmacao": "Encore (Ainda)", "negacao": "Ne... PLUS (Não mais)", "ex_fr": "Il ne fume plus depuis un an.", "ex_pt": "Ele não fuma mais há um ano."},
            {"afirmacao": "Quelque chose / Tout (Algo/Tudo)", "negacao": "Ne... RIEN (Nada)", "ex_fr": "Je n'ai rien entendu dans la nuit.", "ex_pt": "Não ouvi nada durante a noite."},
            {"afirmacao": "Quelqu'un / Tout le monde (Alguém/Todos)", "negacao": "Ne... PERSONNE (Ninguém)", "ex_fr": "Je n'ai vu personne dans la rue.", "ex_pt": "Não vi ninguém na rua."},
            {"afirmacao": "Partout / Quelque part (Em todo lugar/Em algum lugar)", "negacao": "Ne... NULLE PART (Em lugar nenhum)", "ex_fr": "Mes clés ne sont nulle part.", "ex_pt": "Minhas chaves não estão em lugar nenhum."},
            {"afirmacao": "Seulement (Apenas / Somente)", "negacao": "Ne... QUE (Restrição 'somente')", "ex_fr": "Je n'ai que dix euros sur moi.", "ex_pt": "Tenho apenas dez euros comigo."}
        ]
    },
    {
        "id": "prepositions-lieu",
        "icone": "map-pin",
        "titulo": "8. Prépositions de Lieu & Pays",
        "subtitulo": "Cidades, Países Femininos, Masculinos, Plurais e o uso de 'Chez'",
        "descricao": "Em francês, a escolha da preposição que antecede nomes de cidades e países varia estritamente de acordo com o gênero e a terminação do topônimo.",
        "regra_chave": "Cidades: À (à Paris, à São Paulo) | Países femininos (terminados em -e): EN (en France, en Italie) | Países masculinos: AU (au Brésil, au Canada) | Países no plural: AUX (aux États-Unis).",
        "categorias": [
            {
                "tipo": "Cidades",
                "preposicao": "À (origem: DE / D')",
                "exemplos": [
                    {"fr": "J'habite à Lyon et elle vit à Rio de Janeiro.", "pt": "Moro em Lyon e ela mora no Rio de Janeiro."},
                    {"fr": "Le train arrive de Bordeaux à 17h.", "pt": "O trem chega de Bordeaux às 17h."}
                ]
            },
            {
                "tipo": "Países Femininos (terminados em 'e' + iniciados por vogal)",
                "preposicao": "EN (origem: DE / D')",
                "exemplos": [
                    {"fr": "Nous voyageons en France, en Espagne et en Italie.", "pt": "Viajamos na França, na Espanha e na Itália."},
                    {"fr": "Le président est né en Iran (masculino começado por vogal -> EN).", "pt": "O presidente nasceu no Irã."}
                ]
            },
            {
                "tipo": "Países Masculinos (não terminados em 'e')",
                "preposicao": "AU (origem: DU)",
                "exemplos": [
                    {"fr": "Je passe mes vacances au Brésil et au Portugal.", "pt": "Passo minhas férias no Brasil e em Portugal."},
                    {"fr": "Il vient de rentrer du Japon.", "pt": "Ele acaba de voltar do Japão."}
                ]
            },
            {
                "tipo": "Países Plurais",
                "preposicao": "AUX (origem: DES)",
                "exemplos": [
                    {"fr": "Elle travaille aux États-Unis et aux Pays-Bas.", "pt": "Ela trabalha nos Estados Unidos e nos Países Baixos (Holanda)."}
                ]
            },
            {
                "tipo": "A preposição 'CHEZ' (Pessoas, Residências e Profissionais)",
                "preposicao": "CHEZ (em casa de / no estabelecimento de)",
                "exemplos": [
                    {"fr": "Je rentre chez moi me reposer.", "pt": "Volto para minha casa descansar."},
                    {"fr": "Je dois aller chez le dentiste demain matin.", "pt": "Devo ir ao dentista amanhã de manhã."}
                ]
            }
        ]
    },
    {
        "id": "courtoisie-quotidien",
        "icone": "message-circle",
        "titulo": "9. Fórmulas de Cortesia & Situações Cotidianas",
        "subtitulo": "Padaria, Restaurante, Compras e Polidez Essencial",
        "descricao": "Na cultura francesa, a fórmula de polidez é um rito sagrado. Entrar em uma loja sem dizer 'Bonjour Madame/Monsieur' ou esquecer o 'S'il vous plaît' é considerado indelicado.",
        "regra_chave": "Nunca peça coisas dizendo 'Je veux' (muito brusco). Use sempre o Conditionnel de Polidez: 'Je voudrais...' ou 'Pourriez-vous...'",
        "cenarios": [
            {
                "local": "À la boulangerie (Na padaria)",
                "frases": [
                    {"fr": "— Bonjour Madame ! Je voudrais une baguette tradition bien cuite, s'il vous plaît.", "pt": "— Bom dia senhora! Gostaria de uma baguete tradicional bem assada, por favor."},
                    {"fr": "— Et avec ceci ? — Ce sera tout, merci. Combien je vous dois ?", "pt": "— E mais alguma coisa? — Só isso, obrigado. Quanto lhe devo?"}
                ]
            },
            {
                "local": "Au restaurant (No restaurante)",
                "frases": [
                    {"fr": "— Bonjour, nous avons réservé une table au nom de Dupont.", "pt": "— Olá, reservamos uma mesa em nome de Dupont."},
                    {"fr": "— Pourriez-vous nous apporter une carafe d'eau et le menu, s'il vous plaît ?", "pt": "— O senhor poderia nos trazer uma jarra de água da torneira e o cardápio, por favor?"},
                    {"fr": "— L'addition, s'il vous plaît !", "pt": "— A conta, por favor!"}
                ]
            },
            {
                "local": "Demander son chemin (Pedindo orientações na rua)",
                "frases": [
                    {"fr": "— Excusez-moi de vous déranger, monsieur, où se trouve la bouche de métro la plus proche ?", "pt": "— Desculpe incomodá-lo, senhor, onde fica a entrada de metrô mais próxima?"},
                    {"fr": "— Continuez tout droit puis tournez à droite au feu rouge.", "pt": "— Continue em frente e depois vire à direita no semáforo."}
                ]
            }
        ]
    },
    {
        "id": "subjonctif-indicatif",
        "icone": "sparkles",
        "titulo": "10. Le Subjonctif Présent",
        "subtitulo": "Expressão de Vontade, Necessidade, Dúvida e Emoção",
        "descricao": "O Subjonctif não é um tempo de certeza factual (como o Indicatif), mas o modo da subjetividade, do desejo, da exigência e do sentimento. É quase invariavelmente introduzido pela conjunção 'QUE'.",
        "regra_chave": "Formação regular: raiz da 3ª pessoa plural (ils/elles) no presente + terminações: -e, -es, -e, -ions, -iez, -ent.",
        "gatilhos": [
            {"tipo": "Necessidade / Obrigação", "expressao": "Il faut que / Il est nécessaire que", "ex_fr": "Il faut que tu fasses tes devoirs ce soir.", "ex_pt": "É preciso que você faça suas tarefas hoje à noite."},
            {"tipo": "Desejo / Vontade", "expressao": "Vouloir que / Souhaiter que / Aimer que", "ex_fr": "Je veux que nous réussissions cet examen.", "ex_pt": "Quero que nós passemos nesta prova."},
            {"tipo": "Emoção / Sentimento", "expressao": "Être content que / Avoir peur que", "ex_fr": "Je suis heureux que vous soyez venus nous voir.", "ex_pt": "Estou feliz que vocês tenham vindo nos ver."},
            {"tipo": "Dúvida / Incerteza", "expressao": "Douter que / Il est peu probable que", "ex_fr": "Je doute qu'il vienne à l'heure.", "ex_pt": "Duvido que ele venha no horário."}
        ],
        "contraste": [
            {"indicativo": "Je pense qu'il est honnête (Certeza na afirmativa -> Indicativo).", "subjuntivo": "Je ne pense pas qu'il soit honnête (Dúvida na negativa -> Subjuntivo)."},
            {"indicativo": "Il est certain que le train part à midi (Certeza absoluta).", "subjuntivo": "Il n'est pas certain que le train parte à midi (Incerteza)."}
        ]
    }
]
