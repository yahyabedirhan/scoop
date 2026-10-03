// Renders the Chrome Web Store images into assets/store/ with headless Chrome.
//
// Run through `npm run store-assets`, which builds dist/ first so the
// screenshots run the current content.js. Set CHROME to use a Chrome binary
// other than the macOS default.
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const HERE = fileURLToPath(new URL(".", import.meta.url));
const OUT = fileURLToPath(new URL("../../assets/store/", import.meta.url));

const TARGETS = [
  // Headless Chrome will not open a window narrower than about 500 px, so the
  // 440x280 tile is laid out at twice its size and captured at half scale.
  { out: "promo-small.png", page: "promo.html", size: [880, 560], scale: 0.5 },
  { out: "promo-marquee.png", page: "promo.html", size: [1400, 560] },
  { out: "screenshot-1.png", page: "screenshot.html?shot=1", size: [1280, 800] },
  { out: "screenshot-2.png", page: "screenshot.html?shot=2", size: [1280, 800] },
  { out: "screenshot-3.png", page: "screenshot.html?shot=3", size: [1280, 800] },
];

mkdirSync(OUT, { recursive: true });
for (const { out, page, size, scale = 1 } of TARGETS) {
  const url = pathToFileURL(HERE + page.split("?")[0]).href + (page.includes("?") ? "?" + page.split("?")[1] : "");
  execFileSync(CHROME, [
    "--headless",
    "--disable-gpu",
    "--hide-scrollbars",
    `--force-device-scale-factor=${scale}`,
    "--allow-file-access-from-files",
    "--virtual-time-budget=2000",
    `--window-size=${size.join(",")}`,
    `--screenshot=${OUT}${out}`,
    url,
  ], { stdio: "ignore" });
  console.log("wrote", "assets/store/" + out);
}
