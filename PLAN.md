# PLAN — Arène équitable et vitrine publique Taboun

> Document temporaire de chantier. À supprimer lorsque l'arène, la publication
> et la page publique sont en production et documentées dans les README.

## Vision

Le but n'est pas seulement de produire un classement : `taboun` devient le
laboratoire où les bots sont développés et testés, et `geheim-land` devient la
vitrine où l'on peut constater leur progression.

Le flux cible est simple :

```text
nouveau bot dans taboun
        ↓
tests + match SPRT contre la version précédente
        ↓
tournoi officiel reproductible avec fastchess
        ↓
PGN + classement relatif + métadonnées immuables
        ↓
publication atomique sur geheim.land
        ↓
classement, fiches des bots et replay des parties dans le navigateur
```

L'arène publique est une preuve vérifiable, pas un décor marketing : chaque
résultat renvoie aux parties, aux conditions du tournoi et au commit exact du
code testé.

## Principes non négociables

1. **Comportement historique préservé.** Sans nouvel argument, chaque bot joue
   comme avant. Les anciens bots conservent aussi leur profondeur maximale
   historique : un budget de temps les borne, il ne les transforme pas en une
   nouvelle version capable de chercher arbitrairement plus profond.
2. **Même opportunité de calcul.** Même pendule, un seul thread par moteur,
   ouvertures imposées en paires miroir et livres internes désactivés.
3. **Résultats reproductibles.** Graine, versions des outils, commit Git,
   commande, matériel et réglages sont enregistrés avec chaque tournoi.
4. **Elo honnête.** Le classement est relatif au pool et accompagné de son
   incertitude. Fixer V1 à 1000 est une convention d'origine, pas un Elo absolu.
5. **Publication découplée du calcul.** Rejouer une partie publiée ne lance
   aucun bot. Le site ne lit que des artefacts en lecture seule.
6. **Ouverture publique progressive.** La page Arène, peu coûteuse, devient
   publique en premier. Le jeu interactif ne devient public qu'après limitation
   de débit et test de charge.
7. **Clarté avant compacité.** Le code doit rester très simple, fonctionnel et
   organisé comme le projet actuel. Multiplier les petits fichiers Python n'est
   pas un problème si chacun porte une responsabilité évidente. On ne concentre
   pas plusieurs usages dans un gros fichier uniquement pour réduire le nombre
   de fichiers.
8. **Propreté et rangement.** Le projet doit rester ordonné au sens
   organisationnel : chaque fichier a une place logique et chaque dossier une
   responsabilité compréhensible. Aucun script de tournoi, export généré ou
   code du site ne doit finir à la racine par commodité.

## Règles de simplicité du code

- Un fichier correspond autant que possible à **un usage principal** : lire
  UCI, construire les ouvertures, lancer un tournoi, calculer le classement,
  publier les artefacts ou servir la page web.
- Préférer des fonctions courtes, des noms explicites et un flux lisible de
  haut en bas à des abstractions génériques difficiles à suivre.
- Éviter les frameworks, couches, classes de service et systèmes de plugins
  supplémentaires tant qu'une fonction ou un petit module Python suffit.
- Ne pas créer une abstraction pour éliminer seulement quelques lignes
  répétées. Une duplication locale et claire est acceptable si la factorisation
  rendrait les versions historiques des bots plus difficiles à comprendre.
- Séparer le code métier des commandes externes et des entrées/sorties, mais
  sans architecture cérémonielle : des modules Python simples qui s'appellent
  directement suffisent.
- Chaque script doit avoir une entrée évidente, une aide `--help`, des erreurs
  compréhensibles et des valeurs par défaut sûres.
- Les formats échangés entre `taboun` et `geheim-land` restent petits,
  documentés et versionnés ; aucun mécanisme implicite ne doit être nécessaire
  pour comprendre comment un résultat arrive sur le site.
- Les commentaires expliquent les décisions et les pièges, pas ce que fait déjà
  clairement chaque ligne.
- Si deux solutions fonctionnent, retenir celle qu'un lecteur peut modifier
  sans devoir comprendre tout le projet.

