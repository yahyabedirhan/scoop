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

/** Pixels of an 8-bit RGBA, non-interlaced PNG, as one [r, g, b, a] array per pixel per row. */
function pixelRows(png: Png): number[][][] {
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
  const rows: number[][][] = [];
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
    rows.push(Array.from({ length: width }, (_, x) => [...row.subarray(x * bpp, (x + 1) * bpp)]));
    prev = row;
  }
  return rows;
}

/** Alpha channel of an 8-bit RGBA, non-interlaced PNG, as one array per row. */
function alphaRows(png: Png): number[][] {
  return pixelRows(png).map((row) => row.map((pixel) => pixel[3]));
}

/** Whether an [r, g, b, a] pixel is the white tile: opaque and near white. */
const isWhite = ([r, g, b, a]: number[]) => a === 255 && Math.min(r, g, b) >= 0xe8;
/** Whether an [r, g, b, a] pixel is the green mark: opaque, with green well above red and blue. */
const isGreen = ([r, g, b, a]: number[]) => a === 255 && g - r > 40 && g - b > 40;

/**
 * The extension icons' colourway, read from the shipped 128 px icon rather
 * than assumed, so switching it in the generator needs no change here. Its
 * tile is the colour most of its opaque pixels have, and the mark is drawn in
 * the other one: cream, which isWhite also matches, on green, or green on white.
 */
function iconColourway() {
  const tile = pixelRows(readPng(manifest.icons["128"])).flat().filter(([, , , a]) => a === 255);
  const white = tile.filter(isWhite).length > tile.length / 2;
  return white
    ? { name: "the green mark on a white tile", isTile: isWhite, isMark: isGreen }
    : { name: "the cream mark on a green tile", isTile: isGreen, isMark: isWhite };
}

interface Box {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

/** The bounding box of the pixels that hit, in whole pixels of the PNG, edges included. */
function boundingBox(png: Png, hit: (pixel: number[]) => boolean): Box {
  const xs: number[] = [];
  const ys: number[] = [];
  pixelRows(png).forEach((row, y) =>
    row.forEach((pixel, x) => {
      if (hit(pixel)) {
        xs.push(x);
        ys.push(y);
      }
    }),
  );
  return { left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys) };
}

/** The mark's box and the tile's box, the tile being every pixel that is not transparent. */
function markAndTile(png: Png, isMark: (pixel: number[]) => boolean) {
  return { mark: boundingBox(png, isMark), tile: boundingBox(png, ([, , , a]) => a > 0) };
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

  test.each(["16", "32"])("the %s px icon's tile fills the canvas, so the mark is as large as it can be", (size) => {
    const rows = alphaRows(readPng(manifest.icons[size]));
    const mid = rows.length / 2;
    for (const alpha of [rows[0][mid], rows[rows.length - 1][mid], rows[mid][0], rows[mid][rows.length - 1]]) {
      expect(alpha).toBe(255);
    }
  });

  test.each(declared)("%s %s px (%s) is a squircle tile, transparent at its corners", (_where, _size, path) => {
    const rows = alphaRows(readPng(path));
    const last = rows.length - 1;
    expect([rows[0][0], rows[0][last], rows[last][0], rows[last][last]]).toEqual([0, 0, 0, 0]);
  });

  test.each(declared)("%s %s px (%s) is in the 128 px icon's colourway, a tile of one colour and a mark of the other", (_where, _size, path) => {
    const { name, isTile, isMark } = iconColourway();
    const pixels = pixelRows(readPng(path)).flat();
    const tile = pixels.filter(([, , , a]) => a === 255);
    expect(tile.filter(isTile).length, name).toBeGreaterThan(tile.length / 2);
    expect(pixels.some(isMark), name).toBe(true);
  });

  // Spec 06's mark is the spoon-pointer alone, a tall shape, so its size is
  // its height. With its padding halved in 0.0.10 it spans 0.75 of the tile at
  // 16 px and 0.80 at 128 px, where 0.0.9's spanned 0.56 and 0.63.
  test.each(["16", "32", "48", "128"])("the %s px icon's mark spans more than 0.7 of its tile's height", (size) => {
    const { isMark } = iconColourway();
    const { mark, tile } = markAndTile(readPng(manifest.icons[size]), isMark);
    expect((mark.bottom - mark.top + 1) / (tile.bottom - tile.top + 1)).toBeGreaterThan(0.7);
  });

  // The mark used to sit off to one side of its tile. Antialiasing can shift
  // a box edge by a pixel, so the centres may differ by up to one pixel.
  test.each(["16", "32", "48", "128"])("the %s px icon's mark is centred on its tile", (size) => {
    const { isMark } = iconColourway();
    const { mark, tile } = markAndTile(readPng(manifest.icons[size]), isMark);
    expect(Math.abs((mark.left + mark.right) / 2 - (tile.left + tile.right) / 2)).toBeLessThanOrEqual(1);
    expect(Math.abs((mark.top + mark.bottom) / 2 - (tile.top + tile.bottom) / 2)).toBeLessThanOrEqual(1);
  });
});

