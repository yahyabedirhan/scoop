/**
 * Service-worker entry: owns the toolbar action, injects the content bundle on
 * demand, and keeps the `ON` badge in sync with per-tab inspect-mode state.
 */
import { MessageType, type Message } from "../lib/messages";

/** Tab ids where inspect mode is currently on. */
const activeTabs = new Set<number>();

const BADGE_TEXT = "ON";
const BADGE_COLOR = "#1a73e8";

async function setBadge(tabId: number, on: boolean): Promise<void> {
  try {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: BADGE_COLOR });
    await chrome.action.setBadgeText({ tabId, text: on ? BADGE_TEXT : "" });
  } catch {
    // Tab may have closed; ignore.
  }
}

async function ensureInjected(tabId: number): Promise<void> {
  // Injecting twice is safe: content.ts guards against double init. The single
  // bundle carries every `src/lib/` dependency inlined.
  await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] });
  await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
}

async function toggleOnTab(tab: chrome.tabs.Tab | undefined): Promise<void> {
  if (!tab || tab.id == null) return;
  const tabId = tab.id;
  try {
    await ensureInjected(tabId);
    await chrome.tabs.sendMessage(tabId, { type: MessageType.Toggle } satisfies Message);
  } catch (e) {
    // Most common cause: a restricted page (chrome://, the Web Store, PDF
    // viewer) where content scripts cannot run.
    console.warn("Scoop: cannot run on this page.", e);
  }
}

// Toolbar icon.
chrome.action.onClicked.addListener((tab) => void toggleOnTab(tab));

/**
 * Keyboard shortcut (default Ctrl+Shift+S / Cmd+Shift+S, rebindable at
 * `chrome://extensions/shortcuts`). Newer Chrome passes the active tab; fall
 * back to querying it.
 */
chrome.commands.onCommand.addListener(async (command, tab) => {
  if (command !== "toggle-scoop") return;
  if (!tab) {
    [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  }
  void toggleOnTab(tab);
});

chrome.runtime.onMessage.addListener((msg: Message, sender) => {
  const tabId = sender.tab?.id;
  if (tabId == null || !msg || typeof msg.type !== "string") return;

  if (msg.type === MessageType.Started) {
    activeTabs.add(tabId);
    void setBadge(tabId, true);
  } else if (msg.type === MessageType.Ended) {
    activeTabs.delete(tabId);
    void setBadge(tabId, false);
  }
});

/**
 * The injected script does not survive a navigation, so clear our state when
 * the page reloads or navigates.
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" && activeTabs.has(tabId)) {
    activeTabs.delete(tabId);
    void setBadge(tabId, false);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  activeTabs.delete(tabId);
});
