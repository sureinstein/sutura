# Sutura — Spécifications fonctionnelles MVP

## 1. Objet et utilisateurs

Sutura est une application communautaire mobile-first permettant aux habitants de Dakar de publier, consulter et confirmer des incidents de quartier. Le MVP privilégie un parcours court, le français simple, une faible consommation de données et la continuité de consultation hors ligne.

Acteurs : visiteur non connecté, membre authentifié, auteur d’une alerte. Aucun rôle administrateur n’est inclus au MVP.

## 2. Parcours et règles fonctionnelles

### Authentification et profil

1. Le visiteur saisit un numéro mobile sénégalais valide (`+221 70/75/76/77/78`).
2. Il reçoit un OTP à quatre chiffres, valable cinq minutes et utilisable une seule fois.
3. À la première connexion, il renseigne un pseudo de 2 à 50 caractères et son quartier principal.
4. Une session reste ouverte pendant sept jours. Il peut modifier son profil et se déconnecter.

En développement et dans les tests, l’OTP est retourné par l’API afin de ne pas dépendre d’un fournisseur SMS. En production, il doit uniquement être remis au fournisseur SMS.

### Fil d’actualité

- `Mon quartier` est la vue par défaut et utilise le quartier du profil.
- `Tout Dakar` affiche les alertes actives de tous les quartiers.
- Un filtre facultatif limite le fil à une catégorie.
- Les alertes sont triées de la plus récente à la plus ancienne, avec un maximum de 100 éléments.
- La carte présente catégorie, description, quartier, auteur, temps écoulé, photo éventuelle et actions disponibles.
- Les dernières réponses chargées sont consultables sans réseau.

### Publication

Un membre choisit une catégorie, un quartier prérempli, une description de 1 à 280 caractères, une photo facultative et l’exposition facultative de son numéro WhatsApp. Il peut aussi placer précisément l’incident sur une carte, par clic, déplacement du marqueur ou position GPS. L’alerte devient immédiatement active.

### Interaction et cycle de vie

- Un membre autre que l’auteur peut confirmer une alerte active une seule fois.
- Seul l’auteur peut marquer son alerte comme résolue.
- Une alerte résolue reste disponible pendant 24 h si les résolues sont demandées, puis expire.
- Une alerte active non renouvelée expire 48 h après publication.
- Les alertes expirées ne sont jamais présentes dans le fil courant.

## 3. Critères d’acceptation principaux

- Un numéro hors du plan mobile sénégalais est refusé avec un message explicite.
- Un OTP faux, expiré ou déjà utilisé est refusé.
- Un utilisateur non authentifié ne peut ni lire le fil ni publier.
- Une description de plus de 280 caractères est refusée côté interface et API.
- Une deuxième confirmation du même utilisateur n’incrémente pas le compteur.
- Un utilisateur ne peut pas résoudre l’alerte d’un autre.
- Le numéro WhatsApp n’apparaît que si l’auteur a activé l’option.
- Si une position exacte est renseignée, latitude et longitude sont enregistrées ensemble et un lien cartographique est affiché.
- Une image valide est orientée, redimensionnée et convertie en WebP sous 200 Ko.

## 4. Hors périmètre MVP

Modération avancée, commentaires, notifications push, renouvellement d’alerte, langues locales, analytics, intégration SMS réelle et suppression de compte.

## 5. Backoffice de traitement

Un utilisateur administrateur dispose d’un tableau de bord national protégé. Il peut consulter les indicateurs, filtrer par territoire, priorité, statut et groupe, basculer entre une liste et une carte, qualifier la priorité, faire évoluer le traitement et affecter une alerte à un groupe. La gestion des groupes permet la création, la consultation et la désactivation. La recherche des communes, communes d’arrondissement et quartiers interroge le référentiel OpenStreetMap en étant strictement limitée au Sénégal.

Les utilisateurs peuvent être affectés à un ou plusieurs groupes. Un groupe possède au maximum un lead. Un membre connecté accède à un espace de traitement qui ne restitue que les alertes affectées à ses groupes ; il peut en faire évoluer le statut opérationnel. La carte représente la criticité par couleur et l’impact communautaire par la taille du marqueur.

La carte du backoffice regroupe les alertes par quartier : chaque repère indique le nombre d’alertes de la zone, prend la couleur de la criticité maximale et augmente avec le volume d’alertes et de confirmations. Une recherche de quartier validée dans les suggestions ou par la touche Entrée actualise immédiatement la liste et la carte.

Le fil public affiche le statut provenant du backoffice au lieu d’une action de résolution par l’auteur. Toutes les alertes sont triées selon leur dernière modification : une affectation à un groupe ou un changement de priorité/statut replace immédiatement l’alerte concernée en tête.

Le fil se synchronise périodiquement lorsque l’application est visible. Les changements d’ordre sont animés et le statut « En cours » possède un indicateur d’activité. Les alertes traitées ou rejetées disparaissent du fil public, tout en restant consultables par leur auteur depuis « Mes alertes déclarées » dans son profil.

Le contact WhatsApp d’une alerte n’est jamais exposé dans le fil public. Lorsqu’il a été autorisé par le déclarant, il est uniquement transmis et affiché dans le backoffice administrateur et l’espace sécurisé des membres du groupe de traitement affecté.

« Mon quartier » est déterminé à chaque ouverture depuis la position actuelle de l’utilisateur ; le quartier du profil sert uniquement de repli si la localisation est indisponible. Le backoffice permet de filtrer les alertes par période de publication et de les trier par modification, publication ou criticité.
