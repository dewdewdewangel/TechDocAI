# TechDoc AI 智能技术文档问答系统改造计划

## 1. 项目目标

将当前的 FastAPI 全栈模板改造成一个面向技术资料、项目文档、接口文档、论文资料和内部知识库的智能问答系统。

系统需要支持用户上传技术文档，自动解析文档内容，构建可检索知识库，并通过大模型实现基于文档内容的问答。

核心目标：

- 保留现有登录、注册、用户管理和权限体系。
- 替换模板示例业务，形成 TechDoc AI 自有业务模块。
- 支持文档上传、解析、切片、索引和检索。
- 支持基于 RAG 的智能问答。
- 在答案中展示引用来源，降低模型幻觉风险。
- 提供清晰的文档库、问答界面和系统仪表盘。

## 2. 当前项目基础

当前项目来自 FastAPI 全栈模板，已有较完整的基础能力：

- 后端：FastAPI、SQLModel、Pydantic、PostgreSQL、Alembic。
- 前端：React、TypeScript、Vite、TanStack Router、TanStack Query、shadcn/ui、Tailwind CSS。
- 认证：JWT 登录认证、用户注册、密码重置、管理员权限。
- 工程化：Docker Compose、OpenAPI 客户端生成、Pytest、Playwright。

这些能力可以继续保留，重点改造业务层。

## 3. 总体架构

推荐架构如下：

```text
用户
  |
  v
React 前端
  |
  v
FastAPI 后端
  |
  +--> PostgreSQL 业务数据库
  |
  +--> pgvector 向量检索
  |
  +--> 文档解析模块
  |
  +--> Embedding 模型
  |
  +--> 大语言模型 API
```

第一阶段建议使用 PostgreSQL + pgvector 作为向量存储，原因是当前项目已经依赖 PostgreSQL，部署和维护成本最低。

后续如果文档规模变大，可以扩展为：

- Qdrant
- Milvus
- Elasticsearch
- OpenSearch

### 3.1 MVP 模型选型

MVP 确定使用以下混合架构：

```text
问答模型：DeepSeek V4 Flash（云端 API）
向量模型：BGE-M3（本地 Ollama）
向量维度：1024
数据库：PostgreSQL + pgvector
```

选择原因：

- DeepSeek V4 Flash 提供较好的技术问答和中文表达质量。
- BGE-M3 参数量较小，适合低配电脑本地生成向量。
- 原始文档和全量向量保留在本地，仅检索命中的文档片段发送给 DeepSeek。
- PostgreSQL + pgvector 继续复用当前部署架构。

注意：BGE-M3 固定输出 1024 维向量，更换其他 Embedding 模型后必须执行数据库迁移并重新索引全部文档。

## 4. 核心模块规划

### 4.1 用户与权限模块

复用当前模板已有能力：

- 用户注册
- 用户登录
- JWT 鉴权
- 当前用户信息
- 管理员用户管理
- 普通用户数据隔离

改造重点：

- 页面文案改为 TechDoc AI。
- 权限逻辑应用到文档库和问答会话。
- 普通用户只能访问自己上传的文档和自己的问答记录。
- 管理员可以查看全局文档和用户使用情况。

### 4.2 文档库模块

文档库是系统的核心数据入口。

功能：

- 上传技术文档。
- 查看文档列表。
- 查看解析状态。
- 删除文档。
- 重新索引文档。
- 查看文档详情和切片数量。

首期支持格式：

- TXT
- Markdown
- PDF

第二阶段支持格式：

- DOCX
- HTML
- OpenAPI JSON / YAML
- 代码仓库 README 和 Markdown 文档集合

### 4.3 文档解析模块

处理流程：

```text
上传文件
  |
  v
保存原始文件
  |
  v
提取文本
  |
  v
清洗文本
  |
  v
文本切片
  |
  v
生成 embedding
  |
  v
保存切片和向量
```

切片策略：

- 按标题和段落优先切分。
- 单个 chunk 控制在合理 token 范围内。
- chunk 之间保留 overlap，避免上下文断裂。
- 保存页码、段落序号、原始文档 ID。

建议配置：

```text
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
```

### 4.4 向量检索模块

检索流程：

```text
用户问题
  |
  v
生成问题 embedding
  |
  v
向量相似度检索
  |
  v
获取 Top-K 文档切片
  |
  v
组织上下文
```

首期推荐使用 pgvector：

- 便于和现有 PostgreSQL 集成。
- 减少服务数量。
- 适合毕业设计、课程项目、中小型企业内部系统。

后期优化方向：

- 混合检索：关键词检索 + 向量检索。
- 重排序：rerank 模型提升召回质量。
- 文档级权限过滤。
- 多文档集合检索。

### 4.5 智能问答模块

问答流程：

```text
用户输入问题
  |
  v
检索相关文档切片
  |
  v
构造提示词
  |
  v
调用大语言模型
  |
  v
返回答案
  |
  v
展示引用来源
  |
  v
保存问答记录
```

回答要求：

- 优先依据上传文档回答。
- 不确定时明确说明无法从文档中确认。
- 返回引用来源，包括文档名、页码或片段序号。
- 支持多轮会话。

