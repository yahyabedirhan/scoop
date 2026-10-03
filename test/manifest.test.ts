// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { describe, test, expect } from "vitest";

// The Chrome Web Store reads the name, version and description from
// manifest.json and rejects or slows the review of a manifest that asks for
// more than it needs. These pin what the store listing in
// docs/store-listing.md relies on.

const ROOT = new URL("../", import.meta.url);
const read = (path: string) => JSON.parse(readFileSync(new URL(path, ROOT), "utf8"));

const manifest = read("manifest.json");
const pkg = read("package.json");

describe("manifest.json for the Chrome Web Store", () => {
  test("carries the same version as package.json", () => {
    expect(manifest.version).toBe(pkg.version);
  });

  test("keeps the description within the store's 132 characters", () => {
    expect(manifest.description.length).toBeGreaterThan(0);
    expect(manifest.description.length).toBeLessThanOrEqual(132);
  });

  test("asks only for the permissions the listing justifies", () => {
    expect([...manifest.permissions].sort()).toEqual(["activeTab", "scripting", "storage"]);
    expect(manifest.host_permissions).toBeUndefined();
    expect(manifest.optional_host_permissions).toBeUndefined();
    expect(manifest.content_scripts).toBeUndefined();
  });

  test("loads no remote code", () => {
    expect(manifest.content_security_policy).toBeUndefined();
    expect(manifest.externally_connectable).toBeUndefined();
  });
});
