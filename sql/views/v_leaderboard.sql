WITH user_totals AS (
    SELECT *
    FROM `${project_id}.${analytics_dataset}.v_user_totals`
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY total_correct DESC, total_answers DESC, user_email ASC
    ) AS rank,
    user_email,
    display_name,
    total_correct,
    total_answers
FROM user_totals
ORDER BY rank
