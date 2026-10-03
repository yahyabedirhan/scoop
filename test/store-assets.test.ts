// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { describe, test, expect } from "vitest";

// The images uploaded to the Chrome Web Store, at the sizes its dashboard
// accepts. `npm run store-assets` renders them; this only checks what ships.

const ROOT = new URL("../", import.meta.url);

function pngSize(path: string): [number, number] {
  const bytes = readFileSync(new URL(path, ROOT));
  expect(bytes.toString("latin1", 1, 4)).toBe("PNG");
  expect(bytes.toString("latin1", 12, 16)).toBe("IHDR");
  return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
}

describe("Chrome Web Store images", () => {
  test.each([
    ["assets/store/promo-small.png", 440, 280],
    ["assets/store/promo-marquee.png", 1400, 560],
    ["assets/store/screenshot-1.png", 1280, 800],
    ["assets/store/screenshot-2.png", 1280, 800],
    ["assets/store/screenshot-3.png", 1280, 800],
  ])("%s is %ix%i", (path, width, height) => {
    expect(pngSize(path)).toEqual([width, height]);
  });
});
