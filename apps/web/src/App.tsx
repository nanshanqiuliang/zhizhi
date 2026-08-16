import { useEffect, useMemo, useRef, useState } from "react";

import type {
  AiDraftResult,
  AnchorRef,
  AnswerResult,
  CommandResult,
  ConceptLocks,
  ConceptNode,
  HistoryRecord,
  PersistApi,
  ResourceInfo,
  SearchResultItem,
  WorkspaceSnapshot,
} from "./api";
import { DEFAULT_WORKSPACE_ID, buildSetLockPatch } from "./api";
import type { EdgeKind } from "./api";
import { renderMarkdown } from "./markdown";
import { PdfRenderer } from "./PdfRenderer";
import { canvasSurfaceSize } from "./canvas";

type DragState = {
  mode: "node" | "pan";
  nodeId: string;
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
  currentX: number;
  currentY: number;
  startPanX: number;
  startPanY: number;
  before: WorkspaceSnapshot;
};

const sampleNotes = [
  { title: "极限的直觉", detail: "从趋近到严格定义", nodeId: "limit" },
  { title: "连续的三个条件", detail: "存在、相等、可趋近", nodeId: "continuity" },
  { title: "可导为什么更强", detail: "连续与局部线性", nodeId: "derivative" },
] as const;

const DEFAULT_LOCKS: ConceptLocks = {
  content: false,
  relations: false,
  position: false,
  annotations: false,
};

function saveErrorMessage(code: string): string {
  switch (code) {
    case "target_locked":
      return "保存被拒：该内容已锁定，请先解锁";
    case "revision_conflict":
    case "patch_revision_conflict":
      return "保存被拒：版本冲突，请刷新后重试";
    case "workspace_corrupt":
      return "本地数据损坏，请从备份恢复";
    case "workspace_missing":
      return "工作区不存在，请重新创建";
    default:
      return "保存未完成，请重试";
  }
}

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

const EDGE_TYPE_LABELS: Record<EdgeKind, string> = {
  prerequisite_of: "先修",
  related_to: "相关",
  part_of: "包含",
  example_of: "举例",
};

function edgeTypeLabel(kind: EdgeKind): string {
  return EDGE_TYPE_LABELS[kind] ?? kind;
}

function Icon({ name }: { name: "undo" | "redo" | "layout" | "reset" | "plus" | "trash" | "lock" | "link" }) {
  const paths = {
    undo: <path d="M9 7H5v-4M5 7c2-3 7-4 10-1 3 2 3 7 0 10-2 2-5 2-7 1" />,
    redo: <path d="M15 7h4v-4m0 4c-2-3-7-4-10-1-3 2-3 7 0 10 2 2 5 2 7 1" />,
    layout: <path d="M12 4v4m-6 3h12M6 11v4m6-4v4m6-4v4M3 15h6v5H3zm6 0h6v5H9zm6 0h6v5h-6z" />,
    reset: <path d="M5 5v5h5M5 10a7 7 0 1 1 2 7" />,
    plus: <path d="M12 5v14M5 12h14" />,
    trash: <path d="M5 7h14M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" />,
    lock: <path d="M7 10V7a5 5 0 0 1 10 0v3m-12 0h14v10H5z" />,
    link: <path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5" />,
  } as const;

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="17" height="17">
      {paths[name]}
    </svg>
  );
}

