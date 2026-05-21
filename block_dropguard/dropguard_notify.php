<?php
// DropGuard — Envoi notification manuelle enseignant
// Human-in-the-loop : l'enseignant écrit son message, Groq suggère
// IRD / UGB Saint-Louis — 2026

require_once('../../config.php');

$userid   = required_param('userid',   PARAM_INT);
$courseid = required_param('courseid', PARAM_INT);
$confirm  = optional_param('confirm',  0, PARAM_INT);

$course  = $DB->get_record('course',  ['id' => $courseid], '*', MUST_EXIST);
$context = context_course::instance($courseid);

require_login($course);
require_capability('moodle/course:viewhiddenactivities', $context);

$result = $DB->get_record('block_dropguard_results', [
    'userid'   => $userid,
    'courseid' => $courseid,
], '*', MUST_EXIST);

$user    = core_user::get_user($userid, '*', MUST_EXIST);
$support = core_user::get_support_user();

$report_url = new moodle_url(
    '/blocks/dropguard/dropguard_report.php',
    ['courseid' => $courseid]
);

// ── Traitement du formulaire ──
if ($confirm && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $custom_message = optional_param('custom_message', '', PARAM_TEXT);

    if (empty(trim($custom_message))) {
        redirect($report_url, "❌ Message vide — notification non envoyée.", 3);
    }

    // Envoyer le message personnalisé de l'enseignant
    $message                    = new \core\message\message();
    $message->component         = 'block_dropguard';
    $message->name              = 'dropguard_alert';
    $message->userfrom          = $support;
    $message->userto            = $user;
    $message->subject           = '📚 DropGuard — Message de votre enseignant';
    $message->fullmessage       = $custom_message;
    $message->fullmessageformat = FORMAT_PLAIN;
    $message->fullmessagehtml   = '<p>' . nl2br(htmlspecialchars($custom_message)) . '</p>';
    $message->smallmessage      = 'Votre enseignant vous a envoyé un message via DropGuard.';
    $message->notification      = 1;

    message_send($message);

    $DB->set_field('block_dropguard_results',
        'notification_envoyee', 1,
        ['userid' => $userid, 'courseid' => $courseid]
    );

    redirect($report_url,
        "✅ Message envoyé à {$user->firstname} {$user->lastname}",
        3
    );
}

// ── Données pour l'affichage ──
$groq_message = htmlspecialchars($result->message_motivation ?? '');

$causes_labels = [
    'inactivite'           => '😴 Inactivité comportementale',
    'difficulte_academique'=> '📉 Difficulté académique',
    'surcharge'            => '⚠️ Surcharge de crédits',
    'desengagement_module' => '🔌 Désengagement du module',
];
$cause_label = $causes_labels[$result->cause_principale] ?? $result->cause_principale;

$niveaux_colors = [
    'critique' => '#EF4444',
    'modere'   => '#F59E0B',
    'faible'   => '#10B981',
];
$niveau_color = $niveaux_colors[$result->niveau_risque] ?? '#6B7280';

$ressources = json_decode($result->activites_recommandees ?? '[]', true);

// Message pré-rempli suggéré pour l'enseignant
$message_suggere = "Bonjour {$user->firstname},\n\n" .
    "Je suis votre enseignant et j'ai remarqué que vous n'avez pas été très actif récemment dans le cours.\n\n" .
    "Je voulais vous contacter personnellement pour vous encourager à reprendre. " .
    "Des ressources adaptées à votre profil sont disponibles dans votre espace DropGuard.\n\n" .
    "N'hésitez pas à me contacter si vous avez des difficultés — je suis là pour vous aider.\n\n" .
    "Cordialement,\nVotre enseignant";