### 4.6 仪表盘模块

仪表盘用于展示系统概况。

普通用户视角：

- 我的文档总数。
- 已索引文档数。
- 最近上传文档。
- 最近问答记录。
- 本月问答次数。

管理员视角：

- 用户总数。
- 全站文档总数。
- 全站问答次数。
- 解析失败文档数。
- 最近活跃用户。

## 5. 数据模型规划

### 5.1 Document

用于保存文档元数据。

字段建议：

```text
id
title
filename
content_type
file_size
storage_path
status
error_message
chunk_count
owner_id
created_at
updated_at
```

状态枚举：

```text
uploaded
processing
indexed
failed
```

### 5.2 DocumentChunk

用于保存文档切片。

字段建议：

```text
id
document_id
content
page_number
chunk_index
token_count
embedding
created_at
```

如果第一阶段暂不接 pgvector，可以先保存 content 和 metadata，后续再补 embedding 字段。

### 5.3 ChatSession

用于保存问答会话。

字段建议：

```text
id
title
owner_id
created_at
updated_at
```

### 5.4 ChatMessage

用于保存问答消息。

字段建议：

```text
id
session_id
role
content
sources
created_at
```

role 可选值：

```text
user
assistant
system
```

sources 可以使用 JSON 字段保存引用来源。

## 6. 后端接口规划

### 6.1 文档接口

```text
POST   /api/v1/documents/upload
GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
POST   /api/v1/documents/{document_id}/reindex
GET    /api/v1/documents/{document_id}/chunks
```

### 6.2 问答接口

```text
POST /api/v1/chat/ask
GET  /api/v1/chat/sessions
POST /api/v1/chat/sessions
GET  /api/v1/chat/sessions/{session_id}
GET  /api/v1/chat/sessions/{session_id}/messages
DELETE /api/v1/chat/sessions/{session_id}
```

### 6.3 仪表盘接口

```text
GET /api/v1/dashboard/summary
GET /api/v1/dashboard/recent-documents
GET /api/v1/dashboard/recent-questions
```

## 7. 前端页面规划

### 7.1 侧边栏菜单

将当前模板菜单改为：

```text
仪表盘
文档库
智能问答
用户管理
设置
```

其中用户管理仅管理员可见。

### 7.2 仪表盘页面

展示：

- 文档统计。
- 问答统计。
- 解析状态统计。
- 最近文档。
- 最近问答。

### 7.3 文档库页面

核心组件：

- 上传按钮。
- 文档列表表格。
- 状态标签。
- 文档操作菜单。
- 删除确认弹窗。
- 重新索引按钮。

表格字段：

```text
文档名
类型
大小
状态
切片数
上传时间
操作
```

### 7.4 智能问答页面

布局建议：

```text
左侧：会话列表
中间：聊天消息
底部：输入框和发送按钮
右侧或答案下方：引用来源
```

核心交互：

- 新建会话。
- 输入问题。
- 展示模型回答。
- 展示引用片段。
- 支持继续追问。

### 7.5 设置页面

首期可以不做前端设置页，先通过 `.env` 配置模型。

后续可增加：

- 模型供应商。
- 模型名称。
- Embedding 模型。
- Top-K。
- Chunk Size。
- Chunk Overlap。

## 8. 环境变量规划

建议新增配置：

```text
LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
EMBEDDING_API_KEY=ollama
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDING_MODEL=bge-m3
EMBEDDING_BATCH_SIZE=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
RETRIEVAL_TOP_K=5
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=50
```

如使用 pgvector，还需要在数据库初始化或迁移中启用：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 9. 实施阶段

### 阶段一：项目品牌和结构改造

目标：让项目从模板形态变成 TechDoc AI 项目。

任务：

- 修改项目标题为 TechDoc AI。
- 修改登录页、仪表盘、侧边栏文案。
- 替换 FastAPI 模板 Logo 或改为文字 Logo。
- 将 Items 示例模块替换为 Documents 模块入口。
- 更新 README。

交付物：

- TechDoc AI 基础界面。
- 清理后的导航菜单。
- 项目说明文档。

### 阶段二：文档模型和上传接口

目标：实现文档上传和文档列表。

任务：

- 新增 Document 数据模型。
- 新增 Alembic 数据库迁移。
- 新增 documents 路由。
- 实现上传文件接口。
- 实现文档列表接口。
- 实现文档删除接口。
- 前端实现文档库页面。

交付物：

- 用户可以上传文档。
- 用户可以查看自己的文档列表。
- 用户可以删除文档。

### 阶段三：文档解析和切片

目标：把上传文档变成可检索文本块。

任务：

- 新增 DocumentChunk 数据模型。
- 实现 TXT 和 Markdown 解析。
- 实现 PDF 文本提取。
- 实现文本切片。
- 保存 chunk 到数据库。
- 展示文档解析状态和 chunk 数量。

交付物：

- 上传文档后自动解析。
- 文档状态从 uploaded 变为 indexed 或 failed。
- 数据库中保存文档切片。

### 阶段四：Embedding 和向量检索

目标：实现基于语义的文档检索。

任务：

