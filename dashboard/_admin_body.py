"""Admin : configuration des profils et ratios."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import yaml

PROFILS_PATH = ROOT / "config" / "profils.yaml"
RATIOS_PATH = ROOT / "config" / "ratios_config.yaml"
USER_PATH = ROOT / "data" / "config_user.yaml"


def load_yaml(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


st.markdown("# ⚙️ Configuration Admin")
st.caption("Modifiez les profils, les poids et les ratios actifs. Puis sauvegardez.")

# ============================================================
# Charger config effective
# ============================================================
user_cfg = load_yaml(USER_PATH)
if user_cfg:
    profils = user_cfg.get("profils") or load_yaml(PROFILS_PATH)
    ratios_cfg = user_cfg.get("ratios") or load_yaml(RATIOS_PATH)
    st.success("✅ Config utilisateur active")
else:
    profils = load_yaml(PROFILS_PATH)
    ratios_cfg = load_yaml(RATIOS_PATH)
    st.info("ℹ️ Config par defaut (aucune sauvegarde utilisateur)")

if not profils:
    st.error("❌ Aucun profil charge depuis config/profils.yaml")
    st.stop()
if not ratios_cfg.get("categories"):
    st.error("❌ Aucune categorie dans config/ratios_config.yaml")
    st.stop()

# ============================================================
# Tabs
# ============================================================
tab1, tab2, tab3 = st.tabs(["📊 Profils", "🎯 Ratios actifs", "💾 Sauvegarde"])

# ============================================================
# ONGLET 1 : Profils
# ============================================================
with tab1:
    st.subheader("Poids des categories par profil")
    st.caption("La somme des 6 categories doit faire 1.00 (100%)")

    categories = list(ratios_cfg.get("categories", {}).keys())
    new_profils = {}

    for profil_nom, profil_info in profils.items():
        label = profil_info.get("label", profil_nom)
        with st.expander(f"**{label}**", expanded=(profil_nom == "moyen_terme")):
            st.caption(profil_info.get("description", ""))
            poids = profil_info.get("poids_categories", {})
            new_poids = {}

            cols = st.columns(3)
            for i, cat in enumerate(categories):
                with cols[i % 3]:
                    cat_label = cat.replace("_", " ").title()
                    val = float(poids.get(cat, 0.0))
                    new_poids[cat] = st.slider(
                        f"{cat_label} = {val:.2f}",
                        0.0, 1.0, val, 0.01,
                        key=f"p_{profil_nom}_{cat}",
                    )

            total = sum(new_poids.values())
            if abs(total - 1.0) > 0.01:
                st.warning(f"⚠️ Somme = {total:.2f} (doit etre 1.00)")
            else:
                st.success(f"✅ Somme = {total:.2f}")

            new_profils[profil_nom] = {**profil_info, "poids_categories": new_poids}

    st.session_state["new_profils"] = new_profils

# ============================================================
# ONGLET 2 : Ratios
# ============================================================
with tab2:
    st.subheader("Ratios actifs et poids internes")
    st.caption("Cochez les ratios a utiliser. Poids relatif dans chaque categorie.")

    categories_dict = ratios_cfg.get("categories", {})
    new_categories = {}

    for cat, cat_info in categories_dict.items():
        ratios_actifs = cat_info.get("ratios_actifs", [])
        ratios_details = ratios_cfg.get(cat, {})

        titre = f"**{cat.replace('_', ' ').title()}** ({len(ratios_actifs)} actifs / {len(ratios_details)} total)"
        with st.expander(titre, expanded=False):
            if not ratios_details:
                st.warning(f"Aucun ratio defini pour '{cat}'")
                continue

            all_ratios = list(ratios_details.keys())
            selected = []
            poids_dict = {}

            for ratio in all_ratios:
                c1, c2 = st.columns([1, 3])
                with c1:
                    actif = ratio in ratios_actifs
                    new_actif = st.checkbox(ratio, value=actif, key=f"act_{cat}_{ratio}")
                with c2:
                    if new_actif:
                        val = float(ratios_details[ratio].get("poids", 0.0))
                        poids_dict[ratio] = st.slider(
                            f"{ratio} = {val:.2f}",
                            0.0, 1.0, val, 0.01,
                            key=f"pds_{cat}_{ratio}",
                        )
                        selected.append(ratio)

            new_categories[cat] = {"ratios_actifs": selected}

            for ratio, val in poids_dict.items():
                if ratio in ratios_details:
                    ratios_cfg[cat][ratio]["poids"] = val

    ratios_cfg["categories"] = new_categories
    st.session_state["new_ratios"] = ratios_cfg

# ============================================================
# ONGLET 3 : Sauvegarde
# ============================================================
with tab3:
    st.subheader("Sauvegarder la configuration")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💾 Sauvegarder", type="primary", use_container_width=True):
            new_config = {
                "profils": st.session_state.get("new_profils", profils),
                "ratios": st.session_state.get("new_ratios", ratios_cfg),
            }
            save_yaml(USER_PATH, new_config)
            st.success(f"✅ Sauvegarde : {USER_PATH}")
            st.rerun()

    with c2:
        if st.button("♻️ Reinitialiser", use_container_width=True):
            if USER_PATH.exists():
                USER_PATH.unlink()
                st.success("✅ Config utilisateur supprimee")
                st.rerun()
            else:
                st.info("Aucune config utilisateur a supprimer")

    with c3:
        if st.button("📥 Exporter YAML", use_container_width=True):
            import io
            buf = io.BytesIO()
            new_config = {
                "profils": st.session_state.get("new_profils", profils),
                "ratios": st.session_state.get("new_ratios", ratios_cfg),
            }
            buf.write(yaml.dump(new_config, default_flow_style=False, allow_unicode=True, sort_keys=False).encode("utf-8"))
            st.download_button(
                "Telecharger",
                data=buf.getvalue(),
                file_name="config_user.yaml",
                mime="text/yaml",
            )

    st.divider()
    st.caption(f"Config utilisateur : {USER_PATH}")
    if USER_PATH.exists():
        st.caption(f"Taille : {USER_PATH.stat().st_size} octets")
    else:
        st.caption("Pas encore de sauvegarde utilisateur")
