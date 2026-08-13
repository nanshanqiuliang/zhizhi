const gates = [
  { label: "架构与流程基线", state: "已建立", tone: "ready" },
  { label: "Anchor / GraphPatch v1", state: "待冻结", tone: "pending" },
  { label: "真实 LLM", state: "未启用", tone: "locked" },
] as const;

export function App() {
  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">KNOWLEDGE TREE · ENGINEERING PREVIEW</p>
        <div className="hero-grid">
          <div>
            <p className="stage">阶段 -1 / 架构与证据准备</p>
            <h1 id="page-title">把知识连接起来，也把每个结论带回来源。</h1>
            <p className="lead">
              当前只建立可验证的工程骨架。知识导入、图编辑与 AI 草案将在对应门禁通过后逐步开放。
            </p>
          </div>
          <div className="tree-mark" aria-hidden="true">
            <span className="node node-a" />
            <span className="node node-b" />
            <span className="node node-c" />
            <span className="node node-d" />
            <span className="branch branch-a" />
            <span className="branch branch-b" />
            <span className="branch branch-c" />
          </div>
        </div>
      </section>

      <section className="status-panel" aria-labelledby="gate-title">
        <div>
          <p className="section-kicker">BUILD GATES</p>
          <h2 id="gate-title">当前工程门</h2>
        </div>
        <ul className="gate-list">
          {gates.map((gate) => (
            <li key={gate.label}>
              <span>{gate.label}</span>
              <span className={`badge badge-${gate.tone}`}>{gate.state}</span>
            </li>
          ))}
        </ul>
      </section>

      <footer>
        <span>本地优先</span>
        <span>来源可追溯</span>
        <span>人工修改优先</span>
      </footer>
    </main>
  );
}
