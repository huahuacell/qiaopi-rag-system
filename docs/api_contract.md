# API Contract

合同版本：`1.0`

冻结日期：`2026-06-18`

Base URL：`http://localhost:8000`

交互文档：`http://localhost:8000/docs`

本合同描述当前真实运行的 API，而不是未来目标。技术完成度和页面接入情况见 `docs/technology_acceptance_matrix.md`。

## 1. 字段冻结规则

从合同版本 `1.0` 起：

- 已记录的请求和响应字段不得直接重命名或删除。
- 字段类型、是否必填、取值语义和状态码发生变化，均视为合同变更。
- 新增可选字段属于兼容性变更，但仍须先更新本文档和契约测试。
- 新增必填字段、删除字段或修改字段类型属于破坏性变更，必须升级合同主版本。
- 合同变化必须同步更新后端 Schema、`backend/tests/test_api_contract.py`、前端 API 封装、页面、mock 和测试。
- 客户端不得依赖未写入本合同的额外字段。当前 Pydantic 可能忽略额外请求字段，但这不代表这些字段受到支持。

当前前端风格转换页面发送的 `top_k`、`expansion_mode`、`dry_run` 不属于 `StyleTransferRequest`，后端目前忽略它们。正式支持前不得把它们视为有效参数。

## 2. 当前实现边界

| 接口能力 | 当前真实实现 |
|---|---|
| 看板 | SQLite 聚合查询 |
| 关键词检索 | SQLite FTS5/BM25 排序、Jieba 分词、别名扩展、记录去重和条件过滤 |
| 语义检索 | 暂时复用关键词检索，不是向量检索 |
| 混合检索 | 暂时复用关键词检索，没有 BM25/向量融合 |
| 相似推荐 | 根据来源地、关系、主题拼接查询后执行 FTS5，不是向量近邻 |
| 记录、实体、证据 | 读取 SQLite 真实数据 |
| 白话释读 | 优先读取数据库 `rag_summary_text`，没有调用 Qwen |
| 风格转换 | 确定性模板加 SQLite 风格证据检索，没有调用 Qwen |

搜索响应中的 `score` 当前是根据结果位置生成的归一化展示分数，不是原始 BM25 分数，也不是向量相似度。不得在前端标记为真实语义相似度。

## 3. 通用对象

### ChartItem

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `label` | string | 是 | 分组标签 |
| `value` | integer | 是 | 数量 |

### EvidenceItem

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source_field` | string | 是 | 来源字段或检索单元类型 |
| `source_text` | string | 是 | 证据原文 |
| `reason` | string | 是 | 证据类型或命中原因 |
| `similarity_score` | number | 是 | `0.0` 至 `1.0`；当前部分接口为展示分数或固定值 |

### EntityItem

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `entity_type` | string | 是 | 如 `person`、`place`、`kinship`、`money`、`date`、`style_formula` |
| `value` | string | 是 | 规范化值优先，否则使用原始实体文本 |
| `source_text` | string | 是 | 原始实体文本 |
| `confidence` | number | 是 | `0.0` 至 `1.0` |

### EvidenceMappingItem

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `target_span` | string | 是 | 目标片段标签 |
| `source_field` | string | 是 | 来源字段 |
| `source_text` | string | 是 | 来源证据 |
| `reason` | string | 是 | 映射理由 |
| `similarity_score` | number | 是 | `0.0` 至 `1.0` |

### ConsistencyCheck

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `status` | string | 是 | 当前可能为 `passed`、`pending` 或 `failed` |
| `warnings` | string[] | 是 | 警告列表 |
| `passed_rules` | string[] | 是 | 通过规则 |
| `failed_rules` | string[] | 是 | 失败规则 |

## 4. 接口总览

| 方法 | 路径 | 请求模型 | 200 响应模型 | 当前前端页面 |
|---|---|---|---|---|
| GET | `/api/health` | 无 | `HealthResponse` | 未接 |
| GET | `/api/dashboard/stats` | 无 | `DashboardStatsResponse` | `/dashboard`、`/analysis` |
| GET | `/api/dashboard/distributions` | 无 | `DashboardDistributionsResponse` | `/dashboard`、`/analysis` |
| POST | `/api/search/keyword` | `SearchRequest` | `SearchResponse` | `/search` |
| POST | `/api/search/semantic` | `SearchRequest` | `SearchResponse` | `/search` |
| POST | `/api/search/hybrid` | `SearchRequest` | `SearchResponse` | `/search` |
| GET | `/api/records/{record_id}` | 路径参数 | `RecordDetailResponse` | `/records/:recordId` |
| GET | `/api/records/{record_id}/entities` | 路径参数 | `EntityResponse` | `/records/:recordId` |
| GET | `/api/records/{record_id}/evidence` | 路径参数 | `EvidenceResponse` | `/records/:recordId` |
| GET | `/api/records/{record_id}/similar` | 路径参数 | `SearchResponse` | 未接 |
| POST | `/api/generation/plain-interpretation` | `PlainInterpretationRequest` | `PlainInterpretationResponse` | `/plain-interpretation` |
| POST | `/api/generation/style-transfer` | `StyleTransferRequest` | `StyleTransferResponse` | `/style-transfer` |

## 5. 健康检查

### GET `/api/health`

响应字段：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `status` | string | 是 |
| `version` | string | 是 |
| `message` | string | 是 |

当前响应：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "message": "Qiaopi RAG backend is running"
}
```

