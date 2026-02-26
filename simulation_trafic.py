##
# @file simulation_trafic.py  # Nom de fichier suggéré
# @brief Simulation 2D de trafic routier avec voitures, feux, obstacles et piétons utilisant Pygame.
# @details Ce script met en place une grille représentant un réseau routier simplifié.
#          Les voitures se déplacent vers des destinations aléatoires en suivant les sens de circulation
#          et en respectant les feux de signalisation et les piétons sur les passages dédiés.
#          Les utilisateurs peuvent ajouter/retirer des obstacles avec la souris.
# @author Sokhna Oumou DIOUF
# @author Rym BENOUMECHIARA
# @author Serigne Abdoulaye DIAO
# @author Daouda Sognoume COULIBALY
# @date 2025-04-06 

import pygame
import sys
import time
import random
import heapq

# Initialisation de Pygame
pygame.init() # Indispensable pour démarrer les modules Pygame

# --- Constantes de Configuration ---

## @brief Largeur de la fenêtre de simulation en pixels. */
LARGEUR = 1200
## @brief Hauteur de la fenêtre de simulation en pixels. */
HAUTEUR = 600
## @brief Taille de chaque cellule carrée de la grille en pixels. */
TAILLE_CELLULE = 40

# --- Définition des Couleurs ---

## @brief Couleur blanche (RVB). */
BLANC = (255, 255, 255)
## @brief Couleur noire (RVB). */
NOIR = (0, 0, 0)
## @brief Couleur verte (RVB), utilisée pour les feux verts. */
VERT = (0, 255, 0)
## @brief Couleur orange (RVB), utilisée pour les feux oranges. */
ORANGE = (255, 165, 0)
## @brief Couleur rouge (RVB), utilisée pour les feux rouges. */
ROUGE = (255, 0, 0)
## @brief Couleur gris foncé (RVB), utilisée pour les cercles inactifs des feux. */
GRIS_FONCE = (80, 80, 80)
## @brief Couleur jaune/dorée (RVB), utilisée pour dessiner les places de parking (destinations). */
JAUNE_PARKING = (255, 190, 0)

# --- Configuration de la Fenêtre et Horloge ---

## @brief Surface principale de dessin (la fenêtre). */
fenetre = pygame.display.set_mode((LARGEUR, HAUTEUR))
## @brief Titre affiché dans la barre de la fenêtre. */
pygame.display.set_caption("Simulation de Trafic Urbain")
## @brief Horloge Pygame pour contrôler la vitesse de la simulation (framerate). */
clock = pygame.time.Clock()

# --- Constantes de Simulation ---

## @brief Vitesse de base des voitures (peut être ajusté pour ralentir/accélérer). */
VITESSE_VOITURE = 1.5
## @brief Délai minimum en secondes entre deux déplacements d'une voiture (inverse de la vitesse). */
DELAI_MIN_MOUVEMENT = 1.0 / VITESSE_VOITURE
## @brief Temps en secondes après lequel une voiture bloquée tente un recalcul de chemin. */
SEUIL_BLOCAGE = 2.5
## @brief Nombre maximum d'échecs de recalcul avant de choisir une nouvelle destination. */
MAX_RECALCUL_ECHECS = 4

# --- Constantes et Structures pour Piétons ---

## @brief Nombre de passages piétons à générer initialement sur la grille. */
NB_PASSAGES_PIETONS = 5
## @brief Couleur (RVB) utilisée pour dessiner les zébrures des passages piétons. */
COULEUR_PASSAGE = (220, 220, 220) # Gris clair
## @brief Couleur (RVB) utilisée pour dessiner les piétons (bonshommes allumettes). */
COULEUR_PIETON = (0, 0, 0)       # Noir
## @brief Vitesse de traversée des piétons (fraction de la cellule par frame). Une valeur basse signifie une traversée lente. */
VITESSE_PIETON = 0.02
## @brief Probabilité (par frame et par passage libre) qu'un nouveau piéton apparaisse. */
PROBA_APPARITION_PIETON = 0.005 # Très faible pour éviter la surpopulation

##
# @var passages_pietons
# @brief Liste contenant les dictionnaires décrivant chaque passage piéton.
# @details Format: `[{'position': (x,y), 'orientation': 'horizontal'/'vertical'}, ...]`
passages_pietons = []
##
# @var pietons_actifs
# @brief Liste contenant les dictionnaires décrivant chaque piéton en cours de traversée.
# @details Format: `[{'id':int, 'passage_pos':(x,y), 'orientation':'h'/'v', 'progres':float(0.0-1.0)}, ...]`
pietons_actifs = []
## @brief Compteur pour attribuer un ID unique à chaque nouveau piéton. */
prochain_id_pieton = 0

# --- Chargement et Préparation de l'Image de Voiture ---

##
# @var car_image_base_scaled
# @brief Image de base de la voiture, redimensionnée à la taille de la cellule. Sera utilisée pour créer des instances colorées.
# @details Initialisée à `None`. Si le chargement échoue, les voitures seront des cercles.
car_image_base_scaled = None
try:
    # Tentative de charger l'image depuis un fichier 'car.png'
    car_image_original = pygame.image.load('car.png').convert_alpha() # `convert_alpha` pour la transparence
    # Calcul des dimensions pour que la voiture tienne dans la cellule avec une marge
    car_width = int(TAILLE_CELLULE * 0.85) # 85% de la largeur de la cellule
    # Conserver le ratio de l'image originale pour la hauteur
    car_height = int(car_image_original.get_height() * (car_width / car_image_original.get_width()))
    # Redimensionner l'image chargée aux dimensions calculées
    car_image_base_scaled = pygame.transform.scale(car_image_original, (car_width, car_height))
    print(f"Image de base 'car.png' chargée et redimensionnée ({car_width}x{car_height}).")
except Exception as e:
    # En cas d'échec (fichier manquant, erreur Pygame...), afficher un avertissement
    print(f"AVERTISSEMENT: Impossible de charger/redimensionner 'car.png'. Les voitures seront représentées par des cercles. Erreur: {e}")

# --- Fonctions Utilitaires ---

##
# @brief Crée une grille 2D vide (remplie d'espaces).
# @param taille_x Nombre de colonnes (largeur en cellules).
# @param taille_y Nombre de lignes (hauteur en cellules).
# @return Une liste de listes représentant la grille.
def creer_grille(taille_x, taille_y):
    """Crée une grille 2D initialisée avec des espaces."""
    return [[" " for _ in range(taille_x)] for _ in range(taille_y)]

##
# @brief Ajoute un obstacle ('X') sur la grille à la position spécifiée.
# @param grille La grille de simulation (liste de listes).
# @param x Coordonnée X (colonne) de l'obstacle.
# @param y Coordonnée Y (ligne) de l'obstacle.
# @param feux La liste des feux de circulation (pour ne pas placer d'obstacle sur un feu).
# @return True si l'obstacle a été ajouté (case libre et pas un feu), False sinon.
def ajouter_obstacle(grille, x, y, feux):
    """Ajoute un obstacle 'X' si la case est libre et n'est pas un feu."""
    positions_feux = {feu["position"] for feu in feux} # Ensemble des positions des feux pour recherche rapide
    # Vérifie si la position (x, y) n'est pas un feu et n'est pas déjà un obstacle
    if (x, y) not in positions_feux and grille[y][x] != "X":
        grille[y][x] = "X" # Place l'obstacle
        return True
    return False

##
# @brief Force les voitures affectées par un nouvel obstacle à recalculer leur chemin.
# @param obstacle_x Coordonnée X (colonne) du nouvel obstacle.
# @param obstacle_y Coordonnée Y (ligne) du nouvel obstacle.
# @param voitures La liste des voitures actives.
# @details Une voiture est affectée si l'obstacle se trouve sur son chemin actuel
#          ou si l'obstacle est sa destination actuelle.
def forcer_recalcul_si_affecte(obstacle_x, obstacle_y, voitures):
    """Réinitialise le chemin des voitures si l'obstacle ajouté les impacte."""
    obstacle_pos = tuple([obstacle_x, obstacle_y]) # Position de l'obstacle en tuple pour comparaison facile
    for v in voitures:
        # Convertit le chemin en liste de tuples pour la recherche (si le chemin existe)
        chemin_tuples = [tuple(p) for p in v["chemin"]] if v["chemin"] else []
        # Condition: obstacle sur le chemin OU obstacle est la destination et voiture pas encore arrivée
        if (obstacle_pos in chemin_tuples) or \
           (tuple(v["destination"]) == obstacle_pos and v["temps_arrivee"] is None):
            v["chemin"] = [] # Efface le chemin actuel pour forcer le recalcul
            v["recalcul_echecs"] = 0 # Réinitialise le compteur d'échecs

# --- Fonctions de Gestion des Piétons ---

