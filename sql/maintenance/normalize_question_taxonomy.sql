CREATE TEMP FUNCTION normalize_taxonomy_value(raw_value STRING)
RETURNS STRING
LANGUAGE js AS """
  if (raw_value === null) {
    return null;
  }

  const normalized = raw_value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/ +/g, ' ');

  return normalized === '' ? null : normalized;
""";

UPDATE `{{QUESTION_TABLE_ID}}`
SET
  subject = normalize_taxonomy_value(subject),
  topic = normalize_taxonomy_value(topic),
  updated_at_utc = CURRENT_TIMESTAMP()
WHERE
  IFNULL(subject, '') != IFNULL(normalize_taxonomy_value(subject), '')
  OR IFNULL(topic, '') != IFNULL(normalize_taxonomy_value(topic), '');
