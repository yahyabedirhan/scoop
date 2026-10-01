/**
 * The DOM-facing interface for everything Steal itself adds to or changes on
 * the page.
 *
 * Owns three genuinely independent things:
 * - the registry of injected UI roots (so they can be excluded from a capture),
 * - the temporary `ic-active` class on `<html>` (the inspect cursor),
 * - clean capture: a clone of a subtree with both of the above undone.
 *
 * No knowledge of scrolling at all. `Scooper` settles any pending scroll patch
 * (via `Scroller.flush()`) before calling `capture()`, so by the time
 * `Inspector` clones anything the live page already carries no scroll residue.
 */

interface InspectClass {
  el: Element;
  /** `class` attribute text before Steal touched it (`null` if absent). */
  original: string | null;
  /** `class` attribute text immediately after Steal added `ic-active`. */
  applied: string | null;
}

const INSPECT_CLASS = "ic-active";

function restoreAttribute(el: Element, name: string, value: string | null): void {
  if (value === null) el.removeAttribute(name);
  else el.setAttribute(name, value);
}

export class Inspector {
  /** The actual UI root nodes Steal has mounted; membership is by identity. */
  private readonly roots = new WeakSet<Node>();
  private inspectClass: InspectClass | null = null;

  /** Register `root` as Steal's own and append it to the page. */
  mount(root: Node): void {
    this.roots.add(root);
    (document.body || document.documentElement).appendChild(root);
  }

  /**
   * Did Steal itself put this node here? (Is it inside a mounted root?)
   *
   * Used by `Scooper` as the arrow-traversal skip predicate and as the guard
   * before setting the pointer target, so navigation and clicks never land on
   * Steal's own overlay. Follows node identity, not matching id / class /
   * `data-*`, so a page element that happens to share Steal's id stays
   * selectable.
   */
  isExtensionNode(el: Element | null): boolean {
    for (let node: Element | null = el; node; node = node.parentElement) {
      if (this.roots.has(node)) return true;
    }
    return false;
  }

  /** Add or remove the temporary inspect-cursor class on `<html>`. */
  setInspecting(on: boolean): void {
    if (on) {
      const el = document.documentElement;
      if (this.inspectClass || el.classList.contains(INSPECT_CLASS)) return;
      const original = el.getAttribute("class");
      el.classList.add(INSPECT_CLASS);
      this.inspectClass = { el, original, applied: el.getAttribute("class") };
    } else if (this.inspectClass) {
      this.restoreInspectClass(this.inspectClass.el);
      this.inspectClass = null;
    }
  }

  /**
   * A clone of `el` with Steal's own nodes removed and the inspect class undone,
   * ready for a mode's `transform()`.
   *
   * Match by position before removing anything: page-owned ids and classes may
   * share names with ours and must survive unchanged.
   */
  capture(el: Element): Element {
    const copy = el.cloneNode(true) as Element;
    const originals = [el, ...Array.from(el.querySelectorAll("*"))];
    const copies = [copy, ...Array.from(copy.querySelectorAll("*"))];
    originals.forEach((node, index) => {
      if (this.roots.has(node)) copies[index].remove();
      if (this.inspectClass && node === this.inspectClass.el) {
        this.restoreInspectClass(copies[index]);
      }
    });
    return copy;
  }

  /**
   * Undo the `ic-active` token on `el` (which may be the live `<html>` or a
   * clone of it).
   *
   * - If `class` is still exactly what Steal produced, restore the original
   *   attribute verbatim (including whether it existed at all).
   * - Otherwise the page has edited its classes; drop only our token.
   */
  private restoreInspectClass(el: Element): void {
    const applied = this.inspectClass?.applied ?? null;
    const original = this.inspectClass?.original ?? null;
    if (el.getAttribute("class") === applied) {
      restoreAttribute(el, "class", original);
    } else if (el.classList.contains(INSPECT_CLASS)) {
      el.classList.remove(INSPECT_CLASS);
      if (el.className === "" && original === null) el.removeAttribute("class");
    }
  }
}
