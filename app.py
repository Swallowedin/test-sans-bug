# Remplacer la section d'affichage des résultats par ceci :

st.success("Analyse terminée. Voici votre estimation :")

col1, col2 = st.columns(2)

with col1:
    st.metric(label="Estimation basse", value=f"{estimation_basse} €HT")

with col2:
    st.metric(label="Estimation haute", value=f"{estimation_haute} €HT")

st.markdown("---")

st.subheader("Détails de l'analyse")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown(f"**Domaine juridique**")
    st.info(domaine if domaine else 'Non déterminé')

with col4:
    st.markdown(f"**Prestation**")
    st.info(prestation if prestation else 'Non déterminée')

with col5:
    st.markdown("**Indice de confiance**")
    st.progress(confidence)
    st.write(f"{confidence:.2%}")

if confidence < 0.5:
    st.warning("⚠️ Attention : Notre IA a eu des difficultés à analyser votre question avec certitude. L'estimation ci-dessus peut manquer de précision.")
elif not is_relevant:
    st.info("Nous ne sommes pas sûrs qu'il s'agisse d'une question d'ordre juridique. L'estimation ci-dessus est purement indicative.")

st.markdown("---")
st.markdown("### 💡 Alternative Recommandée")
st.info("**Consultation initiale d'une heure** - Tarif fixe : 100 € HT")
