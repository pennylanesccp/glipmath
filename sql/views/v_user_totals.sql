WITH active_users AS (
    SELECT
        id_user,
        LOWER(TRIM(email)) AS email,
        COALESCE(NULLIF(name, ""), LOWER(TRIM(email))) AS display_name
    FROM `${project_id}.${core_dataset}.whitelist`
    WHERE is_active = TRUE
),
answer_totals AS (
    SELECT
        id_user,
        COUNT(*) AS total_answers,
        COUNTIF(is_correct) AS total_correct
    FROM `${project_id}.${events_dataset}.answers`
    GROUP BY id_user
)
SELECT
    users.id_user,
    users.email,
    users.display_name,
    COALESCE(answer_totals.total_correct, 0) AS total_correct,
    COALESCE(answer_totals.total_answers, 0) AS total_answers
FROM active_users AS users
LEFT JOIN answer_totals
    ON users.id_user = answer_totals.id_user
