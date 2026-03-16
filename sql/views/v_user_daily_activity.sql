SELECT
    LOWER(TRIM(user_email)) AS user_email,
    DATE(answered_at_local) AS activity_date,
    COUNT(*) AS total_answers,
    COUNTIF(is_correct) AS total_correct
FROM `${project_id}.${events_dataset}.answers`
WHERE user_email IS NOT NULL
  AND TRIM(user_email) != ""
GROUP BY LOWER(TRIM(user_email)), DATE(answered_at_local)
