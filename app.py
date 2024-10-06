import streamlit as st
import os
from openai import OpenAI
import json
import logging
from typing import Tuple, Dict, Any
import importlib.util

st.set_page_config(page_title="View Avocats - Obtenez une estimation grâce à l'IA", page_icon="⚖️", layout="wide")

# Fonction pour appliquer le CSS personnalisé
def apply_custom_css():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp > header {
                background-color: transparent;
            }
            .stApp {
                margin-top: -80px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .loading-icon {
                animation: spin 1s linear infinite;
                display: inline-block;
                margin-right: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration du client OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY n'est pas défini dans les variables d'environnement")

client = OpenAI(api_key=OPENAI_API_KEY)

# Chargement des modules
def load_py_module(file_path: str, module_name: str):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Erreur lors du chargement du module {module_name}: {e}")
        return None

prestations_module = load_py_module('./prestations-heures.py', 'prestations_heures')
tarifs_module = load_py_module('./tarifs-prestations.py', 'tarifs_prestations')
instructions_module = load_py_module('./chatbot-instructions.py', 'consignes_chatbot')

# Initialisation des variables globales
prestations = prestations_module.get_prestations() if prestations_module else {}
tarifs = tarifs_module.get_tarifs() if tarifs_module else {}
instructions = instructions_module.get_chatbot_instructions() if instructions_module else ""

def get_openai_response(prompt: str, model: str = "gpt-3.5-turbo", num_iterations: int = 3) -> list:
    try:
        responses = []
        for _ in range(num_iterations):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            content = response.choices[0].message.content.strip()
            responses.append(content)
        return responses
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API OpenAI: {e}")
        raise

def analyze_question(question: str, client_type: str, urgency: str) -> Tuple[str, str, float, bool]:
    options = [f"{domaine}: {', '.join(prestations_domaine.keys())}" for domaine, prestations_domaine in prestations.items()]
    prompt = f"""Analysez la question suivante et déterminez si elle concerne un problème juridique. Si c'est le cas, identifiez le domaine juridique et la prestation la plus pertinente.

Question : {question}
Type de client : {client_type}
Degré d'urgence : {urgency}

Options de domaines et prestations :
{' '.join(options)}

Répondez au format JSON strict suivant :
{{
    "est_juridique": true/false,
    "domaine": "nom du domaine juridique",
    "prestation": "nom de la prestation",
    "indice_confiance": 0.0 à 1.0
}}
"""

    responses = get_openai_response(prompt)
    
    results = []
    for response in responses:
        try:
            result = json.loads(response)
            results.append(result)
        except json.JSONDecodeError:
            logger.error("Erreur de décodage JSON dans la réponse de l'API")
    
    if not results:
        return "", "", 0.0, False

    # Analyse simplifiée des résultats
    is_legal = sum(r['est_juridique'] for r in results) > len(results) / 2
    domain = max(set(r['domaine'] for r in results), key=lambda x: [r['domaine'] for r in results].count(x))
    service = max(set(r['prestation'] for r in results), key=lambda x: [r['prestation'] for r in results].count(x))
    confidence = sum(r['indice_confiance'] for r in results) / len(results)
    
    is_relevant = is_legal and domain in prestations and service in prestations[domain]
    
    return domain, service, confidence, is_relevant

def calculate_estimate(domaine: str, prestation: str, urgency: str) -> Tuple[int, int]:
    try:
        heures = prestations.get(domaine, {}).get(prestation, 10)
        tarif_horaire = tarifs.get("tarif_horaire_standard", 0)
        estimation = heures * tarif_horaire

        if urgency == "Urgent":
            facteur_urgence = tarifs.get("facteur_urgence", 1.5)
            estimation *= facteur_urgence

        forfait = tarifs.get("forfaits", {}).get(prestation)
        if forfait and forfait < estimation:
            estimation = forfait

        estimation_basse, estimation_haute = round(estimation * 0.8), round(estimation * 1.2)

        return estimation_basse, estimation_haute
    except Exception as e:
        logger.exception(f"Erreur dans calculate_estimate: {str(e)}")
        raise

def display_loading_animation():
    return st.markdown("""
    <div style="display: flex; align-items: center; justify-content: center; flex-direction: column;">
        <svg class="loading-icon" width="50" height="50" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,1,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/>
            <path d="M12,4a8,8,0,0,1,7.89,6.7A1.53,1.53,0,0,0,21.38,12h0a1.5,1.5,0,0,0,1.48-1.75,11,11,0,0,0-21.72,0A1.5,1.5,0,0,0,2.62,12h0a1.53,1.53,0,0,0,1.49-1.3A8,8,0,0,1,12,4Z"/>
        </svg>
        <p style="margin-top: 10px; font-weight: bold;">Notre IA surpuissante analyse votre cas juridique...</p>
        <p>Préparez-vous à découvrir une analyse juridique révolutionnaire !</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    apply_custom_css()
    
    st.title("🏛️ View Avocats - Estimateur de devis")

    client_type = st.selectbox("Vous êtes :", ("Particulier", "Entreprise"))
    urgency = st.selectbox("Degré d'urgence :", ("Normal", "Urgent"))
    question = st.text_area("Expliquez brièvement votre cas, notre intelligence artificielle s'occupe du reste !", height=150)

    if st.button("Obtenir une estimation grâce à l'intelligence artificielle"):
        if question:
            try:
                loading_placeholder = st.empty()
                with loading_placeholder:
                    loading_animation = display_loading_animation()
                
                # Effectuer l'analyse et le calcul
                domaine, prestation, confidence, is_relevant = analyze_question(question, client_type, urgency)
                estimation_basse, estimation_haute = calculate_estimate(domaine, prestation, urgency)

                # Une fois que tout est prêt, supprimer l'animation de chargement
                loading_placeholder.empty()

                # Afficher les résultats
                st.success("Analyse terminée. Voici les résultats :")
                
                st.subheader("Indice de confiance de l'analyse")
                st.progress(confidence)
                st.write(f"Confiance : {confidence:.2%}")

                if confidence < 0.5:
                    st.warning("⚠️ Attention : Notre IA a eu des difficultés à analyser votre question avec certitude. L'estimation suivante peut manquer de précision.")
                elif not is_relevant:
                    st.info("Nous ne sommes pas sûr qu'il s'agisse d'une question d'ordre juridique. Nous allons tout de même tenter de vous fournir une estimation indicative.")

                st.subheader("Résumé de l'estimation")
                st.write(f"**Domaine juridique :** {domaine if domaine else 'Non déterminé'}")
                st.write(f"**Prestation :** {prestation if prestation else 'Non déterminée'}")
                st.write(f"**Estimation :** Entre {estimation_basse} €HT et {estimation_haute} €HT")

                st.markdown("---")
                st.markdown("### 💡 Alternative Recommandée")
                st.info("**Consultation initiale d'une heure** - Tarif fixe : 100 € HT")

            except Exception as e:
                st.error(f"Une erreur s'est produite : {str(e)}")
                logger.exception("Erreur dans le processus d'estimation")
        else:
            st.warning("Veuillez décrire votre cas avant de demander une estimation.")

    st.markdown("---")
    st.write("© 2024 View Avocats. Tous droits réservés.")

if __name__ == "__main__":
    main()
