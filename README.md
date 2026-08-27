# Local Wiki Veil

针对本地 **LLM Wiki** 知识库的公开前脱敏 App 与可复现工作流。

- 在线 App：<https://lucienin.github.io/workspace-redaction-app/>
- 执行依据：[docs/execution-basis.md](docs/execution-basis.md)
- 隐私门禁：[.github/workflows/privacy-gate.yml](.github/workflows/privacy-gate.yml)

## 它解决的不是“怎么把整个知识库传上网”

本地知识库同时包含原始资料、生成 Wiki、图谱、向量索引、对话、任务队列和私密档案。对整库做字符串替换后上传，仍可能泄露语义、来源、文件名、元数据和可组合身份线索。

Local Wiki Veil 采用另一条路线：

`确定公开目的 → 知识分区 → 只抽取方法 → 一般化身份与环境 → 内容零知识快照 → 本地扫描 → 最小提交 → 远端回读`

公开仓库保留工作原理、判断门、脚本和验证方式；原始资料与私密知识继续留在本机。

## 本地 LLM Wiki 如何工作

1. `raw/sources/` 保存原始资料与来源证据。
2. 摄入先分析实体、概念、论点、冲突和结构，再生成带 frontmatter、`sources` 与 `[[wikilinks]]` 的 Wiki 页面。
3. `wiki/` 形成可维护的来源卡、概念、综合、比较和工作流页面。
4. Wikilinks、来源重叠、共同邻居和类型亲和构成知识图谱；LanceDB 保存可选向量索引。
5. 查询组合关键词、向量和图谱扩展，并在上下文预算内读取证据。

这套架构的重点是“原始资料 → 持久 Wiki → 可再生成索引”，不是把所有文档直接视为可公开的向量语料。

## 五个隐私分区

| 分区 | 代表目录 | 默认决定 |
|---|---|---|
| 原始资料层 | `raw/sources/`, `raw/assets/` | 仅限本地 |
| 私密档案层 | `archive/private-*/` | 禁止公开 |
| 运行状态层 | `.llm-wiki/chats/`, `.llm-wiki/lancedb/`, 队列与缓存 | 禁止公开 |
| Wiki 生成层 | `wiki/sources/`, `wiki/synthesis/`, `wiki/concepts/` | 人工复核并抽象 |
| 方法与工具层 | `tools/`, `schema.md`, `purpose.md` | 去身份审计后的公开候选 |

“由 LLM 生成”不等于“可以公开”。Wiki 页面仍可能包含来自私有资料的事实、原话、关系和业务判断。

## 内容零知识快照

`scripts/audit_local_kb.py` 只读本地 LLM Wiki 的目录计数和白名单状态字段：

```bash
python3 scripts/audit_local_kb.py "$LOCAL_KB" \
  --output ./local-kb-snapshot.json
```

输出明确声明：

- 不包含知识原文。
- 不包含标题和文件名。
- 不包含源文件路径或本机绝对路径。
- 不能证明任何具体 Wiki 页面适合公开。

仓库中的 [data/local-kb-snapshot.json](data/local-kb-snapshot.json) 是一次真实但已去内容的状态快照。它保留 `quality_warning` 和搜索基准未全通过的事实，没有把状态包装成“完全健康”。

## 公开仓库扫描

扫描器只面向已经隔离、准备公开的产物，不直接修改私有知识库：

```bash
python3 scripts/sanitize_workspace.py scan . --fail-on high
```

它检查常见凭据、邮箱、手机号和本机用户路径。报告只包含规则、严重性和数量，不回显命中原文。

如需导出普通文本工作区的脱敏副本：

```bash
python3 scripts/sanitize_workspace.py export /path/to/public-candidate \
  --output /path/to/new-sanitized-copy
```

该命令只写入新的、位于源目录之外的文本副本；二进制和符号链接默认跳过。

## 本地运行

```bash
npm start
```

访问 <http://127.0.0.1:4173/>。App 不需要第三方运行依赖；交互仅展示架构、分区策略和已生成的无内容快照。

## 验证

```bash
npm run check
```

验证包括：

- 本地知识库快照不泄露内容、文件名和项目路径。
- 工作区脱敏副本不覆盖源目录。
- 扫描报告不回显敏感片段。
- 当前公开仓库不命中已配置的高风险规则。

GitHub Actions 在每次 push 和 pull request 时运行同一门禁。

## 仍需人工处理的边界

- Wiki 生成页中的语义型隐私和可组合身份线索。
- 第三方文档、图片、论文、网页和代码的版权与许可证。
- PDF、Office、图片、音视频和压缩包中的隐藏元数据。
- 已进入 Git 历史的真实凭据；此时应先撤销或轮换凭据。
- 任何财务、健康、合同、客户和身份原始数据。

## 许可证

[MIT](LICENSE)