?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DropGuard — Notifier <?php echo htmlspecialchars($user->firstname . ' ' . $user->lastname); ?></title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #F3F4F6;
            color: #1F2937;
            padding: 24px;
        }
        .container {
            max-width: 760px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #1E3A5F, #2563EB);
            color: white;
            padding: 20px 24px;
            border-radius: 12px 12px 0 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header h1 {
            font-size: 1.1rem;
            font-weight: 700;
        }
        .header p {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-top: 2px;
        }

        /* Card */
        .card {
            background: white;
            border: 1px solid #E5E7EB;
            border-top: none;
            border-radius: 0 0 12px 12px;
            padding: 24px;
        }

        /* Profil étudiant */
        .student-profile {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px;
            background: #F8FAFC;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563EB, #7C3AED);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 1.1rem;
            flex-shrink: 0;
        }
        .student-info h3 {
            font-size: 1rem;
            font-weight: 600;
            color: #1E293B;
        }
        .student-info p {
            font-size: 0.8rem;
            color: #6B7280;
            margin-top: 2px;
        }
        .badge {
            margin-left: auto;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 4px;
        }
        .niveau-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            color: white;
        }
        .score-text {
            font-size: 0.75rem;
            color: #6B7280;
        }

        /* Sections */
        .section-title {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6B7280;
            margin-bottom: 10px;
        }

        /* Cause + ressources */
        .info-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        .info-box {
            background: #F8FAFC;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 12px;
        }
        .info-box .label {
            font-size: 0.72rem;
            color: #9CA3AF;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .info-box .value {
            font-size: 0.85rem;
            font-weight: 500;
            color: #1E293B;
        }
        .resource-item {
            font-size: 0.8rem;
            color: #374151;
            padding: 3px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Message Groq */
        .groq-box {
            background: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-left: 4px solid #2563EB;
            border-radius: 0 8px 8px 0;
            padding: 14px 16px;
            margin-bottom: 20px;
        }
        .groq-box .groq-label {
            font-size: 0.72rem;
            font-weight: 600;
            color: #2563EB;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .groq-box .groq-text {
            font-size: 0.85rem;
            color: #1E3A5F;
            line-height: 1.6;
            white-space: pre-wrap;
        }

        /* Zone de texte enseignant */
        .form-section {
            margin-bottom: 20px;
        }
        .form-section label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }
        .form-section textarea {
            width: 100%;
            min-height: 160px;
            padding: 12px 14px;
            border: 1px solid #D1D5DB;
            border-radius: 8px;
            font-size: 0.875rem;
            font-family: inherit;
            color: #1F2937;
            line-height: 1.6;
            resize: vertical;
            transition: border-color 0.15s;
            outline: none;
        }
        .form-section textarea:focus {
            border-color: #2563EB;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        .form-hint {
            font-size: 0.75rem;
            color: #9CA3AF;
            margin-top: 6px;
        }

        /* Boutons */
        .actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            padding-top: 16px;
            border-top: 1px solid #F3F4F6;
        }
        .btn {
            padding: 10px 24px;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.15s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary {
            background: #2563EB;
            color: white;
        }
        .btn-primary:hover {
            background: #1D4ED8;
        }
        .btn-secondary {
            background: white;
            color: #6B7280;
            border: 1px solid #D1D5DB;
        }
        .btn-secondary:hover {
            background: #F9FAFB;
        }

        /* Use suggestion button */
        .use-suggestion {
            font-size: 0.75rem;
            color: #2563EB;
            cursor: pointer;
            background: none;
            border: none;
            padding: 0;
            text-decoration: underline;
            margin-top: 4px;
        }
    </style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="header">
        <span style="font-size:1.5rem;">🛡️</span>
        <div>
            <h1>DropGuard — Envoyer un message</h1>
            <p>Rédigez votre message personnalisé pour l'étudiant</p>
        </div>
    </div>

    <div class="card">

        <!-- Profil étudiant -->
        <div class="student-profile">
            <div class="avatar">
                <?php echo strtoupper(substr($user->firstname, 0, 1) . substr($user->lastname, 0, 1)); ?>
            </div>
            <div class="student-info">
                <h3><?php echo htmlspecialchars($user->firstname . ' ' . $user->lastname); ?></h3>
                <p><?php echo htmlspecialchars($user->email); ?></p>
            </div>
            <div class="badge">
                <span class="niveau-badge" style="background:<?php echo $niveau_color; ?>">
                    <?php echo strtoupper($result->niveau_risque); ?>
                </span>
                <span class="score-text">Score : <?php echo number_format($result->dropout_score, 3); ?></span>
            </div>
        </div>

        <!-- Cause + Ressources -->
        <div class="section-title">Diagnostic DropGuard</div>
        <div class="info-row">
            <div class="info-box">
                <div class="label">Cause principale</div>
                <div class="value"><?php echo $cause_label; ?></div>
            </div>
            <div class="info-box">
                <div class="label">Ressources recommandées</div>
                <?php foreach (array_slice($ressources, 0, 3) as $res): ?>
                    <div class="resource-item">
                        <?php
                            $icon = match($res['type'] ?? '') {
                                'quiz'  => '📝',
                                'forum' => '💬',
                                'page'  => '📄',
                                'url'   => '🔗',
                                default => '→'
                            };
                            echo $icon . ' ' . htmlspecialchars($res['name'] ?? '');
                        ?>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- Message Groq -->
        <div class="section-title">💡 Message suggéré par DropGuard</div>
        <div class="groq-box">
            <div class="groq-label">
                <span>🤖</span> Généré par l'IA — à titre indicatif uniquement
            </div>
            <div class="groq-text"><?php echo $groq_message; ?></div>
        </div>

        <!-- Formulaire message enseignant -->
        <form method="POST" action="">
            <input type="hidden" name="userid"   value="<?php echo $userid; ?>">
            <input type="hidden" name="courseid" value="<?php echo $courseid; ?>">
            <input type="hidden" name="confirm"  value="1">

            <div class="form-section">
                <label for="custom_message">
                    ✏️ Votre message personnel à <?php echo htmlspecialchars($user->firstname); ?>
                </label>
                <textarea
                    id="custom_message"
                    name="custom_message"
                    placeholder="Écrivez votre message ici..."
                ><?php echo htmlspecialchars($message_suggere); ?></textarea>
                <div class="form-hint">
                    Ce message sera envoyé directement à l'étudiant via Moodle.
                    Le message DropGuard ci-dessus peut vous servir d'inspiration.
                </div>
            </div>

            <div class="actions">
                <a href="<?php echo $report_url; ?>" class="btn btn-secondary">
                    ← Annuler
                </a>
                <button type="submit" class="btn btn-primary">
                    📨 Envoyer le message
                </button>
            </div>
        </form>

    </div>
</div>
</body>
</html>