<?php
// DropGuard — Bloc principal
// Ce fichier définit le comportement du bloc dans Moodle

defined('MOODLE_INTERNAL') || die();

class block_dropguard extends block_base {

    // Initialisation du bloc
    public function init() {
        $this->title = get_string('pluginname', 'block_dropguard');
    }

    // Le bloc peut apparaître dans les cours
    public function applicable_formats() {
        return [
            'course-view' => true,
            'site'        => false,
            'my'          => false,
        ];
    }

    // Contenu du bloc
    public function get_content() {
        global $USER, $COURSE, $CFG;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass();

        // Récupérer le rôle de l'utilisateur
        $context    = context_course::instance($COURSE->id);
        $is_teacher = has_capability('moodle/course:viewhiddenactivities', $context);

        if ($is_teacher) {
            // VUE ENSEIGNANT
            $this->content->text = $this->render_teacher_view();
        } else {
            // VUE ÉTUDIANT
            $this->content->text = $this->render_student_view($USER->id, $COURSE->id);
        }

        $this->content->footer = '';
        return $this->content;
    }

    // ── Vue Étudiant ──
    private function render_student_view($user_id, $course_id) {
        global $DB;

        $rec = $DB->get_record('block_dropguard_results', [
            'userid'   => $user_id,
            'courseid' => $course_id,
        ]);

        if (!$rec) {
            return $this->render_no_data_student();
        }

        $niveau  = $rec->niveau_risque;
        $message = htmlspecialchars($rec->message_motivation);

        $colors = [
            'critique' => '#EF4444',
            'modere'   => '#F59E0B',
            'faible'   => '#10B981',
        ];
        $color = $colors[$niveau] ?? '#6B7280';

        $labels = [
            'critique' => 'Suivi actif 🔴',
            'modere'   => 'Suivi actif 🟠',
            'faible'   => 'Suivi actif 🟢',
        ];
        $label = $labels[$niveau] ?? 'Suivi actif';

        // Ressources avec liens
        $ressources = json_decode($rec->activites_recommandees, true) ?? [];
        $ressources_html = '';
        foreach ($ressources as $res) {
            $name = htmlspecialchars($res['name'] ?? '');
            $url  = htmlspecialchars($res['url']  ?? '');
            $type = $res['type'] ?? '';

            $icon = match($type) {
                'quiz'   => '📝',
                'forum'  => '💬',
                'page'   => '📄',
                'url'    => '🔗',
                default  => '→'
            };

            if ($url) {
                $ressources_html .= "
                <a href='{$url}' style='
                    display:flex;
                    align-items:center;
                    gap:8px;
                    padding:8px 10px;
                    margin-bottom:6px;
                    background:white;
                    border:1px solid #E5E7EB;
                    border-radius:8px;
                    text-decoration:none;
                    color:#1E293B;
                    font-size:0.85rem;
                    font-weight:500;
                    transition:all 0.15s;
                ' onmouseover=\"this.style.borderColor='{$color}';this.style.color='{$color}'\"
                onmouseout=\"this.style.borderColor='#E5E7EB';this.style.color='#1E293B'\">
                    <span style='font-size:1rem;'>{$icon}</span>
                    <span>{$name}</span>
                    <span style='margin-left:auto;color:#9CA3AF;font-size:0.75rem;'>→</span>
                </a>";
            } else {
                $ressources_html .= "
                <div style='
                    display:flex;align-items:center;gap:8px;
                    padding:8px 10px;margin-bottom:6px;
                    color:#374151;font-size:0.85rem;
                '>{$icon} {$name}</div>";
            }
        }

        return "
        <div style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:0;'>

            <!-- Header -->
            <div style='
                background:linear-gradient(135deg,#1E3A5F,#2563EB);
                color:white;padding:14px 16px;
                border-radius:8px 8px 0 0;
                display:flex;align-items:center;gap:8px;
            '>
                <span style='font-size:1.2rem;'>🛡️</span>
                <div>
                    <div style='font-weight:700;font-size:0.95rem;'>DropGuard</div>
                    <div style='font-size:0.72rem;opacity:0.8;'>Votre parcours personnalisé</div>
                </div>
            </div>

            <!-- Contenu -->
            <div style='
                background:white;border:1px solid #E5E7EB;
                border-top:none;border-radius:0 0 8px 8px;
                padding:14px 16px;
            '>
                <!-- Message motivation -->
                <div style='
                    background:#F0F7FF;
                    border-left:3px solid #2563EB;
                    padding:10px 12px;border-radius:0 6px 6px 0;
                    font-size:0.85rem;color:#1E293B;
                    margin-bottom:14px;line-height:1.5;
                '>{$message}</div>

                <!-- Ressources recommandées -->
                <div style='
                    font-size:0.72rem;font-weight:600;
                    text-transform:uppercase;letter-spacing:1px;
                    color:#6B7280;margin-bottom:8px;
                '>📚 Recommandé pour vous</div>

                {$ressources_html}

                <!-- Indicateur -->
                <div style='
                    margin-top:10px;padding-top:10px;
                    border-top:1px solid #F3F4F6;
                    display:flex;align-items:center;gap:6px;
                '>
                    <div style='
                        width:8px;height:8px;border-radius:50%;
                        background:{$color};
                    '></div>
                    <span style='font-size:0.72rem;color:#9CA3AF;'>
                        {$label}
                    </span>
                </div>
            </div>
        </div>";
    }

    // ── Vue Enseignant ──
    private function render_teacher_view() {
        global $DB, $COURSE, $CFG;

        // Compter les étudiants à risque
        $critiques = $DB->count_records_select(
            'block_dropguard_results',
            "courseid = ? AND niveau_risque = 'critique'",
            [$COURSE->id]
        );
        $moderes = $DB->count_records_select(
            'block_dropguard_results',
            "courseid = ? AND niveau_risque = 'modere'",
            [$COURSE->id]
        );

        $report_url = new moodle_url(
            '/blocks/dropguard/dropguard_report.php',
            ['courseid' => $COURSE->id]
        );

        $html = "
        <div style='
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            padding: 0;
        '>
            <!-- Header -->
            <div style='
                background: linear-gradient(135deg, #1E3A5F, #2563EB);
                color: white;
                padding: 14px 16px;
                border-radius: 8px 8px 0 0;
                display: flex;
                align-items: center;
                gap: 8px;
            '>
                <span style='font-size:1.2rem;'>🛡️</span>
                <div>
                    <div style='font-weight:700;font-size:0.95rem;'>DropGuard</div>
                    <div style='font-size:0.72rem;opacity:0.8;'>Vue Enseignant</div>
                </div>
            </div>

            <!-- Stats -->
            <div style='
                background:white;
                border:1px solid #E5E7EB;
                border-top:none;
                border-radius:0 0 8px 8px;
                padding:14px 16px;
            '>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;'>
                    <div style='
                        background:#FEF2F2;
                        border:1px solid #FECACA;
                        border-radius:8px;
                        padding:10px;
                        text-align:center;
                    '>
                        <div style='font-size:1.5rem;font-weight:700;color:#DC2626;'>{$critiques}</div>
                        <div style='font-size:0.72rem;color:#DC2626;font-weight:600;'>Critiques</div>
                    </div>
                    <div style='
                        background:#FFFBEB;
                        border:1px solid #FDE68A;
                        border-radius:8px;
                        padding:10px;
                        text-align:center;
                    '>
                        <div style='font-size:1.5rem;font-weight:700;color:#D97706;'>{$moderes}</div>
                        <div style='font-size:0.72rem;color:#D97706;font-weight:600;'>Modérés</div>
                    </div>
                </div>

                <!-- Bouton rapport -->
                <a href='{$report_url}' style='
                    display:block;
                    background:#2563EB;
                    color:white;
                    text-align:center;
                    padding:8px;
                    border-radius:6px;
                    font-size:0.85rem;
                    font-weight:600;
                    text-decoration:none;
                '>
                    Voir le rapport complet →
                </a>
            </div>
        </div>";

        return $html;
    }

    // ── Pas encore de données ──
    private function render_no_data_student() {
        return "
        <div style='
            font-family:-apple-system,sans-serif;
            padding:16px;
            background:white;
            border:1px solid #E5E7EB;
            border-radius:8px;
            text-align:center;
            color:#6B7280;
            font-size:0.85rem;
        '>
            🛡️ <strong style='color:#1E293B;'>DropGuard</strong><br><br>
            Votre suivi personnalisé sera disponible<br>
            après 4 semaines de cours.
        </div>";
    }

    // Instance unique par cours
    public function instance_allow_multiple() {
        return false;
    }

    // Pas de configuration requise
    public function has_config() {
        return true;
    }
}