/**
 * Side-effect-free DOM traversal for arrow-key selection, plus the element
 * descriptions the hover label shows.
 *
 * Knows nothing about the extension runtime: it takes a `skip` predicate from
 * the caller (so `Scooper` can fold in "is this Scoop's own node?") and never
 * touches anything outside the nodes passed to it.
 */

export type Direction = "up" | "down" | "left" | "right";

/** Predicate: should arrow traversal step straight over this element? */
export type SkipPredicate = (el: Element | null) => boolean;

/**
 * Elements never worth selecting: document metadata and other non-visual nodes.
 * Pressing Right on `<html>` steps over `<head>` and lands on `<body>`.
 */
const SKIP_TAGS = new Set([
  "HEAD",
  "META",
  "TITLE",
  "SCRIPT",
  "LINK",
  "STYLE",
  "BASE",
  "NOSCRIPT",
]);

function isElement(node: unknown): node is Element {
  return !!node && (node as Node).nodeType === 1;
}

export class DomNavigator {
  /** True for non-elements and document-metadata tags (see `SKIP_TAGS`). */
  isSkippable(el: Element | null): boolean {
    return !isElement(el) || SKIP_TAGS.has(el.tagName);
  }

  private nextSiblingPast(el: Element | null, skip: SkipPredicate): Element | null {
    let n = el?.nextElementSibling ?? null;
    while (n && skip(n)) n = n.nextElementSibling;
    return n;
  }

  private prevSiblingPast(el: Element | null, skip: SkipPredicate): Element | null {
    let n = el?.previousElementSibling ?? null;
    while (n && skip(n)) n = n.previousElementSibling;
    return n;
  }

  private firstChildPast(el: Element | null, skip: SkipPredicate): Element | null {
    let n = el?.firstElementChild ?? null;
    while (n && skip(n)) n = n.nextElementSibling;
    return n;
  }

  /**
   * The element to move selection to for `direction`, or `null` when there is
   * nothing sensible there (no wrap-around).
   *
   * - `up`: previous element sibling; the parent if there is none.
   * - `down`: next element sibling; otherwise the nearest following element of
   *   an ancestor, so a lone child still steps forward instead of dead-ending.
   * - `left`: parent element (stops above `<html>`).
   * - `right`: first element child.
   *
   * `skip` defaults to `isSkippable`; `Scooper` passes one that also skips
   * Scoop's own overlay nodes.
   */
  nextTarget(
    node: Element | null,
    direction: Direction,
    skip: SkipPredicate = (el) => this.isSkippable(el),
  ): Element | null {
    if (!isElement(node)) return null;

    switch (direction) {
      case "up": {
        const prev = this.prevSiblingPast(node, skip);
        if (prev) return prev;
        const parent = node.parentElement;
        return parent && !skip(parent) ? parent : null;
      }
      case "down": {
        const next = this.nextSiblingPast(node, skip);
        if (next) return next;
        let p = node.parentElement;
        while (p) {
          const s = this.nextSiblingPast(p, skip);
          if (s) return s;
          p = p.parentElement;
        }
        return null;
      }
      case "left": {
        const parent = node.parentElement;
        return parent && !skip(parent) ? parent : null;
      }
      case "right":
        return this.firstChildPast(node, skip);
      default:
        return null;
    }
  }

  /** Build a `tag#id.class1.class2` description of an element. */
  describeElement(el: Element | null): string {
    if (!isElement(el)) return "";
    let out = el.tagName.toLowerCase();
    if (el.id) out += "#" + el.id;
    for (const c of Array.from(el.classList)) out += "." + c;
    return out;
  }
}
