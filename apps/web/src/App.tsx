import { useEffect, useMemo, useRef, useState } from "react";

import type {
  AnchorRef,
  ConceptNode,
  PersistApi,
  ResourceInfo,
  SearchResultItem,
  WorkspaceSnapshot,
} from "./api";
import { PdfRenderer } from "./PdfRenderer";

type DragState = {
  nodeId: string;
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
  currentX: number;
  currentY: number;
  before: WorkspaceSnapshot;
};

const sampleNotes = [
  { title: "极限的直觉", detail: "从趋近到严格定义", nodeId: "limit" },
  { title: "连续的三个条件", detail: "存在、相等、可趋近", nodeId: "continuity" },
  { title: "可导为什么更强", detail: "连续与局部线性", nodeId: "derivative" },
] as const;

function createSampleWorkspace(): WorkspaceSnapshot {
  return {
    nodes: [
      {
        id: "course",
        title: "连续性与可导性",
        note: "从函数、极限出发，理解连续与可导之间的关系。",
        x: 390,
        y: 44,
        positionLocked: false,
        tone: "root",
      },
      {
        id: "limit",
        title: "极限",
        note: "描述自变量趋近某一点时，函数值所表现出的趋势。",
        x: 115,
        y: 205,
        positionLocked: false,
        tone: "branch",
      },
      {
        id: "continuity",
        title: "连续",
        note: "函数值、极限值与定义值在一点相互吻合。",
        x: 390,
        y: 205,
        positionLocked: false,
        tone: "branch",
      },
      {
        id: "derivative",
        title: "导数",
        note: "函数在一点的瞬时变化率，也代表切线斜率。",
        x: 665,
        y: 205,
        positionLocked: false,
        tone: "branch",
      },
      {
        id: "function",
        title: "函数",
        note: "把输入映射为唯一输出的规则。",
        x: 35,
        y: 405,
        positionLocked: false,
        tone: "leaf",
      },
      {
        id: "neighborhood",
        title: "邻域",
        note: "围绕某一点的一段局部范围。",
        x: 205,
        y: 405,
        positionLocked: false,
        tone: "leaf",
      },
      {
        id: "epsilon",
        title: "ε-δ 语言",
        note: "用任意精度 ε 与输入距离 δ 严格描述极限。",
        x: 390,
        y: 405,
        positionLocked: false,
        tone: "leaf",
      },
      {
        id: "differentiable",
        title: "可导",
        note: "差商极限存在，意味着局部可由线性函数逼近。",
        x: 665,
        y: 405,
        positionLocked: false,
        tone: "leaf",
      },
    ],
    edges: [
      { from: "course", to: "limit" },
      { from: "course", to: "continuity" },
      { from: "course", to: "derivative" },
      { from: "limit", to: "function" },
      { from: "limit", to: "neighborhood" },
      { from: "continuity", to: "epsilon" },
      { from: "derivative", to: "differentiable" },
    ],
  };
}

function parentOf(snapshot: WorkspaceSnapshot, nodeId: string) {
  return snapshot.edges.find((edge) => edge.to === nodeId)?.from;
}

function layoutWorkspace(snapshot: WorkspaceSnapshot): WorkspaceSnapshot {
  const positions = new Map<string, { x: number; y: number }>([
    ["course", { x: 390, y: 44 }],
    ["limit", { x: 115, y: 205 }],
    ["continuity", { x: 390, y: 205 }],
    ["derivative", { x: 665, y: 205 }],
  ]);
  const childGroups = new Map<string, string[]>();

  for (const edge of snapshot.edges) {
    const children = childGroups.get(edge.from) ?? [];
    children.push(edge.to);
    childGroups.set(edge.from, children);
  }

  const branchX = new Map<string, number>([
    ["limit", 115],
    ["continuity", 390],
    ["derivative", 665],
  ]);

  for (const [parentId, children] of childGroups) {
    if (parentId === "course") continue;
    const center = branchX.get(parentId) ?? snapshot.nodes.find((node) => node.id === parentId)?.x ?? 390;
    const width = Math.max(170, (children.length - 1) * 170);
    children.forEach((childId, index) => {
      positions.set(childId, {
        x: center - width / 2 + index * 170,
        y: 405,
      });
    });
  }

  return {
    ...snapshot,
    nodes: snapshot.nodes.map((node) => {
      const position = positions.get(node.id);
      return !position || node.positionLocked ? node : { ...node, ...position };
    }),
  };
}

