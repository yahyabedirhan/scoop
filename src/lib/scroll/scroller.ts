/**
 * The swap point for "how do we bring a target into view."
 *
 * Fully independent of `Inspector`. A `Scroller` never references DOM-footprint
 * tracking, and `Inspector` never references scrolling. `Scooper` is the only
 * entity that holds both. Trying a different scrolling approach later (say one
 * that scrolls a scrollable ancestor rather than patching the target) is a
 * one-line swap in `Scooper`.
 */

export interface ScrollAlignment {
  /** Which edge of the viewport the target went past. */
  block: "start" | "end";
  inline: "nearest";
  /** Breathing room, in px, to leave between the target and that edge. */
  margin: number;
}

export interface Scroller {
  /** Bring `el` into view, honoring `alignment`. */
  scrollIntoView(el: Element, alignment: ScrollAlignment): void;
  /**
   * Synchronously settle any pending scroll patch right now.
   *
   * `Scooper` calls this immediately before `Inspector.capture()` and on
   * `stop()`, so the live page never carries scroll-related residue by the time
   * anything is cloned, which is what lets `Inspector` stay unaware a
   * `Scroller` exists.
   */
  flush(): void;
}
