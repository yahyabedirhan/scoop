import { defineConfig } from "vite";
import { viteStaticCopy } from "vite-plugin-static-copy";

/**
 * Two self-contained bundles, one per entry, built in separate passes
 * (`--mode content`, `--mode background`).
 *
 * - Content scripts are injected by `chrome.scripting.executeScript({ files })`,
 *   which cannot load ES modules, so each entry is emitted as a standalone IIFE
 *   with every dependency inlined — no shared chunk between the two.
 * - `dist/` is wiped once by `npm run clean` before the first pass; neither pass
 *   empties it, so the second bundle lands beside the first.
 * - The background pass also copies the static files (`manifest.json`, `icons/`,
 *   `content.css`) so `dist/` is the complete "Load unpacked" folder.
 */
export default defineConfig(({ mode }) => {
  const entry = mode === "background" ? "background" : "content";

  return {
    build: {
      outDir: "dist",
      emptyOutDir: false,
      target: "chrome111",
      minify: false,
      lib: {
        entry: `src/entries/${entry}.ts`,
        formats: ["iife"],
        name: `__scoop_${entry}`,
        fileName: () => `${entry}.js`,
      },
    },
    plugins:
      entry === "background"
        ? [
            viteStaticCopy({
              targets: [
                { src: "manifest.json", dest: "." },
                { src: "icons/*", dest: "icons" },
                { src: "content.css", dest: "." },
              ],
            }),
          ]
        : [],
  };
});
