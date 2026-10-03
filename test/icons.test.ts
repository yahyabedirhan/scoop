// @vitest-environment node
// This reference adds Node types to the whole program, since there is one
// tsconfig. That is accepted because these tests need node:fs and node:zlib,
// and src/ must still not rely on Node globals.
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

/** Alpha channel of an 8-bit RGBA, non-interlaced PNG, as one array per row. */
function alphaRows(png: Png): Uint8Array[] {
  const { bytes, width, height } = png;
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
  const rows: Uint8Array[] = [];
  let prev = new Uint8Array(stride);
  for (let r = 0; r < height; r++) {
    const filter = raw[r * (stride + 1)];
    const line = raw.subarray(r * (stride + 1) + 1, (r + 1) * (stride + 1));
    const row = new Uint8Array(stride);
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? row[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      const p = a + b - c;
      const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      const predictor = [0, a, b, (a + b) >> 1, pa <= pb && pa <= pc ? a : pb <= pc ? b : c][filter];
      row[i] = (line[i] + predictor) & 0xff;
    }
    rows.push(row.filter((_, i) => i % bpp === 3));
    prev = row;
  }
  return rows;
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

  test("the 128 px icon keeps Chrome's 16 px transparent margin", () => {
    const rows = alphaRows(readPng(manifest.icons["128"]));
    rows.forEach((row, y) =>
      row.forEach((alpha, x) => {
        if (x < 16 || x >= 112 || y < 16 || y >= 112) expect(alpha, `(${x}, ${y})`).toBe(0);
      }),
    );
  });

  test("the 16 px icon is cropped to the mark, so the mark reaches its top and bottom rows", () => {
    const rows = alphaRows(readPng(manifest.icons["16"]));
    expect(Math.max(...rows[0])).toBeGreaterThan(0);
    expect(Math.max(...rows[15])).toBeGreaterThan(0);
  });

  test.each(declared)("%s %s px (%s) is transparent around the mark, with a clear top-right corner", (_where, _size, path) => {
    const rows = alphaRows(readPng(path));
    expect(rows[0][rows[0].length - 1]).toBe(0);
  });
});

describe("README logo", () => {
  const LOGO = "assets/images/logo/scoop.png";

  test("is a 512 x 512 PNG, so the 128 px README image is sharp on retina screens", () => {
    const png = readPng(LOGO);
    expect([png.width, png.height]).toEqual([512, 512]);
  });

  test("keeps a transparent margin around an opaque tile, as Shipyard's logo does", () => {
    const rows = alphaRows(readPng(LOGO));
    expect(rows[256][0]).toBe(0);
    expect(rows[256][256]).toBe(255);
  });
});

describe("logo folder", () => {
  // The generator reads the two SVG masters and writes only the README logo
  // beside them, so no stale preview or concept is left behind.
  test("holds the masters, the README logo and the archive only", () => {
    const files = readdirSync(new URL("assets/images/logo/", ROOT)).filter((name) => !name.startsWith("."));
    expect(files.sort()).toEqual(["archive", "scoop-16.svg", "scoop.png", "scoop.svg"]);
  });
});

describe("archived icons", () => {
  // Rejected figures kept as a record. The generator never writes here.
  const archived = readdirSync(new URL("assets/images/logo/archive/", ROOT)).filter((name) => !name.startsWith("."));

  test("the rejected icons and concepts, including the former pointer icon, are archived", () => {
    expect(archived.sort()).toEqual([
      "scoop-ball-terminal.png",
      "scoop-ball.png",
      "scoop-bite.png",
      "scoop-brackets.png",
      "scoop-carve.png",
      "scoop-clip-spoon.png",
      "scoop-clipboard-bite.png",
      "scoop-clipboard-scoop.png",
      "scoop-clipboard.png",
      "scoop-cone-cursor.png",
      "scoop-cradle.png",
      "scoop-cursor-scoop.png",
      "scoop-ladle.png",
      "scoop-lifted-o.png",
      "scoop-marquee.png",
      "scoop-monogram.png",
      "scoop-peel.png",
      "scoop-pointer-scoop.png",
      "scoop-pointer.png",
      "scoop-scoop-arc.png",
      "scoop-scoop-cone.png",
      "scoop-scoop-to-clipboard.png",
      "scoop-scoop-tub.png",
      "scoop-scooped-line.png",
      "scoop-scooper.png",
      "scoop-spoon-line.png",
      "scoop-spoon-pointer-ball.png",
      "scoop-spoon-pointer-line.png",
      "scoop-spoon-pointer-square.png",
      "scoop-window-cup.png",
    ]);
  });

  test.each(archived)("%s is a 512 x 512 PNG", (name) => {
    const png = readPng(`assets/images/logo/archive/${name}`);
    expect([png.width, png.height]).toEqual([512, 512]);
  });
});
