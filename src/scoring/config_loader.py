"""Chargement de la config effective (user > defauts)."""
from pathlib import Path
import yaml


ROOT = Path(__file__).parent.parent.parent
PROFILS_PATH = ROOT / "config" / "profils.yaml"
RATIOS_PATH = ROOT / "config" / "ratios_config.yaml"
USER_PATH = ROOT / "data" / "config_user.yaml"


def _load_yaml(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_effective_config():
    """Retourne (profils, ratios) en priorisant la config utilisateur.

    Returns:
        profils : {nom_profil: {label, description, poids_categories}}
        ratios  : {categories: {...}, liquidite: {...}, ...}
    """
    user = _load_yaml(USER_PATH)
    if user:
        profils = user.get("profils") or _load_yaml(PROFILS_PATH)
        ratios = user.get("ratios") or _load_yaml(RATIOS_PATH)
    else:
        profils = _load_yaml(PROFILS_PATH)
        ratios = _load_yaml(RATIOS_PATH)
    return profils, ratios


def load_profils():
    profils, _ = load_effective_config()
    return profils


def load_ratios():
    _, ratios = load_effective_config()
    return ratios


def has_user_config():
    return USER_PATH.exists()
