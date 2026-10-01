import { test, expect, vi, afterEach } from "vitest";
import { Scooper } from "../src/lib/scooper";
import { Inspector } from "../src/lib/inspector";
import { MarginScroller } from "../src/lib/scroll/margin-scroller";
import { MODES } from "../src/lib/modes/modes";
import type { Scroller } from "../src/lib/scroll/scroller";

/**
 * Input-driven behavioral tests: a real `Inspector` and `Scroller`, real
 * `MODES`, with only the `chrome.*` boundary (storage + messaging) and the
 * clipboard faked. Drives real key/pointer events against jsdom and asserts on
 * the resulting DOM / label / clipboard state — the same seam the old
 * `test/content.test.js` used.
 */

interface Harness {
  scooper: Scooper;
  writes: { text: string; resolve: () => void; reject: (e: unknown) => void }[];
  messages: string[];
  stored: Record<string, string>;
  toggle: () => void;
  key: (key: string) => void;
  point: (el: Element) => void;
  frame: () => void;
  label: () => string;
  labelIcon: () => string | undefined;
}

let active: Harness | null = null;

afterEach(() => {
  // Detach any listeners a still-running Scooper left on `window`.
  if (active && active.messages.at(-1) === "inspect:started") active.scooper.toggle();
  active = null;
  vi.unstubAllGlobals();
  document.documentElement.innerHTML = "<head></head><body></body>";
  document.documentElement.removeAttribute("class");
});

function setup(
  markup = '<button id="pick">Pick me</button>',
  store: Record<string, string> = {},
  scroller: Scroller = new MarginScroller(),
): Harness {
  document.documentElement.removeAttribute("class");
  document.head.innerHTML = "";
  const htmlMatch = markup.match(/^\s*<html([^>]*)>([\s\S]*)<\/html>\s*$/i);
  if (htmlMatch) {
    const cls = htmlMatch[1].match(/class="([^"]*)"/);
    if (cls) document.documentElement.setAttribute("class", cls[1]);
    const bodyInner = htmlMatch[2].match(/<body[^>]*>([\s\S]*)<\/body>/i);
    document.body.innerHTML = bodyInner ? bodyInner[1] : "";
  } else {
    document.body.innerHTML = markup;
  }

  const writes: Harness["writes"] = [];
  const messages: string[] = [];
  const frames: FrameRequestCallback[] = [];

  let pointed: Element = document.querySelector("#pick") || document.body;
  document.elementFromPoint = () => pointed;
  Element.prototype.scrollIntoView = () => {};
  vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) => {
    frames.push(fn);
    return frames.length;
  });

  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: (text: string) =>
        new Promise<void>((resolve, reject) => {
          writes.push({ text, resolve, reject });
        }),
    },
  });

  const scooper = new Scooper({
    inspector: new Inspector(),
    scroller,
    modes: MODES,
    getStoredModeId: (cb) => cb(store["activeModeId"]),
    setStoredModeId: (id) => {
      store["activeModeId"] = id;
    },
    notify: (type) => messages.push(type),
  });

  const harness: Harness = {
    scooper,
    writes,
    messages,
    stored: store,
    toggle: () => scooper.toggle(),
    key: (key) =>
      window.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true })),
    point: (el) => {
      pointed = el;
      window.dispatchEvent(new MouseEvent("mousemove", { clientX: 100, clientY: 100 }));
    },
    frame: () => frames.splice(0).forEach((fn) => fn(0)),
    label: () => document.querySelector(".ic-label-text")!.textContent!,
    labelIcon: () => (document.querySelector(".ic-label") as HTMLElement).dataset.icon,
  };
  active = harness;
  return harness;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

test("repeated copy input waits for the pending write and a failed copy can be retried", async () => {
  const app = setup();
  app.toggle();
  app.key("Enter");
  app.key("Enter");
  window.dispatchEvent(new MouseEvent("click", { cancelable: true }));
  expect(app.writes.length).toBe(1);
  app.writes[0].reject(new Error("Denied"));
  await settle();
  expect(document.querySelector(".ic-toast")!.textContent).toBe("✕ Copy failed");
  app.key("Enter");
  expect(app.writes.length).toBe(2);
  app.writes[1].resolve();
  await settle();
  expect(app.messages.filter((m) => m === "inspect:ended").length).toBe(1);
});

