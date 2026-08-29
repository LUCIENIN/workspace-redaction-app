const stageContent = {
  raw: {
    kicker: "PRIVATE SOURCE OF TRUTH",
    title: "原始资料层保留证据，不承担公开展示。",
    body: "PDF、文档、网页剪藏、图片和其他资料进入 raw/sources。它们是来源证据，可能包含完整上下文、作者信息、客户记录和附件，因此默认只留在本机。",
    facts: ["原始内容不可变优先", "目录结构参与分类上下文", "内容哈希用于增量判断"],
    decision: "LOCAL ONLY",
  },
  ingest: {
    kicker: "ANALYZE, THEN GENERATE",
    title: "摄入分两步：先理解，再写 Wiki。",
    body: "第一步抽取实体、概念、论点、冲突和结构建议；第二步才生成带 frontmatter、sources 和 wikilinks 的页面。持久化队列负责串行、重试和恢复。",
    facts: ["两次顺序 LLM 调用", "失败任务最多重试", "变更后可自动生成 embedding"],
    decision: "CONTROLLED INGEST",
  },
  wiki: {
    kicker: "PERSISTENT KNOWLEDGE",
    title: "Wiki 是可维护知识层，不是原文副本。",
    body: "来源卡、实体、概念、比较、综合与工作流页面构成长期知识结构。每页使用 YAML frontmatter 和 wikilinks，既可被 LLM 读取，也可在 Obsidian 中浏览。",
    facts: ["sources 回链来源", "index 与 overview 导航", "人类审核结构与结论"],
    decision: "REVIEW BEFORE PUBLIC",
  },
  graph: {
    kicker: "CONNECTED + SEARCHABLE",
    title: "图谱表达关系，向量负责语义召回。",
    body: "Wikilinks、来源重叠、共同邻居和类型亲和共同形成关联度；LanceDB 保存可选向量索引。两者都能重建，但运行索引本身不进入公开仓库。",
    facts: ["四信号关联度", "Louvain 社区检测", "向量指纹检查一致性"],
    decision: "RUNTIME STAYS LOCAL",
  },
  query: {
    kicker: "HYBRID RETRIEVAL",
    title: "查询先找候选，再沿图谱扩展。",
    body: "检索先做中英文分词与标题加权，再按配置加入向量召回，最后从种子页面做两跳图谱扩展，并在上下文预算内选择内容。",
    facts: ["关键词精确线索", "向量语义线索", "图谱关系线索"],
    decision: "EVIDENCE-BOUNDED ANSWER",
  },
};

const fallbackZones = [
  { zone: "source", label: "原始资料层", examples: ["raw/sources/"], decision: "local_only", reason: "来源证据默认只留在本机。" },
  { zone: "private_archive", label: "私密档案层", examples: ["archive/private-*/"], decision: "never_publish", reason: "财务、健康和身份记录不进入公开集。" },
  { zone: "runtime_state", label: "运行状态层", examples: [".llm-wiki/"], decision: "never_publish", reason: "对话、向量和队列可能包含隐式私密。" },
  { zone: "generated_wiki", label: "Wiki 生成层", examples: ["wiki/"], decision: "review_and_abstract", reason: "只抽取方法，不默认公开事实。" },
  { zone: "workflow", label: "方法与工具层", examples: ["tools/"], decision: "public_candidate", reason: "去除路径、凭据和身份后才可公开。" },
];

const decisionLabels = {
  local_only: "仅限本地",
  never_publish: "禁止公开",
  review_and_abstract: "复核并抽象",
  public_candidate: "公开候选",
};

function renderStage(key) {
  const stage = stageContent[key];
  const detail = document.querySelector("#stageDetail");
  detail.innerHTML = "";

  const kicker = document.createElement("p");
  kicker.className = "detail-kicker";
  kicker.textContent = stage.kicker;
  const title = document.createElement("h3");
  title.textContent = stage.title;
  const body = document.createElement("p");
  body.className = "detail-body";
  body.textContent = stage.body;
  const list = document.createElement("ul");
  for (const fact of stage.facts) {
    const item = document.createElement("li");
    item.textContent = fact;
    list.append(item);
  }
  const decision = document.createElement("strong");
  decision.className = "stage-decision";
  decision.textContent = stage.decision;
  detail.append(kicker, title, body, list, decision);
}

