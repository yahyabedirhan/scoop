import { test, expect, beforeEach, afterEach, vi } from "vitest";
import {
  MarginScroller,
  applyScrollMargin,
  restoreScrollMargin,
} from "../../src/lib/scroll/margin-scroller";
import type { ScrollAlignment } from "../../src/lib/scroll/scroller";

const START: ScrollAlignment = { block: "start", inline: "nearest", margin: 96 };

let frames: FrameRequestCallback[];

beforeEach(() => {
  frames = [];
  vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) => {
    frames.push(fn);
    return frames.length;
  });
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => vi.unstubAllGlobals());

const runFrames = () => frames.splice(0).forEach((fn) => fn(0));

function elementFor(html: string): HTMLElement {
  document.body.innerHTML = html;
  return document.body.firstElementChild as HTMLElement;
}

test("scrollIntoView applies the margin, then the next frame reverts it", () => {
  const el = elementFor("<p>Hi</p>");
  const scroller = new MarginScroller();
  scroller.scrollIntoView(el, START);
  expect(el.style.getPropertyValue("scroll-margin-top")).toBe("96px");
  expect(el.scrollIntoView).toHaveBeenCalledOnce();
  runFrames();
  expect(el.hasAttribute("style")).toBe(false);
});

test("flush() settles a pending change synchronously, before its frame", () => {
  const el = elementFor("<p>Hi</p>");
  const scroller = new MarginScroller();
  scroller.scrollIntoView(el, START);
  scroller.flush();
  expect(el.hasAttribute("style")).toBe(false);
  runFrames(); // the stale frame is now a no-op
  expect(el.hasAttribute("style")).toBe(false);
});

test("repeated navigation on the same element never retains a Scoop margin", () => {
  const el = elementFor("<p>Hi</p>");
  const scroller = new MarginScroller();
  scroller.scrollIntoView(el, START);
  scroller.scrollIntoView(el, START);
  scroller.scrollIntoView(el, START);
  runFrames();
  expect(el.hasAttribute("style")).toBe(false);
});

test("a throwing scrollIntoView reverts the margin and rethrows", () => {
  const el = elementFor("<p>Hi</p>");
  (el.scrollIntoView as ReturnType<typeof vi.fn>).mockImplementation(() => {
    throw new Error("boom");
  });
  const scroller = new MarginScroller();
  expect(() => scroller.scrollIntoView(el, START)).toThrow("boom");
  expect(el.hasAttribute("style")).toBe(false);
});

// --- Pure scroll-margin math ---------------------------------------------

test("applyScrollMargin sets both margin properties and records the prior state", () => {
  const el = elementFor('<p style="color:red">Hi</p>');
  const change = applyScrollMargin(el, 96);
  expect(el.style.getPropertyValue("scroll-margin-top")).toBe("96px");
  expect(el.style.getPropertyValue("scroll-margin-bottom")).toBe("96px");
  expect(change.original).toBe("color:red");
  expect(change.marginValue).toBe("96px");
});

test("restoreScrollMargin on an untouched element puts the original style attribute back exactly", () => {
  const el = elementFor('<p style="color:red">Hi</p>');
  restoreScrollMargin(el, applyScrollMargin(el, 96));
  expect(el.getAttribute("style")).toBe("color:red");
});

test("restoreScrollMargin removes the style attribute entirely when there was none", () => {
  const el = elementFor("<p>Hi</p>");
  restoreScrollMargin(el, applyScrollMargin(el, 96));
  expect(el.hasAttribute("style")).toBe(false);
});

test("restoreScrollMargin keeps a page edit made after the patch, dropping only Scoop's margins", () => {
  const el = elementFor("<p>Hi</p>");
  const change = applyScrollMargin(el, 96);
  el.style.color = "blue";
  restoreScrollMargin(el, change);
  expect(el.style.getPropertyValue("color")).toBe("blue");
  expect(el.style.getPropertyValue("scroll-margin-top")).toBe("");
  expect(el.style.getPropertyValue("scroll-margin-bottom")).toBe("");
});

test("restoreScrollMargin leaves a page-overridden margin (different value) alone", () => {
  const el = elementFor("<p>Hi</p>");
  const change = applyScrollMargin(el, 96);
  el.style.setProperty("scroll-margin-top", "13px");
  restoreScrollMargin(el, change);
  expect(el.style.getPropertyValue("scroll-margin-top")).toBe("13px");
});