Le nombre de fichiers n'est donc pas un indicateur de complexité. Un dossier de
petits modules nommés clairement est préférable à un unique script qui mélange
tournoi, statistiques, export et publication.

## Arborescence cible

L'organisation précise pourra légèrement évoluer pendant l'implémentation,
mais les responsabilités restent rangées ainsi :

```text
taboun/
├── src/
│   ├── bot/                    # une version de bot par fichier
│   │   └── time_control.py     # uniquement le mécanisme commun de deadline
│   ├── uci.py                  # point d'entrée UCI
│   └── arena/
│       ├── build_openings.py   # génération déterministe des ouvertures
│       ├── run_tournament.py   # lancement et reprise de fastchess
│       ├── ranking.py          # appel à Ordo et contrôle du classement
│       └── publish.py          # création du paquet destiné au site
├── data/
│   ├── bots.json               # textes de présentation des versions
│   ├── openings/               # livres source et ouvertures d'arène
│   └── arena/
│       ├── runs/               # un dossier immuable par tournoi publié
│       └── latest.json         # pointeur atomique vers le dernier tournoi
└── tests/
    ├── bots/                   # comportement historique et timeouts
    ├── uci/                    # protocole et gestion de la pendule
    └── arena/                  # ouvertures, classement et publication

geheim-land/apps/taboun_chess_engine/
├── engine/                     # calcul des coups, isolé du site
├── arena/                      # lecture et validation des données publiées
├── templates/
│   ├── index.html              # page Play
│   └── arena.html              # page Arena
├── static/
│   ├── chess/                  # Chessground et chess.js partagés
│   └── arena/                  # JS/CSS propres au classement et au replay
├── router.py                   # routes fines, sans logique de classement
└── config.py                   # chemins et limites configurables
```

Les fichiers générés vont uniquement sous `data/arena/`. Les fichiers source
vont sous `src/`, les tests sous `tests/`, et le code propre au site reste dans
`geheim-land`. Un README court dans `src/arena/` et dans le dossier `arena/` du
site explique le rôle de chaque fichier et le flux des données.

---

## Étape 1 — Budget de temps optionnel dans les bots (`taboun`)

### Pourquoi

V6/V7 peuvent dépasser 17 s par coup et V9 5,7 s, tandis que V10–V12 sont
plafonnés à 1 s. Le classement actuel mélange donc qualité de recherche et
temps de calcul disponible. Le même problème peut déclencher le watchdog du
site.

### Implémentation

- Ajouter `time_limit: float | None = None` aux constructeurs de V2 à V9.
- `None` emprunte le chemin historique et doit produire exactement le même
  coup qu'avant.
- Une valeur active une deadline monotone et un approfondissement itératif de
  1 jusqu'à **`self.depth` au maximum**. Si une profondeur n'est pas terminée,
  rendre le meilleur coup de la dernière profondeur entièrement terminée.
- Vérifier la deadline à la racine, dans minimax/alpha-beta et dans la
  quiescence de V6–V9.
- Tous les `board.push()` susceptibles d'être traversés par `SearchTimeout`
  utilisent `try/finally: board.pop()` afin qu'un timeout ne corrompe jamais le
  plateau fourni par l'appelant.
- Le petit mécanisme commun de deadline peut vivre dans
  `src/bot/time_control.py`; les algorithmes de recherche restent dans chaque
  version pour conserver leur valeur pédagogique.
- Ajouter `use_book: bool = True` à V11 et V12. `True` conserve le comportement
  actuel ; l'arène utilisera `False`.
- V1 reste inchangé : son choix aléatoire est immédiat.
- V10–V12 conservent leur limite par défaut actuelle de 1 s.

### Tests

- Constituer avant la modification un corpus versionné de FEN et de coups
  attendus pour V2–V10 ; tester V11/V12 hors livre ou avec `use_book=False`.
- Vérifier les coups par défaut, mais aussi le FEN, le trait et la pile de coups
  du plateau après chaque recherche.