test("a copy completing after Escape and restart leaves the new inspection active", async () => {
  const app = setup();
  app.toggle();
  app.key("Enter");
  app.key("Escape");
  app.toggle();
  app.writes[0].resolve();
  await settle();
  expect(app.messages.at(-1)).toBe("inspect:started");
  expect(document.querySelector(".ic-toast")).toBe(null);
  app.key("Enter");
  expect(app.writes.length).toBe(2);
});

test("a rejected old copy cannot affect a new inspection", async () => {
  const app = setup();
  app.toggle();
  app.key("Enter");
  app.key("Escape");
  app.toggle();
  app.writes[0].reject(new Error("Denied"));
  await settle();
  expect(document.querySelector(".ic-toast")).toBe(null);
  expect(app.messages.at(-1)).toBe("inspect:started");
});

test("a rejected copy leaves inspection running so it can be retried", async () => {
  const app = setup();
  app.toggle();
  app.key("Enter");
  app.writes[0].reject(new Error("Denied"));
  await settle();
  expect(document.querySelector(".ic-toast")!.textContent).toBe("✕ Copy failed");
  app.key("Enter");
  app.writes[1].resolve();
  await settle();
  expect(app.messages.at(-1)).toBe("inspect:ended");
});

test("copying body excludes Steal UI while preserving page markup with similar names", () => {
  const app = setup('<main data-inspect-copy=""><p id="__inspect_copy_ui">Page content</p></main>');
  app.toggle();
  app.point(document.body);
  app.key("Enter");
  expect(app.writes[0].text).toBe(
    [
      "<body>",
      '  <main data-inspect-copy="">',
      '    <p id="__inspect_copy_ui">',
      "      Page content",
      "    </p>",
      "  </main>",
      "</body>",
    ].join("\n"),
  );
});

test("copying html excludes the inspect class and preserves new page classes on exit", () => {
  const app = setup('<html class="  site  "><head></head><body>Page</body></html>');
  app.toggle();
  app.point(document.documentElement);
  app.key("Enter");
  expect(app.writes[0].text).toBe(
    ['<html class="  site  ">', "  <head></head>", "  <body>", "    Page", "  </body>", "</html>"].join("\n"),
  );
  document.documentElement.classList.add("changed-by-page");
  app.key("Escape");
  expect(document.documentElement.className).toBe("site changed-by-page");
});

test("copying before the scroll frame preserves the original inline styles", () => {
  const app = setup('<main id="pick"><p style="color:red;scroll-margin-top:7px!important">Child</p></main>');
  app.toggle();
  app.key("ArrowRight");
  app.key("Enter");
  expect(app.writes[0].text).toBe('<p style="color:red;scroll-margin-top:7px!important">\n  Child\n</p>');
  app.key("Escape");
  expect(document.querySelector("p")!.getAttribute("style")).toBe("color:red;scroll-margin-top:7px!important");
  app.frame();
  expect(document.querySelector("p")!.getAttribute("style")).toBe("color:red;scroll-margin-top:7px!important");
});

test("scroll cleanup preserves page edits and repeated navigation never retains Steal margins", () => {
  const app = setup('<main id="pick"><p>Child</p></main>');
  const child = document.querySelector("p") as HTMLElement;
  app.toggle();
  app.key("ArrowRight");
  app.key("ArrowLeft");
  app.key("ArrowRight");
  child.style.color = "blue";
  child.style.setProperty("scroll-margin-top", "13px");
  app.frame();
  app.key("Enter");
  expect(app.writes[0].text).toBe('<p style="scroll-margin-top: 13px; color: blue;">\n  Child\n</p>');
  expect(document.querySelector("main")!.hasAttribute("style")).toBe(false);
});

test("an early stop() eagerly reverts a still-pending scroll patch (flush on exit)", () => {
  const flush = vi.fn();
  const scroller: Scroller = { scrollIntoView: vi.fn(), flush };
  const app = setup('<main id="pick"><p>Child</p></main>', {}, scroller);
  app.toggle();
  app.key("ArrowRight");
  expect(scroller.scrollIntoView).toHaveBeenCalledOnce();
  app.key("Escape");
  // stop() flushed without waiting for the animation frame.
  expect(flush).toHaveBeenCalled();
});

