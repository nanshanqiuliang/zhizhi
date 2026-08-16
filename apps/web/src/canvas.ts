/** Content-driven canvas geometry (WORK-2026-045). */

export const CANVAS_MIN_WIDTH = 1000;
export const CANVAS_MIN_HEIGHT = 650;
const CANVAS_MARGIN = 48;
const NODE_WIDTH = 150;
const NODE_HEIGHT = 68;

export interface SurfaceSize {
  width: number;
  height: number;
}

/** Content-driven canvas size: node bounding box + node size + margin, floored. */
export function canvasSurfaceSize(nodes: readonly { x: number; y: number }[]): SurfaceSize {
  let maxX = 0;
  let maxY = 0;
  for (const node of nodes) {
    if (node.x > maxX) maxX = node.x;
    if (node.y > maxY) maxY = node.y;
  }
  return {
    width: Math.max(CANVAS_MIN_WIDTH, maxX + NODE_WIDTH + CANVAS_MARGIN),
    height: Math.max(CANVAS_MIN_HEIGHT, maxY + NODE_HEIGHT + CANVAS_MARGIN),
  };
}
