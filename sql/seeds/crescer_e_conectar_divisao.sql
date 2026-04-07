-- Seed de questoes de divisao para o projeto Crescer e Conectar.
-- Reexecutavel: limpa apenas as questoes desse source/cohort antes de inserir.

DELETE FROM `ide-math-app.glipmath_core.question_bank`
WHERE source = 'crescer_e_conectar_divisao_v1'
  AND cohort_key = 'crescer_e_conectar';

INSERT INTO `ide-math-app.glipmath_core.question_bank`
(
  id_question,
  statement,
  correct_answer,
  wrong_answers,
  subject,
  topic,
  difficulty,
  source,
  cohort_key,
  is_active,
  created_at_utc,
  updated_at_utc
)
WITH source_rows AS (
  SELECT
    3001 AS id_question,
    'João tinha 12 figurinhas e quis guardar em 3 envelopes iguais. Quantas figurinhas ele colocou em cada envelope?' AS statement,
    '4' AS correct_alternative_text,
    '12 dividido por 3 é igual a 4.' AS correct_explanation,
    ['3', '5', '6'] AS wrong_alternative_texts,
    [
      'Se fossem 3 em cada envelope, teriamos 3 x 3 = 9 figurinhas.',
      'Se fossem 5 em cada envelope, teriamos 5 x 3 = 15 figurinhas.',
      'Se fossem 6 em cada envelope, teriamos 6 x 3 = 18 figurinhas.'
    ] AS wrong_explanations,
    'facil' AS difficulty
  UNION ALL
  SELECT
    3002,
    'Pedro ganhou 16 carrinhos e colocou em 4 prateleiras iguais. Quantos carrinhos ficaram em cada prateleira?',
    '4',
    '16 dividido por 4 é igual a 4.',
    ['3', '5', '6'],
    [
      'Se fossem 3 por prateleira, teriamos 3 x 4 = 12 carrinhos.',
      'Se fossem 5 por prateleira, teriamos 5 x 4 = 20 carrinhos.',
      'Se fossem 6 por prateleira, teriamos 6 x 4 = 24 carrinhos.'
    ],
    'facil'
  UNION ALL
  SELECT
    3003,
    'Um treinador separou 18 bolas de tênis em 6 cestos iguais. Quantas bolas ficaram em cada cesto?',
    '3',
    '18 dividido por 6 é igual a 3.',
    ['2', '4', '6'],
    [
      'Se fossem 2 por cesto, teriamos 2 x 6 = 12 bolas.',
      'Se fossem 4 por cesto, teriamos 4 x 6 = 24 bolas.',
      'Se fossem 6 por cesto, teriamos 6 x 6 = 36 bolas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3004,
    'Lucas tinha 20 peças de montar e dividiu em 5 caixas iguais. Quantas peças ficaram em cada caixa?',
    '4',
    '20 dividido por 5 é igual a 4.',
    ['3', '5', '6'],
    [
      'Se fossem 3 por caixa, teriamos 3 x 5 = 15 peças.',
      'Se fossem 5 por caixa, teriamos 5 x 5 = 25 peças.',
      'Se fossem 6 por caixa, teriamos 6 x 5 = 30 peças.'
    ],
    'facil'
  UNION ALL
  SELECT
    3005,
    'Um menino fez 24 gols de brincadeira em 6 partidas. Se ele fez a mesma quantidade em cada partida, quantos gols ele fez por partida?',
    '4',
    '24 dividido por 6 é igual a 4.',
    ['3', '5', '6'],
    [
      'Se fossem 3 por partida, teriamos 3 x 6 = 18 gols.',
      'Se fossem 5 por partida, teriamos 5 x 6 = 30 gols.',
      'Se fossem 6 por partida, teriamos 6 x 6 = 36 gols.'
    ],
    'facil'
  UNION ALL
  SELECT
    3006,
    'Caio comprou 28 adesivos e repartiu igualmente entre 4 pastas. Quantos adesivos ficaram em cada pasta?',
    '7',
    '28 dividido por 4 é igual a 7.',
    ['6', '8', '9'],
    [
      'Se fossem 6 por pasta, teriamos 6 x 4 = 24 adesivos.',
      'Se fossem 8 por pasta, teriamos 8 x 4 = 32 adesivos.',
      'Se fossem 9 por pasta, teriamos 9 x 4 = 36 adesivos.'
    ],
    'facil'
  UNION ALL
  SELECT
    3007,
    'Miguel separou 30 moedas de brinquedo em 5 saquinhos iguais. Quantas moedas ficaram em cada saquinho?',
    '6',
    '30 dividido por 5 é igual a 6.',
    ['5', '7', '10'],
    [
      'Se fossem 5 por saquinho, teriamos 5 x 5 = 25 moedas.',
      'Se fossem 7 por saquinho, teriamos 7 x 5 = 35 moedas.',
      'Se fossem 10 por saquinho, teriamos 10 x 5 = 50 moedas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3008,
    'Um álbum tem 32 figurinhas para colocar em 8 páginas iguais. Quantas figurinhas vão em cada página?',
    '4',
    '32 dividido por 8 é igual a 4.',
    ['3', '5', '8'],
    [
      'Se fossem 3 por pagina, teriamos 3 x 8 = 24 figurinhas.',
      'Se fossem 5 por pagina, teriamos 5 x 8 = 40 figurinhas.',
      'Se fossem 8 por pagina, teriamos 8 x 8 = 64 figurinhas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3009,
    'Na escolinha, 36 cones foram organizados em 6 filas iguais para o treino. Quantos cones ficaram em cada fila?',
    '6',
    '36 dividido por 6 é igual a 6.',
    ['5', '7', '8'],
    [
      'Se fossem 5 por fila, teriamos 5 x 6 = 30 cones.',
      'Se fossem 7 por fila, teriamos 7 x 6 = 42 cones.',
      'Se fossem 8 por fila, teriamos 8 x 6 = 48 cones.'
    ],
    'facil'
  UNION ALL
  SELECT
    3010,
    'Arthur tinha 40 cartas e quis dividir igualmente entre 5 amigos. Quantas cartas cada amigo recebeu?',
    '8',
    '40 dividido por 5 é igual a 8.',
    ['6', '7', '10'],
    [
      'Se fossem 6 para cada amigo, teriamos 6 x 5 = 30 cartas.',
      'Se fossem 7 para cada amigo, teriamos 7 x 5 = 35 cartas.',
      'Se fossem 10 para cada amigo, teriamos 10 x 5 = 50 cartas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3011,
    'Um pacote tinha 42 balas. Essas balas foram divididas igualmente entre 6 crianças. Com quantas balas cada criança ficou?',
    '7',
    '42 dividido por 6 é igual a 7.',
    ['6', '8', '9'],
    [
      'Se fossem 6 para cada criança, teriamos 6 x 6 = 36 balas.',
      'Se fossem 8 para cada criança, teriamos 8 x 6 = 48 balas.',
      'Se fossem 9 para cada criança, teriamos 9 x 6 = 54 balas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3012,
    'Em um campeonato de videogame, havia 48 fichas para repartir igualmente em 8 rodadas. Quantas fichas ficaram para cada rodada?',
    '6',
    '48 dividido por 8 é igual a 6.',
    ['5', '7', '8'],
    [
      'Se fossem 5 por rodada, teriamos 5 x 8 = 40 fichas.',
      'Se fossem 7 por rodada, teriamos 7 x 8 = 56 fichas.',
      'Se fossem 8 por rodada, teriamos 8 x 8 = 64 fichas.'
    ],
    'facil'
  UNION ALL
  SELECT
    3013,
    'Um time treinou cobranças e chutou 54 bolas em 9 séries iguais. Quantos chutes teve em cada série?',
    '6',
    '54 dividido por 9 é igual a 6.',
    ['5', '7', '9'],
    [
      'Se fossem 5 por serie, teriamos 5 x 9 = 45 chutes.',
      'Se fossem 7 por serie, teriamos 7 x 9 = 63 chutes.',
      'Se fossem 9 por serie, teriamos 9 x 9 = 81 chutes.'
    ],
    'facil'
  UNION ALL
  SELECT
    3014,
    'Enzo tinha 56 bloquinhos e montou 7 torres com a mesma quantidade. Quantos bloquinhos foram usados em cada torre?',
    '8',
    '56 dividido por 7 é igual a 8.',
    ['6', '7', '9'],
    [
      'Se fossem 6 por torre, teriamos 6 x 7 = 42 bloquinhos.',
      'Se fossem 7 por torre, teriamos 7 x 7 = 49 bloquinhos.',
      'Se fossem 9 por torre, teriamos 9 x 7 = 63 bloquinhos.'
    ],
    'facil'
  UNION ALL
  SELECT
    3015,
    'Rafael tinha 18 figurinhas e ganhou mais 6 do irmão. Depois, dividiu tudo igualmente em 4 montinhos. Quantas figurinhas ficaram em cada montinho?',
    '6',
    'Primeiro somamos 18 + 6 = 24. Depois, 24 dividido por 4 é igual a 6.',
    ['4', '5', '8'],
    [
      '24 dividido por 4 nao é 4.',
      'Se fossem 5 por montinho, teriamos 5 x 4 = 20 figurinhas.',
      'Se fossem 8 por montinho, teriamos 8 x 4 = 32 figurinhas.'
    ],
    'media'
  UNION ALL
  SELECT
    3016,
    'No treino de futebol, havia 35 coletes, mas 5 estavam rasgados e não puderam ser usados. Os que sobraram foram divididos igualmente entre 5 times. Quantos coletes cada time recebeu?',
    '6',
    'Primeiro fazemos 35 - 5 = 30. Depois, 30 dividido por 5 é igual a 6.',
    ['5', '7', '8'],
    [
      'Se fossem 5 por time, teriamos 5 x 5 = 25 coletes.',
      'Se fossem 7 por time, teriamos 7 x 5 = 35 coletes.',
      'Se fossem 8 por time, teriamos 8 x 5 = 40 coletes.'
    ],
    'media'
  UNION ALL
  SELECT
    3017,
    'Davi juntou 24 peças de LEGO e depois encontrou mais 12 no chão. Ele resolveu guardar tudo em 6 caixas iguais. Quantas peças ficaram em cada caixa?',
    '6',
    'Primeiro somamos 24 + 12 = 36. Depois, 36 dividido por 6 é igual a 6.',
    ['4', '5', '8'],
    [
      '36 dividido por 6 nao é 4.',
      'Se fossem 5 por caixa, teriamos 5 x 6 = 30 peças.',
      'Se fossem 8 por caixa, teriamos 8 x 6 = 48 peças.'
    ],
    'media'
  UNION ALL
  SELECT
    3018,
    'Um menino tinha 50 cromos, mas deu 10 para o primo. Depois, separou o restante igualmente em 5 envelopes. Quantos cromos ficaram em cada envelope?',
    '8',
    'Primeiro fazemos 50 - 10 = 40. Depois, 40 dividido por 5 é igual a 8.',
    ['6', '7', '10'],
    [
      'Se fossem 6 por envelope, teriamos 6 x 5 = 30 cromos.',
      'Se fossem 7 por envelope, teriamos 7 x 5 = 35 cromos.',
      'Se fossem 10 por envelope, teriamos 10 x 5 = 50 cromos.'
    ],
    'media'
  UNION ALL
  SELECT
    3019,
    'Na festa, chegaram 27 brigadeiros e depois colocaram mais 9 na mesa. No final, eles foram divididos igualmente entre 6 crianças. Quantos brigadeiros cada criança recebeu?',
    '6',
    'Primeiro somamos 27 + 9 = 36. Depois, 36 dividido por 6 é igual a 6.',
    ['5', '7', '9'],
    [
      'Se fossem 5 para cada criança, teriamos 5 x 6 = 30 brigadeiros.',
      'Se fossem 7 para cada criança, teriamos 7 x 6 = 42 brigadeiros.',
      'Se fossem 9 para cada criança, teriamos 9 x 6 = 54 brigadeiros.'
    ],
    'media'
  UNION ALL
  SELECT
    3020,
    'Henrique tinha 64 bolinhas de gude, mas perdeu 8 durante a brincadeira. Depois, guardou o que sobrou em 7 saquinhos iguais. Quantas bolinhas ficaram em cada saquinho?',
    '8',
    'Primeiro fazemos 64 - 8 = 56. Depois, 56 dividido por 7 é igual a 8.',
    ['6', '7', '9'],
    [
      'Se fossem 6 por saquinho, teriamos 6 x 7 = 42 bolinhas.',
      'Se fossem 7 por saquinho, teriamos 7 x 7 = 49 bolinhas.',
      'Se fossem 9 por saquinho, teriamos 9 x 7 = 63 bolinhas.'
    ],
    'media'
  UNION ALL
  SELECT
    3021,
    'Um treinador levou 72 bolas para um torneio. Antes do jogo, ele separou essas bolas igualmente em 8 carrinhos. Quantas bolas foram colocadas em cada carrinho?',
    '9',
    '72 dividido por 8 é igual a 9.',
    ['8', '10', '12'],
    [
      'Se fossem 8 por carrinho, teriamos 8 x 8 = 64 bolas.',
      'Se fossem 10 por carrinho, teriamos 10 x 8 = 80 bolas.',
      'Se fossem 12 por carrinho, teriamos 12 x 8 = 96 bolas.'
    ],
    'media'
  UNION ALL
  SELECT
    3022,
    'Guilherme tinha 45 cartas raras e ganhou mais 15 em uma troca. Depois, repartiu tudo igualmente entre 6 pastas. Quantas cartas ficaram em cada pasta?',
    '10',
    'Primeiro somamos 45 + 15 = 60. Depois, 60 dividido por 6 é igual a 10.',
    ['8', '9', '12'],
    [
      'Se fossem 8 por pasta, teriamos 8 x 6 = 48 cartas.',
      'Se fossem 9 por pasta, teriamos 9 x 6 = 54 cartas.',
      'Se fossem 12 por pasta, teriamos 12 x 6 = 72 cartas.'
    ],
    'media'
  UNION ALL
  SELECT
    3023,
    'Em uma brincadeira, havia 84 pontos para repartir igualmente entre 7 fases do jogo. Quantos pontos ficaram para cada fase?',
    '12',
    '84 dividido por 7 é igual a 12.',
    ['10', '11', '14'],
    [
      'Se fossem 10 por fase, teriamos 10 x 7 = 70 pontos.',
      'Se fossem 11 por fase, teriamos 11 x 7 = 77 pontos.',
      'Se fossem 14 por fase, teriamos 14 x 7 = 98 pontos.'
    ],
    'media'
  UNION ALL
  SELECT
    3024,
    'Um menino juntou 63 moedas no cofrinho. Depois, comprou um chaveiro por 7 moedas e resolveu dividir o restante igualmente entre 7 saquinhos. Quantas moedas ficaram em cada saquinho?',
    '8',
    'Primeiro fazemos 63 - 7 = 56. Depois, 56 dividido por 7 é igual a 8.',
    ['7', '9', '10'],
    [
      'Se fossem 7 por saquinho, teriamos 7 x 7 = 49 moedas.',
      'Se fossem 9 por saquinho, teriamos 9 x 7 = 63 moedas.',
      'Se fossem 10 por saquinho, teriamos 10 x 7 = 70 moedas.'
    ],
    'media'
  UNION ALL
  SELECT
    3025,
    'Mateus tinha 36 figurinhas do campeonato e seu amigo deu mais 18. Depois, ele perdeu 6 figurinhas repetidas. Com o que sobrou, fez 6 montinhos iguais. Quantas figurinhas ficaram em cada montinho?',
    '8',
    'Primeiro fazemos 36 + 18 = 54. Depois, 54 - 6 = 48. Por fim, 48 dividido por 6 é igual a 8.',
    ['6', '7', '9'],
    [
      'Se fossem 6 por montinho, teriamos 6 x 6 = 36 figurinhas.',
      'Se fossem 7 por montinho, teriamos 7 x 6 = 42 figurinhas.',
      'Se fossem 9 por montinho, teriamos 9 x 6 = 54 figurinhas.'
    ],
    'desafio_leve'
  UNION ALL
  SELECT
    3026,
    'No videogame, Pedro ganhou 48 moedas, depois ganhou mais 24 numa fase bônus. Antes de guardar, ele gastou 12 moedas. O restante foi dividido igualmente entre 6 baús. Quantas moedas ficaram em cada baú?',
    '10',
    'Primeiro fazemos 48 + 24 = 72. Depois, 72 - 12 = 60. Por fim, 60 dividido por 6 é igual a 10.',
    ['8', '9', '12'],
    [
      'Se fossem 8 por bau, teriamos 8 x 6 = 48 moedas.',
      'Se fossem 9 por bau, teriamos 9 x 6 = 54 moedas.',
      'Se fossem 12 por bau, teriamos 12 x 6 = 72 moedas.'
    ],
    'desafio_leve'
  UNION ALL
  SELECT
    3027,
    'Um professor levou 70 lápis para a sala, mas 14 ficaram na mochila e não foram usados. Os outros foram divididos igualmente entre 8 alunos. Quantos lápis cada aluno recebeu?',
    '7',
    'Primeiro fazemos 70 - 14 = 56. Depois, 56 dividido por 8 é igual a 7.',
    ['6', '8', '9'],
    [
      'Se fossem 6 por aluno, teriamos 6 x 8 = 48 lapis.',
      'Se fossem 8 por aluno, teriamos 8 x 8 = 64 lapis.',
      'Se fossem 9 por aluno, teriamos 9 x 8 = 72 lapis.'
    ],
    'desafio_leve'
  UNION ALL
  SELECT
    3028,
    'Um time infantil tinha 49 camisetas para separar entre 7 gavetas iguais. Depois de colocar a mesma quantidade em cada gaveta, quantas camisetas ficaram em cada uma?',
    '7',
    '49 dividido por 7 é igual a 7.',
    ['6', '8', '9'],
    [
      'Se fossem 6 por gaveta, teriamos 6 x 7 = 42 camisetas.',
      'Se fossem 8 por gaveta, teriamos 8 x 7 = 56 camisetas.',
      'Se fossem 9 por gaveta, teriamos 9 x 7 = 63 camisetas.'
    ],
    'desafio_leve'
)
SELECT
  id_question,
  statement,
  STRUCT(
    correct_alternative_text AS alternative_text,
    correct_explanation AS explanation
  ) AS correct_answer,
  ARRAY(
    SELECT AS STRUCT
      wrong_alternative_texts[OFFSET(pos)] AS alternative_text,
      wrong_explanations[OFFSET(pos)] AS explanation
    FROM UNNEST(GENERATE_ARRAY(0, ARRAY_LENGTH(wrong_alternative_texts) - 1)) AS pos
  ) AS wrong_answers,
  'Matematica' AS subject,
  'divisao' AS topic,
  difficulty,
  'crescer_e_conectar_divisao_v1' AS source,
  'crescer_e_conectar' AS cohort_key,
  TRUE AS is_active,
  CURRENT_TIMESTAMP() AS created_at_utc,
  CURRENT_TIMESTAMP() AS updated_at_utc
FROM source_rows;
