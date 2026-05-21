<?php
// DropGuard — Déclaration des messages Moodle

defined('MOODLE_INTERNAL') || die();

$messageproviders = [
    'dropguard_alert' => [
        'defaults' => [
            'popup'  => MESSAGE_PERMITTED + MESSAGE_DEFAULT_ENABLED,
            'email'  => MESSAGE_PERMITTED + MESSAGE_DEFAULT_ENABLED,
        ],
    ],
];