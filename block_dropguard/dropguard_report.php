<?php
// DropGuard — Page rapport enseignant
// Accessible depuis : Cours → Bloc DropGuard → "Voir le rapport complet"

require_once('../../config.php');
require_once($CFG->libdir . '/tablelib.php');

// Paramètres
$courseid = required_param('courseid', PARAM_INT);
$course   = $DB->get_record('course', ['id' => $courseid], '*', MUST_EXIST);
$context  = context_course::instance($courseid);

// Vérification accès enseignant
require_login($course);
require_capability('moodle/course:viewhiddenactivities', $context);

// Configuration page Moodle
$PAGE->set_url('/blocks/dropguard/dropguard_report.php', ['courseid' => $courseid]);
$PAGE->set_context($context);
$PAGE->set_course($course);
$PAGE->set_title('DropGuard — Rapport ' . $course->fullname);
$PAGE->set_heading($course->fullname);
$PAGE->set_pagelayout('report');

// Récupérer tous les résultats du cours
$results = $DB->get_records_sql("
    SELECT
        dgr.*,
        u.firstname,
        u.lastname,
        u.email
    FROM {block_dropguard_results} dgr
    JOIN {user} u ON u.id = dgr.userid
    WHERE dgr.courseid = ?
    ORDER BY dgr.dropout_score DESC
", [$courseid]);

// Statistiques globales
$total     = count($results);
$critiques = 0;
$moderes   = 0;
$faibles   = 0;

foreach ($results as $r) {
    if ($r->niveau_risque === 'critique') $critiques++;
    elseif ($r->niveau_risque === 'modere') $moderes++;
    else $faibles++;
}

// ── Rendu HTML ──
echo $OUTPUT->header();

echo "
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .dg-wrap {
        font-family: 'Inter', sans-serif;
        max-width: 1100px;
        margin: 0 auto;
        padding: 0 1rem 3rem;
    }

    /* Header */
    .dg-header {
        background: linear-gradient(135deg, #1E3A5F, #2563EB);
        color: white;
        border-radius: 14px;
        padding: 1.8rem 2rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .dg-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .dg-logo {
        width: 48px; height: 48px;
        background: rgba(255,255,255,0.15);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    .dg-title { font-size: 1.4rem; font-weight: 700; }
    .dg-subtitle { font-size: 0.82rem; opacity: 0.75; margin-top: 2px; }
    .dg-badge {
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    /* Stats cards */
    .dg-stats {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 1.5rem;
    }
    .dg-stat-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .dg-stat-bar {
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .dg-stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1;
        margin-bottom: 4px;
    }
    .dg-stat-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #6B7280;
    }

    /* Table */
    .dg-table-wrap {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .dg-table-header {
        padding: 1.2rem 1.5rem;
        border-bottom: 1px solid #F3F4F6;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .dg-table-title {
        font-size: 1rem;
        font-weight: 600;
        color: #0F172A;
    }
    table.dg-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }
    table.dg-table th {
        background: #F8FAFC;
        padding: 10px 16px;
        text-align: left;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #6B7280;
        border-bottom: 1px solid #E5E7EB;
    }
    table.dg-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #F9FAFB;
        color: #374151;
        vertical-align: middle;
    }
    table.dg-table tr:hover td {
        background: #FAFBFF;
    }
    table.dg-table tr:last-child td {
        border-bottom: none;
    }

    /* Badges */
    .dg-badge-niveau {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-critique { background:#FEE2E2; color:#DC2626; }
    .badge-modere   { background:#FEF3C7; color:#D97706; }
    .badge-faible   { background:#D1FAE5; color:#059669; }

    /* Score bar */
    .dg-score-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .dg-score-bar {
        flex: 1;
        height: 6px;
        background: #F3F4F6;
        border-radius: 3px;
        overflow: hidden;
    }
    .dg-score-fill {
        height: 100%;
        border-radius: 3px;
    }
    .dg-score-val {
        font-size: 0.82rem;
        font-weight: 600;
        color: #374151;
        min-width: 38px;
    }

    /* Bouton notifier */
    .dg-btn-notify {
        background: #2563EB;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        transition: background 0.15s;
    }
    .dg-btn-notify:hover { background: #1D4ED8; color: white; }
    .dg-btn-notify.sent {
        background: #D1FAE5;
        color: #059669;
        cursor: default;
    }

    /* Empty state */
    .dg-empty {
        text-align: center;
        padding: 3rem;
        color: #6B7280;
    }
    .dg-empty-icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
</style>

<div class='dg-wrap'>

    <!-- Header -->
    <div class='dg-header'>
        <div class='dg-header-left'>
            <div class='dg-logo'>🛡️</div>
            <div>
                <div class='dg-title'>DropGuard</div>
                <div class='dg-subtitle'>
                    Rapport d'analyse — {$course->fullname}
                </div>
            </div>
        </div>
        <div class='dg-badge'>IRD / UGB Saint-Louis · v1.0</div>
    </div>

    <!-- Stats -->
    <div class='dg-stats'>
        <div class='dg-stat-card'>
            <div class='dg-stat-bar' style='background:#2563EB;'></div>
            <div class='dg-stat-value'>{$total}</div>
            <div class='dg-stat-label'>Étudiants analysés</div>
        </div>
        <div class='dg-stat-card'>
            <div class='dg-stat-bar' style='background:#DC2626;'></div>
            <div class='dg-stat-value' style='color:#DC2626;'>{$critiques}</div>
            <div class='dg-stat-label'>Risque critique</div>
        </div>
        <div class='dg-stat-card'>
            <div class='dg-stat-bar' style='background:#D97706;'></div>
            <div class='dg-stat-value' style='color:#D97706;'>{$moderes}</div>
            <div class='dg-stat-label'>Risque modéré</div>
        </div>
        <div class='dg-stat-card'>
            <div class='dg-stat-bar' style='background:#059669;'></div>
            <div class='dg-stat-value' style='color:#059669;'>{$faibles}</div>
            <div class='dg-stat-label'>Risque faible</div>
        </div>
    </div>

    <!-- Table étudiants -->
    <div class='dg-table-wrap'>
        <div class='dg-table-header'>
            <div class='dg-table-title'>
                📋 Liste des étudiants — triés par niveau de risque
            </div>
            <div style='font-size:0.78rem;color:#9CA3AF;'>
                Mis à jour automatiquement chaque nuit · Cutoff J28
            </div>
        </div>";

if (empty($results)) {
    echo "
        <div class='dg-empty'>
            <div class='dg-empty-icon'>🔍</div>
            <div style='font-weight:600;color:#374151;margin-bottom:4px;'>
                Aucune analyse disponible
            </div>
            <div style='font-size:0.85rem;'>
                Le cron DropGuard n'a pas encore tourné pour ce cours.
            </div>
        </div>";
} else {
    echo "
        <table class='dg-table'>
            <thead>
                <tr>
                    <th>Étudiant</th>
                    <th>Score de risque</th>
                    <th>Niveau</th>
                    <th>Cause principale</th>
                    <th>Recommandations</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>";

    // Mapping causes
    $cause_labels = [
        'inactivite'            => '😴 Inactivité',
        'difficulte_academique' => '📉 Difficulté académique',
        'surcharge'             => '😰 Surcharge',
        'desengagement_module'  => '💤 Désengagement',
    ];

    foreach ($results as $r) {
        $score      = round($r->dropout_score, 3);
        $pct        = round($r->dropout_score * 100);
        $niveau     = $r->niveau_risque;
        $cause      = $cause_labels[$r->cause_principale] ?? $r->cause_principale;
        $nom        = fullname((object)[
            'firstname' => $r->firstname,
            'lastname'  => $r->lastname
        ]);

        // Couleur score bar
        $bar_color = match($niveau) {
            'critique' => '#DC2626',
            'modere'   => '#D97706',
            default    => '#059669'
        };

        // Activités recommandées
        $ressources_data = json_decode($r->activites_recommandees ?? '[]', true);
        $act_html = '';
        foreach (array_slice($ressources_data, 0, 2) as $res) {
            $name = htmlspecialchars($res['name'] ?? '');
            $url  = htmlspecialchars($res['url']  ?? '');
            if ($url) {
                $act_html .= "<a href='{$url}' style='
                    display:block;color:#2563EB;
                    font-size:0.78rem;margin-bottom:2px;
                    text-decoration:none;
                '>→ {$name}</a>";
            } else {
                $act_html .= "<span style='font-size:0.78rem;color:#6B7280;display:block;'>→ {$name}</span>";
            }
        }

        // Bouton notification
        if ($r->notification_envoyee) {
            $btn = "<span class='dg-btn-notify sent'>✓ Envoyé</span>";
        } else {
            $notify_url = new moodle_url(
                '/blocks/dropguard/dropguard_notify.php',
                ['userid' => $r->userid, 'courseid' => $courseid]
            );
            $btn = "<a href='{$notify_url}' class='dg-btn-notify'>
                        📧 Notifier
                    </a>";
        }

        echo "
            <tr>
                <td>
                    <div style='font-weight:600;color:#0F172A;'>{$nom}</div>
                    <div style='font-size:0.75rem;color:#9CA3AF;'>{$r->email}</div>
                </td>
                <td>
                    <div class='dg-score-wrap'>
                        <div class='dg-score-bar'>
                            <div class='dg-score-fill'
                                 style='width:{$pct}%;background:{$bar_color};'>
                            </div>
                        </div>
                        <div class='dg-score-val'>{$score}</div>
                    </div>
                </td>
                <td>
                    <span class='dg-badge-niveau badge-{$niveau}'>
                        {$niveau}
                    </span>
                </td>
                <td style='color:#374151;'>{$cause}</td>
                <td style='font-size:0.82rem;color:#6B7280;'>{$act_html}</td>
                <td>{$btn}</td>
            </tr>";
    }

    echo "
            </tbody>
        </table>";
}

echo "
    </div>
</div>";

echo $OUTPUT->footer();