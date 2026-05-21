
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import sys, os

# ── Configuration page ──
st.set_page_config(
    page_title = "MOOC Dropout Plugin — Dashboard Tuteur",
    page_icon  = "🎓",
    layout     = "wide",
    initial_sidebar_state = "expanded"
)

# ── Style CSS ──
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .risk-critique { color: #E74C3C; font-weight: bold; }
    .risk-modere   { color: #F39C12; font-weight: bold; }
    .risk-faible   { color: #27AE60; font-weight: bold; }
    .stButton button {
        border-radius: 8px;
        font-weight: bold;
    }
    .prescription-box {
        background: #EBF5FB;
        border-left: 4px solid #2E75B6;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Chargement données ──
@st.cache_data
def load_prescriptions():
    """Charge les prescriptions générées par le notebook 04."""
    try:
        path = "/content/drive/MyDrive/MOOC_Recommandation_Adaptative/results/prescriptif/prescriptions_all.csv"
        df = pd.read_csv(path)
        # Parser les colonnes JSON
        df['ressources'] = df['ressources'].apply(
            lambda x: json.loads(x.replace("'", """)) if isinstance(x, str) else x
        )
        df['facteurs_shap'] = df['facteurs_shap'].apply(
            lambda x: json.loads(x.replace("'", """)) if isinstance(x, str) else {}
        )
        df['donnees_etudiant'] = df['donnees_etudiant'].apply(
            lambda x: json.loads(x.replace("'", """)) if isinstance(x, str) else {}
        )
        return df
    except Exception as e:
        st.error(f"Erreur chargement données : {e}")
        return pd.DataFrame()

df = load_prescriptions()

# ── SIDEBAR ──
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/1B3A6B/FFFFFF?text=MOOC+Plugin",
             use_column_width=True)
    st.markdown("---")

    st.markdown("### 🎓 Navigation")
    page = st.radio(
        "",
        ["📊 Vue Globale",
         "👤 Profil Étudiant",
         "🔴 Alertes Critiques",
         "📈 Statistiques",
         "🔌 Test API"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 🔧 Filtres")

    modules_dispo = ["Tous"] + sorted(df['code_module'].unique().tolist()) if not df.empty else ["Tous"]
    module_selec  = st.selectbox("Module", modules_dispo)

    niveaux_dispo = ["Tous", "critique", "modere", "faible"]
    niveau_selec  = st.selectbox("Niveau de risque", niveaux_dispo)

    st.markdown("---")
    st.markdown("""
    <small>
    🔬 <b>Projet IRD</b><br>
    UGB Saint-Louis<br>
    Dataset OULAD — 32 593 étudiants
    </small>
    """, unsafe_allow_html=True)

# ── Filtrage des données ──
df_filtered = df.copy()
if module_selec != "Tous" and not df.empty:
    df_filtered = df_filtered[df_filtered['code_module'] == module_selec]
if niveau_selec != "Tous" and not df.empty:
    df_filtered = df_filtered[df_filtered['niveau_risque'] == niveau_selec]

# ════════════════════════════════════════════════════════════
# PAGE 1 — VUE GLOBALE
# ════════════════════════════════════════════════════════════
if page == "📊 Vue Globale":

    st.title("📊 Tableau de Bord — Prédiction d'Abandon MOOC")
    st.markdown(f"**{len(df_filtered):,} étudiants** analysés · Cutoff Jour 42 · XGBoost AUC=0.863")
    st.markdown("---")

    # ── Métriques globales ──
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        n_critique = (df_filtered['niveau_risque'] == 'critique').sum()
        n_modere   = (df_filtered['niveau_risque'] == 'modere').sum()
        n_faible   = (df_filtered['niveau_risque'] == 'faible').sum()
        pct_risque = 100 * (n_critique + n_modere) / len(df_filtered) if len(df_filtered) > 0 else 0

        with col1:
            st.metric("🔴 Critiques",   f"{n_critique:,}",
                      f"{100*n_critique/len(df_filtered):.1f}%" if len(df_filtered) > 0 else "")
        with col2:
            st.metric("🟠 Modérés",     f"{n_modere:,}",
                      f"{100*n_modere/len(df_filtered):.1f}%" if len(df_filtered) > 0 else "")
        with col3:
            st.metric("🟢 Faibles",     f"{n_faible:,}",
                      f"{100*n_faible/len(df_filtered):.1f}%" if len(df_filtered) > 0 else "")
        with col4:
            st.metric("⚠️ Taux à risque", f"{pct_risque:.1f}%",
                      "nécessitent une intervention")

    st.markdown("---")

    # ── Graphiques ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Distribution des causes d'abandon")
        cause_map = {
            'inactivite'           : "Inactivité",
            'difficulte_academique': "Difficulté académique",
            'surcharge'            : "Surcharge",
            'desengagement_module' : "Désengagement"
        }
        cause_counts = df_filtered['cause_principale'].map(cause_map).value_counts()
        fig_pie = px.pie(
            values = cause_counts.values,
            names  = cause_counts.index,
            color_discrete_sequence = ['#E74C3C','#3498DB','#F39C12','#9B59B6'],
            hole   = 0.4
        )
        fig_pie.update_layout(
            showlegend=True, height=300,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("Distribution du score de risque")
        fig_hist = px.histogram(
            df_filtered, x='dropout_score',
            nbins=40,
            color='niveau_risque',
            color_discrete_map={
                'critique': '#E74C3C',
                'modere'  : '#F39C12',
                'faible'  : '#27AE60'
            },
            labels={'dropout_score': 'Score de risque', 'count': 'Étudiants'}
        )
        fig_hist.update_layout(
            height=300, showlegend=True,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # ── Tableau des étudiants ──
    st.subheader("📋 Liste des étudiants par niveau de risque")

    df_display = df_filtered[[
        'id_student','code_module','code_presentation',
        'dropout_score','niveau_risque','cause_label','action'
    ]].copy()

    df_display['dropout_score'] = df_display['dropout_score'].round(3)
    df_display = df_display.sort_values('dropout_score', ascending=False)

    df_display.columns = [
        'ID Étudiant','Module','Présentation',
        'Score Risque','Niveau','Cause','Action Recommandée'
    ]

    def color_niveau(val):
        colors = {'critique': 'background-color: #FADBD8',
                  'modere'  : 'background-color: #FDEBD0',
                  'faible'  : 'background-color: #D5F5E3'}
        return colors.get(val, '')

    st.dataframe(
        df_display.style.applymap(color_niveau, subset=['Niveau']),
        use_container_width=True,
        height=400
    )

    # Export
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Exporter CSV",
        csv,
        "prescriptions_export.csv",
        "text/csv"
    )

# ════════════════════════════════════════════════════════════
# PAGE 2 — PROFIL ÉTUDIANT
# ════════════════════════════════════════════════════════════
elif page == "👤 Profil Étudiant":

    st.title("👤 Profil Détaillé d'un Étudiant")
    st.markdown("---")

    if df.empty:
        st.warning("Aucune donnée disponible.")
    else:
        student_ids = df_filtered['id_student'].tolist()
        selected_id = st.selectbox(
            "Sélectionner un étudiant",
            student_ids,
            format_func=lambda x: f"Étudiant {x}"
        )

        student = df_filtered[df_filtered['id_student'] == selected_id].iloc[0]

        # ── En-tête ──
        col1, col2 = st.columns([1, 3])
        with col1:
            emoji = student['emoji_risque']
            niveau = student['niveau_risque'].upper()
            score  = student['dropout_score']
            st.markdown(f"""
            <div style="text-align:center; padding:20px; background:white;
                        border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.1)">
                <div style="font-size:48px">{emoji}</div>
                <div style="font-size:14px; color:#666">Risque {niveau}</div>
                <div style="font-size:36px; font-weight:bold; color:#1B3A6B">{score:.3f}</div>
                <div style="font-size:12px; color:#999">Score d'abandon</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"### Étudiant {selected_id}")
            st.markdown(f"**Module :** {student['code_module']} — {student['code_presentation']}")
            st.markdown(f"**Cause principale :** {student['cause_label']}")
            st.markdown("---")
            st.markdown(f"**Action recommandée :**")
            st.markdown(f"""
            <div class="prescription-box">
                <b>{student['action']}</b><br><br>
                {student['intervention']}
            </div>
            """, unsafe_allow_html=True)

            ressources = student['ressources']
            if isinstance(ressources, str):
                try:
                    ressources = json.loads(ressources.replace("'", """))
                except:
                    ressources = [ressources]

            st.markdown("**Ressources recommandées :**")
            for r in ressources:
                st.markdown(f"- 📚 {r}")

        st.markdown("---")

        # ── Données comportementales ──
        st.subheader("📊 Données comportementales")

        donnees = student['donnees_etudiant']
        if isinstance(donnees, str):
            try:
                donnees = json.loads(donnees.replace("'", """))
            except:
                donnees = {}

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Clics totaux",    f"{int(donnees.get('total_clicks', 0))}")
        col_b.metric("Jours actifs",    f"{int(donnees.get('total_days_active', 0))}")
        col_c.metric("Dernier jour actif", f"J{int(donnees.get('last_activity_day', 0))}")
        col_d.metric("Score moyen",     f"{donnees.get('avg_score', 0):.1f}%")

        # ── SHAP ──
        st.subheader("🔍 Facteurs explicatifs (SHAP)")
        facteurs = student['facteurs_shap']
        if isinstance(facteurs, str):
            try:
                facteurs = json.loads(facteurs.replace("'", """))
            except:
                facteurs = {}

        if facteurs:
            shap_df = pd.DataFrame(
                list(facteurs.items()),
                columns=['Feature', 'Impact SHAP']
            ).sort_values('Impact SHAP', ascending=True)

            fig_shap = px.bar(
                shap_df, x='Impact SHAP', y='Feature',
                orientation='h',
                color='Impact SHAP',
                color_continuous_scale=['#27AE60','#F39C12','#E74C3C'],
                title="Impact des facteurs sur le risque d'abandon"
            )
            fig_shap.update_layout(height=250, showlegend=False,
                                   margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_shap, use_container_width=True)

            st.info("💡 Les facteurs avec un impact positif **augmentent** le risque d'abandon.")

# ════════════════════════════════════════════════════════════
# PAGE 3 — ALERTES CRITIQUES
# ════════════════════════════════════════════════════════════
elif page == "🔴 Alertes Critiques":

    st.title("🔴 Alertes Critiques — Intervention Immédiate")
    st.markdown("---")

    df_crit = df[df['niveau_risque'] == 'critique'].sort_values(
        'dropout_score', ascending=False
    )

    st.error(f"⚠️ **{len(df_crit)} étudiants** nécessitent une intervention immédiate.")

    for _, row in df_crit.head(20).iterrows():
        with st.expander(
            f"🔴 Étudiant {row['id_student']} — Score: {row['dropout_score']:.3f} — {row['cause_label']}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Module :** {row['code_module']} — {row['code_presentation']}")
                st.markdown(f"**Cause :** {row['cause_label']}")
                st.markdown(f"**Action :** {row['action']}")
                st.markdown(f"**Intervention :** {row['intervention']}")
            with col2:
                donnees = row['donnees_etudiant']
                if isinstance(donnees, str):
                    try:
                        donnees = json.loads(donnees.replace("'", """))
                    except:
                        donnees = {}
                st.metric("Score risque",    f"{row['dropout_score']:.3f}")
                st.metric("Clics totaux",    f"{int(donnees.get('total_clicks', 0))}")
                st.metric("Jours actifs",    f"{int(donnees.get('total_days_active', 0))}")

            if st.button(f"📧 Notifier tuteur — Étudiant {row['id_student']}",
                         key=f"notif_{row['id_student']}"):
                st.success(f"✅ Notification envoyée pour l'étudiant {row['id_student']}")

# ════════════════════════════════════════════════════════════
# PAGE 4 — STATISTIQUES
# ════════════════════════════════════════════════════════════
elif page == "📈 Statistiques":

    st.title("📈 Statistiques Globales")
    st.markdown("---")

    if df.empty:
        st.warning("Aucune donnée disponible.")
    else:
        # Risque par module
        st.subheader("Taux de risque par module")
        risk_by_module = df.groupby('code_module').agg(
            total     = ('id_student', 'count'),
            critiques = ('niveau_risque', lambda x: (x == 'critique').sum()),
            score_moy = ('dropout_score', 'mean')
        ).reset_index()
        risk_by_module['taux_critique'] = (
            100 * risk_by_module['critiques'] / risk_by_module['total']
        ).round(1)

        fig_mod = px.bar(
            risk_by_module,
            x='code_module', y='taux_critique',
            color='score_moy',
            color_continuous_scale='RdYlGn_r',
            labels={'taux_critique': '% Critiques', 'code_module': 'Module'},
            text='taux_critique'
        )
        fig_mod.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_mod.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig_mod, use_container_width=True)

        # Cause x Module
        st.subheader("Causes d'abandon par module")
        cause_module = df.groupby(
            ['code_module','cause_principale']
        ).size().reset_index(name='count')

        fig_cm = px.bar(
            cause_module,
            x='code_module', y='count',
            color='cause_principale',
            color_discrete_sequence=['#E74C3C','#3498DB','#F39C12','#9B59B6'],
            labels={'count': 'Étudiants', 'code_module': 'Module'},
            barmode='stack'
        )
        fig_cm.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig_cm, use_container_width=True)

        # Résumé chiffres clés
        st.subheader("Résumé des chiffres clés")
        col1, col2, col3 = st.columns(3)
        col1.metric("AUC-ROC XGBoost",    "0.863")
        col2.metric("Recall abandons",     "71%")
        col3.metric("Cutoff optimal",      "Jour 28")
        col1.metric("Wilcoxon p-value",    "0.002")
        col2.metric("Étudiants analysés",  f"{len(df):,}")
        col3.metric("Profils d'abandon",  "7 identifiés")

# ════════════════════════════════════════════════════════════
# PAGE 5 — TEST API
# ════════════════════════════════════════════════════════════
elif page == "🔌 Test API":

    st.title("🔌 Test de l'API Plugin")
    st.markdown("---")

    api_url = st.text_input("URL de l'API", "http://localhost:8000")

    st.subheader("Test — Prédiction d'un étudiant")

    col1, col2 = st.columns(2)
    with col1:
        id_student    = st.number_input("ID Étudiant", value=12345)
        code_module   = st.text_input("Code Module",   value="AAA")
        total_clicks  = st.slider("Clics totaux",      0, 1000, 45)
        days_active   = st.slider("Jours actifs",      0, 42,   5)
        last_day      = st.slider("Dernier jour actif",0, 42,   12)
    with col2:
        avg_score     = st.slider("Score moyen",       0, 100,  52)
        assessments   = st.slider("Évaluations",       0, 10,   1)
        credits       = st.slider("Crédits inscrits",  30, 180, 60)

    if st.button("🚀 Tester la prédiction", type="primary"):
        payload = {
            "id_student"               : int(id_student),
            "code_module"              : code_module,
            "code_presentation"        : "test",
            "total_clicks"             : float(total_clicks),
            "total_days_active"        : float(days_active),
            "avg_clicks_per_day"       : float(total_clicks / max(days_active, 1)),
            "last_activity_day"        : float(last_day),
            "total_span_days"          : float(last_day),
            "avg_score"                : float(avg_score),
            "num_submitted_assessments": float(assessments),
            "studied_credits"          : float(credits)
        }

        try:
            response = requests.post(
                f"{api_url}/predict",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                st.success("✅ Prédiction réussie !")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Score de risque", f"{result['dropout_score']:.3f}")
                col_b.metric("Niveau",          f"{result['emoji_risque']} {result['niveau_risque'].upper()}")
                col_c.metric("Urgence",         f"Niveau {result['urgence']}/3")

                st.markdown(f"**Cause :** {result['cause_label']}")
                st.markdown(f"**Action :** {result['action']}")
                st.markdown(f"**Intervention :** {result['intervention']}")

                st.subheader("Réponse JSON complète")
                st.json(result)
            else:
                st.error(f"Erreur API : {response.status_code} — {response.text}")
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ API non accessible. Lance d'abord le serveur FastAPI.")
            st.code("!cd plugin_mooc && uvicorn main:app --host 0.0.0.0 --port 8000 &")

    # Test health
    st.markdown("---")
    if st.button("❤️ Vérifier santé de l'API"):
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            if r.status_code == 200:
                st.success("✅ API opérationnelle")
                st.json(r.json())
            else:
                st.error("API non disponible")
        except:
            st.warning("API non accessible — vérifie que le serveur est lancé.")
