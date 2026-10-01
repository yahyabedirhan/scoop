/**
 * Content-script entry: the `chrome.storage` / `chrome.runtime` boundary.
 *
 * Injected on demand by `background.ts`. Everything with real logic lives in
 * `src/lib/` and never touches `chrome.*`; this file only wires that logic to
 * the extension runtime and guards against being injected twice.
 */
import { Scooper } from "../lib/scooper";
import { Inspector } from "../lib/inspector";
import { MarginScroller } from "../lib/scroll/margin-scroller";
import { MODES } from "../lib/modes/modes";
import { MessageType, type Message } from "../lib/messages";

const MODE_STORAGE_KEY = "activeModeId";

declare global {
  interface Window {
    __stealScooper?: Scooper;
  }
}

/**
 * Re-injected on every toolbar click. Once loaded, the background's
 * `MessageType.Toggle` message is the single source of truth, so just bail.
 */
if (!window.__stealScooper) {
  const scooper = new Scooper({
    inspector: new Inspector(),
    scroller: new MarginScroller(),
    modes: MODES,

    getStoredModeId: (cb) => {
      try {
        chrome.storage.local.get([MODE_STORAGE_KEY], (result) => {
          cb(result[MODE_STORAGE_KEY]);
        });
      } catch {
        // Extension context invalidated (e.g. reloaded). Stay on the default.
        cb(undefined);
      }
    },

    setStoredModeId: (id) => {
      try {
        chrome.storage.local.set({ [MODE_STORAGE_KEY]: id });
      } catch {
        // Extension context invalidated (e.g. reloaded). Nothing to do.
      }
    },

    notify: (type) => {
      try {
        chrome.runtime.sendMessage({ type } satisfies Message);
      } catch {
        // Extension context invalidated (e.g. reloaded). Nothing to do.
      }
    },
  });

  window.__stealScooper = scooper;

  chrome.runtime.onMessage.addListener((msg: Message) => {
    if (msg && msg.type === MessageType.Toggle) scooper.toggle();
  });
}