##
# @brief Initialise et place aléatoirement les passages piétons sur la grille.
# @param n_passages Le nombre souhaité de passages piétons.
# @param taille_x Largeur de la grille en cellules.
# @param taille_y Hauteur de la grille en cellules.
# @param feux Liste des feux pour éviter de placer des passages dessus.
# @param grille La grille pour éviter de placer des passages sur des obstacles existants.
# @return Une liste de dictionnaires représentant les passages piétons placés.
# @details Tente de placer les passages sur des cases libres (ni feu, ni obstacle, ni autre passage),
#          en évitant les bords stricts pour simplifier. L'orientation (horizontale/verticale) est aléatoire.
def initialiser_passages_pietons(n_passages, taille_x, taille_y, feux, grille):
    """Place aléatoirement N passages piétons sur la grille."""
    nouveaux_passages = []
    # Ensemble des positions déjà occupées par des feux
    positions_interdites = {f['position'] for f in feux}
    # Ajoute les positions des obstacles existants
    for y in range(taille_y):
        for x in range(taille_x):
            if grille[y][x] == 'X':
                positions_interdites.add((x,y))

    tentatives = 0 # Compteur pour éviter une boucle infinie si la grille est trop pleine
    max_tentatives = n_passages * 100 # Limite raisonnable de tentatives

    # Boucle jusqu'à avoir placé N passages ou atteint la limite de tentatives
    while len(nouveaux_passages) < n_passages and tentatives < max_tentatives:
        # Choisit une position aléatoire (en évitant les bords x=0, x=max, y=0, y=max)
        px = random.randrange(1, taille_x - 1)
        py = random.randrange(1, taille_y - 1)
        pos = (px, py)

        # Vérifie si la case est disponible
        if pos not in positions_interdites and pos not in {p['position'] for p in nouveaux_passages}:
            # Choisit une orientation (direction des zébrures/traversée)
            orientation = random.choice(['horizontal', 'vertical'])
            passage = {'position': pos, 'orientation': orientation}
            nouveaux_passages.append(passage)
            positions_interdites.add(pos) # Marque la position comme occupée pour les suivants

        tentatives += 1

    # Affiche un avertissement si tous les passages n'ont pas pu être placés
    if len(nouveaux_passages) < n_passages:
         print(f"Avertissement: N'a pu placer que {len(nouveaux_passages)} passages piétons sur {n_passages} demandés.")

    print(f"Initialisé {len(nouveaux_passages)} passages piétons.")
    return nouveaux_passages

##
# @brief Met à jour l'état des piétons (déplacement, disparition) et en fait apparaître de nouveaux.
# @param passages Liste des passages piétons existants.
# @param pietons Liste des piétons actuellement actifs (cette liste sera modifiée).
# @param voitures Liste des voitures actives (pour vérifier les blocages).
# @details Fait avancer les piétons existants sauf si une voiture est arrêtée sur leur passage.
#          Supprime les piétons ayant fini de traverser.
#          Tente de faire apparaître de nouveaux piétons sur des passages libres (pas d'autre piéton, pas de voiture).
def mettre_a_jour_pietons(passages, pietons, voitures):
    """Gère l'apparition, le déplacement (conditionnel) et la disparition des piétons."""
    global prochain_id_pieton # Permet de modifier la variable globale

    # 1. Mise à jour des piétons existants
    pietons_restants = [] # Liste temporaire pour garder les piétons non arrivés
    for pieton in pietons:
        passage_pos = pieton['passage_pos'] # Position du passage du piéton
        # Vérifie si une voiture est ARRÊTÉE ('bloquee_depuis' non None) sur la case du passage
        voiture_bloquante_sur_passage = any(
            tuple(v['position']) == passage_pos and v.get('bloquee_depuis') is not None
            for v in voitures if v['temps_arrivee'] is None # Ne considérer que les voitures actives
        )

        # Le piéton avance seulement si AUCUNE voiture n'est ARRÊTÉE sur le passage
        if not voiture_bloquante_sur_passage:
             pieton['progres'] += VITESSE_PIETON # Augmente la progression

        # Garde le piéton s'il n'a pas atteint 100% de progression
        if pieton['progres'] < 1.0:
            pietons_restants.append(pieton)

    pietons[:] = pietons_restants # Remplace l'ancienne liste par la nouvelle

    # 2. Tentative d'apparition de nouveaux piétons
    # Condition probabiliste globale pour limiter la fréquence d'apparition
    if passages and random.random() < PROBA_APPARITION_PIETON * len(passages):
        # Choisir un passage au hasard parmi ceux disponibles
        passage_choisi = random.choice(passages)
        pos_passage = passage_choisi['position']

        # Vérifier si un autre piéton est DÉJÀ sur ce passage
        passage_occupe_par_pieton = any(p['passage_pos'] == pos_passage for p in pietons)

        # Vérifier si une voiture (active) occupe DÉJÀ la case du passage
        passage_occupe_par_voiture = any(
            tuple(v['position']) == pos_passage
            for v in voitures if v['temps_arrivee'] is None
        )

        # Crée un nouveau piéton uniquement si le passage est libre (ni piéton, ni voiture)
        if not passage_occupe_par_pieton and not passage_occupe_par_voiture:
            nouveau_pieton = {
                'id': prochain_id_pieton,
                'passage_pos': pos_passage,
                'orientation': passage_choisi['orientation'],
                'progres': 0.0 # Commence au début
            }
            pietons.append(nouveau_pieton) # Ajoute à la liste des actifs
            prochain_id_pieton += 1 # Incrémente l'ID pour le prochain

# --- Fonctions de Dessin ---

##
# @brief Dessine les zébrures (lignes) des passages piétons sur la fenêtre.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param passages La liste des passages piétons à dessiner.
# @param taille_cellule La taille d'une cellule en pixels.
# @param couleur La couleur (RVB) des zébrures. Par défaut: COULEUR_PASSAGE.
# @param largeur_zebre L'épaisseur des lignes de zébrures en pixels.
def dessiner_passages_pietons(fenetre, passages, taille_cellule, couleur=COULEUR_PASSAGE, largeur_zebre=5):
    """Dessine les zébrures des passages piétons."""
    marge = taille_cellule // 6 # Petite marge à l'intérieur de la cellule pour l'esthétique

    for passage in passages:
        x_cell, y_cell = passage['position'] # Coordonnées de la cellule du passage
        orientation = passage['orientation'] # 'horizontal' ou 'vertical'
        # Rectangle délimitant la cellule sur la fenêtre
        cell_rect = pygame.Rect(x_cell * taille_cellule, y_cell * taille_cellule, taille_cellule, taille_cellule)

        if orientation == 'horizontal': # Si traversée horizontale -> zébrures verticales
            y_debut = cell_rect.top + marge
            y_fin = cell_rect.bottom - marge
            x_courant = cell_rect.left + marge
            # Dessine des lignes verticales espacées
            while x_courant < cell_rect.right - marge:
                 pygame.draw.line(fenetre, couleur, (x_courant, y_debut), (x_courant, y_fin), largeur_zebre)
                 x_courant += largeur_zebre * 2 # Espace entre les lignes = largeur ligne
        else: # Si traversée verticale -> zébrures horizontales
             x_debut = cell_rect.left + marge
             x_fin = cell_rect.right - marge
             y_courant = cell_rect.top + marge
             # Dessine des lignes horizontales espacées
             while y_courant < cell_rect.bottom - marge:
                 pygame.draw.line(fenetre, couleur, (x_debut, y_courant), (x_fin, y_courant), largeur_zebre)
                 y_courant += largeur_zebre * 2