- Injecter des budgets très courts dans chaque bot et vérifier : coup légal,
  plateau intact, retour avec une tolérance raisonnable liée à l'ordonnanceur.
- Tester explicitement les chaînes de captures longues de V6/V7.

### Fichiers

`src/bot/tabounv2.py` à `tabounv9.py`, `tabounv11.py`, `tabounv12.py`,
éventuellement `src/bot/time_control.py`, tests et README.

---

## Étape 2 — Adaptateur UCI suffisamment conforme (`taboun`)

### Pourquoi

fastchess et les interfaces graphiques pilotent les moteurs avec UCI. Un
adaptateur évite d'embarquer les règles de tournoi dans les bots.

### Implémentation

Créer `src/uci.py`, lancé ainsi :

```bash
python3 src/uci.py tabounv12
```

L'adaptateur prend en charge au minimum :

- `uci`, `isready`, `setoption`, `ucinewgame`, `position startpos`,
  `position fen ...`, `go`, `stop` et `quit` ;
- `go movetime`, `wtime`, `btime`, `winc`, `binc`, `movestogo` et `depth` ;
- un gestionnaire de temps commun qui transforme la pendule restante en budget
  par coup, avec une marge de sécurité ; ne jamais passer tout le temps restant
  à un seul `choose_move` ;
- l'option UCI `OwnBook`, reliée à `use_book` pour V11/V12 ;
- la remise à zéro des caches de partie à `ucinewgame` ;
- une boucle d'entrée capable de répondre à `isready` et `stop` pendant la
  recherche, plutôt qu'un lecteur bloqué dans `choose_move` ;
- `bestmove` pour chaque `go` et des lignes `info` limitées aux données
  réellement connues. Comme le contrôle fastchess exige `info score`, publier
  une évaluation statique réelle après le coup avec la famille d'évaluation du
  bot, explicitement étiquetée dans la documentation comme **non issue de la
  recherche et interdite pour l'adjudication** ; ne jamais inventer un score
  constant.

La première version ne promet pas l'analyse infinie, le ponder ou MultiPV.

### Validation

- tests unitaires du parseur avec espaces, FEN, promotions et commandes
  inconnues ;
- `fastchess --compliance` pour chaque bot ;
- mini-partie automatique UCI contre UCI ;
- test dans Cute Chess GUI ;
- test qu'un `stop` rend toujours rapidement un coup légal.

### Fichiers

`src/uci.py`, tests et README.

---

## Étape 3 — Arène officielle fastchess (`taboun` + VPS)

### Outil retenu

Utiliser **fastchess**, avec une version ou un commit épinglé et enregistré
dans le manifeste du tournoi. Il fournit pendules, ouvertures répétées avec
couleurs inversées, concurrence, PGN, SPRT, contrôle de conformité et reprise.

### Ouvertures

Créer `src/arena/build_openings.py` :

- parcourir `data/openings/books/komodo3.bin` avec une graine explicite ;
- produire des lignes légales de 6 à 10 demi-coups ;
- rejeter les doublons et les lignes trop courtes ;
- produire un PGN déterministe et un résumé avec graine, nombre de lignes et
  empreinte SHA-256 ;
- ne jamais utiliser `weighted_choice()` sans source aléatoire reproductible.

Chaque ligne est jouée deux fois, couleurs inversées. V11/V12 jouent avec
`OwnBook=false`.

### Lanceur

Créer `src/arena/run_tournament.py`, qui construit puis exécute la commande
fastchess sans interpolation shell fragile.

Réglages officiels initiaux :

- cadence : **60 s + 0,6 s/coup** ;
- un thread par moteur ;
- concurrence : **4 parties maximum sur le VPS à 6 cœurs**, en laissant de la
  capacité au site ; utiliser l'affinité CPU ou les limites du conteneur si le
  tournoi tourne pendant que le site est public ;