function Icon({ name }: { name: "undo" | "redo" | "layout" | "reset" | "plus" | "trash" | "lock" }) {
  const paths = {
    undo: <path d="M9 7H5v-4M5 7c2-3 7-4 10-1 3 2 3 7 0 10-2 2-5 2-7 1" />,
    redo: <path d="M15 7h4v-4m0 4c-2-3-7-4-10-1-3 2-3 7 0 10 2 2 5 2 7 1" />,
    layout: <path d="M12 4v4m-6 3h12M6 11v4m6-4v4m6-4v4M3 15h6v5H3zm6 0h6v5H9zm6 0h6v5h-6z" />,
    reset: <path d="M5 5v5h5M5 10a7 7 0 1 1 2 7" />,
    plus: <path d="M12 5v14M5 12h14" />,
    trash: <path d="M5 7h14M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" />,
    lock: <path d="M7 10V7a5 5 0 0 1 10 0v3m-12 0h14v10H5z" />,
  } as const;

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="17" height="17">
      {paths[name]}
    </svg>
  );
}

export function App({ api }: { api?: PersistApi }) {
  const [present, setPresent] = useState<WorkspaceSnapshot>(() => createSampleWorkspace());
  const [past, setPast] = useState<WorkspaceSnapshot[]>([]);
  const [future, setFuture] = useState<WorkspaceSnapshot[]>([]);
  const [selectedId, setSelectedId] = useState("course");
  const [titleDraft, setTitleDraft] = useState("连续性与可导性");
  const [noteDraft, setNoteDraft] = useState("从函数、极限出发，理解连续与可导之间的关系。");
  const [status, setStatus] = useState("已载入示例知识树，可以开始编辑");
  const [connection, setConnection] = useState<"idle" | "connected" | "offline">("idle");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchStatus, setSearchStatus] = useState<"idle" | "searching" | "done" | "failed">("idle");
  const [resources, setResources] = useState<ResourceInfo[]>([]);
  const [importStatus, setImportStatus] = useState<"idle" | "importing" | "failed">("idle");
  const [viewerResource, setViewerResource] = useState<ResourceInfo | null>(null);
  const [viewerPage, setViewerPage] = useState(1);
  const [viewerText, setViewerText] = useState("");
  const [viewerStatus, setViewerStatus] = useState<"idle" | "loading" | "failed" | "drift">("idle");
  const [anchors, setAnchors] = useState<AnchorRef[]>([]);
  const [viewerMode, setViewerMode] = useState<"text" | "render">("text");
  const [activeAnchor, setActiveAnchor] = useState<AnchorRef | null>(null);
  const nextNodeNumber = useRef(1);
  const drag = useRef<DragState | null>(null);
  const canvasViewport = useRef<HTMLDivElement | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selectedNode = present.nodes.find((node) => node.id === selectedId) ?? present.nodes[0];
  const nodeById = useMemo(
    () => new Map(present.nodes.map((node) => [node.id, node])),
    [present.nodes],
  );

  useEffect(() => {
    const viewport = canvasViewport.current;
    if (!viewport) return;
    viewport.scrollLeft = Math.max(0, selectedNode.x + 75 - viewport.clientWidth / 2);
  }, [selectedId, selectedNode.x]);

  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    api
      .loadGraph()
      .then((saved) => {
        if (cancelled) return;
        if (saved) {
          setPresent(saved);
          const preferred = saved.nodes[0] ?? present.nodes[0];
          setSelectedId(preferred.id);
          setTitleDraft(preferred.title);
          setNoteDraft(preferred.note);
          setStatus("已从本地恢复保存的知识树");
        } else {
          setStatus("本地暂无保存内容，当前显示示例知识树");
        }
        setConnection("connected");
      })
      .catch(() => {
        if (cancelled) return;
        setConnection("offline");
        setStatus("本地服务未连接，当前显示示例知识树");
      });
    api
      .listResources()
      .then((items) => {
        if (!cancelled) setResources(items);
      })
      .catch(() => {
        if (!cancelled) setResources([]);
      });
    return () => {
      cancelled = true;
    };
    // api is a stable prop for the lifetime of the app; present is intentionally
    // captured for the initial fallback only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, []);

  function scheduleAutoSave(snapshot: WorkspaceSnapshot) {
    if (!api) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveState("saving");
    saveTimer.current = setTimeout(() => {
      api
        .saveGraph(snapshot)
        .then(() => setSaveState("saved"))
        .catch(() => setSaveState("failed"));
    }, 600);
  }

  async function runSearch(query: string) {
    if (!api || !query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearchStatus("searching");
    try {
      const results = await api.searchGraph(query.trim());
      setSearchResults(results);
      setSearchStatus("done");
    } catch {
      setSearchResults([]);
      setSearchStatus("failed");
    }
  }

  function jumpToResult(resultId: string) {
    const node = present.nodes.find((candidate) => candidate.id === resultId);
    if (!node) return;
    selectNode(node.id);
    const viewport = canvasViewport.current;
    if (viewport) {
      viewport.scrollLeft = Math.max(0, node.x + 75 - viewport.clientWidth / 2);
    }
  }

  async function handleImport(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !api) return;
    setImportStatus("importing");
    try {
      const info = await api.importResource(file);
      setResources((current) => [...current.filter((item) => item.id !== info.id), info]);
      setImportStatus("idle");
      setStatus(`已导入“${info.display_name}”`);
    } catch {
      setImportStatus("failed");
      setStatus("导入失败，请检查文件类型与大小");
    } finally {
      event.target.value = "";
    }
  }

  async function openViewer(resource: ResourceInfo) {
    if (!api) return;
    setViewerResource(resource);
    setViewerPage(1);
    setViewerText("");
    setActiveAnchor(null);
    setViewerStatus("loading");
    try {
      const [page, anchorList] = await Promise.all([
        api.getPageText(resource.id, 1),
        api.listAnchors(resource.id),
      ]);
      setViewerText(page.text);
      setAnchors(anchorList);
      setViewerStatus("idle");
    } catch {
      setViewerStatus("failed");
    }
  }

  async function changeViewerPage(page: number) {
    if (!api || !viewerResource) return;
    if (page < 1) return;
    setViewerPage(page);
    setActiveAnchor(null);
    setViewerStatus("loading");
    try {
      const next = await api.getPageText(viewerResource.id, page);
      setViewerText(next.text);
      setViewerStatus("idle");
    } catch {
      setViewerStatus("drift");
      setViewerText("");
    }
  }

  async function jumpToAnchor(anchor: AnchorRef) {
    if (!api || !viewerResource) return;
    setViewerPage(anchor.page);
    setActiveAnchor(anchor);
    if (anchor.bboxNorm) {
      setViewerMode("render");
    }
    setViewerStatus("loading");
    try {
      const page = await api.getPageText(viewerResource.id, anchor.page);
      setViewerText(page.text);
      setViewerStatus("idle");
    } catch {
      setViewerStatus("drift");
      setViewerText("");
    }
  }

  function commit(next: WorkspaceSnapshot, message: string) {
    setPast([...past, present]);
    setPresent(next);
    setFuture([]);
    setStatus(message);
    scheduleAutoSave(next);
  }

  function selectNode(nodeId: string) {
    const node = present.nodes.find((candidate) => candidate.id === nodeId);
    if (!node) return;
    setSelectedId(node.id);
    setTitleDraft(node.title);
    setNoteDraft(node.note);
    setStatus(`已选择“${node.title}”`);
  }

  function restoreDrafts(snapshot: WorkspaceSnapshot, preferredId: string) {
    const node = snapshot.nodes.find((candidate) => candidate.id === preferredId) ?? snapshot.nodes[0];
    setSelectedId(node.id);
    setTitleDraft(node.title);
    setNoteDraft(node.note);
  }

  function undo() {
    const previous = past.at(-1);
    if (!previous) return;
    setPast(past.slice(0, -1));
    setFuture([present, ...future]);
    setPresent(previous);
    restoreDrafts(previous, selectedId);
    setStatus("已撤销上一步修改");
  }

  function redo() {
    const next = future[0];
    if (!next) return;
    setPast([...past, present]);
    setFuture(future.slice(1));
    setPresent(next);
    restoreDrafts(next, selectedId);
    setStatus("已重做上一步修改");
  }

  function saveNode() {
    const title = titleDraft.trim();
    if (!title) {
      setStatus("概念标题不能为空");
      return;
    }
    if (title === selectedNode.title && noteDraft === selectedNode.note) {
      setStatus("当前概念没有需要保存的修改");
      return;
    }
    commit(
      {
        ...present,
        nodes: present.nodes.map((node) =>
          node.id === selectedNode.id ? { ...node, title, note: noteDraft } : node,
        ),
      },
      `已保存“${title}”`,
    );
    setTitleDraft(title);
  }

  function addChild() {
    const id = `new-concept-${nextNodeNumber.current++}`;
    const siblings = present.edges.filter((edge) => edge.from === selectedNode.id).length;
    const child: ConceptNode = {
      id,
      title: "新概念",
      note: "在这里记录这个概念的定义、例子或疑问。",
      x: Math.min(800, Math.max(20, selectedNode.x + (siblings - 0.5) * 170)),
      y: Math.min(535, selectedNode.y + 185),
      positionLocked: false,
      tone: "leaf",
    };
    const next = {
      nodes: [...present.nodes, child],
      edges: [...present.edges, { from: selectedNode.id, to: id }],
    };
    commit(next, "已添加子概念，可以在右侧继续编辑");
    setSelectedId(id);
    setTitleDraft(child.title);
    setNoteDraft(child.note);
  }

  function deleteSelected() {
    if (present.edges.some((edge) => edge.from === selectedNode.id)) {
      setStatus("只能删除没有子节点的概念");
      return;
    }
    const parentId = parentOf(present, selectedNode.id) ?? "course";
    const next = {
      nodes: present.nodes.filter((node) => node.id !== selectedNode.id),
      edges: present.edges.filter((edge) => edge.from !== selectedNode.id && edge.to !== selectedNode.id),
    };
    const parent = next.nodes.find((node) => node.id === parentId) ?? next.nodes[0];
    commit(next, `已删除“${selectedNode.title}”`);
    setSelectedId(parent.id);
    setTitleDraft(parent.title);
    setNoteDraft(parent.note);
  }

  function togglePositionLock() {
    const locked = !selectedNode.positionLocked;
    commit(
      {
        ...present,
        nodes: present.nodes.map((node) =>
          node.id === selectedNode.id ? { ...node, positionLocked: locked } : node,
        ),
      },
      locked ? `已锁定“${selectedNode.title}”的位置` : `已解除“${selectedNode.title}”的位置锁定`,
    );
  }

  function autoLayout() {
    commit(layoutWorkspace(present), "已自动排布，锁定的节点保持原位");
  }

  function resetDemo() {
    const sample = createSampleWorkspace();
    setPresent(sample);
    setPast([]);
    setFuture([]);
    restoreDrafts(sample, "course");
    nextNodeNumber.current = 1;
    setStatus("示例已重新载入");
  }

  function startDrag(event: React.PointerEvent<HTMLButtonElement>, node: ConceptNode) {
    selectNode(node.id);
    drag.current = {
      nodeId: node.id,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: node.x,
      originY: node.y,
      currentX: node.x,
      currentY: node.y,
      before: present,
    };
  }

  function moveDrag(event: React.PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    const x = Math.max(8, Math.min(835, active.originX + event.clientX - active.startX));
    const y = Math.max(8, Math.min(555, active.originY + event.clientY - active.startY));
    active.currentX = x;
    active.currentY = y;
    setPresent((snapshot) => ({
      ...snapshot,
      nodes: snapshot.nodes.map((node) => (node.id === active.nodeId ? { ...node, x, y } : node)),
    }));
  }

  function endDrag(event: React.PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    drag.current = null;
    if (active.currentX === active.originX && active.currentY === active.originY) return;
    setPast([...past, active.before]);
    setFuture([]);
    setStatus("已移动概念节点");
    scheduleAutoSave({
      ...present,
      nodes: present.nodes.map((node) =>
        node.id === active.nodeId ? { ...node, x: active.currentX, y: active.currentY } : node,
      ),
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#workspace" aria-label="知枝笔记首页">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>知枝</span>
        </a>
        <div className="course-heading">
          <span className="course-path">学习空间 / 高等数学</span>
          <h1>微积分 · 连续性与可导性</h1>
        </div>
        <div className="search-area">
          <label className="visually-hidden" htmlFor="concept-search">搜索概念或笔记</label>
          <input
            id="concept-search"
            type="search"
            placeholder="搜索概念或笔记…"
            maxLength={100}
            value={searchQuery}
            onChange={(event) => {
              setSearchQuery(event.target.value);
              void runSearch(event.target.value);
            }}
          />
          {searchStatus === "searching" && <span className="search-note">搜索中…</span>}
          {searchStatus === "failed" && <span className="search-note">搜索失败，请检查搜索词</span>}
          {searchQuery.trim() && searchStatus === "done" && searchResults.length > 0 && (
            <ul className="search-results" aria-label="搜索结果">
              {searchResults.map((result) => (
                <li key={result.id}>
                  <button
                    type="button"
                    onClick={() => jumpToResult(result.id)}
                    aria-label={`定位到概念：${result.label}`}
                  >
                    <strong>{result.label}</strong>
                    <span>{result.snippet}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {searchQuery.trim() && searchStatus === "done" && searchResults.length === 0 && (
            <p className="search-note">没有匹配的概念</p>
          )}
        </div>
        <div className="mode-badges" aria-label="当前工作模式">
          <span className="mode-badge sample">示例数据</span>
          <span className="mode-badge offline"><i aria-hidden="true" />AI 未连接</span>
        </div>
      </header>

      <aside className="compact-boundary" aria-label="演示能力边界">
        <span aria-hidden="true">演示</span>
        <p>示例数据 · 仅本次会话 · AI 未连接 · 来源跳转未接入 · 未连接数据库</p>
      </aside>

      <div id="workspace" className="workspace">
        <nav className="sidebar" aria-label="课程与笔记">
          <div className="side-heading">
            <p className="overline">我的课程</p>
            <button type="button" className="icon-button" aria-label="添加课程" disabled>＋</button>
          </div>
          <button type="button" className="course-card active">
            <span className="course-icon">微</span>
            <span><strong>微积分</strong><small>8 个概念 · 3 篇笔记</small></span>
          </button>
          <button type="button" className="course-card muted" disabled>
            <span className="course-icon ghost">＋</span>
            <span><strong>新建课程</strong><small>后续版本开放</small></span>
          </button>

          <div className="notes-heading">
            <p className="overline">相关笔记</p>
            <span>{sampleNotes.length}</span>
          </div>
          <div className="note-list">
            {sampleNotes.map((note, index) => (
              <button type="button" className="note-link" key={note.title} onClick={() => selectNode(note.nodeId)}>
                <span className="note-index">0{index + 1}</span>
                <span><strong>{note.title}</strong><small>{note.detail}</small></span>
              </button>
            ))}
          </div>
          <div className="resource-section" aria-label="资料导入">
            <p className="overline">本地资料</p>
            <label className="import-control" htmlFor="resource-upload">
              导入资料（MD / TXT / PDF）
              <input
                id="resource-upload"
                type="file"
                accept=".md,.txt,.pdf,text/markdown,text/plain,application/pdf"
                onChange={handleImport}
              />
            </label>
            {importStatus === "failed" && <p className="import-note">导入失败，请检查文件类型与大小</p>}
            {importStatus === "importing" && <p className="import-note">导入中…</p>}
            <ul className="resource-list">
              {resources.map((resource) => (
                <li key={resource.id}>
                  <span className="resource-icon" aria-hidden="true">📄</span>
                  <span className="resource-meta">
                    <strong>{resource.display_name}</strong>
                    <small>{resource.mime} · {(resource.byte_size / 1024).toFixed(1)} KB</small>
                  </span>
                  {resource.mime === "application/pdf" && (
                    <button
                      type="button"
                      className="resource-open"
                      onClick={() => openViewer(resource)}
                    >
                      打开
                    </button>
                  )}
                </li>
              ))}
              {resources.length === 0 && importStatus !== "importing" && (
                <li className="resource-empty">还没有导入资料</li>
              )}
            </ul>
          </div>
          <div className="session-notice">
            <span aria-hidden="true">◷</span>
            <p><strong>会话内演示</strong>所有修改仅保留在本次会话，刷新页面后会恢复示例。</p>
          </div>
        </nav>

        <section className="canvas-column" aria-label="知识树画布">
          <div className="canvas-toolbar" role="toolbar" aria-label="知识树工具">
            <div className="toolbar-group">
              <button type="button" onClick={undo} disabled={past.length === 0}><Icon name="undo" />撤销</button>
              <button type="button" onClick={redo} disabled={future.length === 0}><Icon name="redo" />重做</button>
            </div>
            <span className="toolbar-rule" />
            <button type="button" onClick={autoLayout}><Icon name="layout" />自动排布</button>
            <button type="button" onClick={resetDemo}><Icon name="reset" />重新载入示例</button>
            <span className="canvas-tip">拖动节点调整位置</span>
          </div>

          <div className="canvas-viewport" ref={canvasViewport}>
            <div className="canvas-surface">
              <div className="canvas-grid" aria-hidden="true" />
              <svg className="edge-layer" viewBox="0 0 1000 650" aria-hidden="true">
                {present.edges.map((edge) => {
                  const from = nodeById.get(edge.from);
                  const to = nodeById.get(edge.to);
                  if (!from || !to) return null;
                  const x1 = from.x + 75;
                  const y1 = from.y + 68;
                  const x2 = to.x + 75;
                  const y2 = to.y;
                  const middle = (y1 + y2) / 2;
                  return (
                    <path
                      key={`${edge.from}-${edge.to}`}
                      d={`M ${x1} ${y1} C ${x1} ${middle}, ${x2} ${middle}, ${x2} ${y2}`}
                    />
                  );
                })}
              </svg>
              {present.nodes.map((node) => (
                <button
                  type="button"
                  key={node.id}
                  aria-label={`概念：${node.title}`}
                  aria-pressed={node.id === selectedNode.id}
                  className={`concept-node ${node.tone}${node.id === selectedNode.id ? " selected" : ""}${node.positionLocked ? " locked" : ""}`}
                  style={{ left: node.x, top: node.y }}
                  onClick={() => selectNode(node.id)}
                  onPointerDown={(event) => startDrag(event, node)}
                  onPointerMove={moveDrag}
                  onPointerUp={endDrag}
                >
                  <span className="node-type">{node.tone === "root" ? "主题" : node.tone === "branch" ? "概念" : "知识点"}</span>
                  <strong>{node.title}</strong>
                  {node.positionLocked && <span className="lock-dot" aria-label="位置已锁定">⌑</span>}
                </button>
              ))}
              <div className="canvas-legend" aria-hidden="true">
                <span><i className="legend-root" />主题</span>
                <span><i className="legend-branch" />概念</span>
                <span><i className="legend-leaf" />知识点</span>
              </div>
            </div>
          </div>
        </section>

        <section className="detail-panel" aria-label="节点详情">
          <div className="detail-header">
            <div>
              <p className="overline">节点详情</p>
              <span className={`detail-chip ${selectedNode.tone}`}>{selectedNode.tone === "root" ? "主题" : "概念"}</span>
            </div>
            <span className="selected-dot" title="当前选中" />
          </div>

          <label className="field-label" htmlFor="concept-title">概念标题</label>
          <input
            id="concept-title"
            value={titleDraft}
            onChange={(event) => setTitleDraft(event.target.value)}
            maxLength={48}
          />

          <label className="field-label" htmlFor="concept-note">概念笔记</label>
          <textarea
            id="concept-note"
            value={noteDraft}
            onChange={(event) => setNoteDraft(event.target.value)}
            rows={7}
            maxLength={600}
          />
          <div className="character-count">{noteDraft.length} / 600</div>

          <button type="button" className="primary-button" onClick={saveNode}>保存修改</button>

          <div className="detail-divider" />
          <p className="overline action-label">结构与位置</p>
          <div className="structure-actions">
            <button type="button" onClick={addChild}><Icon name="plus" />添加子概念</button>
            <button type="button" onClick={togglePositionLock}><Icon name="lock" />{selectedNode.positionLocked ? "解除位置锁定" : "锁定位置"}</button>
            <button type="button" className="danger-button" onClick={deleteSelected}><Icon name="trash" />删除当前节点</button>
          </div>

          <div className="source-card">
            <span className="source-icon" aria-hidden="true">↗</span>
            <div><strong>来源将在后续接入</strong><p>当前示例没有导入文档，不提供虚假的来源跳转。</p></div>
          </div>
        </section>
      </div>

      {viewerResource && (
        <section className="pdf-viewer" aria-label="资料查看器">
          <header className="viewer-header">
            <div>
              <p className="overline">资料查看器</p>
              <strong>{viewerResource.display_name}</strong>
            </div>
            <div className="viewer-controls">
              <button type="button" onClick={() => changeViewerPage(viewerPage - 1)} disabled={viewerPage <= 1}>← 上一页</button>
              <span>第 {viewerPage} 页</span>
              <button type="button" onClick={() => changeViewerPage(viewerPage + 1)}>下一页 →</button>
              <button
                type="button"
                className={viewerMode === "text" ? "viewer-mode active" : "viewer-mode"}
                onClick={() => setViewerMode("text")}
              >
                文本
              </button>
              <button
                type="button"
                className={viewerMode === "render" ? "viewer-mode active" : "viewer-mode"}
                onClick={() => setViewerMode("render")}
              >
                渲染
              </button>
              <button type="button" className="viewer-close" onClick={() => setViewerResource(null)}>关闭</button>
            </div>
          </header>
          {viewerStatus === "drift" && (
            <p className="viewer-warning">资料已变化，无法定位：请重新导入或查看最新版本。</p>
          )}
          {viewerStatus === "failed" && (
            <p className="viewer-warning">无法读取该资料，请确认文件已解析。</p>
          )}
          <div className="viewer-body" aria-live="polite">
            {viewerStatus === "loading" ? (
              "加载中…"
            ) : viewerMode === "render" && api ? (
              <PdfRenderer
                key={viewerPage}
                fileUrl={api.getFileUrl(viewerResource.id)}
                page={viewerPage}
                activeAnchor={activeAnchor}
              />
            ) : (
              <pre>{viewerText}</pre>
            )}
          </div>
          {anchors.length > 0 && (
            <nav className="anchor-list" aria-label="锚点目录">
              <p className="overline">锚点目录</p>
              <ul>
                {anchors.map((anchor) => (
                  <li key={anchor.id}>
                    <button type="button" onClick={() => jumpToAnchor(anchor)}>
                      第 {anchor.page} 页 · {anchor.label}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </section>
      )}

      <footer className="statusbar">
        <p role="status" aria-live="polite"><i aria-hidden="true" />{status}</p>
        <span className="persistence-state">
          {connection === "offline"
            ? "本地服务未连接"
            : saveState === "saving"
              ? "保存中…"
              : saveState === "failed"
                ? "保存失败"
                : saveState === "saved"
                  ? "已保存到本地"
                  : connection === "connected"
                    ? "已连接本地数据库"
                    : "本地演示 · 未连接数据库"}
        </span>
      </footer>
    </main>
  );
}
