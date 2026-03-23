WITH normalized_answers AS (
    SELECT
        LOWER(TRIM(user_email)) AS user_email,
        COUNT(*) AS total_answers,
        COUNTIF(is_correct) AS total_correct
    FROM `${project_id}.${events_dataset}.answers`
    WHERE user_email IS NOT NULL
      AND TRIM(user_email) != ""
    GROUP BY LOWER(TRIM(user_email))
),
active_access AS (
    SELECT
        LOWER(TRIM(user_email)) AS user_email,
        LOWER(TRIM(role)) AS role,
        LOWER(TRIM(cohort_key)) AS cohort_key,
        COALESCE(NULLIF(TRIM(display_name), ''), LOWER(TRIM(user_email))) AS display_name
    FROM `${project_id}.${core_dataset}.user_access`
    WHERE is_active = TRUE
      AND user_email IS NOT NULL
      AND TRIM(user_email) != ""
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY LOWER(TRIM(user_email))
        ORDER BY updated_at_utc DESC NULLS LAST, created_at_utc DESC NULLS LAST
    ) = 1
)
SELECT
    normalized_answers.user_email,
    COALESCE(active_access.display_name, normalized_answers.user_email) AS display_name,
    active_access.role,
    active_access.cohort_key,
    normalized_answers.total_correct,
    normalized_answers.total_answers
FROM normalized_answers
LEFT JOIN active_access
  ON active_access.user_email = normalized_answers.user_email