## 6. 数据看板

### GET `/api/dashboard/stats`

`DashboardStatsResponse` 字段：

| 字段 | 类型 | 必填 | 数据来源 |
|---|---|---:|---|
| `total_records` | integer | 是 | `qiaopi_metadata_records` |
| `text_records` | integer | 是 | `qiaopi_text_records` |
| `origin_places` | `ChartItem[]` | 是 | 元数据来源地聚合 |
| `destination_places` | `ChartItem[]` | 是 | 元数据目的地聚合 |
| `kinship_distribution` | `ChartItem[]` | 是 | 实体表亲属聚合 |
| `money_distribution` | `ChartItem[]` | 是 | 金额提及聚合 |
| `timeline` | `ChartItem[]` | 是 | 元数据年代聚合 |

当前数据库基线：

```json
{
  "total_records": 50064,
  "text_records": 213
}
```

分布数组内容随数据库变化，不能把具体标签和数量视为冻结字段。

### GET `/api/dashboard/distributions`

`DashboardDistributionsResponse` 字段：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `top_places` | `ChartItem[]` | 是 |
| `relationship_distribution` | `ChartItem[]` | 是 |
| `year_distribution` | `ChartItem[]` | 是 |

## 7. 检索

### SearchRequest

适用于 `/keyword`、`/semantic`、`/hybrid`。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `query` | string | 否 | `""` | 查询文本 |
| `filters` | object | 否 | `{}` | 值为 string 或 null 的过滤条件 |
| `page` | integer | 否 | `1` | 最小值 `1` |
| `page_size` | integer | 否 | `10` | `1` 至 `100` |
| `top_k` | integer/null | 否 | `null` | `1` 至 `100`；存在时覆盖 `page_size` |
| `expansion_mode` | string/null | 否 | `null` | 已冻结为兼容字段，当前后端不使用 |

当前明确处理的过滤字段：

- `origin_place`
- `destination_place`
- `kinship`

其他字段会尝试对同名结果字段进行字符串包含匹配，但在正式写入合同前不视为稳定过滤能力。

请求示例：

```json
{
  "query": "八元 母亲 新加坡",
  "filters": {
    "origin_place": "新加坡",
    "kinship": "母亲"
  },
  "top_k": 10,
  "expansion_mode": "balanced"
}
```

### SearchResponse

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `mode` | string | 是 | `keyword`、`semantic`、`hybrid` 或 `similar` |
| `query` | string | 是 | 原查询；相似推荐返回记录 ID |
| `total` | integer | 是 | 过滤和记录去重后的总记录数 |
| `results` | `SearchResult[]` | 是 | 当前页结果 |

### SearchResult

| 字段 | 类型 | 必填 |
|---|---|---:|
| `record_id` | string | 是 |
| `title` | string | 是 |
| `origin_place` | string | 是 |
| `destination_place` | string | 是 |
| `date` | string | 是 |
| `sender` | string | 是 |
| `recipient` | string | 是 |
| `kinship` | string | 是 |
| `money` | string | 是 |
| `snippet` | string | 是 |
| `score` | number | 是 |
| `evidence` | `EvidenceItem[]` | 是 |

### POST `/api/search/keyword`

- `mode` 固定为 `keyword`。
- 当前使用 SQLite FTS5/BM25 排序。
- 响应展示分数不是原始 BM25 rank。

