import type { Scroller, ScrollAlignment } from "./scroller";

/**
 * A `Scroller` backed by a temporary `scroll-margin` patch that self-cleans on
 * the next animation frame.
 *
 * The browser's own `Element.scrollIntoView` walks to the nearest scrollable
 * ancestor (a plain `window.scrollBy` would miss elements inside a scroll
 * container), and `scroll-margin` is the only way to give it the edge gap it
 * otherwise has no option for. The patch is reverted a frame later, or
 * immediately via `flush()`, so it is never captured as page content.
 *
 * The property-diffing math (`applyScrollMargin` / `restoreScrollMargin`) sits
 * at the bottom of this file as pure input/output functions: no `Map`, no
 * timing, no `requestAnimationFrame`.
 */
export class MarginScroller implements Scroller {
  private readonly scrollChanges = new Map<Element, ScrollMarginChange>();

  scrollIntoView(el: Element, alignment: ScrollAlignment): void {
    // A repeated arrow press must never save our own previous margin as the
    // "original" for the next revert.
    const pending = this.scrollChanges.get(el);
    if (pending) this.finishScroll(el, pending);

    const change = applyScrollMargin(el, alignment.margin);
    this.scrollChanges.set(el, change);
    try {
      el.scrollIntoView({ block: alignment.block, inline: alignment.inline });
    } catch (error) {
      this.finishScroll(el, change);
      throw error;
    }
    requestAnimationFrame(() => this.finishScroll(el, change));
  }

  flush(): void {
    for (const [el, change] of this.scrollChanges) this.finishScroll(el, change);
  }

  /** Revert one still-pending change, unless a newer one has replaced it. */
  private finishScroll(el: Element, change: ScrollMarginChange): void {
    if (this.scrollChanges.get(el) !== change) return;
    restoreScrollMargin(el, change);
    this.scrollChanges.delete(el);
  }
}

// --- Pure scroll-margin math ------------------------------------------------

const NAMES = ["scroll-margin-top", "scroll-margin-bottom"] as const;

interface PreviousProperty {
  name: string;
  value: string;
  priority: string;
}

/** Everything `restoreScrollMargin` needs to undo one `applyScrollMargin`. */
export interface ScrollMarginChange {
  /** `style` attribute text before the patch (`null` if there was no attribute). */
  original: string | null;
  /** `style` attribute text immediately after the patch. */
  applied: string | null;
  /** The value written to each margin property, e.g. `"96px"`. */
  marginValue: string;
  /** Each patched property's prior value and priority. */
  previous: PreviousProperty[];
}

/**
 * Write `marginPx` to both scroll-margin properties on `el` and return a record
 * describing exactly what changed.
 */
export function applyScrollMargin(el: Element, marginPx: number): ScrollMarginChange {
  const style = (el as HTMLElement).style;
  const marginValue = marginPx + "px";
  const previous: PreviousProperty[] = NAMES.map((name) => ({
    name,
    value: style.getPropertyValue(name),
    priority: style.getPropertyPriority(name),
  }));
  const original = el.getAttribute("style");
  for (const name of NAMES) style.setProperty(name, marginValue);
  return { original, applied: el.getAttribute("style"), marginValue, previous };
}

/**
 * Undo an `applyScrollMargin`.
 *
 * - If the `style` attribute is still byte-for-byte what the patch produced,
 *   restore the original attribute exactly (including whether it existed).
 * - Otherwise the page has edited the element since; restore only the margin
 *   properties Scoop still owns (value unchanged, priority not raised to
 *   `!important`), leaving every other page edit alone, priorities included.
 */
export function restoreScrollMargin(el: Element, change: ScrollMarginChange): void {
  if (el.getAttribute("style") === change.applied) {
    if (change.original === null) el.removeAttribute("style");
    else el.setAttribute("style", change.original);
    return;
  }
  const style = (el as HTMLElement).style;
  for (const prev of change.previous) {
    if (
      style.getPropertyValue(prev.name) === change.marginValue &&
      style.getPropertyPriority(prev.name) === ""
    ) {
      style.setProperty(prev.name, prev.value, prev.priority);
    }
  }
}
