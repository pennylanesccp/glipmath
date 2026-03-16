WITH normalized_answers AS (
    SELECT
        LOWER(TRIM(user_email)) AS user_email,
        COUNT(*) AS total_answers,
        COUNTIF(is_correct) AS total_correct
    FROM `${project_id}.${events_dataset}.answers`
    WHERE user_email IS NOT NULL
      AND TRIM(user_email) != ""
    GROUP BY LOWER(TRIM(user_email))
)
SELECT
    user_email,
    user_email AS display_name,
    total_correct,
    total_answers
FROM normalized_answers