- pilote : 10 ouvertures, soit 20 parties par duel ;
- publication officielle : 25 ouvertures, soit 50 parties par duel ;
- pour 12 bots : 66 duels, donc 1 320 parties au pilote ou 3 300 à l'officiel ;
- crash, timeout ou coup illégal : défaite ;
- règles normales de nulle de python-chess/fastchess et `maxmoves` explicite.

### Adjudication

Ne pas activer au premier tournoi `-draw ... score=` ou
`-resign ... score=` : l'adaptateur ne fournit pas encore le score de recherche
et une évaluation statique inventée fausserait les résultats. Une adjudication
par score ne sera ajoutée que si l'API interne retourne proprement
`move + score + profondeur`, puis après mesure des faux positifs. Des tables
Syzygy peuvent être ajoutées séparément plus tard.

### Sorties et reprise

- PGN complet avec la terminaison exacte de chaque partie ;
- logs fastchess ;
- configuration/autosauvegarde permettant de reprendre après interruption ;
- commande complète et versions dans le manifeste ;
- refus par défaut de lancer un tournoi officiel depuis un worktree sale.

### Validation

1. conformité UCI de tous les bots ;
2. deux bots, deux ouvertures, sans concurrence ;
3. deux bots, dix ouvertures, concurrence 4 et reprise après interruption ;
4. round-robin pilote ;
5. seulement ensuite, tournoi officiel.

---

## Étape 4 — Classement relatif et artefact de publication (`taboun`)

### Classement

Passer le PGN à **Ordo**, plutôt que maintenir immédiatement un solveur
Bradley–Terry maison. Ordo ajuste tous les résultats simultanément.

- V1 est fixé conventionnellement à **1000 Elo relatif** pour stabiliser
  l'origine de l'échelle entre les publications.
- Le site et le README disent explicitement « Elo relatif, V1 = 1000 ».
- Publier l'incertitude à 95 % en documentant exactement la commande et la
  méthode de simulation employées.
- Le LOS/CFS est une comparaison : publier celui avec le bot classé juste
  devant/derrière et calculer le LOS direct dans les pages de duel. Ne pas le
  présenter comme une propriété intrinsèque du bot.
- Un Stockfish bridé pourra plus tard rejoindre le pool, mais ne rendra le
  classement comparable à l'extérieur que si version, matériel et protocole
  de calibration sont eux-mêmes stables et documentés.

### Artefact public versionné

Créer `src/arena/publish.py`. Pour chaque tournoi validé, il produit :

```text
data/arena/runs/<date>-<commit>/
├── manifest.json          # schema_version, commit, outils, matériel, cadence,
│                          # graine, commande, nombre de parties, checksums
├── ranking.csv            # format humain/export
├── ranking.json           # format du site
├── games.pgn              # source canonique complète
├── games/
│   ├── index.json         # id, blancs, noirs, résultat, ouverture, terminaison
│   └── <game-id>.json     # coups UCI/SAN et en-têtes nécessaires au replay
└── openings.pgn

data/arena/latest.json     # pointeur mis à jour atomiquement vers un run validé
```

Les gros artefacts générés ne sont pas dupliqués dans les deux dépôts. Ils sont
conservés sur le VPS ou dans une release, avec checksums ; le conteneur web ne
voit que le répertoire publié, monté en lecture seule.

Ajouter un fichier éditorial versionné (`data/bots.json` ou équivalent) avec,
pour chaque bot : résumé de l'idée, nouveauté par rapport à la version
précédente et lien vers le code. Le site ne doit pas extraire ces textes du
README à la volée.

### Validation

- Ordo et l'export refusent un PGN incomplet ou incohérent ;
- totaux W/D/L identiques entre PGN, CSV et JSON ;
- chaque entrée de `games/index.json` ouvre une partie rejouable et légale ;
- schéma JSON testé et versionné ;
- publication dans un dossier temporaire, puis bascule atomique de
  `latest.json` seulement après tous les contrôles.

---

## Étape 5 — Page Arène publique et replay (`geheim-land`)

### Architecture observée

L'app existante possède déjà Chessground, `chess.js`, un échiquier responsive
et une liste de coups. Le replay réutilise ces composants ; il ne contacte
jamais le conteneur `chess-engine`.

