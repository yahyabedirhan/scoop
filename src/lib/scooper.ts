import type { Inspector } from "./inspector";
import type { Scroller } from "./scroll/scroller";
import type { Mode } from "./modes/modes";
import { DomNavigator, type Direction } from "./dom-navigator";
import { formatHTML } from "./utils/format-html";
import { MessageType } from "./messages";

/**
 * The orchestrator, named after the extension itself ("Scoop").
 *
 * Registers the pointer/keyboard listeners, owns which mode is active, and
 * sequences `Inspector` and `Scroller`. It is the only entity that holds both
 * of them, and therefore the only place that needs to know both exist.
 *
 * Everything that touches `chrome.*` is injected at the constructor boundary
 * (`getStoredModeId`, `setStoredModeId`, `notify`), so neither `Scooper` nor its
 * tests ever need a mocked `chrome` global.
 */

const UI_ID = "__inspect_copy_ui";

/**
 * Breathing room between a scrolled-to target and the viewport edge it lands
 * against (also keeps it clear of a fixed page header).
 */
const SCROLL_MARGIN = 96;

/**
 * Hover-label glyphs, keyed by mode id.
 *
 * Paint (fill/stroke) is set in `content.css`; a plain presentation attribute
 * would lose to the `all: initial` reset every node under `#__inspect_copy_ui`
 * gets. Geometry (`d`, `cx`/`cy`/`r`) is *also* a CSS property in Chrome and is
 * reset the same way, but differs per icon, so each is repeated inline via
 * `style`. Inline style beats any external rule regardless of specificity, so
 * it survives the reset without `content.css` needing to change.
 */
const ICONS: Record<string, string> = {
  "full-html":
    '<svg viewBox="0 0 24 24"><path d="M8 5 3 12l5 7M16 5l5 7-5 7" style="d:path(\'M8 5 3 12l5 7M16 5l5 7-5 7\')"/></svg>',
  "clean-html":
    '<svg viewBox="0 0 24 24"><path d="M8 5 3 12l5 7M16 5l5 7-5 7" style="d:path(\'M8 5 3 12l5 7M16 5l5 7-5 7\')"/><circle class="ic-icon-dot" cx="12" cy="12" r="1.6" style="cx:12px;cy:12px;r:1.6px"/></svg>',
  "plain-text":
    '<svg viewBox="0 0 24 24"><path d="M5 6h14M12 6v13" style="d:path(\'M5 6h14M12 6v13\')"/></svg>',
  markdown:
    '<svg viewBox="0 0 24 24"><path d="M3 17V7l4 5 4-5v10M17 7v7M14 11l3 3 3-3" style="d:path(\'M3 17V7l4 5 4-5v10M17 7v7M14 11l3 3 3-3\')"/></svg>',
};

/** How `Scooper` restores the last-used mode and reports lifecycle changes. */
export interface ScooperDeps {
  inspector: Inspector;
  scroller: Scroller;
  modes: readonly Mode[];
  /**
   * Read the persisted mode id. `cb` may be called synchronously or later; by
   * the time it runs the session may have ended or already moved on, which
   * `Scooper` checks before applying the result.
   */
  getStoredModeId: (cb: (id: string | undefined) => void) => void;
  setStoredModeId: (id: string) => void;
  /** Report `MessageType.Started` / `.Ended` to the service worker. */
  notify: (type: MessageType) => void;
}

interface Session {
  copying: boolean;
  mode: Mode;
}

interface UI {
  root: HTMLElement;
  overlay: HTMLElement;
  label: HTMLElement;
  labelIcon: HTMLElement;
  labelText: HTMLElement;
}

interface LengthCache {
  target: Element;
  modeId: string;
  length: number;
}

type StopReason = "copied" | "escape" | "toggle";

export class Scooper {
  private readonly inspector: Inspector;
  private readonly scroller: Scroller;
  private readonly modes: readonly Mode[];
  private readonly getStoredModeId: ScooperDeps["getStoredModeId"];
  private readonly setStoredModeId: ScooperDeps["setStoredModeId"];
  private readonly notify: ScooperDeps["notify"];
  private readonly nav = new DomNavigator();

