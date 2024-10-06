import streamlit as st
import os
from openai import OpenAI
import json
import importlib.util

st.set_page_config(page_title="View Avocats - Devis en ligne", page_icon="⚖️", layout="wide")

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
            .stSpinner {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY n'est pas défini dans les variables d'environnement")

client = OpenAI(api_key=OPENAI_API_KEY)

def load_py_module(file_path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

prestations_module = load_py_module('./prestations-heures.py', 'prestations_heures')
tarifs_module = load_py_module('./tarifs-prestations.py', 'tarifs_prestations')
instructions_module = load_py_module('./chatbot-instructions.py', 'consignes_chatbot')

prestations = prestations_module.get_prestations() if prestations_module else {}
tarifs = tarifs_module.get_tarifs() if tarifs_module else {}
instructions = instructions_module.get_chatbot_instructions() if instructions_module else ""

def get_openai_response(prompt: str, model: str = "gpt-3.5-turbo", num_iterations: int = 5):
    responses = []
    for _ in range(num_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        responses.append(content)
    
    most_common = max(set(responses), key=responses.count)
    confidence = responses.count(most_common) / num_iterations
    
    return most_common, confidence

def check_response_relevance(response: str, options: list):
    response_lower = response.lower()
    return any(option.lower().split(':')[0].strip() in response_lower for option in options)

def analyze_question(question: str, client_type: str, urgency: str):
    options = [f"{domaine}: {', '.join(prestations_domaine.keys())}" for domaine, prestations_domaine in prestations.items()]
    prompt = f"""Analysez la question suivante et déterminez si elle concerne un problème juridique. Si c'est le cas, identifiez le domaine juridique et la prestation la plus pertinente.

Question : {question}
Type de client : {client_type}
Degré d'urgence : {urgency}

Options de domaines et prestations :
{' '.join(options)}

Répondez au format suivant :
1. Est-ce un problème juridique ? (Oui/Non)
2. Si oui, indiquez le domaine et la prestation, séparés par une virgule.
3. Si non, expliquez brièvement pourquoi ce n'est pas un problème juridique.
"""

    response, confidence = get_openai_response(prompt)
    lines = response.split('\n')
    
    is_legal = lines[0].lower().strip() == "oui"
    
    if is_legal:
        domain, service = lines[1].split(',', 1) if len(lines) > 1 and ',' in lines[1] else ("", "")
        is_relevant = check_response_relevance(lines[1], options)
    else:
        domain, service = "", ""
        is_relevant = False
        confidence = min(confidence, 0.4)
    
    return domain.strip(), service.strip(), confidence, is_relevant, is_legal

def calculate_estimate(domaine: str, prestation: str, urgency: str):
    heures = prestations.get(domaine, {}).get(prestation, 10)
    tarif_horaire = tarifs.get("tarif_horaire_standard", 0)
    estimation = heures * tarif_horaire

    calcul_details = [
        f"Heures estimées: {heures}",
        f"Tarif horaire standard: {tarif_horaire} €",
        f"Estimation initiale: {heures} x {tarif_horaire} = {estimation} €"
    ]

    if urgency == "Urgent":
        facteur_urgence = tarifs.get("facteur_urgence", 1.5)
        estimation *= facteur_urgence
        calcul_details.extend([
            f"Facteur d'urgence appliqué: x{facteur_urgence}",
            f"Estimation après urgence: {estimation} €"
        ])

    forfait = tarifs.get("forfaits", {}).get(prestation)
    if forfait:
        calcul_details.append(f"Forfait disponible: {forfait} €")
        if forfait < estimation:
            estimation = forfait
            calcul_details.append(f"Forfait appliqué: {forfait} €")

    estimation_basse, estimation_haute = round(estimation * 0.8), round(estimation * 1.2)
    calcul_details.append(f"Fourchette d'estimation: {estimation_basse} € - {estimation_haute} €")

    tarifs_utilises = {
        "tarif_horaire_standard": tarif_horaire,
        "facteur_urgence": tarifs.get("facteur_urgence") if urgency == "Urgent" else "Non appliqué",
        "forfait_prestation": forfait if forfait else "Pas de forfait"
    }

    return estimation_basse, estimation_haute, calcul_details, tarifs_utilises

def get_detailed_analysis(question: str, client_type: str, urgency: str, domaine: str, prestation: str):
    prompt = f"""En tant qu'assistant juridique virtuel pour View Avocats, analysez la question suivante et expliquez votre raisonnement pour le choix du domaine juridique et de la prestation.

Question : {question}
Type de client : {client_type}
Degré d'urgence : {urgency}
Domaine recommandé : {domaine}
Prestation recommandée : {prestation}

Structurez votre réponse en trois parties clairement séparées par des lignes vides :

1. Analyse détaillée :
Fournissez une analyse concise mais détaillée du cas, en tenant compte du type de client et du degré d'urgence.

2. Éléments spécifiques utilisés (format JSON strict) :
{{"domaine": {{"nom": "nom_du_domaine", "description": "description_du_domaine"}}, "prestation": {{"nom": "nom_de_la_prestation", "description": "description_de_la_prestation"}}}}

3. Sources d'information :
Listez les sources d'information utilisées pour cette analyse, si applicable.

Assurez-vous que chaque partie est clairement séparée et que le JSON dans la partie 2 est valide et strict."""

    response, _ = get_openai_response(prompt)

    parts = response.split('\n\n')
    
    analysis = parts[0] if len(parts) > 0 else "Analyse non disponible."
    
    elements_used = {}
    if len(parts) > 1:
        json_part = next((part for part in parts if '{' in part and '}' in part), None)
        if json_part:
            json_str = json_part[json_part.index('{'):json_part.rindex('}')+1]
            elements_used = json.loads(json_str)
        else:
            elements_used = {
                "domaine": {"nom": domaine, "description": "Information non fournie par l'API"},
                "prestation": {"nom": prestation, "description": "Information non fournie par l'API"}
            }
    else:
        elements_used = {
            "domaine": {"nom": domaine, "description": "Information non disponible"},
            "prestation": {"nom": prestation, "description": "Information non disponible"}
        }
    
    sources = parts[2] if len(parts) > 2 else "Aucune source spécifique mentionnée."

    return analysis, elements_used, sources

def main():
    apply_custom_css()
    
    st.title("🏛️ View Avocats - Estimateur de devis")

    client_type = st.selectbox("Vous êtes :", ("Particulier", "Professionnel", "Société"))
    urgency = st.selectbox("Degré d'urgence :", ("Normal", "Urgent"))
    question = st.text_area("Expliquez brièvement votre cas :", height=150)

    if st.button("Obtenir une estimation"):
        if question:
            analysis_placeholder = st.empty()
            with analysis_placeholder:
                st.markdown("""
                <div style="display: flex; align-items: center; justify-content: center; flex-direction: column;">
                    <div style="width: 50px; height: 50px;" class="stSpinner">
                        <svg width="50" height="50" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/>
                            <path d="M12,4a8,8,0,0,1,7.89,6.7A1.53,1.53,0,0,0,21.38,12h0a1.5,1.5,0,0,0,1.48-1.75,11,11,0,0,0-21.72,0A1.5,1.5,0,0,0,2.62,12h0a1.53,1.53,0,0,0,1.49-1.3A8,8,0,0,1,12,4Z">
                                <animateTransform attributeName="transform" type="rotate" dur="0.75s" values="0 12 12;360 12 12" repeatCount="indefinite"/>
                            </path>
                        </svg>
                    </div>
                    <p style="margin-top: 10px; font-weight: bold;">Notre IA surpuissante analyse votre cas juridique...</p>
                    <p>Préparez-vous à découvrir une analyse juridique révolutionnaire !</p>
                </div>
                """, unsafe_allow_html=True)
            
            domaine, prestation, confidence, is_relevant, is_legal = analyze_question(question, client_type, urgency)
            analysis_placeholder.empty()

            if not is_legal:
                st.warning("⚠️ Attention : Votre question ne semble pas concerner un problème juridique ou a peut-être été mal formulée. Notre IA est dubitative sur la nature juridique de votre demande.")
                st.info("Malgré cela, nous allons tenter de vous fournir une réponse, mais veuillez noter que notre analyse pourrait ne pas être entièrement adaptée à votre situation.")

            if is_relevant or not is_legal:
                estimation_basse, estimation_haute, calcul_details, tarifs_utilises = calculate_estimate(domaine, prestation, urgency)
                detailed_analysis, elements_used, sources = get_detailed_analysis(question, client_type, urgency, domaine, prestation)

                st.success("Analyse terminée. Voici les résultats :")
                
                st.subheader("Indice de confiance de l'analyse")
                st.progress(confidence)
                st.write(f"Confiance : {confidence:.2%}")

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Résumé de l'estimation")
                    st.write(f"**Domaine juridique :** {domaine if domaine else 'Non déterminé'}")
                    st.write(f"**Prestation :** {prestation if prestation else 'Non déterminée'}")
                    st.write(f"**Estimation :** Entre {estimation_basse} €HT et {estimation_haute} €HT")
                    
                    st.subheader("Détails du calcul")
                    for detail in calcul_details:
                        st.write(detail)

                with col2:
                    st.subheader("Éléments tarifaires utilisés")
                    st.json(tarifs_utilises)

                    st.subheader("Éléments spécifiques pris en compte")
                    if isinstance(elements_used, dict) and "domaine" in elements_used and "prestation" in elements_used:
                        st.json(elements_used)
                    else:
                        st.warning("Les éléments spécifiques n'ont pas pu être analysés de manière optimale.")
                        st.json(elements_used)

                st.subheader("Analyse détaillée")
                st.write(detailed_analysis)

                if sources and sources != "Aucune source spécifique mentionnée.":
                    st.subheader("Sources d'information")
                    st.write(sources)

                st.markdown("---")
                st.markdown("### 💡 Alternative Recommandée")
                st.info("**Consultation initiale d'une heure** - Tarif fixe : 100 € HT")

            else:
                st.warning("Malheureusement, je n'ai pas été en mesure d'identifier votre problème juridique de manière précise. Vous pouvez toutefois contacter directement le cabinet View Avocats par mail ou par téléphone au numéro suivant : [insérez le numéro ici]")
                st.info("Pour une assistance plus personnalisée, n'hésitez pas à nous contacter directement.")
        else:
            st.warning("Veuillez décrire votre cas avant de demander une estimation.")

    st.markdown("---")
    st.write("© 2024 View Avocats. Tous droits réservés.")

if __name__ == "__main__":
    main()
