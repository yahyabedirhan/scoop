// Drives the built content.js on sample.html for one store screenshot.
//
// Loaded before content.js, so the chrome.* stub below is in place when the
// content script wires itself up. The stub keeps everything in the page: the
// remembered mode is a variable and the clipboard write resolves without
// touching the real clipboard. `?shot=N` picks the scene.

(() => {
  let onMessage = null;
  let storedMode;

  window.chrome = {
    runtime: {
      onMessage: { addListener: (fn) => (onMessage = fn) },
      sendMessage: () => {},
    },
    storage: {
      local: {
        get: (_keys, cb) => cb({ activeModeId: storedMode }),
        set: (items) => (storedMode = items.activeModeId),
      },
    },
  };
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: () => Promise.resolve() },
  });

  const key = (k) => window.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true }));

  // A point just inside the element's top-left corner, so the hit test lands
  // on the element itself rather than a child.
  function pointIn(selector) {
    const r = document.querySelector(selector).getBoundingClientRect();
    return { clientX: r.left + 6, clientY: r.top + 6 };
  }
  const move = (p) => document.elementFromPoint(p.clientX, p.clientY)
    .dispatchEvent(new MouseEvent("mousemove", { ...p, bubbles: true }));

  const SHOTS = {
    // Full HTML on the ingredients card.
    1: () => { key("1"); move(pointIn("#ingredients")); },
    // Markdown on the method list: hover a step, then Left to its parent list.
    2: () => { key("4"); move(pointIn("#method li")); key("ArrowLeft"); },
    // Clean HTML on the intro, then a click copies it and shows the toast.
    // The toast fades in over 0.15 s and starts fading out 1.2 s after the
    // click, so the click waits 1.5 s into render.mjs's 2 s virtual-time
    // budget to have the toast fully shown at capture.
    3: () => {
      key("2");
      // Click near the paragraph's lower right, so the toast that opens just
      // below the pointer lands in the blank space beside the next heading.
      const r = document.querySelector("#intro").getBoundingClientRect();
      const p = { clientX: r.left + r.width * 0.6, clientY: r.bottom - 8 };
      move(p);
      setTimeout(() => document.elementFromPoint(p.clientX, p.clientY)
        .dispatchEvent(new MouseEvent("click", { ...p, bubbles: true })), 1500);
    },
  };

  window.scoopShot = () => {
    const shot = new URLSearchParams(location.search).get("shot") || "1";
    onMessage({ type: "inspect:toggle" });
    SHOTS[shot]();
  };
})();