  private session: Session | null = null;
  private target: Element | null = null;
  private lastMouse = { x: 0, y: 0 };
  private ui: UI | null = null;
  /**
   * Caches the transform+format cost by (target, mode): the overlay also
   * redraws on scroll/resize, where the target hasn't changed, so this keeps
   * the expensive part to once per genuine target/mode change.
   */
  private lengthCache: LengthCache | null = null;

  private readonly listeners: [keyof WindowEventMap, EventListener][];

  constructor(deps: ScooperDeps) {
    this.inspector = deps.inspector;
    this.scroller = deps.scroller;
    this.modes = deps.modes;
    this.getStoredModeId = deps.getStoredModeId;
    this.setStoredModeId = deps.setStoredModeId;
    this.notify = deps.notify;

    // All in the capture phase, so Scoop sees events before the page does.
    this.listeners = [
      ["mousemove", this.onMouseMove as EventListener],
      ["mousedown", this.swallow as EventListener],
      ["mouseup", this.swallow as EventListener],
      ["click", this.onClick as EventListener],
      ["keydown", this.onKeyDown as EventListener],
      ["scroll", this.onScrollOrResize as EventListener],
      ["resize", this.onScrollOrResize as EventListener],
    ];
  }

  /** The one public entry point: flip inspect mode on or off. */
  toggle(): void {
    if (this.session) this.stop("toggle");
    else this.start();
  }

  // --- UI ----------------------------------------------------------------

  private buildUI(): UI {
    const root = document.createElement("div");
    root.id = UI_ID;
    root.setAttribute("data-inspect-copy", "");

    const overlay = document.createElement("div");
    overlay.className = "ic-overlay";

    const label = document.createElement("div");
    label.className = "ic-label";
    const labelIcon = document.createElement("span");
    labelIcon.className = "ic-label-icon";
    const labelText = document.createElement("span");
    labelText.className = "ic-label-text";
    label.appendChild(labelIcon);
    label.appendChild(labelText);

    root.appendChild(overlay);
    root.appendChild(label);
    this.inspector.mount(root);
    return { root, overlay, label, labelIcon, labelText };
  }

  /** Arrow navigation skips document metadata and Scoop's own overlay nodes. */
  private skipForNav = (el: Element | null): boolean =>
    this.nav.isSkippable(el) || this.inspector.isExtensionNode(el);

  private setTarget(el: Element | null): void {
    if (!el || el.nodeType !== 1 || this.inspector.isExtensionNode(el) || el === this.target) return;
    this.target = el;
    this.drawOverlay();
  }

  /** A mode's output is either a node (needs `formatHTML`) or a ready string. */
  private stringify(output: Element | string): string {
    return typeof output === "string" ? output : formatHTML(output);
  }

  /**
   * The hover label's text for the active mode. Purely data-driven off the
   * mode's `showDescriptor` / `showDimensions` / `showLength` fields. Nothing
   * here branches on which mode is active, so a future mode only sets those
   * fields, it doesn't touch this method.
   */
  private buildLabelText(mode: Mode, r: DOMRect): string {
    const target = this.target!;
    const parts: string[] = [];
    if (mode.showDescriptor === "full") parts.push(this.nav.describeElement(target));
    else if (mode.showDescriptor === "tag") parts.push(target.tagName.toLowerCase());
    if (mode.showDimensions) parts.push(Math.round(r.width) + "×" + Math.round(r.height));
    let text = parts.join("  ");
    if (mode.showLength) {
      if (!this.lengthCache || this.lengthCache.target !== target || this.lengthCache.modeId !== mode.id) {
        // Settle any pending scroll patch first, for the same reason `doCopy`
        // does: the clone must not carry an injected `scroll-margin` style,
        // which would inflate the char count shown in the label.
        this.scroller.flush();
        const output = mode.transform(this.inspector.capture(target));
        this.lengthCache = { target, modeId: mode.id, length: this.stringify(output).length };
      }
      text += (text ? "  ·  " : "") + this.lengthCache.length + " chars";
    }
    return text;
  }

