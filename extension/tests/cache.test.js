const test = require("node:test");
const assert = require("node:assert/strict");
const { createScanCache } = require("../src/lib/cache.js");

test("a message not yet scanned should be rescanned", () => {
  const cache = createScanCache();
  assert.equal(cache.shouldRescan("msg-1"), true);
});

test("a freshly scanned message should not be rescanned", () => {
  const cache = createScanCache();
  cache.set("msg-1", { prediction: "spam", confidence: 0.9 });
  assert.equal(cache.shouldRescan("msg-1"), false);
});

test("forceRescan always returns true even if cached", () => {
  const cache = createScanCache();
  cache.set("msg-1", { prediction: "spam", confidence: 0.9 });
  assert.equal(cache.shouldRescan("msg-1", true), true);
});

test("a dismissed message stays dismissed and is not rescanned", () => {
  const cache = createScanCache();
  cache.set("msg-1", { prediction: "spam", confidence: 0.9 });
  cache.dismiss("msg-1");
  assert.equal(cache.get("msg-1").dismissed, true);
  assert.equal(cache.shouldRescan("msg-1"), false);
});

test("an entry older than the ttl should be rescanned", () => {
  const cache = createScanCache(50);
  cache.set("msg-1", { prediction: "spam", confidence: 0.9 });
  return new Promise((resolve) => {
    setTimeout(() => {
      assert.equal(cache.shouldRescan("msg-1"), true);
      resolve();
    }, 75);
  });
});

test("clear empties the cache", () => {
  const cache = createScanCache();
  cache.set("msg-1", { prediction: "spam", confidence: 0.9 });
  cache.clear();
  assert.equal(cache.get("msg-1"), null);
});
