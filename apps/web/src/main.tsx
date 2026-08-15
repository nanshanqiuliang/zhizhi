import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { httpPersistApi } from "./api";
import "./styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element is missing");
}

const apiBase = import.meta.env.VITE_LOCAL_API ?? "http://127.0.0.1:8000";
const apiFactory = (workspaceId: string) => httpPersistApi(apiBase, workspaceId);

createRoot(root).render(
  <StrictMode>
    <App apiFactory={apiFactory} />
  </StrictMode>,
);
