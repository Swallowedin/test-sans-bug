def get_tarifs():
    return {
        "tarif_horaire_standard": 250,  # Taux horaire moyen
        "tarif_externalisation": 150,  # Taux horaire moyen
        "facteur_urgence": 1.5,  # Facteur multiplicateur pour les cas urgents
        "forfaits": {
            "consultation_initiale": 100,
            "création_entreprise": 3000,
            "rédaction_contrat_simple": 800,
            "rédaction_contrat_complexe": 2000,
            "procédure_divorce_amiable": 3750,
            "rédaction_statuts_société": 1200,
            "dépôt_marque": 1000,
            "rédaction_bail_commercial": 2500,  # Ajout de la virgule ici
            "rédaction_bail_locatif": 1000,
            "assignation_justice": 1000,
            "constitution_partie_civile": 5000,
            # Forfaits spécifiques au droit de la construction
            "litige_droit_construction": 500,
            "rédaction_contrat_construction": 2500,
            "litige_malfacons_simple": 5000,
            "litige_malfacons_complexe": 10000,
            "assistance_expertise_judiciaire": 2000,
            "procédure_référé_construction": 3750
        },
        "frais_additionnels": {
            "frais_de_dossier": 150,
            "frais_de_déplacement_par_km": 0.6,
            "forfait_expertise_judiciaire": 1000,
            "forfait_déplacement_chantier": 300
        }
    }