document.querySelectorAll(".stage-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".stage-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderStage(button.dataset.stage);
  });
});

function renderZone(zone, button) {
  document.querySelectorAll(".zone-button").forEach((item) => {
    item.classList.remove("active");
    item.setAttribute("aria-selected", "false");
  });
  button.classList.add("active");
  button.setAttribute("aria-selected", "true");

  const detail = document.querySelector("#zoneDetail");
  detail.innerHTML = "";
  const top = document.createElement("div");
  top.className = "zone-detail-top";
  const label = document.createElement("div");
  const kicker = document.createElement("p");
  kicker.textContent = `ZONE · ${zone.zone.toUpperCase()}`;
  const title = document.createElement("h3");
  title.textContent = zone.label;
  label.append(kicker, title);
  const badge = document.createElement("span");
  badge.className = `decision decision-${zone.decision}`;
  badge.textContent = decisionLabels[zone.decision] || zone.decision;
  top.append(label, badge);

  const reason = document.createElement("p");
  reason.className = "zone-reason";
  reason.textContent = zone.reason;
  const pathLabel = document.createElement("small");
  pathLabel.textContent = "代表目录（使用相对路径，不暴露本机用户目录）";
  const paths = document.createElement("div");
  paths.className = "path-list";
  for (const example of zone.examples) {
    const code = document.createElement("code");
    code.textContent = example;
    paths.append(code);
  }
  detail.append(top, reason, pathLabel, paths);
}

function setupZones(zones) {
  const container = document.querySelector("#zoneButtons");
  container.replaceChildren();
  zones.forEach((zone, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "zone-button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    const number = document.createElement("span");
    number.textContent = String(index + 1).padStart(2, "0");
    const label = document.createElement("b");
    label.textContent = zone.label;
    button.append(number, label);
    button.addEventListener("click", () => renderZone(zone, button));
    container.append(button);
    if (index === 0) renderZone(zone, button);
  });
  const zoneCount = document.querySelector("#zoneCount");
  if (zoneCount) zoneCount.textContent = zones.length;
}

function formatObserved(value) {
  if (!value) return "无时间记录";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "时间格式不可用";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(date);
}

async function loadSnapshot() {
  try {
    const response = await fetch("data/local-kb-snapshot.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`snapshot ${response.status}`);
    const snapshot = await response.json();
    const wikiPages = snapshot.counts?.wiki_markdown_pages ?? "—";
    const indexedPages = snapshot.vector?.indexed_pages ?? "—";
    const passed = snapshot.health?.search?.passed;
    const total = snapshot.health?.search?.total;
    const searchScore = Number.isInteger(passed) && Number.isInteger(total) ? `${passed}/${total}` : "—";
    const healthStatus = snapshot.health?.status ?? "unknown";
    document.querySelector("#snapshotSummary").textContent = `${wikiPages} 页 · ${indexedPages} 页已索引 · 搜索 ${searchScore} · ${healthStatus}`;
    document.querySelector("#snapshotTime").textContent = `状态观察时间：${formatObserved(snapshot.health?.observed_at)}。这是静态、无内容快照，不是实时监控，也不证明任何具体页面可公开。`;
    setupZones(Array.isArray(snapshot.zones) && snapshot.zones.length ? snapshot.zones : fallbackZones);
  } catch (error) {
    document.querySelector("#snapshotSummary").textContent = "快照不可用 · 当前状态未知";
    document.querySelector("#snapshotTime").textContent = `快照读取失败：${error.message}。页面仍可浏览，但当前本地状态未知。`;
    setupZones(fallbackZones);
  }
}

async function copyText(text) {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall back to the selection-based copy path below.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  return copied;
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target) return;
    const originalLabel = button.textContent;
    const copied = await copyText(target.textContent.trim());
    button.textContent = copied ? "已复制" : "复制失败";
    window.setTimeout(() => {
      button.textContent = originalLabel;
    }, 1800);
  });
});

renderStage("raw");
loadSnapshot();