  private drawOverlay(): void {
    if (!this.target || !this.ui || !this.session) return;
    const r = this.target.getBoundingClientRect();
    const o = this.ui.overlay.style;
    o.display = "block";
    o.top = r.top + "px";
    o.left = r.left + "px";
    o.width = Math.max(0, r.width) + "px";
    o.height = Math.max(0, r.height) + "px";

    const mode = this.session.mode;
    if (this.ui.label.dataset.icon !== mode.id) {
      this.ui.labelIcon.innerHTML = ICONS[mode.id] || "";
      this.ui.label.dataset.icon = mode.id;
    }
    this.ui.labelText.textContent = this.buildLabelText(mode, r);
    this.ui.label.style.display = "flex";
    // Place the label just above the box, or just below if there is no room.
    const labelH = 20;
    let ly = r.top - labelH - 2;
    if (ly < 0) ly = r.bottom + 2;
    this.ui.label.style.top = ly + "px";
    this.ui.label.style.left = Math.max(0, r.left) + "px";
  }

  private showToast(text: string, x: number, y: number, isError: boolean): void {
    if (!this.ui) return;
    const toast = document.createElement("div");
    toast.className = "ic-toast" + (isError ? " ic-toast-error" : "");
    toast.textContent = (isError ? "✕ " : "✓ ") + text;
    this.ui.root.appendChild(toast);
    const tx = Math.min(Math.max(8, x), window.innerWidth - 8);
    const ty = Math.min(Math.max(8, y), window.innerHeight - 8);
    toast.style.left = tx + "px";
    toast.style.top = ty + "px";
    requestAnimationFrame(() => toast.classList.add("ic-toast-in"));
    setTimeout(() => {
      toast.classList.remove("ic-toast-in");
      setTimeout(() => toast.remove(), 250);
    }, 1200);
  }

  // --- Clipboard -------------------------------------------------------

  /**
   * The async Clipboard API is the only write path.
   *
   * A click or Enter handler in a secure context (the only place the element
   * picker is usable at all) already satisfies `writeText`'s user-gesture
   * requirement, so no `document.execCommand` fallback is needed. A rejection
   * surfaces as the "Copy failed" toast.
   */
  private async copyText(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  private async doCopy(originX: number, originY: number): Promise<void> {
    if (!this.target || !this.session || this.session.copying) return;
    const owner = this.session;
    const desc = this.nav.describeElement(this.target);
    // Guarantee no pending scroll patch is still on the live page before cloning.
    this.scroller.flush();
    const output = owner.mode.transform(this.inspector.capture(this.target));
    const html = this.stringify(output);
    owner.copying = true;
    const ok = await this.copyText(html);
    if (this.session !== owner) return; // This inspection ended while copying.
    owner.copying = false;
    if (ok) {
      this.showToast("Copied " + desc, originX, originY, false);
      this.stop("copied");
    } else {
      this.showToast("Copy failed", originX, originY, true);
    }
  }

  // --- Event handlers (capture phase) ---------------------------------

  private onMouseMove = (e: MouseEvent): void => {
    this.lastMouse = { x: e.clientX, y: e.clientY };
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (el && !this.inspector.isExtensionNode(el)) this.setTarget(el);
  };

  private swallow = (e: Event): void => {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
  };

  private onClick = (e: MouseEvent): void => {
    this.swallow(e);
    void this.doCopy(e.clientX, e.clientY);
  };

  private onKeyDown = (e: KeyboardEvent): void => {
    if (!this.session) return;

    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      this.stop("escape");
      return;
    }

    const mode = this.modes.find((m) => m.key === e.key);
    if (mode) {
      e.preventDefault();
      e.stopPropagation();
      if (this.session.mode !== mode) {
        this.session.mode = mode;
        this.drawOverlay();
        this.setStoredModeId(mode.id);
      }
      return;
    }

    const dirs: Record<string, Direction> = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
    };

