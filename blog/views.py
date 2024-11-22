from django.shortcuts import render, get_object_or_404, redirect
from .forms import MoveForm
from .models import Character, Equipement
from django.contrib import messages
from django.http import HttpResponse

# Variables globales pour le comptage
compteur_cuisine = 0
compteurs_lit = {}  # Dictionnaire pour suivre les passages au lit par personnage
min_passages_lit = 0  # Variable pour le minimum des passages au lit

def update_equipment(request, character_id):
    character = get_object_or_404(Character, pk=character_id)
    return HttpResponse("Equipment updated successfully!")

def post_list(request):
    characters = Character.objects.all()
    equipements = Equipement.objects.all()
    
    # Calculer le minimum des passages par le lit
    global min_passages_lit
    if compteurs_lit:
        min_passages_lit = min(compteurs_lit.values())
    
    context = {
        "characters": characters,
        "equipements": equipements,
        "min_passages_lit": min_passages_lit,
        "passages_cuisine": compteur_cuisine
    }
    return render(request, 'blog/character_list.html', context)

def character_detail(request, id_character):
    character = get_object_or_404(Character, id_character=id_character)
    ancien_lieu = get_object_or_404(Equipement, id_equip=character.lieu.id_equip)
    lieu = character.lieu
    global compteur_cuisine, compteurs_lit, min_passages_lit

    # Initialiser le compteur pour ce personnage s'il n'existe pas
    if id_character not in compteurs_lit:
        compteurs_lit[id_character] = 0

    if request.method == "POST":
        form = MoveForm(request.POST, instance=character)

        if form.is_valid():
            nouveau_lieu = get_object_or_404(Equipement, id_equip=form.cleaned_data['lieu'].id_equip)

            # Liste des lieux partageables avec leur capacité maximale
            lieux_partageables = {
                "lit": float('inf'),  # Capacité illimitée
                "centrale": float('inf'),  # Capacité illimitée
                "gymnase": float('inf'),  # Capacité illimitée
                "cuisine": 2  # Limite de 2 personnes
            }
            
            # Vérification spéciale pour l'accès au lit
            if nouveau_lieu.id_equip == "lit":
                if compteurs_lit[id_character] > min_passages_lit:
                    messages.error(request, "Vous ne pouvez pas aller au lit tant que les autres colocataires n'ont pas rattrapé leur retard!")
                    return redirect('character_detail', id_character=id_character)
            
            # Vérifier si le lieu est partageable et sa capacité
            if nouveau_lieu.id_equip in lieux_partageables:
                # Compter le nombre de personnages dans le lieu
                occupants = Character.objects.filter(lieu=nouveau_lieu).count()
                can_enter = occupants < lieux_partageables[nouveau_lieu.id_equip]
                
                # Gestion spéciale de la disponibilité pour la cuisine
                if nouveau_lieu.id_equip == "cuisine":
                    # Si on va atteindre la capacité maximale
                    if occupants + 1 >= lieux_partageables["cuisine"]:
                        nouveau_lieu.disponibilite = "occupé"
                    else:
                        nouveau_lieu.disponibilite = "libre"
            else:
                can_enter = nouveau_lieu.disponibilite == "libre"

            # Définir les états correspondants à chaque lieu
            etats_par_lieu = {
                "lit": "endormi",
                "salle de bain": "a les crocs",
                "cuisine": "motivé" if ancien_lieu.id_equip == "salle de bain" else "fatigué",
                "centrale": "concentré",
                "gymnase": "a les crocs"
            }

            if can_enter:
                # Définition des transitions de lieu dans l'ordre donné
                transitions_valides = {
                    "lit": {
                        "prochain_lieu_possible": ["salle de bain"]
                    },
                    "salle de bain": {
                        "prochain_lieu_possible": ["cuisine"]
                    },
                    "cuisine": {
                        "depuis_salle_de_bain": {
                            "prochain_lieu_possible": ["centrale"]
                        },
                        "depuis_gymnase": {
                            "prochain_lieu_possible": ["lit"]
                        }
                    },
                    "centrale": {
                        "prochain_lieu_possible": ["gymnase"]
                    },
                    "gymnase": {
                        "prochain_lieu_possible": ["cuisine"]
                    }
                }

                if ancien_lieu.id_equip in transitions_valides:
                    # Gestion spéciale pour la cuisine selon le lieu précédent
                    if ancien_lieu.id_equip == "cuisine":
                        if character.etat == "motivé":  # Vient de la salle de bain
                            transition = transitions_valides["cuisine"]["depuis_salle_de_bain"]
                        elif character.etat == "fatigué":  # Vient du gymnase
                            transition = transitions_valides["cuisine"]["depuis_gymnase"]
                        else:
                            messages.error(request, "État non valide pour une transition depuis la cuisine.")
                            return redirect('character_detail', id_character=id_character)
                    else:
                        transition = transitions_valides[ancien_lieu.id_equip]

                    # Vérifier si le nouveau lieu est dans la liste des lieux possibles
                    if nouveau_lieu.id_equip in transition["prochain_lieu_possible"]:
                        # Mise à jour de la disponibilité des lieux non partageables
                        if ancien_lieu.id_equip not in lieux_partageables:
                            ancien_lieu.disponibilite = "libre"
                        elif ancien_lieu.id_equip == "cuisine":
                            # Vérifier combien de personnes restent dans la cuisine
                            remaining_occupants = Character.objects.filter(lieu=ancien_lieu).exclude(id_character=id_character).count()
                            if remaining_occupants < lieux_partageables["cuisine"]:
                                ancien_lieu.disponibilite = "libre"
                        
                        if nouveau_lieu.id_equip not in lieux_partageables:
                            nouveau_lieu.disponibilite = "occupé"

                        # Incrémenter le compteur si on entre en cuisine
                        if nouveau_lieu.id_equip == "cuisine" and ancien_lieu.id_equip != "cuisine":
                            compteur_cuisine += 1

                        # Incrémenter le compteur si on entre dans le lit
                        if nouveau_lieu.id_equip == "lit" and ancien_lieu.id_equip != "lit":
                            compteurs_lit[id_character] += 1
                            # Mettre à jour le minimum global
                            min_passages_lit = min(compteurs_lit.values())

                        # Mise à jour de l'état en fonction du nouveau lieu
                        character.etat = etats_par_lieu[nouveau_lieu.id_equip]
                        character.lieu = nouveau_lieu

                        ancien_lieu.save()
                        nouveau_lieu.save()
                        character.save()
                        return redirect('character_detail', id_character=id_character)
                    else:
                        lieux_possibles = ", ".join(transition["prochain_lieu_possible"])
                        messages.error(request, f"Pas possible ! Depuis {ancien_lieu.id_equip}, il faut aller à : {lieux_possibles}")
                        return redirect('character_detail', id_character=id_character)
                else:
                    messages.error(request, f"Lieu actuel ({ancien_lieu.id_equip}) non valide pour une transition.")
                    return redirect('character_detail', id_character=id_character)
            else:
                messages.error(request, f"La {nouveau_lieu.id_equip} est déjà pleine !")
                return redirect('character_detail', id_character=id_character)
    else:
        form = MoveForm(instance=character)
        context = {
            'character': character, 
            'lieu': lieu, 
            'form': form,
            'passages_cuisine': compteur_cuisine,
            'passages_lit': compteurs_lit[id_character],
            'min_passages_lit': min_passages_lit
        }
        return render(request, 'blog/character_detail.html', context)
    
 
""" réinitiliser les compteurs"""
def reset_counters(request):
    global compteur_cuisine, compteurs_lit, min_passages_lit
    compteur_cuisine = 0
    compteurs_lit.clear()
    min_passages_lit = 0
    messages.success(request, "Tous les compteurs ont été réinitialisés.")
    return redirect('post_list') 

