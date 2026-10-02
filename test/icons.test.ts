// @vitest-environment node
/// <reference types="node" />
import { readdirSync, readFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { describe, test, expect } from "vitest";

// The seam is what ships: the icon files as manifest.json declares them, not
// how tools/gen-icons.py draws them.

const ROOT = new URL("../", import.meta.url);
const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

const manifest = JSON.parse(readFileSync(new URL("manifest.json", ROOT), "utf8")) as {
  icons: Record<string, string>;
  action: { default_icon: Record<string, string> };
};

interface Png {
  width: number;
  height: number;
  bytes: Buffer;
}

function readPng(path: string): Png {
  const bytes = readFileSync(new URL(path, ROOT));
  expect([...bytes.subarray(0, 8)]).toEqual(PNG_SIGNATURE);
  // IHDR is always the first chunk; its width and height follow the type tag.
  expect(bytes.toString("latin1", 12, 16)).toBe("IHDR");
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20), bytes };
}

/** Alpha of the pixel at (x, y) of an 8-bit RGBA, non-interlaced PNG. */
function alphaAt(png: Png, x: number, y: number): number {
  const { bytes, width } = png;
  expect([bytes[24], bytes[25], bytes[28]]).toEqual([8, 6, 0]); // depth, RGBA, no interlace
  const idat: Buffer[] = [];
  for (let at = 8; at < bytes.length; ) {
    const length = bytes.readUInt32BE(at);
    if (bytes.toString("latin1", at + 4, at + 8) === "IDAT") idat.push(bytes.subarray(at + 8, at + 8 + length));
    at += 12 + length;
  }
  const raw = inflateSync(Buffer.concat(idat));
  const bpp = 4;
  const stride = width * bpp;
  let prev = new Uint8Array(stride);
  let row = new Uint8Array(stride);
  for (let r = 0; r <= y; r++) {
    const filter = raw[r * (stride + 1)];
    const line = raw.subarray(r * (stride + 1) + 1, (r + 1) * (stride + 1));
    row = new Uint8Array(stride);
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? row[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      const p = a + b - c;
      const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      const predictor = [0, a, b, (a + b) >> 1, pa <= pb && pa <= pc ? a : pb <= pc ? b : c][filter];
      row[i] = (line[i] + predictor) & 0xff;
    }
    prev = row;
  }
  return row[x * bpp + 3];
}

describe("extension icons", () => {
  const declared = [
    ...Object.entries(manifest.icons).map(([size, path]) => ["icons", size, path]),
    ...Object.entries(manifest.action.default_icon).map(([size, path]) => ["action.default_icon", size, path]),
  ];

  test("the manifest declares the 16, 32, 48 and 128 px icons in both places", () => {
    expect(Object.keys(manifest.icons)).toEqual(["16", "32", "48", "128"]);
    expect(Object.keys(manifest.action.default_icon)).toEqual(["16", "32", "48", "128"]);
  });

  test.each(declared)("%s %s px (%s) is a PNG of the declared size", (_where, size, path) => {
    const png = readPng(path);
    expect([png.width, png.height]).toEqual([Number(size), Number(size)]);
  });

  test("icons/ holds only the declared icons, since the build copies the folder into dist/ whole", () => {
    const declaredFiles = Object.values(manifest.icons).map((path) => path.replace(/^icons\//, ""));
    const files = readdirSync(new URL("icons/", ROOT)).filter((name) => !name.startsWith("."));
    expect(files.sort()).toEqual(declaredFiles.sort());
  });

  test("the 16 px tile fills the canvas, so the middle of its left edge is opaque", () => {
    const png = readPng(manifest.icons["16"]);
    expect(alphaAt(png, 0, 8)).toBe(255);
  });
});

describe("README logo", () => {
  const LOGO = "assets/images/logo/scoop.png";

  test("is a 512 x 512 PNG, so the 128 px README image is sharp on retina screens", () => {
    const png = readPng(LOGO);
    expect([png.width, png.height]).toEqual([512, 512]);
  });

  test("keeps a transparent margin around the tile, as the 128 px icon does", () => {
    const png = readPng(LOGO);
    expect(alphaAt(png, 0, 256)).toBe(0);
  });
});

describe("alternate icon previews", () => {
  // The variants not shipped are written beside the README logo as previews.
  const previews = readdirSync(new URL("assets/images/logo/", ROOT)).filter((name) => /^scoop-.+\.png$/.test(name));

  test("the pointer and ball variants have previews", () => {
    expect(previews.sort()).toEqual(["scoop-ball.png", "scoop-pointer.png"]);
  });

  test.each(previews)("%s is a 512 x 512 PNG with the logo's transparent margin", (name) => {
    const png = readPng(`assets/images/logo/${name}`);
    expect([png.width, png.height]).toEqual([512, 512]);
    expect(alphaAt(png, 0, 256)).toBe(0);
  });
});