export function App({
  api: apiProp,
  apiFactory,
}: {
  api?: PersistApi;
  apiFactory?: (workspaceId: string) => PersistApi;
}) {
  const [workspaceId, setWorkspaceId] = useState(DEFAULT_WORKSPACE_ID);
  const [workspaces, setWorkspaces] = useState<
    Array<{ id: string; name: string; concept_count: number; updated_at: number | string }>
  >([]);
  // `api` targets the current workspace: a passed-in api (tests) is used as-is,
  // otherwise it is rebuilt from the factory whenever the workspace changes.
  const api = useMemo(
    () => apiProp ?? (apiFactory ? apiFactory(workspaceId) : undefined),
    [apiProp, apiFactory, workspaceId],
  );
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
  const [backups, setBackups] = useState<string[]>([]);
  const [historyRecords, setHistoryRecords] = useState<HistoryRecord[]>([]);
  const [camera, setCamera] = useState({ zoom: 1, x: 0, y: 0 });
  const [viewerResource, setViewerResource] = useState<ResourceInfo | null>(null);
  const [viewerPage, setViewerPage] = useState(1);
  const [viewerText, setViewerText] = useState("");
  const [viewerStatus, setViewerStatus] = useState<"idle" | "loading" | "failed" | "drift">("idle");
  const [anchors, setAnchors] = useState<AnchorRef[]>([]);
  const [viewerMode, setViewerMode] = useState<"text" | "render">("text");
  const [activeAnchor, setActiveAnchor] = useState<AnchorRef | null>(null);
  const [draft, setDraft] = useState<AiDraftResult | null>(null);
  const [draftStatus, setDraftStatus] = useState<"idle" | "generating" | "ready" | "applying" | "failed">("idle");
  const [draftError, setDraftError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerResult | null>(null);
  const [answerStatus, setAnswerStatus] = useState<"idle" | "asking" | "done" | "failed">("idle");
  const [command, setCommand] = useState("");
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null);
  const [commandStatus, setCommandStatus] = useState<"idle" | "interpreting" | "ready" | "applying" | "failed">("idle");
  const [aiSettings, setAiSettings] = useState<{ configured: boolean; enabled: boolean } | null>(null);
  const [showAiSettings, setShowAiSettings] = useState(false);
  const [aiKeyInput, setAiKeyInput] = useState("");
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [sidebarHidden, setSidebarHidden] = useState(false);
  const [connectMode, setConnectMode] = useState(false);
  const [connectSource, setConnectSource] = useState<string | null>(null);
  const [connectType, setConnectType] = useState<EdgeKind>("related_to");
  const sidebarDrag = useRef<{ startX: number; startWidth: number } | null>(null);
  const nextNodeNumber = useRef(1);
  const drag = useRef<DragState | null>(null);
  const canvasViewport = useRef<HTMLDivElement | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Real browsers synthesize a `click` after pointerup; a drag must not let
  // that click recenter the canvas (WORK-2026-047).
  const suppressRecentOnClick = useRef(false);

  useEffect(() => {
    if (!connectMode) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setConnectMode(false);
        setConnectSource(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [connectMode]);

  const selectedNode = present.nodes.find((node) => node.id === selectedId) ?? present.nodes[0];
  const nodeById = useMemo(
    () => new Map(present.nodes.map((node) => [node.id, node])),
    [present.nodes],
  );

  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    api
      .loadGraph()
      .then((saved) => {
        if (cancelled) return;
        if (saved) {
          setPresent(saved);
          // An empty saved graph is contract-legal: keep it empty instead of
          // falling back to a demo node that no longer exists (BUG-2026-001).
          const preferred = saved.nodes[0];
          if (preferred) {
            setSelectedId(preferred.id);
            setTitleDraft(preferred.title);
            setNoteDraft(preferred.note);
          }
          setStatus("已从本地恢复保存的知识树");
        } else {
          setStatus("本地暂无保存内容，当前显示示例知识树");
        }
        setConnection("connected");
        void refreshHistory();
      })
      .catch((error) => {
        if (cancelled) return;
        setConnection("offline");
        const code = (error as Error).message;
        setStatus(
          code === "workspace_corrupt"
            ? "本地数据损坏，请从备份恢复"
            : "本地服务未连接，当前显示示例知识树",
        );
      });
    api
      .listResources()
      .then((items) => {
        if (!cancelled) setResources(items);
      })
      .catch(() => {
        if (!cancelled) setResources([]);
      });
    api
      .getAiSettings?.()
      .then((settings) => {
        if (!cancelled) setAiSettings(settings);
      })
      .catch(() => {
        if (!cancelled) setAiSettings({ configured: false, enabled: false });
      });
    api
      .listWorkspaces?.()
      .then((items) => {
        if (!cancelled) setWorkspaces(items);
      })
      .catch(() => {
        if (!cancelled) setWorkspaces([]);
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
        .catch((error) => {
          setSaveState("failed");
          setStatus(saveErrorMessage((error as Error).message));
        });
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

  async function handleBackup() {
    if (!api) return;
    try {
      await api.backupGraph();
      const list = await api.listBackups();
      setBackups(list);
      setStatus("已备份到本地");
    } catch (error) {
      setStatus(`备份失败（${(error as Error).message}）`);
    }
  }

  async function handleRestore(filename: string) {
    if (!api) return;
    try {
      await api.restoreBackup(filename);
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        restoreDrafts(refreshed, selectedId);
        setConnection("connected");
      }
      setStatus("已从备份恢复");
      void refreshHistory();
    } catch (error) {
      setStatus(`恢复失败（${(error as Error).message}）`);
    }
  }

  async function refreshHistory() {
    if (!api) return;
    try {
      setHistoryRecords(await api.listHistory());
    } catch {
      setHistoryRecords([]);
    }
  }

  async function handleOpenDir() {
    if (!api?.openResourcesDir) return;
    try {
      await api.openResourcesDir();
      setStatus("已在文件资源管理器中打开资料目录");
    } catch (error) {
      setStatus(`打开资料目录失败（${(error as Error).message}）`);
    }
  }

  async function handleReveal(resource: ResourceInfo) {
    if (!api?.revealResource) return;
    try {
      await api.revealResource(resource.id);
      setStatus("已在文件资源管理器中显示该文件");
    } catch (error) {
      setStatus(`打开文件位置失败（${(error as Error).message}）`);
    }
  }

  async function handleSaveAiKey() {
    if (!api?.setAiKey) return;
    const key = aiKeyInput.trim();
    if (!key) {
      setStatus("请输入 DeepSeek API Key");
      return;
    }
    try {
      const result = await api.setAiKey(key);
      setAiSettings({ configured: result.configured, enabled: true });
      setAiKeyInput("");
      setShowAiSettings(false);
      setStatus("AI 已接入（DeepSeek），可以开始提问/生成草案");
    } catch (error) {
      setStatus(`AI 设置保存失败（${(error as Error).message}）`);
    }
  }

  async function handleClearAiKey() {
    if (!api?.clearAiKey) return;
    try {
      const result = await api.clearAiKey();
      setAiSettings({ configured: result.configured, enabled: false });
      setAiKeyInput("");
      setStatus("已清除 AI Key，AI 功能未连接");
    } catch (error) {
      setStatus(`清除 AI Key 失败（${(error as Error).message}）`);
    }
  }

  async function handleCreateCourse() {
    if (!api?.createWorkspace) return;
    try {
      const created = await api.createWorkspace("新课程");
      const items = (await api.listWorkspaces?.()) ?? [];
      setWorkspaces(items);
      setWorkspaceId(created.id);
      setStatus(`已创建课程「${created.name}」，请在画布中添加概念`);
    } catch (error) {
      setStatus(`创建课程失败（${(error as Error).message}）`);
    }
  }

  async function openViewer(resource: ResourceInfo) {
    if (!api) return;
    setViewerResource(resource);
    setViewerPage(1);
    setViewerText("");
    setActiveAnchor(null);
    setAnchors([]);
    setViewerStatus("loading");
    if (resource.mime === "application/pdf") {
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
      return;
    }
    // Markdown/TXT: read the raw file text (no paging/rendering/anchors).
    try {
      setViewerText(await api.getResourceText(resource.id));
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
      setActiveAnchor(null);
    }
  }

  async function handleGenerateDraft(resource?: ResourceInfo) {
    if (!api) return;
    setDraft(null);
    setDraftError(null);
    setDraftStatus("generating");
    try {
      const result = await api.generateDraft(resource?.id);
      setDraft(result);
      setDraftStatus("ready");
      setStatus(`已生成草案：${result.draft.concepts.length} 个概念，${result.draft.relations.length} 条关系`);
    } catch (error) {
      const code = (error as Error).message;
      setDraftStatus("failed");
      setDraftError(code === "ai_not_available" ? "AI 未连接" : `草案生成失败（${code}）`);
      setStatus(code === "ai_not_available" ? "AI 未连接，无法生成草案" : "草案生成失败");
    }
  }

  async function acceptDraft() {
    if (!api || !draft) return;
    setDraftStatus("applying");
    try {
      await api.acceptDraft({ ...draft.patch, confirmed: true }, draft.evidence ?? []);
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        restoreDrafts(refreshed, selectedId);
      }
      setDraft(null);
      setDraftStatus("idle");
      setStatus("已接受 AI 草案并写入知识树");
      void refreshHistory();
    } catch (error) {
      setDraftStatus("failed");
      setDraftError(`写入失败（${(error as Error).message}）`);
      setStatus("草案写入失败，请检查锁定或版本冲突");
    }
  }

  function jumpToDraftSource() {
    const evidence = draft?.evidence?.[0];
    if (!evidence) return;
    const resource = resources.find((item) => item.id === evidence.resource_id);
    if (!resource) {
      setStatus("来源资料不存在，无法定位");
      return;
    }
    void openViewer(resource);
  }

  async function handleAsk() {
    if (!api || !question.trim() || answerStatus === "asking") return;
    setAnswerStatus("asking");
    setAnswer(null);
    try {
      const result = await api.askQuestion(question.trim());
      setAnswer(result);
      setAnswerStatus("done");
      setStatus(result.note === "no_matches" ? "本地没有相关内容，换个关键词试试" : "已生成回答");
    } catch (error) {
      const code = (error as Error).message;
      setAnswerStatus("failed");
      setAnswer(null);
      setStatus(code === "ai_not_available" ? "AI 未连接，无法回答" : `问答失败（${code}）`);
    }
  }

  function jumpToAnswerSource(sourceId: string) {
    const node = present.nodes.find((candidate) => candidate.id === sourceId);
    if (!node) {
      setStatus("该来源已不在当前知识树中");
      return;
    }
    selectNode(node.id);
  }

  async function handleInterpret() {
    if (!api || !command.trim() || commandStatus === "interpreting") return;
    setCommandStatus("interpreting");
    setCommandResult(null);
    try {
      const result = await api.interpretCommand(command.trim());
      setCommandResult(result);
      setCommandStatus("ready");
      setStatus(`已解释指令：${result.summary}`);
    } catch (error) {
      const code = (error as Error).message;
      setCommandStatus("failed");
      setStatus(code === "ai_not_available" ? "AI 未连接，无法执行指令" : `指令解释失败（${code}）`);
    }
  }

  async function acceptCommand() {
    if (!api || !commandResult) return;
    setCommandStatus("applying");
    try {
      await api.acceptCommand({ ...commandResult.patch, confirmed: true });
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        restoreDrafts(refreshed, selectedId);
      }
      setCommandResult(null);
      setCommandStatus("idle");
      setCommand("");
      setStatus("已执行指令并写入知识树");
      void refreshHistory();
    } catch (error) {
      setCommandStatus("failed");
      setStatus(`指令写入失败（${(error as Error).message}）`);
    }
  }

  function rejectCommand() {
    setCommandResult(null);
    setCommandStatus("idle");
    setStatus("已丢弃指令预览");
  }

  function rejectDraft() {
    setDraft(null);
    setDraftStatus("idle");
    setDraftError(null);
    setStatus("已丢弃 AI 草案");
  }

  function commit(next: WorkspaceSnapshot, message: string) {
    setPast([...past, present]);
    setPresent(next);
    setFuture([]);
    setStatus(message);
    scheduleAutoSave(next);
  }

  function centerOnNode(node: ConceptNode) {
    const viewport = canvasViewport.current;
    if (!viewport) return;
    const nodeCenterX = (node.x + 75) * camera.zoom;
    const nodeCenterY = (node.y + 34) * camera.zoom;
    setCamera((prev) => ({
      ...prev,
      x: viewport.clientWidth / 2 - nodeCenterX,
      y: viewport.clientHeight / 2 - nodeCenterY,
    }));
  }

  function selectNodeKeepCamera(nodeId: string) {
    const node = present.nodes.find((candidate) => candidate.id === nodeId);
    if (!node) return;
    setSelectedId(node.id);
    setTitleDraft(node.title);
    setNoteDraft(node.note);
    setStatus(`已选择“${node.title}”`);
  }

  function selectNode(nodeId: string) {
    const node = present.nodes.find((candidate) => candidate.id === nodeId);
    if (!node) return;
    // A click synthesized right after a drag must not recenter (jump); a
    // plain click still centers on the node.
    if (!suppressRecentOnClick.current) {
      centerOnNode(node);
    }
    suppressRecentOnClick.current = false;
    setSelectedId(node.id);
    setTitleDraft(node.title);
    setNoteDraft(node.note);
    setStatus(`已选择“${node.title}”`);
  }

  function restoreDrafts(snapshot: WorkspaceSnapshot, preferredId: string) {
    const node = snapshot.nodes.find((candidate) => candidate.id === preferredId) ?? snapshot.nodes[0];
    // Undo/redo can land on an empty snapshot; there is nothing to select then.
    if (!node) return;
    setSelectedId(node.id);
    setTitleDraft(node.title);
    setNoteDraft(node.note);
  }

  async function undo() {
    const previous = past.at(-1);
    if (previous) {
      setPast(past.slice(0, -1));
      setFuture([present, ...future]);
      setPresent(previous);
      restoreDrafts(previous, selectedId);
      setStatus("已撤销上一步修改");
      scheduleAutoSave(previous);
      return;
    }
    if (!api) return;
    try {
      await api.undoGraph();
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        restoreDrafts(refreshed, selectedId);
        setStatus("已撤销上一步持久修改");
        void refreshHistory();
      }
    } catch (error) {
      const code = (error as Error).message;
      setStatus(code === "history_empty" ? "没有可撤销的操作" : `撤销失败（${code}）`);
    }
  }

  async function redo() {
    const next = future[0];
    if (next) {
      setPast([...past, present]);
      setFuture(future.slice(1));
      setPresent(next);
      restoreDrafts(next, selectedId);
      setStatus("已重做上一步修改");
      scheduleAutoSave(next);
      return;
    }
    if (!api) return;
    try {
      await api.redoGraph();
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        restoreDrafts(refreshed, selectedId);
        setStatus("已重做上一步持久修改");
        void refreshHistory();
      }
    } catch (error) {
      const code = (error as Error).message;
      setStatus(code === "history_empty" ? "没有可重做的操作" : `重做失败（${code}）`);
    }
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
    if ((selectedNode.locks ?? DEFAULT_LOCKS).content) {
      setStatus("内容已锁定，无法修改");
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
    if ((selectedNode.locks ?? DEFAULT_LOCKS).relations) {
      setStatus("关系已锁定，无法添加子概念");
      return;
    }
    const id = `new-concept-${nextNodeNumber.current++}`;
    const siblings = present.edges.filter((edge) => edge.from === selectedNode.id).length;
    const child: ConceptNode = {
      id,
      title: "新概念",
      note: "在这里记录这个概念的定义、例子或疑问。",
      x: Math.max(8, selectedNode.x + (siblings - 0.5) * 170),
      y: Math.max(8, selectedNode.y + 185),
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

  function addConcept(tone: "root" | "branch" = "branch") {
    // Place the free block at the viewport center (unbounded canvas), so it
    // appears where the user is looking.
    const viewport = canvasViewport.current;
    const centerX = viewport ? (viewport.clientWidth / 2 - camera.x) / camera.zoom : 320;
    const centerY = viewport ? (viewport.clientHeight / 2 - camera.y) / camera.zoom : 240;
    const id = `new-concept-${nextNodeNumber.current++}`;
    const concept: ConceptNode = {
      id,
      title: tone === "root" ? "新总纲" : "新概念",
      note: "在这里记录这个主题的定义、例子或疑问。",
      x: Math.max(8, centerX - 75),
      y: Math.max(8, centerY - 34),
      positionLocked: false,
      tone,
    };
    const next = { ...present, nodes: [...present.nodes, concept] };
    commit(next, tone === "root" ? "已添加总纲，可在右侧编辑标题" : "已添加概念，可在右侧编辑标题");
    setSelectedId(id);
    setTitleDraft(concept.title);
    setNoteDraft(concept.note);
  }

  function handleNodeClick(node: ConceptNode) {
    if (connectMode) {
      if (node.locks?.relations) {
        setStatus("关系已锁定，无法连线");
        return;
      }
      if (!connectSource) {
        setConnectSource(node.id);
        setStatus(`连线起点：${node.title}，请选择终点`);
        return;
      }
      if (connectSource === node.id) {
        setStatus("起点与终点相同，请重新选择起点");
        setConnectSource(null);
        return;
      }
      const already = present.edges.some(
        (edge) =>
          (edge.from === connectSource && edge.to === node.id) ||
          (edge.from === node.id && edge.to === connectSource),
      );
      if (already) {
        setStatus("这两个节点已存在连线");
        setConnectSource(null);
        return;
      }
      const next = {
        ...present,
        edges: [...present.edges, { from: connectSource, to: node.id, edge_type: connectType }],
      };
      commit(next, "已添加连线");
      setConnectSource(null);
      return;
    }
    selectNode(node.id);
  }

  function disconnectEdge(from: string, to: string) {
    const locked = [from, to].some((id) => {
      const node = present.nodes.find((candidate) => candidate.id === id);
      return node?.locks?.relations ?? false;
    });
    if (locked) {
      setStatus("关系已锁定，无法断开连线");
      return;
    }
    const next = {
      ...present,
      edges: present.edges.filter((edge) => !(edge.from === from && edge.to === to)),
    };
    commit(next, "已删除连线");
  }

  function deleteSelected() {
    const locks = selectedNode.locks ?? DEFAULT_LOCKS;
    if (locks.content || locks.relations || locks.position || locks.annotations) {
      setStatus("该节点已锁定，无法删除");
      return;
    }
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
    // Deleting the last node leaves nothing to reselect; the empty-state
    // guide takes over the detail panel.
    if (parent) {
      setSelectedId(parent.id);
      setTitleDraft(parent.title);
      setNoteDraft(parent.note);
    }
  }

  async function toggleLock(dimension: "content" | "position") {
    const node = selectedNode;
    const locks = node.locks ?? DEFAULT_LOCKS;
    const value = !locks[dimension];
    const label = dimension === "content" ? "内容" : "位置";
    const message = value
      ? `已锁定“${node.title}”的${label}`
      : `已解除“${node.title}”的${label}锁定`;

    if (!api) {
      // No backend: keep the session-local lock, preserving the existing demo.
      const next = {
        ...present,
        nodes: present.nodes.map((candidate) =>
          candidate.id === node.id
            ? {
                ...candidate,
                locks: { ...locks, [dimension]: value },
                positionLocked: dimension === "position" ? value : candidate.positionLocked,
              }
            : candidate,
        ),
      };
      commit(next, message);
      return;
    }

    // Backend attached: sync the current snapshot first (so a first-run lock
    // initialises the workspace), then apply the lock through the protected
    // patch gate so it is persisted, enforced, and recorded in history.
    try {
      await api.saveGraph(present);
      await api.applyPatch(buildSetLockPatch(present, node, dimension, value));
      const refreshed = await api.loadGraph();
      if (refreshed) {
        setPresent(refreshed);
        setPast([]);
        setFuture([]);
        const refreshedNode = refreshed.nodes.find((candidate) => candidate.id === node.id);
        if (refreshedNode) {
          setSelectedId(refreshedNode.id);
          setTitleDraft(refreshedNode.title);
          setNoteDraft(refreshedNode.note);
        }
      }
      setStatus(message);
      void refreshHistory();
    } catch (error) {
      const code = (error as Error).message;
      setStatus(code === "target_locked" ? "该维度已锁定，无法修改" : `锁定失败（${code}）`);
    }
  }

  function autoLayout() {
    commit(layoutWorkspace(present), "已自动排布，锁定的节点保持原位");
  }

  function resetDemo() {
    const sample = createSampleWorkspace();
    sample.revisionNo = present.revisionNo;
    setPresent(sample);
    setPast([]);
    setFuture([]);
    restoreDrafts(sample, "course");
    nextNodeNumber.current = 1;
    setStatus("示例已重新载入");
  }

  function startDrag(event: React.PointerEvent<HTMLButtonElement>, node: ConceptNode) {
    if (event.button !== 0) return; // left button only
    // Selecting during a drag must NOT recenter the viewport, otherwise the
    // background visibly jumps the moment a node is grabbed.
    selectNodeKeepCamera(node.id);
    if (node.positionLocked || node.locks?.position) {
      setStatus("位置已锁定，无法移动");
      return;
    }
    event.stopPropagation();
    drag.current = {
      mode: "node",
      nodeId: node.id,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: node.x,
      originY: node.y,
      currentX: node.x,
      currentY: node.y,
      startPanX: 0,
      startPanY: 0,
      before: present,
    };
    // Capture the pointer so pointerup is delivered even when the cursor
    // leaves the button; drag ends reliably instead of sticking.
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // jsdom / unsupported hosts: drag still works via moveDrag.
    }
  }

  function startPan(event: React.PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return; // left button only
    drag.current = {
      mode: "pan",
      nodeId: "",
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: 0,
      originY: 0,
      currentX: 0,
      currentY: 0,
      startPanX: camera.x,
      startPanY: camera.y,
      before: present,
    };
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // jsdom / unsupported hosts: pan still works via moveDrag.
    }
  }

  function moveDrag(event: React.PointerEvent<HTMLElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    // Drag only while the left mouse button is held. If a pointerup was missed
    // (e.g. released outside the window), a button-less move ends the drag
    // instead of letting it stick until the next click.
    if ((event.buttons & 1) === 0) {
      endDrag(event);
      return;
    }
    if (active.mode === "pan") {
      setCamera((prev) => ({
        ...prev,
        x: active.startPanX + (event.clientX - active.startX),
        y: active.startPanY + (event.clientY - active.startY),
      }));
      return;
    }
    const deltaX = (event.clientX - active.startX) / camera.zoom;
    const deltaY = (event.clientY - active.startY) / camera.zoom;
    // Unbounded canvas (WORK-2026-045): no upper clamp; the surface grows with
    // content. The 8px floor keeps nodes reachable near the origin corner.
    const x = Math.max(8, active.originX + deltaX);
    const y = Math.max(8, active.originY + deltaY);
    active.currentX = x;
    active.currentY = y;
    setPresent((snapshot) => ({
      ...snapshot,
      nodes: snapshot.nodes.map((node) => (node.id === active.nodeId ? { ...node, x, y } : node)),
    }));
  }

  function endDrag(event: React.PointerEvent<HTMLElement>) {
    const active = drag.current;
    if (!active || active.pointerId !== event.pointerId) return;
    drag.current = null;
    if (active.mode === "pan") return;
    if (active.currentX === active.originX && active.currentY === active.originY) return;
    // Suppress the browser's synthesized click so it cannot recenter the
    // canvas right after a node drag (WORK-2026-047).
    suppressRecentOnClick.current = true;
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

  function startSidebarResize(event: React.PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    sidebarDrag.current = { startX: event.clientX, startWidth: sidebarWidth };
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // jsdom / unsupported hosts.
    }
  }

  function moveSidebarResize(event: React.PointerEvent<HTMLDivElement>) {
    const active = sidebarDrag.current;
    if (!active) return;
    if ((event.buttons & 1) === 0) {
      sidebarDrag.current = null;
      return;
    }
    const next = Math.max(170, Math.min(480, active.startWidth + (event.clientX - active.startX)));
    setSidebarWidth(next);
  }

  function endSidebarResize() {
    sidebarDrag.current = null;
  }

  function handleWheel(event: React.WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const viewport = canvasViewport.current;
    if (!viewport) return;
    const rect = viewport.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    const step = event.deltaY > 0 ? -0.1 : 0.1;
    setCamera((prev) => {
      const nextZoom = Math.max(0.5, Math.min(2.5, prev.zoom + step));
      const factor = nextZoom / prev.zoom;
      return {
        zoom: nextZoom,
        x: mouseX - (mouseX - prev.x) * factor,
        y: mouseY - (mouseY - prev.y) * factor,
      };
    });
  }

  const surface = canvasSurfaceSize(present.nodes);

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
          {aiSettings?.enabled ? (
            <span className="mode-badge online"><i aria-hidden="true" />AI 已连接</span>
          ) : (
            <span className="mode-badge offline"><i aria-hidden="true" />AI 未连接</span>
          )}
          {api?.getAiSettings && (
            <button type="button" className="ai-settings-button" onClick={() => setShowAiSettings(true)}>
              AI 设置
            </button>
          )}
        </div>
      </header>

      <aside className="compact-boundary" aria-label="演示能力边界">
        <span aria-hidden="true">演示</span>
        <p>示例数据 · 仅本次会话 · AI 未连接 · 来源跳转未接入 · 未连接数据库</p>
      </aside>

      {sidebarHidden && (
        <button
          type="button"
          className="show-sidebar-button"
          aria-label="显示边栏"
          onClick={() => setSidebarHidden(false)}
        >
          » 显示边栏
        </button>
      )}

      <div
        id="workspace"
        className="workspace"
        style={{
          gridTemplateColumns: sidebarHidden
            ? "0px minmax(430px, 1fr) 300px"
            : `${sidebarWidth}px minmax(430px, 1fr) 300px`,
        }}
      >
        <nav
          className={`sidebar${sidebarHidden ? " hidden" : ""}`}
          aria-label="课程与笔记"
          style={{ width: sidebarHidden ? 0 : sidebarWidth }}
        >
          <div className="side-heading">
            <p className="overline">我的课程</p>
            <span className="side-heading-actions">
              {api?.createWorkspace && (
                <button
                  type="button"
                  className="icon-button"
                  aria-label="添加课程"
                  title="新建课程"
                  onClick={() => void handleCreateCourse()}
                >
                  ＋
                </button>
              )}
              <button
                type="button"
                className="icon-button"
                aria-label="隐藏边栏"
                title="隐藏边栏"
                onClick={() => setSidebarHidden(true)}
              >
                «
              </button>
            </span>
          </div>
          <div
            className="sidebar-resize"
            aria-hidden="true"
            onPointerDown={startSidebarResize}
            onPointerMove={moveSidebarResize}
            onPointerUp={endSidebarResize}
          />
          {workspaces.length === 0 && (
            <button type="button" className="course-card active">
              <span className="course-icon">微</span>
              <span><strong>微积分</strong><small>示例课程</small></span>
            </button>
          )}
          {workspaces.map((ws) => (
            <button
              type="button"
              key={ws.id}
              className={`course-card${ws.id === workspaceId ? " active" : ""}`}
              onClick={() => setWorkspaceId(ws.id)}
            >
              <span className="course-icon">{ws.name.slice(0, 1) || "课"}</span>
              <span>
                <strong>{ws.name}</strong>
                <small>{ws.concept_count} 个概念</small>
              </span>
            </button>
          ))}

          {workspaceId === DEFAULT_WORKSPACE_ID && (
            <>
              <div className="notes-heading">
                <p className="overline">相关笔记</p>
                <span>{sampleNotes.length}</span>
              </div>
              <div className="note-list">
                {sampleNotes.map((note, index) => (
                  <button
                    type="button"
                    className="note-link"
                    key={note.title}
                    onClick={() => selectNode(note.nodeId)}
                  >
                    <span className="note-index">0{index + 1}</span>
                    <span><strong>{note.title}</strong><small>{note.detail}</small></span>
                  </button>
                ))}
              </div>
            </>
          )}
          <div className="answer-section" aria-label="问答">
            <p className="overline">向本地知识提问</p>
            <div className="answer-form">
              <input
                type="text"
                aria-label="向本地知识提问"
                placeholder="提问或输入关键词…"
                maxLength={200}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleAsk();
                }}
              />
              <button
                type="button"
                disabled={!question.trim() || answerStatus === "asking"}
                onClick={() => void handleAsk()}
              >
                提问
              </button>
            </div>
            {answerStatus === "asking" && <p className="import-note">AI 思考中…</p>}
          </div>
          <div className="answer-section" aria-label="指令">
            <p className="overline">自然语言指令</p>
            <div className="answer-form">
              <input
                type="text"
                aria-label="向知识树下达指令"
                placeholder="如：连续以极限为前提"
                maxLength={200}
                value={command}
                onChange={(event) => setCommand(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleInterpret();
                }}
              />
              <button
                type="button"
                disabled={!command.trim() || commandStatus === "interpreting" || commandStatus === "applying"}
                onClick={() => void handleInterpret()}
              >
                执行
              </button>
            </div>
            {commandStatus === "interpreting" && <p className="import-note">解释指令中…</p>}
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
            {api?.openResourcesDir && (
              <button
                type="button"
                className="import-control open-dir-control"
                onClick={() => void handleOpenDir()}
              >
                打开资料目录
              </button>
            )}
            {api && (
              <button
                type="button"
                className="import-control workspace-draft-control"
                disabled={draftStatus === "generating" || draftStatus === "applying"}
                onClick={() => void handleGenerateDraft()}
              >
                从全部资料生成思维导图
              </button>
            )}
            {importStatus === "failed" && <p className="import-note">导入失败，请检查文件类型与大小</p>}
            {importStatus === "importing" && <p className="import-note">导入中…</p>}
            {draftStatus === "generating" && <p className="import-note">AI 生成草案中…</p>}
            {draftStatus === "failed" && !draft && (
              <p className="import-note" role="status">{draftError ?? "草案生成失败"}</p>
            )}
            <ul className="resource-list">
              {resources.map((resource) => (
                <li key={resource.id}>
                  <span className="resource-icon" aria-hidden="true">📄</span>
                  <span className="resource-meta">
                    <strong>{resource.display_name}</strong>
                    <small>{resource.mime} · {(resource.byte_size / 1024).toFixed(1)} KB</small>
                  </span>
                  {(resource.mime === "application/pdf" || resource.mime.startsWith("text/")) && (
                    <button
                      type="button"
                      className="resource-open"
                      onClick={() => openViewer(resource)}
                    >
                      打开
                    </button>
                  )}
                  {(resource.mime === "application/pdf" || resource.mime.startsWith("text/")) && (
                    <button
                      type="button"
                      className="resource-draft"
                      disabled={draftStatus === "generating" || draftStatus === "applying"}
                      onClick={() => void handleGenerateDraft(resource)}
                    >
                      生成草案
                    </button>
                  )}
                  {api?.revealResource && (
                    <button
                      type="button"
                      className="resource-reveal"
                      title="在文件资源管理器中显示该文件"
                      onClick={() => void handleReveal(resource)}
                    >
                      在文件夹中显示
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
            <p>
              {api ? (
                <><strong>本地持久化</strong>修改自动保存到本地，可备份与恢复。</>
              ) : (
                <><strong>会话内演示</strong>所有修改仅保留在本次会话，刷新页面后会恢复示例。</>
              )}
            </p>
            {api && (
              <div className="backup-actions" aria-label="本地备份与恢复">
                <button type="button" onClick={() => void handleBackup()}>备份数据</button>
                {backups.length > 0 && (
                  <ul className="backup-list">
                    {backups.map((filename) => (
                      <li key={filename}>
                        <button type="button" onClick={() => void handleRestore(filename)}>
                          恢复 {filename.replace(/^backup-|\.sqlite3$/g, "")}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
          {api && historyRecords.length > 0 && (
            <div className="history-panel" aria-label="版本历史">
              <p className="overline">版本历史</p>
              <ul className="history-list">
                {historyRecords.map((record) => (
                  <li key={record.change_id}>
                    <span className="history-rev">
                      v{record.before_revision_no} → v{record.after_revision_no}
                    </span>
                    {record.source !== "manual" && (
                      <span className="history-source" aria-label="AI 修改">AI</span>
                    )}
                    <span className="history-id">{record.change_id.slice(0, 8)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </nav>

        <section className="canvas-column" aria-label="知识树画布">
          <div className="canvas-toolbar" role="toolbar" aria-label="知识树工具">
            <div className="toolbar-group">
              <button type="button" onClick={() => void undo()} disabled={past.length === 0 && !api}><Icon name="undo" />撤销</button>
              <button type="button" onClick={() => void redo()} disabled={future.length === 0 && !api}><Icon name="redo" />重做</button>
            </div>
            <span className="toolbar-rule" />
            <button type="button" onClick={() => addConcept("branch")}><Icon name="plus" />添加概念</button>
            <button type="button" onClick={() => addConcept("root")}><Icon name="plus" />添加总纲</button>
            <button
              type="button"
              className={connectMode ? "active-tool" : ""}
              onClick={() => {
                setConnectMode((value) => !value);
                setConnectSource(null);
              }}
            >
              <Icon name="link" />连线
            </button>
            {connectMode && (
              <>
                <select
                  aria-label="连线类型"
                  value={connectType}
                  onChange={(event) => setConnectType(event.target.value as EdgeKind)}
                >
                  <option value="related_to">相关</option>
                  <option value="prerequisite_of">先修</option>
                  <option value="part_of">包含</option>
                  <option value="example_of">举例</option>
                </select>
                <span className="canvas-tip">先点起点块，再点终点块；Esc 退出</span>
              </>
            )}
            <button type="button" onClick={autoLayout}><Icon name="layout" />自动排布</button>
            <button type="button" onClick={resetDemo}><Icon name="reset" />重新载入示例</button>
            <span className="canvas-tip">滚轮缩放 · 拖动空白平移 · 拖动节点调整位置</span>
          </div>

          <div className="canvas-viewport" ref={canvasViewport} onWheel={handleWheel}>
            <div
              className="canvas-surface"
              style={{
                width: surface.width,
                height: surface.height,
                transform: `translate(${camera.x}px, ${camera.y}px) scale(${camera.zoom})`,
              }}
              onPointerDown={startPan}
              onPointerMove={moveDrag}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
            >
              <div className="canvas-grid" aria-hidden="true" />
              <svg
                className="edge-layer"
                viewBox={`0 0 ${surface.width} ${surface.height}`}
                style={{ width: surface.width, height: surface.height }}
                aria-hidden="true"
              >
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
                      aria-label={`连线：${from.title} → ${to.title}（${edgeTypeLabel(edge.edge_type ?? "related_to")}）`}
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
                  className={`concept-node ${node.tone}${node.id === selectedNode.id ? " selected" : ""}${node.positionLocked ? " locked" : ""}${connectMode && connectSource === node.id ? " connect-source" : ""}`}
                  style={{ left: node.x, top: node.y }}
                  onClick={() => handleNodeClick(node)}
                  onPointerDown={(event) => startDrag(event, node)}
                >
                  <span className="node-type">{node.tone === "root" ? "主题" : node.tone === "branch" ? "概念" : "知识点"}</span>
                  <strong>{node.title}</strong>
                  {(node.locks?.content ?? false) && <span className="lock-dot content-lock" aria-label="内容已锁定">锁</span>}
                  {node.positionLocked && <span className="lock-dot" aria-label="位置已锁定">⌑</span>}
                </button>
              ))}
            </div>
            {/* Legend stays anchored to the viewport corner, not the (possibly
                huge) transformed surface, so it never drifts out of view. */}
            <div className="canvas-legend" aria-hidden="true">
              <span><i className="legend-root" />主题</span>
              <span><i className="legend-branch" />概念</span>
              <span><i className="legend-leaf" />知识点</span>
            </div>
          </div>
        </section>

        <div className="right-column">
          {present.nodes.length === 0 ? (
          <section className="detail-panel" aria-label="空工作区引导">
          <div className="detail-header">
            <div>
              <p className="overline">节点详情</p>
            </div>
          </div>
          <p className="edge-empty">这个工作区还没有节点。可以导入资料生成 AI 草案，或先添加一个总纲。</p>
          <button type="button" className="primary-button" onClick={() => addConcept("root")}><Icon name="plus" />添加总纲</button>
          </section>
          ) : (
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
            <button type="button" onClick={() => void toggleLock("content")}><Icon name="lock" />{selectedNode.locks?.content ? "解除内容锁定" : "锁定内容"}</button>
            <button type="button" onClick={() => void toggleLock("position")}><Icon name="lock" />{selectedNode.positionLocked ? "解除位置锁定" : "锁定位置"}</button>
            <button type="button" className="danger-button" onClick={deleteSelected}><Icon name="trash" />删除当前节点</button>
          </div>

          <div className="detail-divider" />
          <p className="overline action-label">关联关系（{present.edges.filter((edge) => edge.from === selectedNode.id || edge.to === selectedNode.id).length}）</p>
          {present.edges.filter((edge) => edge.from === selectedNode.id || edge.to === selectedNode.id).length === 0 ? (
            <p className="edge-empty">暂无连线；点「连线」再点两个块即可建立。</p>
          ) : (
            <ul className="edge-list">
              {present.edges
                .filter((edge) => edge.from === selectedNode.id || edge.to === selectedNode.id)
                .map((edge) => {
                  const otherId = edge.from === selectedNode.id ? edge.to : edge.from;
                  const other = present.nodes.find((node) => node.id === otherId);
                  const label = other
                    ? `${edge.from === selectedNode.id ? "指向" : "来自"} ${other.title}`
                    : otherId;
                  return (
                    <li key={`${edge.from}-${edge.to}`}>
                      <span>{label}（{edgeTypeLabel(edge.edge_type ?? "related_to")}）</span>
                      <button
                        type="button"
                        aria-label={`删除连线 ${label}`}
                        onClick={() => disconnectEdge(edge.from, edge.to)}
                      >
                        删除
                      </button>
                    </li>
                  );
                })}
            </ul>
          )}

          <div className="source-card">
            <span className="source-icon" aria-hidden="true">↗</span>
            <div><strong>来源将在后续接入</strong><p>当前示例没有导入文档，不提供虚假的来源跳转。</p></div>
          </div>
          </section>
          )}

          {/* AI_OUTPUT_PLACEHOLDER */}
          {draft && (
          <section className="draft-panel" aria-label="AI 草案预览">
            <header className="viewer-header">
              <div>
                <p className="overline">AI 草案预览</p>
                <strong>从本地资料生成的知识树草案</strong>
              </div>
              <button type="button" className="viewer-close" onClick={rejectDraft}>关闭</button>
            </header>
            <div className="draft-body" aria-live="polite">
              <div className="draft-columns">
                <div className="draft-list">
                  <p className="overline">概念（{draft.draft.concepts.length}）</p>
                  <ul>
                    {draft.draft.concepts.map((concept) => (
                      <li key={concept.label}>
                        <strong>{concept.label}</strong>
                        <span className="draft-confidence">置信度 {Math.round(concept.confidence * 100)}%</span>
                        <span className="draft-source">{concept.evidence_ids.length} 处来源</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="draft-list">
                  <p className="overline">关系（{draft.draft.relations.length}）</p>
                  <ul>
                    {draft.draft.relations.map((relation) => (
                      <li key={`${relation.source_label}->${relation.target_label}`}>
                        <strong>{relation.source_label} → {relation.target_label}</strong>
                        <span className="draft-confidence">置信度 {Math.round(relation.confidence * 100)}%</span>
                      </li>
                    ))}
                    {draft.draft.relations.length === 0 && (
                      <li className="draft-empty">未推断出先修关系</li>
                    )}
                  </ul>
                </div>
              </div>
              <p className="draft-boundary">
                草案仅在预览后经确认门写入；锁定的内容不会被覆盖，写入后可撤销。
              </p>
            </div>
            <footer className="draft-actions">
              {draft.evidence && draft.evidence.length > 0 && (
                <button type="button" className="secondary-button" onClick={jumpToDraftSource}>
                  跳回原文
                </button>
              )}
              <button
                type="button"
                className="primary-button"
                disabled={draftStatus === "applying"}
                onClick={() => void acceptDraft()}
              >
                {draftStatus === "applying" ? "写入中…" : "接受并写入"}
              </button>
              <button type="button" className="secondary-button" onClick={rejectDraft}>拒绝</button>
            </footer>
          </section>
          )}

          {answer && (
          <section className="draft-panel" aria-label="回答">
            <header className="viewer-header">
              <div>
                <p className="overline">带来源回答</p>
                <strong>基于本地知识片段</strong>
              </div>
              <button type="button" className="viewer-close" onClick={() => setAnswer(null)}>关闭</button>
            </header>
            <div className="answer-body" aria-live="polite">
              <p className="answer-text">{answer.answer || "本地没有相关内容，换个关键词试试。"}</p>
              {answer.sources.length > 0 && (
                <nav className="answer-sources" aria-label="回答来源">
                  <p className="overline">来源</p>
                  <ul>
                    {answer.sources.map((source, index) => (
                      <li key={source.id}>
                        <button type="button" onClick={() => jumpToAnswerSource(source.id)}>
                          [{index + 1}] {source.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                </nav>
              )}
            </div>
          </section>
          )}

          {commandResult && (
          <section className="draft-panel" aria-label="指令预览">
            <header className="viewer-header">
              <div>
                <p className="overline">指令预览</p>
                <strong>拟执行的图修改</strong>
              </div>
              <button type="button" className="viewer-close" onClick={rejectCommand}>关闭</button>
            </header>
            <div className="answer-body" aria-live="polite">
              <p className="answer-text">{commandResult.summary}</p>
              <p className="draft-boundary">指令仅在预览后经确认门写入；锁定的内容不会被覆盖，写入后可撤销。</p>
            </div>
            <footer className="draft-actions">
              <button
                type="button"
                className="primary-button"
                disabled={commandStatus === "applying"}
                onClick={() => void acceptCommand()}
              >
                {commandStatus === "applying" ? "写入中…" : "接受并写入"}
              </button>
              <button type="button" className="secondary-button" onClick={rejectCommand}>拒绝</button>
            </footer>
          </section>
          )}

        </div>
      </div>

      {viewerResource && (
        <section className="pdf-viewer" aria-label="资料查看器">
          <header className="viewer-header">
            <div>
              <p className="overline">资料查看器</p>
              <strong>{viewerResource.display_name}</strong>
            </div>
            <div className="viewer-controls">
              {viewerResource.mime === "application/pdf" && (
                <>
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
                </>
              )}
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
            ) : viewerResource.mime === "text/markdown" ? (
              <div
                className="markdown-body"
                // renderMarkdown escapes raw text first, so this is XSS-safe.
                dangerouslySetInnerHTML={{ __html: renderMarkdown(viewerText) }}
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

      {showAiSettings && (
        <div className="ai-settings-overlay" role="dialog" aria-label="AI 设置" aria-modal="true">
          <div className="ai-settings-dialog">
            <div className="ai-settings-head">
              <p className="overline">AI 设置</p>
              <strong>接入 DeepSeek</strong>
              <span>
                {aiSettings?.enabled
                  ? "状态：已连接（可生成草案 / 提问 / 执行指令）"
                  : "状态：未连接（无 Key 时 AI 功能不可用）"}
              </span>
            </div>
            <label className="ai-settings-field">
              DeepSeek API Key
              <input
                type="password"
                value={aiKeyInput}
                placeholder="粘贴 sk- 开头的 API Key（仅保存在本机数据目录）"
                onChange={(event) => setAiKeyInput(event.target.value)}
              />
            </label>
            <div className="ai-settings-actions">
              <button type="button" className="primary" onClick={() => void handleSaveAiKey()}>
                保存并启用
              </button>
              <button type="button" onClick={() => void handleClearAiKey()}>
                清除 Key
              </button>
              <button type="button" onClick={() => setShowAiSettings(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
