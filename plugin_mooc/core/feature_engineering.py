
import pandas as pd
import numpy as np
from typing import Dict

def compute_features_from_moodle_logs(logs: list, cutoff_day: int = 42) -> dict:
    """
    Calcule les features à partir des logs bruts Moodle.
    Compatible avec le format retourné par l'API REST Moodle.

    Args:
        logs: liste de dicts {userid, component, action, timecreated, ...}
        cutoff_day: nombre de jours depuis l'inscription à considérer

    Returns:
        dict de features prêt pour le prédicteur
    """
    if not logs:
        return _empty_features()

    df = pd.DataFrame(logs)

    # Convertir timestamp en jour relatif
    if 'timecreated' in df.columns:
        df['timecreated'] = pd.to_datetime(df['timecreated'], unit='s')
        min_date = df['timecreated'].min()
        df['day'] = (df['timecreated'] - min_date).dt.days

        # Appliquer le cutoff
        df = df[df['day'] <= cutoff_day]

    if df.empty:
        return _empty_features()

    # Features d'engagement
    total_clicks      = len(df)
    total_days_active = df['day'].nunique() if 'day' in df.columns else 0
    last_activity_day = df['day'].max() if 'day' in df.columns else 0
    total_span_days   = last_activity_day - df['day'].min() if 'day' in df.columns else 0
    avg_clicks_per_day = total_clicks / max(total_days_active, 1)

    # Features par type d'activité
    activity_counts = {}
    if 'component' in df.columns:
        counts = df['component'].value_counts()
        for act in ['forumng','quiz','oucontent','resource',
                    'ouwiki','ouelluminate','homepage','subpage','url','glossary']:
            activity_counts[act] = float(counts.get(f'mod_{act}', 0))

    return {
        'total_clicks'      : float(total_clicks),
        'total_days_active' : float(total_days_active),
        'avg_clicks_per_day': float(avg_clicks_per_day),
        'last_activity_day' : float(last_activity_day),
        'total_span_days'   : float(total_span_days),
        **activity_counts
    }


def _empty_features() -> dict:
    """Retourne des features vides pour un étudiant sans activité."""
    return {
        'total_clicks'      : 0.0,
        'total_days_active' : 0.0,
        'avg_clicks_per_day': 0.0,
        'last_activity_day' : 0.0,
        'total_span_days'   : 0.0,
        'forumng'           : 0.0,
        'quiz'              : 0.0,
        'oucontent'         : 0.0,
        'resource'          : 0.0,
        'ouwiki'            : 0.0,
        'ouelluminate'      : 0.0,
        'homepage'          : 0.0,
        'subpage'           : 0.0,
        'url'               : 0.0,
        'glossary'          : 0.0,
    }
