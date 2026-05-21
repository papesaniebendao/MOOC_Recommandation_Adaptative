<?php
// DropGuard — Tâche cron automatique v2.0
// Analyse nocturne : features cumulatives + récentes + tendance
// Recommandations de vraies ressources Moodle
// Human-in-the-loop : l'enseignant envoie les notifications depuis le rapport
// IRD / UGB Saint-Louis — 2026

namespace block_dropguard\task;

defined('MOODLE_INTERNAL') || die();

class analyse_students extends \core\task\scheduled_task {

    private $_student_firstname = 'Étudiant';

    public function get_name() {
        return 'DropGuard — Analyse nocturne des étudiants';
    }

    public function execute() {
        global $DB, $CFG;

        mtrace('DropGuard — Début analyse nocturne...');

        $config = $DB->get_record('block_dropguard_config', ['actif' => 1]);
        if (!$config) {
            mtrace('DropGuard — Pas de configuration active. Arrêt.');
            return;
        }

        $api_url = $config->api_url;

        $courses = $DB->get_records_sql("
            SELECT DISTINCT bi.parentcontextid, c.id as courseid, c.fullname
            FROM {block_instances} bi
            JOIN {context} ctx ON ctx.id = bi.parentcontextid
            JOIN {course} c ON c.id = ctx.instanceid
            WHERE bi.blockname = 'dropguard'
            AND ctx.contextlevel = 50
        ");

        $total_analyses  = 0;
        $total_critiques = 0;
        $total_ameliores = 0;

        foreach ($courses as $course_ctx) {
            $course_id = $course_ctx->courseid;
            mtrace("  Cours : {$course_ctx->fullname} (ID: {$course_id})");

            $students = $this->get_enrolled_students($course_id);
            mtrace("    Étudiants inscrits : " . count($students));

            foreach ($students as $student) {
                try {
                    $this->_student_firstname = $student->firstname;

                    // Vérifier période minimale d'observation (7 jours)
                    $enrol_time = $DB->get_field_sql("
                        SELECT MIN(ue.timecreated)
                        FROM {user_enrolments} ue
                        JOIN {enrol} e ON e.id = ue.enrolid
                        WHERE ue.userid = ? AND e.courseid = ?
                    ", [$student->id, $course_id]);

                    $jours_depuis = $enrol_time
                        ? round((time() - $enrol_time) / 86400) : 0;

                    if ($jours_depuis < 7) {
                        mtrace("    Étudiant {$student->id} — Phase observation (J{$jours_depuis})");
                        continue;
                    }

                    $features = $this->compute_student_features(
                        $student->id,
                        $course_id,
                        $config->cutoff_days
                    );

                    $result = $this->call_dropguard_api($api_url, $features);

                    if ($result) {
                        $ancien = $DB->get_record('block_dropguard_results', [
                            'userid'   => $student->id,
                            'courseid' => $course_id,
                        ]);
                        $ancien_niveau = $ancien ? $ancien->niveau_risque : null;

                        $this->save_result($student->id, $course_id, $result);
                        $total_analyses++;

                        $nouveau_niveau = $result->niveau_risque;

                        // Logger les changements uniquement
                        // L'enseignant décide d'envoyer depuis le rapport (human-in-the-loop)
                        if ($ancien_niveau !== $nouveau_niveau) {
                            if ($nouveau_niveau === 'critique') {
                                $total_critiques++;
                                mtrace("    ⚠️  {$student->firstname} (id:{$student->id}) — NOUVEAU CRITIQUE — À traiter dans le rapport");
                            } else if ($ancien_niveau === 'critique') {
                                $total_ameliores++;
                                mtrace("    ✅ {$student->firstname} (id:{$student->id}) — Amélioration : {$ancien_niveau} -> {$nouveau_niveau}");
                            } else {
                                mtrace("    📊 {$student->firstname} (id:{$student->id}) — Changement : {$ancien_niveau} -> {$nouveau_niveau}");
                            }
                        }
                        // Aucun envoi automatique — l'enseignant agit depuis le rapport
                    }

                } catch (\Exception $e) {
                    mtrace("    Erreur étudiant {$student->id} : " . $e->getMessage());
                }
            }
        }

        mtrace("DropGuard — Analyse terminée.");
        mtrace("  Total analysés     : {$total_analyses}");
        mtrace("  Nouveaux critiques : {$total_critiques} — à traiter dans le rapport enseignant");
        mtrace("  Améliorés          : {$total_ameliores}");
    }

    // ── Récupérer les étudiants inscrits ──
    private function get_enrolled_students($course_id) {
        global $DB;

        return $DB->get_records_sql("
            SELECT DISTINCT u.id, u.firstname, u.lastname, u.email
            FROM {user} u
            JOIN {user_enrolments} ue ON ue.userid = u.id
            JOIN {enrol} e ON e.id = ue.enrolid
            WHERE e.courseid = ?
            AND e.status = 0
            AND ue.status = 0
            AND u.deleted = 0
            AND u.suspended = 0
        ", [$course_id]);
    }

    // ── Calculer les features d'un étudiant ──
    private function compute_student_features($user_id, $course_id, $cutoff_days) {
        global $DB;

        $enrol_time = $DB->get_field_sql("
            SELECT MIN(ue.timecreated)
            FROM {user_enrolments} ue
            JOIN {enrol} e ON e.id = ue.enrolid
            WHERE ue.userid = ? AND e.courseid = ?
        ", [$user_id, $course_id]);

        if (!$enrol_time) {
            $enrol_time = time() - ($cutoff_days * 86400);
        }

        $jours_depuis = round((time() - $enrol_time) / 86400);
        $recent_start = time() - (14 * 86400);

        $activity_types = [
            'forumng', 'quiz', 'oucontent', 'resource',
            'ouwiki', 'ouelluminate', 'homepage',
            'subpage', 'url', 'glossary'
        ];

        // ── FEATURES CUMULATIVES (J1 → Aujourd'hui) ──
        $logs_cumul = $DB->get_records_sql("
            SELECT id, component, action, timecreated
            FROM {logstore_standard_log}
            WHERE userid = ?
            AND courseid = ?
            AND timecreated >= ?
        ", [$user_id, $course_id, $enrol_time]);

        $total_clicks    = 0;
        $days_active     = [];
        $last_activity   = 0;
        $first_activity  = PHP_INT_MAX;
        $activity_counts = [];

        foreach ($activity_types as $type) {
            $activity_counts[$type] = 0;
        }

        foreach ($logs_cumul as $log) {
            $total_clicks++;
            $day = floor(($log->timecreated - $enrol_time) / 86400);
            $days_active[$day] = true;

            if ($log->timecreated > $last_activity) {
                $last_activity = $log->timecreated;
            }
            if ($log->timecreated < $first_activity) {
                $first_activity = $log->timecreated;
            }

            $component = str_replace('mod_', '', $log->component);
            if (isset($activity_counts[$component])) {
                $activity_counts[$component]++;
            }
        }

        $total_days_active  = count($days_active);
        $last_activity_day  = $last_activity > 0
            ? floor(($last_activity - $enrol_time) / 86400) : 0;
        $first_activity_day = $first_activity < PHP_INT_MAX
            ? floor(($first_activity - $enrol_time) / 86400) : 0;
        $total_span_days    = $last_activity_day - $first_activity_day;
        $avg_clicks_per_day = $total_days_active > 0
            ? $total_clicks / $total_days_active : 0.0;

        $jours_inactivite = $last_activity > 0
            ? round((time() - $last_activity) / 86400)
            : $jours_depuis;

        // ── FEATURES RÉCENTES (14 derniers jours) ──
        $logs_recent = $DB->get_records_sql("
            SELECT id, component, action, timecreated
            FROM {logstore_standard_log}
            WHERE userid = ?
            AND courseid = ?
            AND timecreated >= ?
        ", [$user_id, $course_id, $recent_start]);

        $clicks_recent      = 0;
        $days_active_recent = [];
        $activity_recent    = [];

        foreach ($activity_types as $type) {
            $activity_recent["{$type}_recent"] = 0;
        }

        foreach ($logs_recent as $log) {
            $clicks_recent++;
            $day = floor(($log->timecreated - $recent_start) / 86400);
            $days_active_recent[$day] = true;

            $component = str_replace('mod_', '', $log->component);
            if (isset($activity_recent["{$component}_recent"])) {
                $activity_recent["{$component}_recent"]++;
            }
        }

        $days_active_recent_count = count($days_active_recent);

        // ── FEATURES DÉRIVÉES ──
        $tendance_activite = $total_clicks > 0
            ? min(1.0, $clicks_recent / $total_clicks)
            : 0.0;

        // ── NOTES ET ÉVALUATIONS ──
        $grades = $DB->get_records_sql("
            SELECT gi.itemname, gg.finalgrade
            FROM {grade_grades} gg
            JOIN {grade_items} gi ON gi.id = gg.itemid
            WHERE gg.userid = ?
            AND gi.courseid = ?
            AND gg.finalgrade IS NOT NULL
        ", [$user_id, $course_id]);

        $scores        = array_map(fn($g) => (float)$g->finalgrade, $grades);
        $avg_score     = count($scores) > 0
            ? array_sum($scores) / count($scores) : 0.0;
        $num_submitted = count($scores);

        // ── ASSEMBLAGE FINAL ──
        return array_merge([
            'id_student'                => (int)    $user_id,
            'code_module'               => (string) 'MOODLE_' . $course_id,
            'code_presentation'         => (string) date('Y') . 'J',
            'prenom'                    => (string) $this->_student_firstname,
            'course_id'                 => (int)    $course_id,

            // Features cumulatives
            'total_clicks'              => (float) $total_clicks,
            'total_days_active'         => (float) $total_days_active,
            'avg_clicks_per_day'        => (float) $avg_clicks_per_day,
            'last_activity_day'         => (float) $last_activity_day,
            'total_span_days'           => (float) $total_span_days,
            'avg_score'                 => (float) $avg_score,
            'num_submitted_assessments' => (float) $num_submitted,
            'studied_credits'           => 60.0,

            // Features récentes (14 derniers jours)
            'clicks_recent'             => (float) $clicks_recent,
            'days_active_recent'        => (float) $days_active_recent_count,

            // Features dérivées
            'tendance_activite'         => (float) $tendance_activite,
            'jours_inactivite'          => (float) $jours_inactivite,
            'cutoff_day'                => (float) $jours_depuis,
        ], $activity_counts, $activity_recent);
    }

    // ── Appeler l'API DropGuard ──
    private function call_dropguard_api($api_url, $features) {
        $options = [
            'http' => [
                'method'        => 'POST',
                'header'        => 'Content-Type: application/json',
                'content'       => json_encode($features),
                'timeout'       => 30,
                'ignore_errors' => true,
            ]
        ];

        $context  = stream_context_create($options);
        $response = @file_get_contents(
            $api_url . '/predict', false, $context
        );

        if (!$response) {
            mtrace("    Erreur API : pas de réponse");
            return null;
        }

        $result = json_decode($response);
        if (!$result || !isset($result->dropout_score)) {
            mtrace("    Erreur API : réponse invalide — " . $response);
            return null;
        }

        return $result;
    }

    // ── Sauvegarder les résultats ──
    private function save_result($user_id, $course_id, $result) {
        global $DB;

        $existing = $DB->get_record('block_dropguard_results', [
            'userid'   => $user_id,
            'courseid' => $course_id,
        ]);

        $activites = $result->ressources ?? [];
        $links     = $result->ressources_links ?? [];

        $ressources_enrichies = [];
        if (!empty($links)) {
            foreach ($links as $link) {
                $ressources_enrichies[] = [
                    'name' => $link->name,
                    'url'  => $link->url,
                    'type' => $link->type,
                ];
            }
        } else {
            foreach ($activites as $act) {
                $ressources_enrichies[] = ['name' => $act, 'url' => '', 'type' => ''];
            }
        }

        $record = (object) [
            'userid'                 => $user_id,
            'courseid'               => $course_id,
            'dropout_score'          => $result->dropout_score,
            'niveau_risque'          => $result->niveau_risque,
            'cause_principale'       => $result->cause_principale,
            'cluster_id'             => $result->cluster_id ?? 0,
            'cluster_name'           => $result->cluster_name ?? '',
            'activites_recommandees' => json_encode($ressources_enrichies),
            'message_motivation'     => $result->message_motivation ?? '',
            'timemodified'           => time(),
        ];

        if ($existing) {
            $record->id = $existing->id;

            // Reset notification si niveau change
            if ($existing->niveau_risque !== $result->niveau_risque) {
                $record->notification_envoyee = 0;
            }
            // Reset hebdomadaire si notification envoyée depuis + 7 jours
            else if ($existing->notification_envoyee == 1) {
                $jours_depuis_notif = (time() - $existing->timemodified) / 86400;
                if ($jours_depuis_notif >= 7) {
                    $record->notification_envoyee = 0;
                    mtrace("    🔄 Reset notification hebdomadaire — étudiant {$user_id}");
                } else {
                    $record->notification_envoyee = $existing->notification_envoyee;
                }
            } else {
                $record->notification_envoyee = $existing->notification_envoyee;
            }

            $DB->update_record('block_dropguard_results', $record);
        }
    }
}