Le manifest actuel rend toute l'app privée. Pour publier l'arène sans exposer
immédiatement le calcul :

1. passer le manifest de l'app en public ;
2. protéger temporairement les routes de jeu (`/`, `/bots`, `/move`) avec
   `require_auth` directement dans le routeur ;
3. laisser publiques `/arena`, ses données et les assets statiques ;
4. retirer la protection du jeu seulement à l'étape 6.

Cela donne une frontière claire sans créer une seconde app ni dupliquer les
assets.

### Navigation

Ajouter en haut de l'app deux boutons visibles :

- **Play** → `/apps/taboun-chess-engine` ;
- **Arena** → `/apps/taboun-chess-engine/arena`.

La page d'accueil de geheim.land pointe vers l'Arène publique pendant que le
jeu reste privé.

### Contenu MVP de `/arena`

- carte du champion et date du dernier tournoi ;
- tableau : rang, bot, Elo relatif, intervalle 95 %, W/D/L, parties ;
- rappel visible des conditions : cadence, ouvertures, nombre de parties,
  commit et matériel ;
- fiches courtes expliquant ce que chaque version a ajouté ;
- filtre par bot et par duel ;
- liste paginée des parties avec couleurs, résultat, ouverture et terminaison ;
- bouton **Replay** ouvrant l'échiquier ;
- contrôles début, précédent, lecture/pause, suivant, fin et retournement du
  plateau ; navigation possible au clavier ;
- liste SAN synchronisée et coup courant surligné ;
- téléchargement du PGN complet et lien vers le commit source ;
- explication courte de « Elo relatif » et de l'incertitude.

Le premier jet n'a besoin ni de graphique, ni de base de données, ni d'analyse
Stockfish. Ils ne doivent pas retarder la publication.

### Routes et données

- le répertoire publié est monté dans le conteneur web en lecture seule via
  `TABOUN_ARENA_DATA_DIR` ;
- le serveur charge `latest.json` et `ranking.json`, sert l'index paginé et un
  fichier de partie par identifiant validé ;
- aucune concaténation de chemin fournie par le client ;
- cache HTTP sur les runs immuables, pas de cache long sur `latest.json` ;
- état vide propre si aucun tournoi n'est encore publié ;
- un ancien run reste consultable par son identifiant, même après une nouvelle
  publication.

### Promotion

- retirer `noindex` de la seule page Arène lorsqu'elle devient publique ;
- titre, description et métadonnées de partage dédiés ;
- CTA vers le dépôt et, après l'étape 6, vers « Play against the champion » ;
- ne jamais annoncer « meilleur bot » sans afficher le nombre de parties et
  l'intervalle d'incertitude.

### Validation

- tests FastAPI des routes, du run absent, des identifiants invalides et du
  téléchargement PGN ;
- tests JavaScript ou navigateur du replay : roque, promotion, en passant,
  retour arrière et partie nulle ;
- test mobile et clavier ;
- preuve qu'ouvrir/rejouer 100 parties ne génère aucun appel à `/move` ;
- vérification que l'Arène est publique tandis que le jeu reste protégé.

---

## Étape 6 — Jeu public sûr et watchdog (`geheim-land`)

### Limite de réflexion

Après l'étape 1, `engine/server.py` instancie les bots compatibles avec un
`time_limit` de site configurable, par exemple 2 s. V1 reste sans argument.
V11/V12 gardent leur livre pour les parties visiteurs.

- Le watchdog devient une dernière ceinture de sécurité, supérieur au budget
  normal avec une marge mesurée ; il ne doit plus interrompre une recherche
  légitime.
- Mettre à jour commentaire, README et tests qui affirment actuellement que
  les constructeurs sont toujours appelés sans argument.
- Tester V2–V12 sur une partie et sur des positions tactiques lentes.

### Avant de retirer le mot de passe du jeu

- limitation par IP/session sur `/move` ;
- une seule recherche active et une file bornée, sans boucle de retry pouvant
  amplifier la charge ;
