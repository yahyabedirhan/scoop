import { fullHtml } from "./full-html";
import { cleanHtml } from "./clean-html";
import { plainText } from "./plain-text";
import { markdown } from "./markdown";

/**
 * A copy mode: one entry in the number-key picker (Full HTML, Clean HTML, Plain
 * Text, Markdown).
 *
 * Duck-typed Strategy: a plain object, no base class. `transform` receives a
 * fresh clone of the selected element (as produced by `Inspector.capture`) and
 * returns either a DOM node (Full HTML, Clean HTML) or a string directly (Plain
 * Text, Markdown). The caller turns a returned node into text via `formatHTML`;
 * a returned string is used as-is.
 */
export interface Mode {
  /** Stable identifier, also the `chrome.storage.local` value and icon key. */
  id: string;
  /** Digit key (`"1"` / `"2"` / `"3"` / `"4"`) that switches to this mode. */
  key: string;
  label: string;
  /** How the hover label names the target: full `tag#id.class`, bare `tag`, or nothing. */
  showDescriptor: "full" | "tag" | "none";
  showDimensions: boolean;
  /** Show the character length of what would actually be copied. */
  showLength: boolean;
  transform: (el: Element) => Element | string;
}

/**
 * The ordered mode registry. `Scooper` and the label renderer are both driven by
 * this array. Adding a mode is adding a module plus one entry here (a mode with
 * a distinct hover-label glyph also needs an `ICONS` entry in `scooper.ts`).
 */
export const MODES: readonly Mode[] = [fullHtml, cleanHtml, plainText, markdown];
