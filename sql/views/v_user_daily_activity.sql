SELECT
    id_user,
    DATE(answered_at_local) AS activity_date,
    COUNT(*) AS total_answers,
    COUNTIF(is_correct) AS total_correct
FROM `${project_id}.${events_dataset}.answers`
GROUP BY id_user, activity_date