test("copy() flushes the scroller before capturing", () => {
  const calls: string[] = [];
  const scroller: Scroller = {
    scrollIntoView: vi.fn(),
    flush: () => calls.push("flush"),
  };
  const app = setup('<button id="pick">Hi</button>', {}, scroller);
  const originalCapture = Inspector.prototype.capture;
  const spy = vi
    .spyOn(Inspector.prototype, "capture")
    .mockImplementation(function (this: Inspector, el: Element) {
      calls.push("capture");
      return originalCapture.call(this, el);
    });
  app.toggle();
  app.key("Enter");
  expect(calls).toEqual(["flush", "capture"]);
  spy.mockRestore();
});

test("an earlier success toast is excluded from the next body copy", async () => {
  const app = setup();
  app.toggle();
  app.key("Enter");
  app.writes[0].resolve();
  await settle();
  expect(document.querySelector(".ic-toast")!.textContent).toBe("✓ Copied button#pick");
  app.toggle();
  app.point(document.body);
  app.key("Enter");
  expect(app.writes[1].text).toBe('<body>\n  <button id="pick">\n    Pick me\n  </button>\n</body>');
});

test("ordinary page elements with Steal's ID are selectable and their clicks are suppressed", () => {
  const app = setup('<button id="__inspect_copy_ui">Page button</button>');
  const button = document.querySelector("button") as HTMLButtonElement;
  let pageClicks = 0;
  button.addEventListener("click", () => pageClicks++);
  app.toggle();
  app.point(button);
  const click = new MouseEvent("click", { bubbles: true, cancelable: true });
  button.dispatchEvent(click);
  expect(app.writes[0].text).toBe('<button id="__inspect_copy_ui">\n  Page button\n</button>');
  expect(click.defaultPrevented).toBe(true);
  expect(pageClicks).toBe(0);
  app.key("Escape");
  button.click();
  expect(pageClicks).toBe(1);
});

test("a clipboard write that throws synchronously surfaces as a failed copy", async () => {
  const app = setup();
  navigator.clipboard.writeText = () => {
    throw new Error("Blocked");
  };
  app.toggle();
  app.key("Enter");
  await settle();
  expect(document.querySelector(".ic-toast")!.textContent).toBe("✕ Copy failed");
  expect(app.messages.at(-1)).toBe("inspect:started");
});

test("a digit key switches the active mode without copying or moving the target", () => {
  const app = setup('<div id="pick" class="card">Hello <b>world</b></div>');
  app.toggle();
  expect(app.labelIcon()).toBe("full-html");
  app.key("3");
  expect(app.labelIcon()).toBe("plain-text");
  expect(app.label()).toBe("11 chars");
  expect(app.writes.length).toBe(0);
  app.key("Enter");
  expect(app.writes[0].text).toBe("Hello world");
});

test("pressing 4 during inspection selects Markdown without copying or moving the target", () => {
  const app = setup('<div id="pick" class="card"><h2>Types</h2></div>');
  app.toggle();
  app.key("4");
  expect(app.labelIcon()).toBe("markdown");
  expect(app.writes.length).toBe(0);
  app.key("Enter");
  expect(app.writes[0].text).toBe("## Types");
});

test("switching mode persists as the default for the next inspection", () => {
  const store: Record<string, string> = {};
  const markup = '<div id="pick" class="card"><p>Text</p></div>';

  const first = setup(markup, store);
  first.toggle();
  first.key("2");
  expect(first.labelIcon()).toBe("clean-html");
  first.key("Escape");

  const second = setup(markup, store);
  second.toggle();
  expect(second.labelIcon()).toBe("clean-html");
  second.key("Enter");
  expect(second.writes[0].text).toBe("<div>\n  <p>\n    Text\n  </p>\n</div>");
});

test("Clean HTML's live label length matches what Enter actually copies", () => {
  const app = setup('<div id="pick" class="card" data-x="1"><p class="a">Text</p></div>');
  app.toggle();
  app.key("2");
  const expectedHtml = "<div>\n  <p>\n    Text\n  </p>\n</div>";
  expect(app.label()).toBe("div  0×0  ·  " + expectedHtml.length + " chars");
  app.key("Enter");
  expect(app.writes[0].text).toBe(expectedHtml);
});