- 集成 embedding 模型。
- 引入 pgvector。
- 为 DocumentChunk 增加 embedding 字段。
- 实现问题向量化。
- 实现 Top-K 检索。
- 支持按当前用户过滤文档。

交付物：

- 输入问题可以检索出相关文档片段。
- 检索结果包含文档名、页码和内容片段。

### 阶段五：RAG 智能问答

目标：实现真正的文档问答。

任务：

- 集成大语言模型 API。
- 设计 RAG prompt。
- 实现 `/chat/ask` 接口。
- 保存 ChatSession 和 ChatMessage。
- 返回答案和引用来源。
- 前端实现聊天页面。

交付物：

- 用户可以基于上传文档提问。
- 系统返回答案。
- 答案显示引用来源。

### 阶段六：体验优化和权限完善

目标：提升系统可用性和安全性。

任务：

- 上传大小限制。
- 文件类型校验。
- 文档解析失败提示。
- 问答加载状态。
- 空状态页面。
- 管理员统计视图。
- 权限测试。

交付物：

- 更稳定的文档处理流程。
- 更完整的用户体验。

### 阶段七：测试和部署文档

目标：保证项目可演示、可运行、可交付。

任务：

- 编写后端 API 测试。
- 编写前端关键流程测试。
- 更新 Docker Compose 配置。
- 更新 README。
- 增加本地启动说明。
- 增加部署说明。

交付物：

- 可本地运行的完整系统。
- 可用于演示和答辩的说明文档。

## 10. 推荐开发顺序

推荐按以下顺序执行：

```text
1. 项目品牌替换
2. 删除或替换 Items 示例模块
3. 新增 Document 模型
4. 实现文档上传接口
5. 实现文档库前端页面
6. 新增 DocumentChunk 模型
7. 实现文本解析和切片
8. 集成 embedding
9. 引入 pgvector
10. 实现检索接口
11. 实现 RAG 问答接口
12. 实现智能问答页面
13. 增加仪表盘统计
14. 完善测试和部署文档
```

## 11. MVP 范围

为了尽快形成可演示版本，建议 MVP 控制在以下范围：

- 登录和用户系统沿用模板。
- 支持 TXT、Markdown、PDF 三种文档。
- 支持文档上传、列表、删除。
- 支持文档解析和切片。
- 支持简单 embedding 检索。
- 支持单轮和多轮问答。
- 答案展示引用来源。
- 前端包含文档库和智能问答两个核心页面。

MVP 暂不做：

- 多知识库空间。
- 复杂权限组。
- 在线编辑文档。
- 文档版本管理。
- 企业级审计日志。
- 高级 rerank。
- 多模型可视化配置。

## 12. 技术风险和处理方案

### 12.1 文档解析质量不稳定

风险：

- PDF 可能存在扫描件。
- 表格和代码块结构可能丢失。

处理：

- 首期先支持文本型 PDF。
- 扫描件 OCR 放到后续阶段。
- 保存原始文件和解析错误信息。

### 12.2 大模型回答幻觉

风险：

- 模型可能编造文档中不存在的内容。

处理：

- Prompt 中要求仅基于上下文回答。
- 没有依据时要求明确说明无法确认。
- 每个答案返回引用来源。
- 前端展示引用片段。

### 12.3 向量检索召回不准

风险：

- 切片过大或过小都会影响检索效果。

处理：

- 保留 chunk size 和 overlap 配置。
- 后续加入关键词检索和 rerank。
- 支持重新索引。

### 12.4 部署复杂度上升

风险：

- 引入额外向量数据库会增加部署难度。

处理：

- 首期使用 PostgreSQL + pgvector。
- 后续再根据规模扩展专业向量数据库。

## 13. 初始里程碑

### 里程碑 1：系统改名和界面入口完成

结果：

- 页面显示 TechDoc AI。
- 侧边栏包含仪表盘、文档库、智能问答。
- 模板痕迹基本清除。

### 里程碑 2：文档库可用

结果：

- 用户可以上传文档。
- 用户可以查看文档列表。
- 文档状态可以展示。

### 里程碑 3：文档可解析和索引

结果：

- 文档可以被解析成 chunk。
- chunk 可以保存到数据库。
- 文档状态可以正确更新。

### 里程碑 4：问答闭环完成

结果：

- 用户可以提问。
- 系统可以检索相关文档。
- 大模型基于上下文回答。
- 答案带引用来源。

## 14. 第一批建议修改文件

优先修改：

```text
backend/app/models.py
backend/app/api/main.py
backend/app/api/routes/documents.py
backend/app/api/routes/chat.py
backend/app/core/config.py
frontend/src/components/Sidebar/AppSidebar.tsx
frontend/src/components/Common/Logo.tsx
frontend/src/routes/_layout/index.tsx
frontend/src/routes/_layout/documents.tsx
frontend/src/routes/_layout/chat.tsx
README.md
```

新增：

```text
backend/app/services/document_parser.py
backend/app/services/text_splitter.py
backend/app/services/embedding.py
backend/app/services/retrieval.py
backend/app/services/llm.py
```

后续根据实现进度新增数据库迁移文件。