### POST `/api/search/semantic`

- `mode` 固定为 `semantic`。
- 当前仍使用与关键词接口相同的 FTS5 检索。
- 在向量查询真正接入前，前端不得把 `score` 描述为向量相似度。

### POST `/api/search/hybrid`

- `mode` 固定为 `hybrid`。
- 当前仍使用 FTS5 结果，没有 BM25 与向量融合。

### GET `/api/records/{record_id}/similar`

- `mode` 固定为 `similar`。
- `query` 返回传入的 `record_id`。
- 当前使用记录来源地、关系和主题构造 FTS5 查询。
- 当前前端未调用此接口。

## 8. 记录详情、实体和证据

### GET `/api/records/{record_id}`

`RecordDetailResponse` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `record_id` | string | 是 | 记录 ID |
| `title` | string | 是 | 标题或记录 ID |
| `metadata` | object[string,string] | 是 | 动态元数据字典 |
| `original_text` | string | 是 | 当前优先使用 `body_clean` |
| `normalized_text` | string | 是 | 当前优先使用 `rag_summary_text` |
| `entities` | `EntityItem[]` | 是 | 去重后的实体 |
| `evidence` | `EvidenceItem[]` | 是 | 数据库证据片段 |

记录不存在时返回：

```json
{
  "detail": "Record not found"
}
```

状态码为 `404`。

### GET `/api/records/{record_id}/entities`

`EntityResponse`：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `record_id` | string | 是 |
| `entities` | `EntityItem[]` | 是 |

记录不存在时返回 `404`。

### GET `/api/records/{record_id}/evidence`

`EvidenceResponse`：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `record_id` | string | 是 |
| `evidence` | `EvidenceItem[]` | 是 |

记录不存在时返回 `404`。

## 9. 白话释读

### POST `/api/generation/plain-interpretation`

`PlainInterpretationRequest`：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `record_id` | string/null | 否 | `null` |
| `original_text` | string/null | 否 | `null` |

处理规则：

1. 找到 `record_id` 时，读取数据库摘要、元数据、槽位和证据。
2. 未找到记录但提供 `original_text` 时，当前原样返回用户输入并标记 `pending`。
3. 当前不会调用 Qwen。

`PlainInterpretationResponse`：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `record_id` | string/null | 是 |
| `generated_text` | string | 是 |
| `summary` | string[] | 是 |
| `slots` | object[string,string] | 是 |
| `evidence` | `EvidenceItem[]` | 是 |
| `evidence_mapping` | `EvidenceMappingItem[]` | 是 |
| `consistency_check` | `ConsistencyCheck` | 是 |

## 10. 风格转换

### POST `/api/generation/style-transfer`

`StyleTransferRequest`：

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---:|---|
| `plain_text` | string | 是 | 无 |
| `slots` | object[string,string] | 否 | `{}` |

当前支持的槽位约定：

- `recipient`
- `origin_place`
- `money`
- `purpose`

处理规则：

1. 优先使用请求中的 `slots`。
2. 缺少槽位时从 `plain_text` 使用正则规则提取。
3. 使用确定性模板生成侨批体文本。
4. 使用 SQLite FTS5 检索最多三条风格证据。
5. 当前不会调用 Qwen。

`StyleTransferResponse`：

| 字段 | 类型 | 必填 |
|---|---|---:|
| `generated_text` | string | 是 |
| `summary` | string[] | 是 |
| `slots` | object[string,string] | 是 |
| `evidence` | `EvidenceItem[]` | 是 |
| `evidence_mapping` | `EvidenceMappingItem[]` | 是 |
| `consistency_check` | `ConsistencyCheck` | 是 |

## 11. 通用错误

| 状态码 | 场景 |
|---:|---|
| `404` | 记录详情、实体或证据接口找不到记录 |
| `422` | 请求体类型错误、缺少必填字段或数值超出 Pydantic 范围 |
| `500` | 未处理的数据库或服务异常 |

错误响应沿用 FastAPI 默认 `detail` 字段。当前没有统一业务错误码。

## 12. 契约验证

运行：

```bash
cd backend
python -m pytest -q
```

其中 `backend/tests/test_api_contract.py` 会验证：

- 12 个冻结路由及 HTTP 方法。
- 请求和响应模型的字段集合。
- 必填字段集合。

任何有意的合同变更都应先更新本文档，再更新测试快照和前端消费者。
