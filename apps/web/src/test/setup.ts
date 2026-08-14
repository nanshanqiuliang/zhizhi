import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// pdfjs-dist touches DOMMatrix at import time; jsdom does not provide it.
if (typeof globalThis.DOMMatrix === "undefined") {
  class DOMMatrixPolyfill {
    a = 1;
    b = 0;
    c = 0;
    d = 1;
    e = 0;
    f = 0;
    m11 = 1;
    m12 = 0;
    m13 = 0;
    m14 = 0;
    m21 = 0;
    m22 = 1;
    m23 = 0;
    m24 = 0;
    m31 = 0;
    m32 = 0;
    m33 = 1;
    m34 = 0;
    m41 = 0;
    m42 = 0;
    m43 = 0;
    m44 = 1;
    is2D = true;
    isIdentity = true;
    constructor(init?: string | number[]) {
      if (typeof init === "string" && init.includes(",")) {
        const values = init.split(",").map(Number);
        if (values.length >= 6) {
          this.a = values[0];
          this.b = values[1];
          this.c = values[2];
          this.d = values[3];
          this.e = values[4];
          this.f = values[5];
        }
      }
    }
    multiply(other: DOMMatrixPolyfill) {
      return other;
    }
    translate() {
      return this;
    }
    scale() {
      return this;
    }
    rotate() {
      return this;
    }
    inverse() {
      return this;
    }
    transformPoint(point: { x: number; y: number }) {
      return { x: point.x * this.a + this.e, y: point.y * this.d + this.f, z: 0, w: 1 };
    }
  }
  globalThis.DOMMatrix = DOMMatrixPolyfill as unknown as typeof DOMMatrix;
}

afterEach(() => {
  cleanup();
});