describe("README logos", () => {
  const GREEN_LOGO = "assets/images/logo/scoop.png";
  const WHITE_LOGO = "assets/images/logo/scoop-on-white.png";

  test.each([GREEN_LOGO, WHITE_LOGO])("%s is a 512 x 512 PNG, so the 128 px README image is sharp on retina screens", (logo) => {
    const png = readPng(logo);
    expect([png.width, png.height]).toEqual([512, 512]);
  });

  test.each([GREEN_LOGO, WHITE_LOGO])("%s keeps a transparent margin around an opaque tile, as Shipyard's logo does", (logo) => {
    const rows = alphaRows(readPng(logo));
    expect(rows[256][0]).toBe(0);
    expect(rows[256][256]).toBe(255);
  });

  test("the green logo has a green tile and the white logo a white one", () => {
    // (100, 256) lies on the tile, left of the mark, in both logos.
    expect(isGreen(pixelRows(readPng(GREEN_LOGO))[256][100])).toBe(true);
    expect(isWhite(pixelRows(readPng(WHITE_LOGO))[256][100])).toBe(true);
  });
});

describe("logo folder", () => {
  // The generator reads the one SVG master and writes only the README logos
  // beside it, so no stale preview, concept or retired cut is left behind.
  test("holds the master, the README logos and the archive only", () => {
    const files = readdirSync(new URL("assets/images/logo/", ROOT)).filter((name) => !name.startsWith("."));
    expect(files.sort()).toEqual(["archive", "scoop-on-white.png", "scoop.png", "scoop.svg"]);
  });
});

describe("archived icons", () => {
  // Rejected figures kept as a record. The generator never writes here.
  const archived = readdirSync(new URL("assets/images/logo/archive/", ROOT)).filter((name) => !name.startsWith("."));

  test("the rejected icons and concepts, including the former pointer icon, spec 05's other four prototypes and the page-and-spoon icon it shipped, are archived", () => {
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
      "scoop-compact-glyph.png",
      "scoop-cone-cursor.png",
      "scoop-cradle.png",
      "scoop-cursor-scoop.png",
      "scoop-heavy.png",
      "scoop-ladle.png",
      "scoop-lifted-o.png",
      "scoop-marquee.png",
      "scoop-monogram.png",
      "scoop-page-and-spoon.png",
      "scoop-peel.png",
      "scoop-pointer-scoop.png",
      "scoop-pointer.png",
      "scoop-scoop-arc.png",
      "scoop-scoop-cone.png",
      "scoop-scoop-to-clipboard.png",
      "scoop-scoop-tub.png",
      "scoop-scooped-line.png",
      "scoop-scooper.png",
      "scoop-spoon-led.png",
      "scoop-spoon-line.png",
      "scoop-spoon-pointer-ball.png",
      "scoop-spoon-pointer-line.png",
      "scoop-spoon-pointer-square.png",
      "scoop-tight-diagonal.png",
      "scoop-window-cup.png",
    ]);
  });

  test.each(archived)("%s is a 512 x 512 PNG", (name) => {
    const png = readPng(`assets/images/logo/archive/${name}`);
    expect([png.width, png.height]).toEqual([512, 512]);
  });
});
