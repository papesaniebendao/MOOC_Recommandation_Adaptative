<?php
// DropGuard — Déclaration de la tâche cron

defined('MOODLE_INTERNAL') || die();

$tasks = [
    [
        'classname'  => '\block_dropguard\task\analyse_students',
        'blocking'   => 0,
        'minute'     => '0',
        'hour'       => '2',      // 2h du matin chaque nuit
        'day'        => '*',
        'month'      => '*',
        'dayofweek'  => '*',
        'disabled'   => 0,
    ],
];