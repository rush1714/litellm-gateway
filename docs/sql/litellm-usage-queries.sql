-- LiteLLM Proxy usage queries
-- Database: PostgreSQL
-- Main table: "LiteLLM_SpendLogs"
-- 注意：LiteLLM 的时间字段是大小写敏感的 camelCase 列名，PostgreSQL 中必须写成 "startTime"、"endTime"。

-- 1. 最近请求明细
SELECT
  request_id,
  "startTime",
  "endTime",
  model,
  model_group,
  "user",
  end_user,
  team_id,
  api_key,
  spend,
  prompt_tokens,
  completion_tokens,
  total_tokens
FROM "LiteLLM_SpendLogs"
ORDER BY "startTime" DESC
LIMIT 100;

-- 2. 总使用量
SELECT
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(prompt_tokens) AS total_prompt_tokens,
  SUM(completion_tokens) AS total_completion_tokens,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs";

-- 3. 按天统计使用量
SELECT
  DATE("startTime") AS day,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(prompt_tokens) AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY DATE("startTime")
ORDER BY day DESC;

-- 4. 今天使用量
SELECT
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(prompt_tokens) AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= CURRENT_DATE;

-- 5. 最近 7 天每天用量
SELECT
  DATE("startTime") AS day,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= NOW() - INTERVAL '7 days'
GROUP BY DATE("startTime")
ORDER BY day DESC;

-- 6. 按模型统计使用量
SELECT
  model,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(prompt_tokens) AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model
ORDER BY total_spend DESC;

-- 7. 按模型组统计使用量
SELECT
  model_group,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY model_group
ORDER BY total_spend DESC;

-- 8. 按用户统计使用量
SELECT
  "user",
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(prompt_tokens) AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY "user"
ORDER BY total_spend DESC;

-- 9. 按团队统计使用量
SELECT
  team_id,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY team_id
ORDER BY total_spend DESC;

-- 10. 按 API Key 统计使用量
SELECT
  api_key,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY api_key
ORDER BY total_spend DESC;

-- 10.1 按 API Key 前缀统计使用量，避免暴露完整 key
SELECT
  LEFT(api_key, 12) || '...' AS api_key_prefix,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY LEFT(api_key, 12)
ORDER BY total_spend DESC;

-- 11. 某个用户最近 30 天使用量
SELECT
  DATE("startTime") AS day,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
WHERE "user" = 'your-user-id'
  AND "startTime" >= NOW() - INTERVAL '30 days'
GROUP BY DATE("startTime")
ORDER BY day DESC;

-- 12. 某个模型最近 24 小时使用情况
SELECT
  DATE_TRUNC('hour', "startTime") AS hour,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
WHERE model = 'gpt-4o'
  AND "startTime" >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', "startTime")
ORDER BY hour DESC;

-- 13. 按模型查询平均延迟和 P95 延迟
SELECT
  model,
  COUNT(*) AS request_count,
  AVG(EXTRACT(EPOCH FROM ("endTime" - "startTime"))) AS avg_latency_seconds,
  PERCENTILE_CONT(0.95) WITHIN GROUP (
    ORDER BY EXTRACT(EPOCH FROM ("endTime" - "startTime"))
  ) AS p95_latency_seconds
FROM "LiteLLM_SpendLogs"
WHERE "startTime" IS NOT NULL
  AND "endTime" IS NOT NULL
GROUP BY model
ORDER BY avg_latency_seconds DESC;

-- 14. 最贵的 100 次请求
SELECT
  request_id,
  "startTime",
  model,
  "user",
  team_id,
  spend,
  prompt_tokens,
  completion_tokens,
  total_tokens
FROM "LiteLLM_SpendLogs"
ORDER BY spend DESC
LIMIT 100;

-- 15. 按小时统计请求量和花费
SELECT
  DATE_TRUNC('hour', "startTime") AS hour,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY DATE_TRUNC('hour', "startTime")
ORDER BY hour DESC;

-- 16. 缓存命中情况；仅在存在 cache_hit 字段时可用
SELECT
  cache_hit,
  COUNT(*) AS request_count,
  SUM(spend) AS total_spend,
  SUM(total_tokens) AS total_tokens
FROM "LiteLLM_SpendLogs"
GROUP BY cache_hit;

-- 17. 查看 LiteLLM_SpendLogs 表结构
SELECT
  column_name,
  data_type
FROM information_schema.columns
WHERE table_name = 'LiteLLM_SpendLogs'
ORDER BY ordinal_position;

-- 18. 最近 30 天综合报表：按天、模型、团队、用户统计
SELECT
  DATE("startTime") AS day,
  model,
  team_id,
  "user",
  COUNT(*) AS request_count,
  ROUND(SUM(spend)::numeric, 6) AS total_spend,
  SUM(prompt_tokens) AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens) AS total_tokens,
  ROUND(AVG(EXTRACT(EPOCH FROM ("endTime" - "startTime")))::numeric, 3) AS avg_latency_seconds
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= NOW() - INTERVAL '30 days'
GROUP BY
  DATE("startTime"),
  model,
  team_id,
  "user"
ORDER BY
  day DESC,
  total_spend DESC;