- quota global et réponse `429` avec délai conseillé ;
- métriques : latence, timeouts, redémarrages, taille de file et bot demandé ;
- test de charge pendant qu'un tournoi tourne ;
- au moins deux cœurs laissés au site et au moteur interactif ;
- possibilité de couper le jeu public sans retirer l'Arène publique.

Après une période d'observation privée concluante, rendre publiques la page de
jeu et `/move`, puis activer le CTA « Play against the champion ».

---

## Étape 7 — Validation des futures versions par SPRT

Pour V13 et suivantes :

1. tests unitaires et positions de non-régression ;
2. match fastchess V13 contre V12, mêmes ressources, ouvertures appariées et
   livres coupés ;
3. SPRT avec hypothèses, alpha/beta, modèle et limite maximale documentés ;
4. même en cas d'acceptation, tournoi round-robin officiel avant mise à jour du
   classement public ;
5. publication d'une note courte « ce qui a changé » et lien vers le commit.

Le SPRT décide si la nouvelle version apporte probablement un gain dans les
conditions testées ; il ne remplace ni les tests fonctionnels ni le classement
du pool complet.

---

## Ancienne arène Python

`src/arena/runner.py` reste disponible et marquée **legacy** jusqu'à ce que le
premier tournoi fastchess ait produit un artefact affiché correctement sur le
site. Ensuite elle est supprimée du chemin principal et de la documentation ;
l'historique Git suffit à conserver le « musée ».

---

## Ordre des commits et dépendances

Le tableau indique les dépendances techniques et une progression pratique. Les
commits restent propres : un commit ne mélange pas des responsabilités sans
rapport, et les fichiers d'une livraison sont rangés dans leurs dossiers
dédiés.

| # | Repo | Livraison | Validation principale |
|---|---|---|---|
| 1 | taboun | timeouts, `use_book`, tests historiques | mêmes coups par défaut, plateau intact |
| 2 | taboun | adaptateur UCI | tests + `fastchess --compliance` |
| 3 | taboun | ouvertures et lanceur fastchess | mini-tournoi puis reprise |
| 4 | taboun | Ordo et artefact public | cohérence PGN/CSV/JSON |
| 5 | geheim-land | page Arène publique et replay | aucun calcul moteur au replay |
| 6 | geheim-land | limite du moteur et ouverture progressive du jeu | tests + charge + observabilité |
| 7 | taboun | documentation SPRT | match de démonstration borné |
| 8 | les deux | premier tournoi officiel et publication | contrôle manuel de bout en bout |

Chaque commit doit être testable seul. Les changements des deux repos restent
séparés et référencent explicitement la version de l'autre repo attendue.

## Décisions retenues

- **Oui à l'arène professionnelle** : elle sert directement le développement
  et la promotion du projet.
- **fastchess**, version épinglée.
- **60 s + 0,6 s/coup** pour le classement officiel initial.
- **10 paires** pour les pilotes, **25 paires** pour une publication.
- **4 parties concurrentes maximum** sur le VPS à 6 cœurs.
- **Ordo**, Elo relatif avec **V1 = 1000**, jamais présenté comme absolu.
- **Pas d'adjudication par score** tant que les bots ne publient pas leur vrai
  score de recherche.
- **Arène publique avant jeu public**.
- **Artefacts immuables en lecture seule**, sans base de données pour le MVP.
- **Ancienne arène supprimée après validation**, l'historique Git la conserve.
- **Code très simple et organisé par usage**, même si cela demande davantage
  de petits fichiers Python.
- **Projet propre et bien rangé**, avec des fichiers classés par responsabilité
  selon l'arborescence cible.

## Critère de fin du chantier

Depuis un commit propre de `taboun`, une commande documentée doit pouvoir
lancer ou reprendre le tournoi, produire un classement et un paquet public,
puis publier atomiquement ce paquet. Un visiteur doit pouvoir ouvrir l'Arène,
comprendre les conditions, filtrer un duel, rejouer n'importe quelle partie et
atteindre le code exact des bots — sans déclencher une seule recherche.