    if (e.key in dirs) {
      e.preventDefault();
      e.stopPropagation();
      const next = this.nav.nextTarget(this.target, dirs[e.key], this.skipForNav);
      if (next) {
        this.target = next;
        this.drawOverlay();
        this.scrollTargetIntoView();
      }
      return;
    }

    if (e.key === " " || e.code === "Space") {
      // Only intercepted to stop the page scrolling.
      e.preventDefault();
      e.stopPropagation();
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      if (this.target) {
        const r = this.target.getBoundingClientRect();
        void this.doCopy(r.left + Math.min(r.width, 40), Math.max(0, r.top));
      }
    }
  };

  /**
   * Scroll an arrow-selected target into view when it lands offscreen.
   *
   * Aligns to whichever edge the target went past so the page keeps its natural
   * scroll direction; a target taller than the viewport falls back to
   * top-alignment. The `Scroller` decides *how* to do the scrolling.
   */
  private scrollTargetIntoView(): void {
    if (!this.target) return;
    const r = this.target.getBoundingClientRect();
    const vh = window.innerHeight;
    const above = r.top < SCROLL_MARGIN;
    const below = r.bottom > vh - SCROLL_MARGIN;
    const offSide = r.left < 0 || r.right > window.innerWidth;
    if (!above && !below && !offSide) return;

    const tallerThanViewport = r.height + SCROLL_MARGIN * 2 > vh;
    const toEnd = below && !above && !tallerThanViewport;

    this.scroller.scrollIntoView(this.target, {
      block: toEnd ? "end" : "start",
      inline: "nearest",
      margin: SCROLL_MARGIN,
    });
    const owner = this.session;
    requestAnimationFrame(() => {
      if (this.session === owner) this.drawOverlay();
    });
  }

  private onScrollOrResize = (): void => {
    this.drawOverlay();
  };

  // --- Lifecycle ------------------------------------------------------

  private start(): void {
    if (this.session) return;
    const owner: Session = (this.session = { copying: false, mode: this.modes[0] });
    this.ui = this.buildUI();
    this.target = null;

    for (const [type, fn] of this.listeners) window.addEventListener(type, fn, true);
    this.inspector.setInspecting(true);

    // Seed the target from the current pointer position if we can.
    const el = document.elementFromPoint(this.lastMouse.x, this.lastMouse.y);
    if (el && !this.inspector.isExtensionNode(el)) this.setTarget(el);

    // Restore the last-used mode once storage answers; if the session already
    // ended or moved to a different mode by then, drop it.
    this.getStoredModeId((id) => {
      if (this.session !== owner || owner.mode !== this.modes[0]) return;
      const stored = this.modes.find((m) => m.id === id);
      if (stored) {
        owner.mode = stored;
        this.drawOverlay();
      }
    });

    this.notify(MessageType.Started);
  }

  private stop(reason: StopReason): void {
    if (!this.session) return;
    this.session = null;

    for (const [type, fn] of this.listeners) window.removeEventListener(type, fn, true);
    this.inspector.setInspecting(false);
    // No scroll residue left behind on exit, eagerly, without waiting for the
    // pending animation frame.
    this.scroller.flush();
    this.target = null;
    this.lengthCache = null;

    const root = this.ui?.root ?? null;
    this.ui = null;
    if (root) {
      if (reason === "copied") {
        // A "Copied" toast is animating inside root. Drop the picker chrome now,
        // then remove the whole node once the toast has faded.
        for (const sel of [".ic-overlay", ".ic-label"]) {
          const n = root.querySelector<HTMLElement>(sel);
          if (n) n.style.display = "none";
        }
        setTimeout(() => root.remove(), 1600);
      } else {
        root.remove();
      }
    }

    this.notify(MessageType.Ended);
  }
}
