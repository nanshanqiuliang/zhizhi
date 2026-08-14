import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";

// The worker is served from the app's public directory (copied from the
// pdfjs-dist package), so the same `/pdf.worker.min.mjs` URL works in dev and
// in the production build — avoiding the Windows path-with-spaces issue that
// breaks `?url`/`@fs` resolution in dev.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

import type { AnchorRef } from "./api";

type PdfRendererProps = {
  fileUrl: string;
  page: number;
  activeAnchor: AnchorRef | null;
};

export function PdfRenderer({ fileUrl, page, activeAnchor }: PdfRendererProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [pageSize, setPageSize] = useState<{ width: number; height: number } | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "failed">("loading");

  useEffect(() => {
    let cancelled = false;

    const docTask = pdfjs.getDocument({ url: fileUrl }).promise;
    docTask
      .then(async (doc) => {
        if (cancelled) return;
        const pageHandle = await doc.getPage(page);
        if (cancelled) return;
        const viewport = pageHandle.getViewport({ scale: 1.6 });
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await pageHandle.render({ canvas, viewport }).promise;
        if (cancelled) return;
        setPageSize({ width: viewport.width, height: viewport.height });
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("failed");
      });

    return () => {
      cancelled = true;
    };
  }, [fileUrl, page]);

  return (
    <div className="pdf-render" aria-label="PDF 渲染视图">
      <div
        className="pdf-page"
        style={pageSize ? { width: pageSize.width, height: pageSize.height } : undefined}
      >
        <canvas
          ref={canvasRef}
          aria-label="PDF 页面画布"
          style={pageSize ? { width: pageSize.width, height: pageSize.height } : undefined}
        />
        {status === "loading" && (
          <div className="pdf-overlay" aria-label="PDF 渲染中">正在渲染 PDF…</div>
        )}
        {status === "failed" && (
          <div className="pdf-overlay error" aria-label="PDF 渲染失败">PDF 渲染失败，请确认文件可读。</div>
        )}
        {activeAnchor?.bboxNorm && pageSize && (
          <div
            className="bbox-highlight"
            aria-label="锚点高亮区域"
            style={{
              left: `${activeAnchor.bboxNorm[0] * 100}%`,
              top: `${activeAnchor.bboxNorm[1] * 100}%`,
              width: `${(activeAnchor.bboxNorm[2] - activeAnchor.bboxNorm[0]) * 100}%`,
              height: `${(activeAnchor.bboxNorm[3] - activeAnchor.bboxNorm[1]) * 100}%`,
            }}
          />
        )}
      </div>
    </div>
  );
}
