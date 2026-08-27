const fragments = {
  privateKey: ["-----BEGIN", " PRIVATE KEY-----"].join(""),
};

const rules = [
  {
    name: "密钥头",
    regex: new RegExp(fragments.privateKey.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g"),
    replace: "<REDACTED:PRIVATE_KEY>",
  },
  {
    name: "凭据赋值",
    regex: /\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)\s*[:=]\s*["']?([^\s,"';}{]{6,})["']?/gi,
    replace: (_, key) => `${key}=<REDACTED:CREDENTIAL>`,
  },
  {
    name: "电子邮箱",
    regex: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
    replace: "<REDACTED:EMAIL>",
  },
  {
    name: "中国大陆手机号",
    regex: /(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)/g,
    replace: "<REDACTED:PHONE>",
  },
  {
    name: "macOS 用户路径",
    regex: /\/Users\/[A-Za-z0-9._-]+(?=\/|\b)/g,
    replace: "${HOME}",
  },
  {
    name: "Windows 用户路径",
    regex: /[A-Za-z]:\\Users\\[A-Za-z0-9._-]+(?=\\|\b)/g,
    replace: "%USERPROFILE%",
  },
];

const sourceText = document.querySelector("#sourceText");
const resultText = document.querySelector("#resultText");
const findings = document.querySelector("#findings");
const findingCount = document.querySelector("#findingCount");
const ruleList = document.querySelector("#ruleList");

for (const rule of rules) {
  const item = document.createElement("li");
  item.textContent = rule.name;
  ruleList.append(item);
}

function scanAndRedact() {
  let output = sourceText.value;
  const report = [];

  for (const rule of rules) {
    const matches = output.match(rule.regex) || [];
    if (matches.length) {
      report.push({ name: rule.name, count: matches.length });
      output = output.replace(rule.regex, rule.replace);
    }
    rule.regex.lastIndex = 0;
  }

  resultText.value = output;
  const total = report.reduce((sum, item) => sum + item.count, 0);
  findingCount.textContent = `${total} 项命中`;
  renderFindings(report);
}

function renderFindings(report) {
  findings.replaceChildren();
  if (!report.length) {
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent = "未命中已配置规则。这不代表文本已经绝对安全，仍需要人工复核语义和上下文。";
    findings.append(message);
    return;
  }

  for (const item of report) {
    const pill = document.createElement("span");
    pill.className = "finding-pill";
    const label = document.createTextNode(`${item.name} · `);
    const count = document.createElement("b");
    count.textContent = item.count;
    pill.append(label, count);
    findings.append(pill);
  }
}

document.querySelector("#scanButton").addEventListener("click", scanAndRedact);
document.querySelector("#clearButton").addEventListener("click", () => {
  sourceText.value = "";
  resultText.value = "";
  findingCount.textContent = "0 项命中";
  renderFindings([]);
  sourceText.focus();
});

document.querySelector("#loadDemo").addEventListener("click", () => {
  const email = ["project.owner", "example.test"].join("@");
  const phone = ["138", "0013", "8000"].join("");
  const credential = ["demo_", "value_", "not_real"].join("");
  sourceText.value = [
    "项目说明：准备将工作流整理后公开。",
    `联系人：${email}`,
    `电话：${phone}`,
    `api_key=${credential}`,
    `本地路径：${["", "Users", "demo", "Documents", "private-workspace"].join("/")}`,
  ].join("\n");
  scanAndRedact();
});

document.querySelector("#copyButton").addEventListener("click", async (event) => {
  if (!resultText.value) return;
  try {
    await navigator.clipboard.writeText(resultText.value);
    event.currentTarget.textContent = "已复制";
    setTimeout(() => { event.currentTarget.textContent = "复制结果"; }, 1400);
  } catch {
    resultText.select();
    event.currentTarget.textContent = "请手动复制";
  }
});