##
# @brief Dessine les piétons actifs sous forme de bonshommes allumettes.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param pietons La liste des piétons actifs.
# @param taille_cellule La taille d'une cellule en pixels.
# @param couleur La couleur (RVB) du piéton. Par défaut: COULEUR_PIETON.
# @param epaisseur_ligne L'épaisseur des traits du bonhomme.
def dessiner_pietons(fenetre, pietons, taille_cellule, couleur=COULEUR_PIETON, epaisseur_ligne=2):
    """Dessine les piétons actifs comme des bonshommes allumettes en traversée."""
    demi_cell = taille_cellule // 2

    # --- Dimensions relatives du bonhomme (basées sur la taille de la cellule) ---
    # Ces ratios permettent au bonhomme de s'adapter si TAILLE_CELLULE change.
    head_radius_ratio = 0.10  # Rayon de la tête relatif à la taille de cellule
    torso_height_ratio = 0.25 # Hauteur du torse relative
    limb_length_ratio = 0.20  # Longueur des membres relative

    # Calcul des dimensions en pixels (avec un minimum pour rester visible si cellule petite)
    head_radius = max(2, int(taille_cellule * head_radius_ratio))
    torso_dy = max(3, int(taille_cellule * torso_height_ratio)) # Longueur verticale du torse
    limb_len = max(3, int(taille_cellule * limb_length_ratio)) # Longueur des bras/jambes

    for pieton in pietons:
        x_cell, y_cell = pieton['passage_pos'] # Cellule du passage
        orientation = pieton['orientation']   # Direction de traversée
        progres = pieton['progres']           # Position dans la traversée (0.0 à 1.0)

        # Coordonnées du centre de la cellule du passage (en pixels)
        cx_cell = x_cell * taille_cellule + demi_cell
        cy_cell = y_cell * taille_cellule + demi_cell

        # Calcul de la position du *centre* du piéton en pixels en fonction de la progression
        px, py = cx_cell, cy_cell # Point de référence
        if orientation == 'horizontal':
            # Calcul des points de départ/fin de traversée avec une marge pour la tête
            start_x = cx_cell - demi_cell + head_radius * 2
            end_x = cx_cell + demi_cell - head_radius * 2
            px = start_x + (end_x - start_x) * progres # Position X interpolée
            py = cy_cell                               # Position Y constante
        else: # Vertical
            start_y = cy_cell - demi_cell + head_radius * 2
            end_y = cy_cell + demi_cell - head_radius * 2
            py = start_y + (end_y - start_y) * progres # Position Y interpolée
            px = cx_cell                               # Position X constante

        # Position centrale du corps du bonhomme (entiers pour dessin)
        center_x = int(px)
        center_y = int(py)

        # --- Calcul des points du bonhomme (relatifs à center_x, center_y) ---
        # Tête (cercle au-dessus du torse)
        head_center_y = center_y - (torso_dy // 2) - head_radius
        head_pos = (center_x, head_center_y)

        # Torse (ligne verticale)
        torso_top_y = center_y - (torso_dy // 2)
        torso_bottom_y = center_y + (torso_dy // 2)
        torso_start = (center_x, torso_top_y) # Point haut
        torso_end = (center_x, torso_bottom_y) # Point bas (hanches)

        # Point "épaules" (un peu en dessous du haut du torse)
        shoulder_y = torso_top_y + int(torso_dy * 0.1)
        shoulder_point = (center_x, shoulder_y)

        # Point "hanches" (bas du torse)
        hip_point = torso_end

        # Bras (en forme de V vers le bas depuis les épaules)
        arm_angle_offset_x = int(limb_len * 0.7) # Écartement horizontal
        arm_end_y = shoulder_y + int(limb_len * 0.7) # Descendent un peu
        left_arm_end = (center_x - arm_angle_offset_x, arm_end_y)
        right_arm_end = (center_x + arm_angle_offset_x, arm_end_y)

        # Jambes (en forme de V inversé depuis les hanches)
        leg_angle_offset_x = int(limb_len * 0.5) # Moins écartées
        leg_end_y = torso_bottom_y + limb_len # Descendent
        left_leg_end = (center_x - leg_angle_offset_x, leg_end_y)
        right_leg_end = (center_x + leg_angle_offset_x, leg_end_y)

        # --- Dessiner les parties du bonhomme ---
        pygame.draw.circle(fenetre, couleur, head_pos, head_radius)                  # Tête
        pygame.draw.line(fenetre, couleur, torso_start, torso_end, epaisseur_ligne)   # Torse
        pygame.draw.line(fenetre, couleur, shoulder_point, left_arm_end, epaisseur_ligne) # Bras G
        pygame.draw.line(fenetre, couleur, shoulder_point, right_arm_end, epaisseur_ligne)# Bras D
        pygame.draw.line(fenetre, couleur, hip_point, left_leg_end, epaisseur_ligne)    # Jambe G
        pygame.draw.line(fenetre, couleur, hip_point, right_leg_end, epaisseur_ligne)   # Jambe D

# --- Fonctions de Gestion des Feux ---

##
# @brief Initialise et répartit les feux de circulation sur la grille.
# @param taille_y Hauteur de la grille en cellules.
# @param taille_x Largeur de la grille en cellules.
# @return Une liste de dictionnaires représentant les feux initialisés.
# @details Place les feux sur des intersections potentielles (pas sur les bords)
#          en respectant des contraintes: maximum 1 feu par ligne et 1 par colonne.
#          Les durées (vert, orange, rouge) sont fixes mais l'état initial et le décalage
#          sont aléatoires pour désynchroniser les feux.
def initialiser_feux_repartis(taille_y, taille_x):
    """Crée et place les feux en limitant leur nombre par ligne et par colonne."""
    feux = [] # Liste des feux créés
    positions_occupees = set() # Ensemble pour suivre les cases déjà prises par un feu

    # --- Contraintes et Compteurs ---
    MAX_FEUX_PAR_LIGNE = 1 # Limite par ligne horizontale
    MAX_FEUX_PAR_COLONNE = 1 # Limite par colonne verticale
    feux_par_ligne = {}      # Dictionnaire {ligne_y: nombre_feux}
    feux_par_colonne = {}    # Dictionnaire {colonne_x: nombre_feux}

    # --- Durées fixes pour tous les feux ---
    duree_vert = 20.0   # Secondes
    duree_orange = 3.0  # Secondes
    duree_rouge = 8.0   # Secondes

    # Génère la liste de toutes les cases candidates (pas les bords)
    intersections_potentielles = []
    for y in range(1, taille_y - 1):
        for x in range(1, taille_x - 1):
             intersections_potentielles.append((x, y))

    random.shuffle(intersections_potentielles) # Mélange pour un placement aléatoire

    # Itère sur les positions candidates mélangées
    for pos in intersections_potentielles:
        x, y = pos # Coordonnées de la case candidate

        # Vérifie si on peut placer un feu ici selon les contraintes
        peut_placer = (
            feux_par_ligne.get(y, 0) < MAX_FEUX_PAR_LIGNE and    # Limite ligne ok?
            feux_par_colonne.get(x, 0) < MAX_FEUX_PAR_COLONNE and # Limite colonne ok?
            pos not in positions_occupees                       # Case non déjà prise?
        )

        if peut_placer:
            # --- Déterminer l'état initial et le décalage temporel ---
            # Choisir aléatoirement entre vert ou rouge comme état initial
            if random.choice([True, False]):
                 etat_initial = "vert"
                 duree_actuelle_initiale = duree_vert
            else:
                 etat_initial = "rouge"
                 duree_actuelle_initiale = duree_rouge
            # Introduire un décalage aléatoire dans le cycle pour éviter la synchronisation parfaite
            decalage_initial = random.uniform(0, duree_actuelle_initiale)

            # --- Créer le dictionnaire représentant le feu ---
            feu = {
                "position": pos,                            # Coordonnées (x, y)
                "etat": etat_initial,                       # "vert", "orange" ou "rouge"
                "duree_vert": duree_vert,
                "duree_orange": duree_orange,
                "duree_rouge": duree_rouge,
                "duree_actuelle": duree_actuelle_initiale,  # Durée de l'état en cours
                "dernier_changement": time.time() - decalage_initial # Moment du dernier changement (avec décalage)
            }

            # --- Ajouter le feu et mettre à jour les compteurs/positions ---
            feux.append(feu)
            positions_occupees.add(pos)
            feux_par_ligne[y] = feux_par_ligne.get(y, 0) + 1
            feux_par_colonne[x] = feux_par_colonne.get(x, 0) + 1

    # Affiche un résumé des feux créés
    print(f"Initialisé {len(feux)} feux (max {MAX_FEUX_PAR_LIGNE}/ligne, max {MAX_FEUX_PAR_COLONNE}/colonne) avec durées V:{duree_vert}s, O:{duree_orange}s, R:{duree_rouge}s.")
    return feux

##
# @brief Met à jour l'état (couleur) de chaque feu en fonction du temps écoulé.
# @param feux La liste des feux de circulation (sera modifiée).
# @details Pour chaque feu, vérifie si la durée de son état actuel est dépassée.
#          Si oui, passe à l'état suivant du cycle (vert -> orange -> rouge -> vert)
#          et met à jour la durée et le moment du changement.
def mettre_a_jour_feux(feux):
    """Change l'état des feux (vert/orange/rouge) en fonction du temps."""
    temps_actuel = time.time() # Obtenir le temps courant une seule fois pour la cohérence
    for feu in feux:
        # Vérifie si le temps écoulé depuis le dernier changement dépasse la durée de l'état actuel
        if temps_actuel - feu["dernier_changement"] > feu["duree_actuelle"]:
            # --- Changement d'état selon le cycle V -> O -> R -> V ---
            if feu["etat"] == "vert":
                feu["etat"] = "orange"
                feu["duree_actuelle"] = feu["duree_orange"]
            elif feu["etat"] == "orange":
                feu["etat"] = "rouge"
                feu["duree_actuelle"] = feu["duree_rouge"]
            elif feu["etat"] == "rouge":
                feu["etat"] = "vert"
                feu["duree_actuelle"] = feu["duree_vert"]
            # Met à jour le moment du dernier changement pour le nouvel état
            feu["dernier_changement"] = temps_actuel

# --- Fonctions de Gestion des Directions de Routes ---

##
# @brief Définit les sens de circulation autorisés pour chaque ligne et colonne.
# @param taille_x Largeur de la grille en cellules.
# @param taille_y Hauteur de la grille en cellules.
# @return Un tuple contenant deux dictionnaires:
#         - `directions_lignes`: {ligne_y: "droite" ou "gauche"}
#         - `directions_colonnes`: {colonne_x: "bas" ou "haut"}
# @details Alterne les directions: lignes paires vers la droite, impaires vers la gauche;
#          colonnes paires vers le bas, impaires vers le haut.
def creer_directions_routes(taille_x, taille_y):
    """Définit les sens uniques alternés pour les lignes et colonnes."""
    # Dictionnaire pour les directions des lignes (horizontales)
    directions_lignes = {y: "droite" if y % 2 == 0 else "gauche" for y in range(taille_y)}
    # Dictionnaire pour les directions des colonnes (verticales)
    directions_colonnes = {x: "bas" if x % 2 == 0 else "haut" for x in range(taille_x)}
    return directions_lignes, directions_colonnes

##
# @brief Vérifie si une voiture peut sortir d'une case donnée en suivant les sens de circulation.
# @param pos Le tuple (x, y) de la case à vérifier.
# @param taille_x Largeur de la grille en cellules.
# @param taille_y Hauteur de la grille en cellules.
# @param directions_lignes Dictionnaire des sens de circulation des lignes.
# @param directions_colonnes Dictionnaire des sens de circulation des colonnes.
# @param grille La grille (pour vérifier les obstacles).
# @return True si au moins une sortie valide (non bloquée par 'X' et suivant la direction) existe, False sinon.
# @details Utile pour s'assurer que les positions initiales et les destinations ne sont pas des impasses.
def est_case_escapable(pos, taille_x, taille_y, directions_lignes, directions_colonnes, grille):
    """Vérifie s'il existe au moins une sortie valide depuis cette case."""
    x, y = pos
    # Vérifie la sortie horizontale possible
    direction_ligne = directions_lignes.get(y) # Obtient la direction autorisée pour cette ligne
    if direction_ligne == "droite" and x + 1 < taille_x and grille[y][x+1] != 'X':
        return True # Peut aller à droite
    elif direction_ligne == "gauche" and x - 1 >= 0 and grille[y][x-1] != 'X':
        return True # Peut aller à gauche

    # Vérifie la sortie verticale possible
    direction_colonne = directions_colonnes.get(x) # Obtient la direction autorisée pour cette colonne
    if direction_colonne == "bas" and y + 1 < taille_y and grille[y+1][x] != 'X':
        return True # Peut aller en bas
    elif direction_colonne == "haut" and y - 1 >= 0 and grille[y-1][x] != 'X':
        return True # Peut aller en haut

    # Si aucune des sorties ci-dessus n'est valide
    return False

# --- Fonctions de Dessin (suite) ---

##
# @brief Dessine les lignes de la grille sur la fenêtre.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param largeur Largeur totale de la fenêtre en pixels.
# @param hauteur Hauteur totale de la fenêtre en pixels.
# @param taille_cellule Taille d'une cellule en pixels.
def dessiner_grille(fenetre, largeur, hauteur, taille_cellule):
    """Dessine les lignes noires de la grille."""
    epaisseur_ligne = 2 # Épaisseur des lignes
    # Dessine les lignes verticales
    for x in range(0, largeur + 1, taille_cellule):
        pygame.draw.line(fenetre, NOIR, (x, 0), (x, hauteur), epaisseur_ligne)
    # Dessine les lignes horizontales
    for y in range(0, hauteur + 1, taille_cellule):
        pygame.draw.line(fenetre, NOIR, (0, y), (largeur, y), epaisseur_ligne)

##
# @brief Dessine les obstacles ('X') présents dans la grille comme des carrés noirs.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param grille La grille de simulation.
# @param taille_cellule La taille d'une cellule en pixels.
def dessiner_obstacles(fenetre, grille, taille_cellule):
    """Dessine les obstacles ('X') comme des carrés noirs pleins."""
    for y in range(len(grille)):
        for x in range(len(grille[0])):
            if grille[y][x] == "X":
                # Dessine un rectangle noir remplissant la cellule
                pygame.draw.rect(fenetre, NOIR, (x * taille_cellule, y * taille_cellule, taille_cellule, taille_cellule))

##
# @brief Dessine les feux de circulation comme trois petits cercles verticaux (rouge, orange, vert).
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param feux La liste des feux à dessiner.
# @param taille_cellule La taille d'une cellule en pixels.
# @details Seul le cercle correspondant à l'état actuel du feu est coloré, les autres sont gris foncé.
#          Un contour noir est ajouté pour améliorer la visibilité.
def dessiner_feux(fenetre, feux, taille_cellule):
    """Dessine chaque feu comme 3 petits cercles superposés (R, O, V)."""
    for feu in feux:
        x, y = feu["position"] # Coordonnées de la cellule du feu
        dc = taille_cellule // 2 # Demi-cellule
        cx = x * taille_cellule + dc # Coordonnée X du centre de la cellule
        cy = y * taille_cellule + dc # Coordonnée Y du centre de la cellule

        # --- Paramètres visuels des petits cercles du feu ---
        rayon = max(3, taille_cellule // 8) # Rayon adaptable, minimum 3 pixels
        # Espacement vertical entre les centres des cercles (proportionnel au rayon)
        espacement_vertical = int(rayon * 2.2)
        epaisseur_contour = 1 # Épaisseur du contour noir

        # --- Déterminer les couleurs en fonction de l'état ---
        etat_actuel = feu["etat"]       # "rouge", "orange" ou "vert"
        couleur_inactive = GRIS_FONCE   # Couleur pour les lumières éteintes

        # Assigner la couleur vive si le feu est actif, sinon la couleur inactive
        couleur_r = ROUGE if etat_actuel == "rouge" else couleur_inactive
        couleur_o = ORANGE if etat_actuel == "orange" else couleur_inactive
        couleur_v = VERT if etat_actuel == "vert" else couleur_inactive

        # --- Calculer les positions centrales des 3 cercles alignés verticalement ---
        centre_r = (cx, cy - espacement_vertical) # Rouge en haut
        centre_o = (cx, cy)                       # Orange au milieu (centre de la cellule)
        centre_v = (cx, cy + espacement_vertical) # Vert en bas

        # --- Dessiner les cercles remplis ---
        pygame.draw.circle(fenetre, couleur_r, centre_r, rayon)
        pygame.draw.circle(fenetre, couleur_o, centre_o, rayon)
        pygame.draw.circle(fenetre, couleur_v, centre_v, rayon)

        # --- Dessiner les contours noirs (facultatif, mais améliore la lecture) ---
        if epaisseur_contour > 0:
            pygame.draw.circle(fenetre, NOIR, centre_r, rayon, epaisseur_contour)
            pygame.draw.circle(fenetre, NOIR, centre_o, rayon, epaisseur_contour)
            pygame.draw.circle(fenetre, NOIR, centre_v, rayon, epaisseur_contour)

##
# @brief Dessine de petites flèches sur les bords pour indiquer les sens de circulation.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param directions_lignes Dictionnaire des directions des lignes.
# @param directions_colonnes Dictionnaire des directions des colonnes.
# @param taille_x Largeur de la grille en cellules.
# @param taille_y Hauteur de la grille en cellules.
# @param taille_cellule La taille d'une cellule en pixels.
# @details Dessine des flèches près du bord correspondant à la direction (ex: flèche à gauche pour lignes "droite").
def dessiner_directions(fenetre, directions_lignes, directions_colonnes, taille_x, taille_y, taille_cellule):
    """Dessine des flèches sur les bords pour indiquer les sens de circulation."""
    tf = taille_cellule * 0.3 # Taille relative de la flèche
    dc = taille_cellule // 2 # Demi-cellule
    cf = NOIR               # Couleur de la flèche
    epaisseur = 2           # Épaisseur de la ligne de la flèche
    taille_pointe = 6      # Longueur des "ailes" de la pointe de flèche
    largeur_pointe = 4     # Demi-largeur des "ailes"

    # Flèches pour les directions des LIGNES (Horizontales)
    for y, direction in directions_lignes.items():
        cy = y * taille_cellule + dc # Centre Y de la ligne
        if direction == "droite":
            # Flèche pointant vers la droite, placée sur le bord GAUCHE
            cx = 0 * taille_cellule + dc # Centre X (sur le bord gauche)
            sp = (cx - tf / 2, cy) # Début de la ligne (un peu à gauche du centre)
            ep = (cx + tf / 2, cy) # Fin de la ligne (un peu à droite du centre) -> Pointe de la flèche
            pygame.draw.line(fenetre, cf, sp, ep, epaisseur)
            # Pointe de la flèche (triangle pointant vers la droite)
            pygame.draw.polygon(fenetre, cf, [(ep), (ep[0] - taille_pointe, ep[1] - largeur_pointe), (ep[0] - taille_pointe, ep[1] + largeur_pointe)])
        elif direction == "gauche":
            # Flèche pointant vers la gauche, placée sur le bord DROIT
            cx = (taille_x - 1) * taille_cellule + dc # Centre X (sur le bord droit)
            sp = (cx + tf / 2, cy) # Début de la ligne (droite)
            ep = (cx - tf / 2, cy) # Fin de la ligne (gauche) -> Pointe
            pygame.draw.line(fenetre, cf, sp, ep, epaisseur)
            # Pointe de la flèche (triangle pointant vers la gauche)
            pygame.draw.polygon(fenetre, cf, [(ep), (ep[0] + taille_pointe, ep[1] - largeur_pointe), (ep[0] + taille_pointe, ep[1] + largeur_pointe)])

    # Flèches pour les directions des COLONNES (Verticales)
    for x, direction in directions_colonnes.items():
        cx = x * taille_cellule + dc # Centre X de la colonne
        if direction == "bas":
            # Flèche pointant vers le bas, placée sur le bord HAUT
            cy = 0 * taille_cellule + dc # Centre Y (sur le bord haut)
            sp = (cx, cy - tf / 2) # Début (haut)
            ep = (cx, cy + tf / 2) # Fin (bas) -> Pointe
            pygame.draw.line(fenetre, cf, sp, ep, epaisseur)
            # Pointe de la flèche (triangle pointant vers le bas)
            pygame.draw.polygon(fenetre, cf, [(ep), (ep[0] - largeur_pointe, ep[1] - taille_pointe), (ep[0] + largeur_pointe, ep[1] - taille_pointe)])
        elif direction == "haut":
            # Flèche pointant vers le haut, placée sur le bord BAS
            cy = (taille_y - 1) * taille_cellule + dc # Centre Y (sur le bord bas)
            sp = (cx, cy + tf / 2) # Début (bas)
            ep = (cx, cy - tf / 2) # Fin (haut) -> Pointe
            pygame.draw.line(fenetre, cf, sp, ep, epaisseur)
            # Pointe de la flèche (triangle pointant vers le haut)
            pygame.draw.polygon(fenetre, cf, [(ep), (ep[0] - largeur_pointe, ep[1] + taille_pointe), (ep[0] + largeur_pointe, ep[1] + taille_pointe)])


##
# @brief Dessine les voitures sur la fenêtre.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param voitures La liste des voitures à dessiner.
# @param taille_cellule La taille d'une cellule en pixels.
# @details Utilise l'image préchargée (`car_image_base_scaled`) si disponible, en la colorant
#          spécifiquement pour chaque voiture et en la faisant pivoter selon son orientation.
#          Si l'image n'a pas pu être chargée, dessine des cercles colorés à la place.
#          Affiche également l'ID de la voiture.
#          Une rotation spéciale est appliquée lorsque la voiture est arrivée à destination ("garée").
def dessiner_voitures(fenetre, voitures, taille_cellule):
    """Dessine les voitures (image ou cercle) avec leur orientation et ID."""
    t = time.time() # Temps actuel pour gérer la disparition des voitures arrivées
    font = pygame.font.Font(None, 16) # Police pour afficher l'ID
    font_color_on_image = BLANC        # Couleur de l'ID si dessiné sur l'image
    font_color_on_circle = BLANC       # Couleur de l'ID si dessiné sur le cercle
    dc = taille_cellule // 2           # Demi-cellule pour centrer
    ANGLE_PARKED = 90 # Angle fixe (en degrés) quand la voiture est arrivée (arbitrairement 90°)

    for v in voitures:
        # Ne dessine la voiture que si elle est active OU si elle vient d'arriver (pendant 1 sec)
        if v["temps_arrivee"] is None or t - v["temps_arrivee"] < 1.0:
            x, y = v["position"]         # Coordonnées actuelles de la voiture (cellule)
            cx = x * taille_cellule + dc # Centre X en pixels
            cy = y * taille_cellule + dc # Centre Y en pixels

            # Récupère l'image spécifique (déjà colorée) de cette voiture, si elle existe
            voiture_img_base_colored = v.get("image")

            if voiture_img_base_colored:
                # --- Gestion de l'Image ---
                final_angle = 0 # Angle de rotation par défaut
                # Conditions pour déterminer si la voiture est "garée"
                is_arrived_event = v["temps_arrivee"] is not None  # L'événement d'arrivée a eu lieu
                is_at_destination_pos = tuple(v["position"]) == tuple(v["destination"]) # Elle est physiquement sur la case dest

                # Si arrivée ET sur la case destination -> appliquer l'angle de parking
                if is_arrived_event and is_at_destination_pos:
                    final_angle = ANGLE_PARKED
                else:
                    # Sinon, utiliser l'orientation calculée pendant le déplacement
                    final_angle = v.get("orientation", 0) # Prend l'orientation stockée, ou 0 si non définie

                # Appliquer la rotation à l'image *colorée* de cette voiture
                rotated_img = pygame.transform.rotate(voiture_img_base_colored, final_angle)
                # Obtenir le rectangle de l'image tournée et le recentrer sur (cx, cy)
                rotated_rect = rotated_img.get_rect(center=(cx, cy))
                # Dessiner l'image tournée sur la fenêtre
                fenetre.blit(rotated_img, rotated_rect)

                # --- Dessiner l'ID sur l'image ---
                txt_surface = font.render(str(v["id"]), True, font_color_on_image)
                text_rect = txt_surface.get_rect(center=rotated_rect.center) # Centrer sur le rect de l'image
                fenetre.blit(txt_surface, text_rect)

            else:
                # --- Gestion du Cercle (Fallback si image non chargée) ---
                r = dc - 5 # Rayon un peu plus petit que la demi-cellule
                pygame.draw.circle(fenetre, v["couleur"], (cx, cy), r) # Dessine le cercle

                # --- Dessiner l'ID sur le cercle ---
                txt_surface = font.render(str(v["id"]), True, font_color_on_circle)
                text_rect = txt_surface.get_rect(center=(cx, cy)) # Centrer sur le centre du cercle
                fenetre.blit(txt_surface, text_rect)

##
# @brief Dessine des indicateurs visuels (places de parking stylisées) pour les destinations des voitures actives.
# @param fenetre La surface Pygame sur laquelle dessiner.
# @param voitures La liste des voitures.
# @param taille_cellule La taille d'une cellule en pixels.
# @param couleur_lignes La couleur (RVB) des lignes de la place de parking. Par défaut: JAUNE_PARKING.
# @param epaisseur_lignes L'épaisseur des lignes de la place.
# @details Pour chaque destination unique actuellement visée par au moins une voiture active,
#          dessine une représentation schématique de place de parking (deux lignes latérales, une ligne arrière pointillée).
#          Affiche également l'ID de la *première* voiture trouvée allant vers cette destination.
def dessiner_destinations(fenetre, voitures, taille_cellule, couleur_lignes=JAUNE_PARKING, epaisseur_lignes=2):
    """Dessine une place de parking stylisée pour chaque destination unique active."""
    t = time.time()                   # Temps actuel pour filtrer les voitures actives
    font = pygame.font.Font(None, 16) # Police pour l'ID sur la place
    font_color_id = NOIR              # Couleur de l'ID

    # --- Paramètres visuels de la place de parking (ratios de la taille de cellule) ---
    marge_laterale_ratio = 0.15 # Espace sur les côtés des lignes latérales
    marge_haut_ratio = 0.15     # Espace en haut (où commence la place)
    marge_bas_ratio = 0.40      # Marge en bas (influence la longueur des lignes latérales)
    # Pour la ligne arrière pointillée
    longueur_pointille = max(4, taille_cellule // 10) # Longueur de chaque tiret
    espace_pointille = max(3, taille_cellule // 15)   # Espace entre les tirets

    # --- Étape 1: Identifier les destinations uniques et associer un ID ---
    # On ne veut dessiner qu'UNE SEULE place par coordonnée de destination,
    # même si plusieurs voitures y vont.
    destinations_visibles = {} # Dictionnaire: { (dest_x, dest_y) : premier_id_voiture_trouvé }

    for v in voitures:
        # Considérer uniquement les voitures actives ou qui viennent d'arriver
        if v["temps_arrivee"] is None or t - v["temps_arrivee"] < 1.0:
            dest_tuple = tuple(v["destination"]) # Destination sous forme de tuple (utilisable comme clé)
            # Si cette destination n'est pas encore dans notre dictionnaire, l'ajouter.
            # On prend l'ID de la première voiture qu'on trouve pour cette destination.
            if dest_tuple not in destinations_visibles:
                destinations_visibles[dest_tuple] = v["id"]

    # --- Étape 2: Dessiner une place pour chaque destination unique trouvée ---
    for dest_pos, voiture_id in destinations_visibles.items():
        dx, dy = dest_pos # Coordonnées de la cellule destination

        # --- Calculs des coordonnées en pixels pour dessiner la place DANS la cellule (dx, dy) ---
        cell_x = dx * taille_cellule # Coin supérieur gauche X de la cellule
        cell_y = dy * taille_cellule # Coin supérieur gauche Y de la cellule
        # Conversion des ratios en pixels
        marge_laterale_px = int(taille_cellule * marge_laterale_ratio)
        marge_haut_px = int(taille_cellule * marge_haut_ratio)
        marge_bas_px = int(taille_cellule * marge_bas_ratio) # Détermine jusqu'où descend la ligne latérale

        # Coordonnées des lignes latérales (verticales)
        ligne_gauche_x = cell_x + marge_laterale_px
        ligne_droite_x = cell_x + taille_cellule - marge_laterale_px
        ligne_haut_y = cell_y + marge_haut_px              # Y de départ des lignes lat. et arrière
        ligne_bas_y = cell_y + taille_cellule - marge_bas_px # Y de fin des lignes latérales

        # Coordonnées de la ligne arrière (horizontale, en haut)
        ligne_arriere_y = ligne_haut_y
        ligne_arriere_debut_x = ligne_gauche_x
        ligne_arriere_fin_x = ligne_droite_x

        # --- Dessin des lignes ---
        # Ligne latérale gauche (verticale)
        pygame.draw.line(fenetre, couleur_lignes, (ligne_gauche_x, ligne_haut_y), (ligne_gauche_x, ligne_bas_y), epaisseur_lignes)
        # Ligne latérale droite (verticale)
        pygame.draw.line(fenetre, couleur_lignes, (ligne_droite_x, ligne_haut_y), (ligne_droite_x, ligne_bas_y), epaisseur_lignes)
        # Ligne arrière (pointillée horizontale)
        x_courant = ligne_arriere_debut_x
        while x_courant < ligne_arriere_fin_x:
            # Calcule la fin du tiret actuel (sans dépasser la fin de la ligne)
            x_fin_tiret = min(x_courant + longueur_pointille, ligne_arriere_fin_x)
            # Dessine un tiret
            pygame.draw.line(fenetre, couleur_lignes, (x_courant, ligne_arriere_y), (x_fin_tiret, ligne_arriere_y), epaisseur_lignes)
            # Avance pour le prochain tiret (longueur + espace)
            x_courant += longueur_pointille + espace_pointille

        # --- Dessin de l'ID de la voiture associée (centré dans la place) ---
        centre_id_x = cell_x + taille_cellule // 2 # Milieu horizontal de la cellule
        # Milieu vertical entre le haut et le bas des lignes latérales
        centre_id_y = (ligne_haut_y + ligne_bas_y) // 2

        # Crée la surface texte avec l'ID récupéré
        txt_surface = font.render(str(voiture_id), True, font_color_id)
        # Obtient le rectangle et le centre
        text_rect = txt_surface.get_rect(center=(centre_id_x, centre_id_y))
        # Dessine le texte
        fenetre.blit(txt_surface, text_rect)


# --- Fonctions de Gestion des Voitures ---

##
# @brief Génère la population initiale de voitures sur la grille.
# @param taille_x Largeur de la grille.
# @param taille_y Hauteur de la grille.
# @param feux Liste des feux (pour éviter de placer des voitures dessus).
# @param grille La grille (pour éviter les obstacles).
# @param directions_lignes Dictionnaire des directions de lignes.
# @param directions_colonnes Dictionnaire des directions de colonnes.
# @param img_base_voiture L'image Pygame de base pour les voitures (peut être None).
# @param n_voitures Le nombre souhaité de voitures initiales.
# @return Une liste de dictionnaires représentant les voitures créées.
# @details Place chaque voiture sur une case valide aléatoire (pas un feu, pas un obstacle,
#          pas déjà occupée par une autre voiture initiale, et "escapable") et lui assigne
#          une destination aléatoire valide et différente. Prépare également une version
#          colorée de l'image de base si fournie.
def generer_voitures_initiales(taille_x, taille_y, feux, grille, directions_lignes, directions_colonnes, img_base_voiture, n_voitures = 50):
    """Crée les voitures initiales avec positions et destinations aléatoires valides."""
    voitures = [] # Liste pour stocker les voitures générées
    num_voiture = 1 # ID de la première voiture
    positions_feux = {feu["position"] for feu in feux} # Positions des feux pour vérif rapide
    # Ensemble pour suivre les positions initiales déjà utilisées par d'autres voitures générées DANS CETTE FONCTION
    positions_occupees_initiales = set()
    tentatives_max_par_voiture = 100 # Limite pour trouver une pos/dest valide

    # Boucle pour essayer de générer le nombre demandé de voitures
    # Limite supérieure pour num_voiture pour éviter boucle infinie si placement impossible
    while len(voitures) < n_voitures and num_voiture < n_voitures * 3:
        pos_initiale, dest = None, None

        # --- Trouver une position initiale valide ---
        for _ in range(tentatives_max_par_voiture):
            # Choisir une position aléatoire
            x_pos, y_pos = random.randrange(taille_x), random.randrange(taille_y)
            pos = (x_pos, y_pos)
            # Vérifier toutes les conditions de validité
            if pos not in positions_feux and \
               grille[y_pos][x_pos] != 'X' and \
               pos not in positions_occupees_initiales and \
               est_case_escapable(pos, taille_x, taille_y, directions_lignes, directions_colonnes, grille): # Crucial: doit pouvoir sortir
                pos_initiale = pos # Position trouvée!
                break # Sortir de la boucle de recherche de position
        # Si aucune position initiale valide n'a été trouvée après N tentatives, abandonner (ou la voiture actuelle)
        if pos_initiale is None:
             # print(f"Avertissement: Impossible de trouver une position initiale valide pour la voiture {num_voiture} après {tentatives_max_par_voiture} essais.")
             # On pourrait 'break' ici si on veut arrêter toute génération, ou 'continue' pour juste sauter cette voiture
             break # Arrêter la génération si on ne trouve plus de place

        # --- Trouver une destination valide ---
        for _ in range(tentatives_max_par_voiture):
            # Choisir une destination aléatoire
            x_dest, y_dest = random.randrange(taille_x), random.randrange(taille_y)
            d = (x_dest, y_dest)
            # Vérifier les conditions de validité pour la destination
            if d != pos_initiale and \
               d not in positions_feux and \
               grille[y_dest][x_dest] != 'X' and \
               est_case_escapable(d, taille_x, taille_y, directions_lignes, directions_colonnes, grille): # Crucial: dest doit être escapable
                 dest = d # Destination trouvée!
                 break # Sortir de la boucle de recherche de destination
        # Si aucune destination valide n'a été trouvée, abandonner CETTE voiture et essayer la suivante
        if dest is None:
            # print(f"Avertissement: Impossible de trouver une destination valide pour la voiture {num_voiture} partant de {pos_initiale}.")
            continue # Passe à la tentative de génération de la voiture suivante

        # --- Position et Destination valides trouvées ---
        # Marquer la position initiale comme occupée pour les prochaines voitures de cette initialisation
        positions_occupees_initiales.add(pos_initiale)

        # --- Création de la couleur et de l'image spécifique (si l'image de base existe) ---
        # Couleur aléatoire, plutôt dans les tons bleutés/froids pour contraster
        voiture_couleur = (random.randint(0, 150), random.randint(0, 150), random.randint(100, 255))
        voiture_image_specifique = None # Par défaut: pas d'image spécifique
        if img_base_voiture: # Si une image de base a été chargée avec succès
            try:
                # Créer une copie de l'image de base
                voiture_image_specifique = img_base_voiture.copy()
                # Appliquer la couleur spécifique à cette copie en utilisant le mode MULTIPLY
                # (conserve les ombres/transparences de l'image originale)
                voiture_image_specifique.fill(voiture_couleur, special_flags=pygame.BLEND_RGB_MULT)
            except Exception as img_err:
                # En cas d'erreur pendant la coloration (peu probable mais possible)
                print(f"Erreur lors de la coloration de l'image pour voiture {num_voiture}: {img_err}")
                voiture_image_specifique = None # Revenir au mode sans image pour cette voiture

        # --- Création du dictionnaire représentant la voiture ---
        voiture = {
            "id": num_voiture,                    # Identifiant unique
            "position": list(pos_initiale),       # Position actuelle [x, y] (liste pour modification)
            "destination": list(dest),            # Destination visée [x, y] (liste)
            "chemin": [],                         # Chemin calculé (liste de [x, y]), initialement vide
            "temps_arrivee": None,                # Timestamp de l'arrivée (None si pas arrivée)
            "dernier_deplacement": time.time(),   # Timestamp du dernier mouvement (pour gérer la vitesse)
            "couleur": voiture_couleur,           # Couleur (pour cercle ou image)
            "image": voiture_image_specifique,    # Image spécifique colorée (ou None)
            "orientation": 0,                     # Orientation actuelle en degrés (0=droite, 90=haut, 180=gauche, 270=bas)
            "bloquee_depuis": None,               # Timestamp si bloquée (None sinon)
            "recalcul_echecs": 0                  # Compteur d'échecs de recalcul de chemin
        }

        voitures.append(voiture) # Ajouter la voiture créée à la liste
        num_voiture += 1         # Incrémenter l'ID pour la prochaine

    print(f"Généré {len(voitures)} voitures initiales sur {n_voitures} demandées.")
    return voitures


##
# @brief Trouve une nouvelle destination aléatoire valide pour une voiture bloquée.
# @param voiture_actuelle Le dictionnaire de la voiture nécessitant une nouvelle destination.
# @param taille_x Largeur de la grille.
# @param taille_y Hauteur de la grille.
# @param feux Liste des feux.
# @param grille La grille.
# @param directions_lignes Dictionnaire des directions des lignes.
# @param directions_colonnes Dictionnaire des directions des colonnes.
# @param voitures Liste de toutes les voitures (non utilisé ici, mais pourrait l'être pour éviter destinations communes).
# @return Une nouvelle destination `[x, y]` valide et "escapable", ou `None` si échec après 100 tentatives.
# @details Similaire à la recherche de destination initiale, mais garantit que la nouvelle
#          destination est différente de la position actuelle de la voiture.
def trouver_nouvelle_destination_valide(voiture_actuelle, taille_x, taille_y, feux, grille, directions_lignes, directions_colonnes, voitures):
    """Trouve une nouvelle destination aléatoire qui est valide et d'où l'on peut repartir."""
    positions_feux = {feu["position"] for feu in feux} # Positions des feux
    pos_actuelle = tuple(voiture_actuelle["position"]) # Position actuelle de la voiture

    # Tente de trouver une destination valide un certain nombre de fois
    for _ in range(100): # Limite de tentatives
        # Choisit une destination candidate aléatoire
        x_dest = random.randrange(taille_x)
        y_dest = random.randrange(taille_y)
        dest = (x_dest, y_dest)

        # Vérifie toutes les conditions de validité pour cette candidate
        if dest != pos_actuelle and \
           dest not in positions_feux and \
           grille[y_dest][x_dest] != 'X' and \
           est_case_escapable(dest, taille_x, taille_y, directions_lignes, directions_colonnes, grille): # Doit pouvoir repartir de la dest
            return list(dest) # Retourne la destination valide trouvée [x, y]

    # Si aucune destination valide n'est trouvée après les tentatives
    return None


##
# @brief Trouve le chemin le plus court entre deux points en utilisant l'algorithme A*.
# @param grille La grille de simulation (pour les obstacles 'X').
# @param depart Coordonnées de départ [x, y] ou (x, y).
# @param arrivee Coordonnées d'arrivée [x, y] ou (x, y).
# @param directions_lignes Dictionnaire des directions autorisées par ligne.
# @param directions_colonnes Dictionnaire des directions autorisées par colonne.
# @return Une liste de positions `[x, y]` formant le chemin (incluant départ), ou `None` si aucun chemin n'est trouvé.
# @details Implémentation standard de A* avec une file de priorité (heapq).
#          L'heuristique utilisée est la distance de Manhattan.
#          Les déplacements autorisés sont contraints par les `directions_lignes` et `directions_colonnes`.
def trouver_chemin(grille, depart, arrivee, directions_lignes, directions_colonnes):
    """Calcule le chemin A* en respectant les sens uniques et les obstacles."""

    ## @brief Fonction heuristique (distance de Manhattan) pour A*. */
    def heuristique(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # Conversion en tuples pour utilisation comme clés de dictionnaire/set
    depart, arrivee = tuple(depart), tuple(arrivee)
    tx, ty = len(grille[0]), len(grille) # Dimensions de la grille

    # Vérifications initiales rapides
    # Sortie des limites de la grille?
    if not (0 <= depart[0] < tx and 0 <= depart[1] < ty and 0 <= arrivee[0] < tx and 0 <= arrivee[1] < ty):
        return None
    # Départ ou arrivée sur un obstacle?
    if grille[depart[1]][depart[0]] == "X" or grille[arrivee[1]][arrivee[0]] == "X":
        return None
    # Départ = Arrivée?
    if depart == arrivee:
        return [list(depart)] # Chemin trivial

    # --- Initialisation A* ---
    # File de priorité (min-heap): stocke (priorité, position)
    # Priorité = coût g (depuis départ) + heuristique h (vers arrivée)
    ouverte = [(heuristique(depart, arrivee), depart)] # Commence avec le point de départ
    # Dictionnaire pour reconstruire le chemin: {position: position_precedente}
    precedent = {depart: None}
    # Dictionnaire des coûts réels depuis le départ: {position: cout_g}
    cout_g = {depart: 0}

    # --- Boucle Principale A* ---
    while ouverte: # Tant qu'il y a des nœuds à explorer
        # Récupérer le nœud avec la plus faible priorité (f = g + h)
        _, courant = heapq.heappop(ouverte)

        # Destination atteinte?
        if courant == arrivee:
            # Reconstruire le chemin en remontant via `precedent`
            chemin = []
            temp = courant
            while temp: # Remonte jusqu'au départ (qui a None comme précédent)
                chemin.append(list(temp)) # Ajoute la position (convertie en liste)
                temp = precedent.get(temp)
            return chemin[::-1] # Inverse le chemin pour avoir [depart, ..., arrivee]

        # Exploration des voisins valides
        x, y = courant
        voisins = [] # Liste des voisins accessibles depuis `courant`

        # Déterminer les mouvements autorisés par les directions
        dir_l = directions_lignes.get(y)    # Direction horizontale pour cette ligne
        dir_c = directions_colonnes.get(x)  # Direction verticale pour cette colonne

        # Mouvement horizontal possible?
        if dir_l == "droite" and x + 1 < tx:
            voisins.append((x + 1, y))
        elif dir_l == "gauche" and x - 1 >= 0:
            voisins.append((x - 1, y))

        # Mouvement vertical possible?
        if dir_c == "bas" and y + 1 < ty:
            voisins.append((x, y + 1))
        elif dir_c == "haut" and y - 1 >= 0:
            voisins.append((x, y - 1))

        # Traiter chaque voisin valide trouvé
        for voisin in voisins:
            vx, vy = voisin
            # Ignorer si le voisin est un obstacle
            if grille[vy][vx] == "X":
                continue

            # Calculer le nouveau coût pour atteindre ce voisin depuis le départ
            # (Ici, chaque pas a un coût de 1)
            n_cout_g = cout_g[courant] + 1

            # Si ce voisin n'a jamais été atteint OU si on a trouvé un meilleur chemin pour l'atteindre
            if voisin not in cout_g or n_cout_g < cout_g[voisin]:
                # Mettre à jour le coût et le chemin précédent
                cout_g[voisin] = n_cout_g
                precedent[voisin] = courant
                # Calculer la priorité (f = g + h) pour ce voisin
                priorite = n_cout_g + heuristique(voisin, arrivee)
                # Ajouter/mettre à jour le voisin dans la file de priorité
                heapq.heappush(ouverte, (priorite, voisin))

    # Si la boucle se termine sans atteindre l'arrivée -> pas de chemin trouvé
    return None


##
# @brief Gère la logique de déplacement, de recalcul de chemin, et d'évitement des collisions pour toutes les voitures.
# @param voitures La liste des voitures (sera modifiée).
# @param grille La grille de simulation.
# @param feux La liste des feux.
# @param directions_lignes Dictionnaire des directions des lignes.
# @param directions_colonnes Dictionnaire des directions des colonnes.
# @param taille_x Largeur de la grille.
# @param taille_y Hauteur de la grille.
# @param pietons Liste des piétons actifs (pour l'évitement).
# @details Cette fonction complexe orchestre le comportement des voitures:
#          1. Vérifie si une voiture est arrivée.
#          2. Calcule/Recalcule les chemins si nécessaire (chemin vide, blocage prolongé, échecs répétés).
#          3. Gère le cas où un recalcul échoue (attribution nouvelle destination).
#          4. Détermine l'intention de mouvement de chaque voiture (case suivante visée).
#          5. Résout les conflits potentiels (feux rouges, obstacles, autres voitures, piétons) dans un ordre aléatoire pour l'équité.
#          6. Effectue les déplacements autorisés et met à jour l'état des voitures (position, chemin restant, orientation, état bloqué).
def mettre_a_jour_voitures(voitures, grille, feux, directions_lignes, directions_colonnes, taille_x, taille_y, pietons):
    """Met à jour la position, le chemin et l'état de chaque voiture."""
    temps_actuel = time.time()
    # Dictionnaire pour stocker l'intention de chaque voiture: {id_voiture: (position_suivante_visée, est_prete_a_bouger)}
    intentions = {}

    # === Étape 1: Calcul des chemins et détermination des intentions ===
    for v in voitures:
        # Ignorer les voitures déjà arrivées (elles disparaîtront au dessin)
        if v["temps_arrivee"]:
            continue # Passe à la voiture suivante

        pos_tuple = tuple(v["position"]) # Position actuelle en tuple

        # Vérification d'arrivée à destination
        if pos_tuple == tuple(v["destination"]):
            v["temps_arrivee"] = temps_actuel # Marquer comme arrivée
            v["chemin"] = []                 # Vider le chemin
            v["bloquee_depuis"] = None     # Plus bloquée
            v["recalcul_echecs"] = 0         # Reset compteur
            continue # Passe à la voiture suivante

        # Déterminer si un recalcul de chemin est nécessaire
        recalcul_demande = (
            not v["chemin"] or # Pas de chemin défini
            # Ou bloquée depuis trop longtemps
            (v["bloquee_depuis"] and temps_actuel - v["bloquee_depuis"] > SEUIL_BLOCAGE)
        )

        # Si un recalcul est demandé
        if recalcul_demande:
            # Tentative de trouver un chemin vers la destination actuelle
            path = trouver_chemin(grille, v["position"], v["destination"], directions_lignes, directions_colonnes)

            if path and len(path) > 1: # Chemin trouvé (et contient plus que juste le départ)
                v["chemin"] = path[1:]       # Stocke le chemin (sans la position actuelle)
                v["bloquee_depuis"] = None # N'est plus bloquée
                v["recalcul_echecs"] = 0     # Reset compteur d'échecs
            else: # Échec du recalcul (pas de chemin ou chemin trivial)
                # Marquer comme bloquée si elle ne l'était pas déjà (pour le comptage d'échecs)
                if not v["bloquee_depuis"]:
                     v["bloquee_depuis"] = temps_actuel
                # Incrémenter le compteur d'échecs SEULEMENT si elle était DÉJÀ marquée comme bloquée
                # (pour éviter l'incrément au premier échec de calcul d'un chemin vide)
                elif recalcul_demande: # Était déjà bloquée OU n'avait pas de chemin
                     v["recalcul_echecs"] += 1
                # S'assurer que le chemin est vide en cas d'échec
                v["chemin"] = []

                # Si trop d'échecs consécutifs -> trouver une nouvelle destination
                if v["recalcul_echecs"] > MAX_RECALCUL_ECHECS:
                    print(f"Voiture {v['id']} bloquée trop longtemps ou recalculs échoués. Cherche nouvelle destination...")
                    nouvelle_dest = trouver_nouvelle_destination_valide(
                        v, taille_x, taille_y, feux, grille, directions_lignes, directions_colonnes, voitures
                    )
                    if nouvelle_dest:
                        print(f"  > Nouvelle destination pour {v['id']}: {nouvelle_dest}")
                        v["destination"] = nouvelle_dest
                        # Tenter de calculer le chemin vers la *nouvelle* destination
                        path_nouv = trouver_chemin(grille, v["position"], v["destination"], directions_lignes, directions_colonnes)
                        # Mettre à jour le chemin et l'état bloqué selon le résultat
                        v["chemin"] = path_nouv[1:] if path_nouv and len(path_nouv)>1 else []
                        v["bloquee_depuis"] = None if v["chemin"] else temps_actuel # Bloquée seulement si échec même vers nv dest
                        v["recalcul_echecs"] = 0 # Reset compteur après changement de destination
                    else:
                        # Échec même pour trouver une nouvelle destination -> reste bloquée, reset compteur pour éviter boucle d'essais infinis
                        print(f"  > Échec: Impossible de trouver une nouvelle destination valide pour {v['id']}.")
                        v["recalcul_echecs"] = 0 # Évite boucle de log si la grille est vraiment coincée

        # --- Déterminer l'intention de mouvement (même si chemin recalculé ou non) ---
        # Quelle est la prochaine case visée? (Si chemin existe, sinon c'est la case actuelle)
        next_pos_intended = tuple(v["chemin"][0]) if v["chemin"] else pos_tuple
        # Est-elle prête à bouger? (Chemin existe ET délai minimum écoulé depuis dernier mouvement)
        is_ready_to_move = bool(v["chemin"]) and (temps_actuel - v["dernier_deplacement"] >= DELAI_MIN_MOUVEMENT)
        # Stocker l'intention pour la résolution des conflits
        intentions[v["id"]] = (next_pos_intended, is_ready_to_move)

    # === Étape 2: Résolution des conflits et Mouvements effectifs ===
    # Ensemble des cases qui SERONT occupées à la fin de cette mise à jour
    final_pos_this_tick = set()
    # Mélanger l'ordre des voitures à traiter pour l'équité (évite qu'une voiture ait toujours la priorité)
    voitures_a_traiter = [v for v in voitures if not v["temps_arrivee"]] # Ne traiter que les actives
    random.shuffle(voitures_a_traiter)

    # Initialiser les positions finales avec les positions ACTUELLES de toutes les voitures actives
    # Cela sert de base : on suppose que personne ne bouge au début de la résolution.
    for v_init in voitures_a_traiter:
        final_pos_this_tick.add(tuple(v_init["position"]))

    # Traiter chaque voiture dans l'ordre mélangé
    for v in voitures_a_traiter:
        id_v = v["id"]
        current_pos = tuple(v["position"]) # Position de départ pour cette voiture ce tick

        # Récupérer l'intention calculée à l'étape 1
        next_pos_wanted, is_ready = intentions.get(id_v, (current_pos, False))

        # Condition de base : la voiture VEUT et PEUT (temporellement) bouger vers une case différente
        can_move = is_ready and next_pos_wanted != current_pos

        # --- Vérifications des obstacles SI la voiture veut bouger ---
        if can_move:
            vx, vy = next_pos_wanted # Coordonnées de la case cible

            # 1. Obstacle physique ('X')?
            if grille[vy][vx] == 'X':
                can_move = False # Ne peut pas aller sur un mur
                # Forcer un recalcul au prochain tick car le chemin est invalide
                v["chemin"] = []
                v["recalcul_echecs"] = 0 # Reset echecs car c'est une découverte d'obstacle
                # Marquer comme bloquée (si pas déjà) à cause de l'obstacle statique
                if not v["bloquee_depuis"]: v["bloquee_depuis"] = temps_actuel

            # 2. Feu de circulation? (Si non bloqué par X)
            if can_move:
                for feu in feux:
                    # Si la case cible est un feu ET qu'il n'est pas vert
                    if feu["position"] == next_pos_wanted and feu["etat"] != "vert":
                        can_move = False # Arrêt au feu
                        # Marquer comme bloquée par le feu (si pas déjà)
                        if not v["bloquee_depuis"]: v["bloquee_depuis"] = temps_actuel
                        break # Pas besoin de vérifier les autres feux

            # 3. Collision avec une AUTRE voiture? (Si non bloqué par X ou Feu)
            if can_move:
                # Vérifie si la case cible (next_pos_wanted) est déjà RÉSERVÉE par une autre voiture
                # pour la fin de ce tick DANS L'ENSEMBLE `final_pos_this_tick`.
                # La condition `next_pos_wanted != current_pos` ici est redondante car incluse dans le `if can_move` initial,
                # mais on vérifie que la case cible est DANS l'ensemble des positions finales
                # ET que ce n'est pas simplement notre propre position actuelle qui y serait encore.
                if next_pos_wanted in final_pos_this_tick:
                     # Ici, on pourrait implémenter une logique plus fine (ex: priorité?),
                     # mais la version simple est: si la place est prise (ou réservée par qqn qui a bougé avant nous), on ne bouge pas.
                    can_move = False
                    # Marquer comme bloquée par le trafic (si pas déjà)
                    if not v["bloquee_depuis"]: v["bloquee_depuis"] = temps_actuel

            # 4. Piéton sur la case cible? (Si non bloqué par X, Feu ou Voiture)
            if can_move:
                for pieton in pietons:
                    # Si un piéton actif occupe la case où la voiture veut aller
                    if pieton['passage_pos'] == next_pos_wanted:
                        can_move = False # Céder le passage au piéton
                        # print(f"Voiture {v['id']} bloquée par piéton {pieton['id']} à {next_pos_wanted}")
                        # Marquer comme bloquée par le piéton (si pas déjà)
                        if not v["bloquee_depuis"]: v["bloquee_depuis"] = temps_actuel
                        break # Un seul piéton suffit

        # --- Prise de décision finale et Mouvement ---
        if can_move: # Si TOUTES les vérifications sont passées
            final_decision = next_pos_wanted # La décision est de bouger vers la case voulue

            # --- Calculer la nouvelle orientation basée sur le déplacement ---
            dx = final_decision[0] - current_pos[0] # Mouvement horizontal (-1, 0, 1)
            dy = final_decision[1] - current_pos[1] # Mouvement vertical (-1, 0, 1)
            new_angle = v.get('orientation', 0) # Garde l'ancien angle si pas de mouvement (ne devrait pas arriver ici)
            # Convention: Image 'car.png' pointe vers le HAUT par défaut? (semble être le cas dans `generer_voitures_initiales`)
            # MAIS votre `dessiner_directions` semble utiliser 0=droite, 90=bas... -> Adoptons 0=Droite comme convention image
            # Ajustement: Si votre image 'car.png' pointe vers le HAUT, il faut ajouter/soustraire 90 aux angles ci-dessous.
            # SI 'car.png' POINTE VERS LA DROITE (ce que je vais supposer):
            if dy < 0:    new_angle = 90    # Monte
            elif dy > 0:  new_angle = 270   # Descend (ou -90)
            elif dx > 0:  new_angle = 0     # Va à droite
            elif dx < 0:  new_angle = 180   # Va à gauche
            v['orientation'] = new_angle # Mettre à jour l'orientation pour le dessin

            # --- Appliquer le mouvement et mettre à jour l'état ---
            v["position"] = list(final_decision) # Mettre à jour la position
            if v["chemin"]: v["chemin"].pop(0)  # Retirer la première étape du chemin (celle qui vient d'être faite)
            v["dernier_deplacement"] = temps_actuel # Mémoriser l'heure du mouvement
            v["bloquee_depuis"] = None           # N'est plus bloquée
            v["recalcul_echecs"] = 0             # Reset compteur

            # --- Mettre à jour l'ensemble des positions occupées pour ce tick ---
            # Libérer l'ancienne position DANS l'ensemble `final_pos_this_tick`
            if current_pos in final_pos_this_tick:
                final_pos_this_tick.remove(current_pos)
            # Réserver la nouvelle position DANS l'ensemble `final_pos_this_tick`
            final_pos_this_tick.add(final_decision)

        # Si la voiture ne peut pas bouger (can_move est False)
        # ET qu'elle n'est pas déjà à destination, marquer comme bloquée si elle ne l'était pas encore.
        elif current_pos != tuple(v["destination"]) and not v["bloquee_depuis"] and v['temps_arrivee'] is None:
            # S'assurer qu'elle est marquée comme bloquée pour le SEUIL_BLOCAGE futur
             v["bloquee_depuis"] = temps_actuel


# --- Initialisation Principale et Boucle de Simulation ---

## @brief Largeur de la grille en nombre de cellules. */
taille_x = LARGEUR // TAILLE_CELLULE
## @brief Hauteur de la grille en nombre de cellules. */
taille_y = HAUTEUR // TAILLE_CELLULE

# Création de la grille vide
grille = creer_grille(taille_x, taille_y)
# Initialisation des feux de circulation
feux = initialiser_feux_repartis(taille_y, taille_x)
# Initialisation des passages piétons
passages_pietons = initialiser_passages_pietons(NB_PASSAGES_PIETONS, taille_x, taille_y, feux, grille)
# Initialisation de la liste des piétons actifs (vide au début)
pietons_actifs = []
prochain_id_pieton = 0 # Réinitialise au cas où
# Création des dictionnaires de sens de circulation
lignes_directions, colonnes_directions = creer_directions_routes(taille_x, taille_y)
# Nombre de voitures à générer au départ
nombre_initial_voitures = 100
# Génération de la population initiale de voitures
voitures = generer_voitures_initiales(
    taille_x, taille_y, feux, grille, lignes_directions, colonnes_directions,
    car_image_base_scaled, # Passe l'image de base chargée (peut être None)
    n_voitures=nombre_initial_voitures
)

# --- Boucle Principale de la Simulation ---
running = True # Indicateur pour maintenir la boucle active
while running:
    # Contrôle de la vitesse (framerate) et obtient le temps écoulé (delta time)
    dt = clock.tick(30) / 1000.0 # Vise 30 FPS, dt en secondes (non utilisé directement ici, mais bonne pratique)

    # --- Gestion des Événements (Input Utilisateur) ---
    for event in pygame.event.get():
        # Fermeture de la fenêtre
        if event.type == pygame.QUIT:
            running = False
        # Touche Échap pressée
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        # Clic de souris
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Récupère les coordonnées de la cellule cliquée
            cx = event.pos[0] // TAILLE_CELLULE
            cy = event.pos[1] // TAILLE_CELLULE
            # S'assurer que le clic est dans les limites de la grille
            if 0 <= cx < taille_x and 0 <= cy < taille_y:
                 if event.button == 1: # Clic Gauche -> Ajouter Obstacle
                     # Tente d'ajouter un obstacle et force recalcul si réussi et nécessaire
                     if ajouter_obstacle(grille, cx, cy, feux):
                          forcer_recalcul_si_affecte(cx, cy, voitures)
                 elif event.button == 3: # Clic Droit -> Retirer Obstacle
                     # Ne retire que si c'est bien un obstacle 'X'
                     if grille[cy][cx] == 'X':
                         grille[cy][cx] = ' '
                         # Note: On pourrait aussi forcer recalcul ici si besoin

    # --- Mises à Jour Logiques de la Simulation ---
    # Met à jour l'état des feux
    mettre_a_jour_feux(feux)
    # Met à jour les piétons (déplacement, apparition)
    mettre_a_jour_pietons(passages_pietons, pietons_actifs, voitures)
    # Met à jour les voitures (chemin, déplacement, collisions, etc.) en tenant compte des piétons
    mettre_a_jour_voitures(voitures, grille, feux, lignes_directions, colonnes_directions, taille_x, taille_y, pietons_actifs)

    # --- Section Dessin (rendu graphique) ---
    # 1. Remplir le fond en blanc (efface l'image précédente)
    fenetre.fill(BLANC)
    # 2. Dessiner la grille
    dessiner_grille(fenetre, LARGEUR, HAUTEUR, TAILLE_CELLULE)
    # 3. Dessiner les obstacles
    dessiner_obstacles(fenetre, grille, TAILLE_CELLULE)
    # 4. Dessiner les passages piétons (zébrures)
    dessiner_passages_pietons(fenetre, passages_pietons, TAILLE_CELLULE)
    # 5. Dessiner les flèches de direction
    dessiner_directions(fenetre, lignes_directions, colonnes_directions, taille_x, taille_y, TAILLE_CELLULE)
    # 6. Dessiner les feux de circulation
    dessiner_feux(fenetre, feux, TAILLE_CELLULE)
    # 7. Dessiner les indicateurs de destination (places de parking)
    dessiner_destinations(fenetre, voitures, TAILLE_CELLULE)
    # 8. Dessiner les piétons actifs (bonshommes allumettes) - Avant les voitures pour qu'ils soient en dessous si superposition
    dessiner_pietons(fenetre, pietons_actifs, TAILLE_CELLULE)
    # 9. Dessiner les voitures (elles apparaissent au-dessus des passages, feux, etc.)
    dessiner_voitures(fenetre, voitures, TAILLE_CELLULE)

    # --- Afficher le résultat final dessiné sur l'écran ---
    pygame.display.flip()

# --- Fin de la Simulation (sortie de la boucle while) ---
print("Arrêt de la simulation.")
pygame.quit() # Nettoie les ressources Pygame
sys.exit()    # Termine proprement le script Python