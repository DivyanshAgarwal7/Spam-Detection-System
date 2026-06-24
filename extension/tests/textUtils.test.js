const test = require("node:test");
const assert = require("node:assert/strict");
const { truncateForClassification, badgeForPrediction } = require("../src/lib/textUtils.js");

test("truncateForClassification collapses whitespace and trims", () => {
  const result = truncateForClassification("  Hello\n\nworld   foo  ");
  assert.equal(result, "Hello world foo");
});

test("truncateForClassification respects the max length", () => {
  const result = truncateForClassification("a".repeat(1000), 10);
  assert.equal(result.length, 10);
});

test("truncateForClassification defaults to 500 chars", () => {
  const result = truncateForClassification("a".repeat(1000));
  assert.equal(result.length, 500);
});

test("badgeForPrediction maps known labels", () => {
  assert.equal(badgeForPrediction("spam").label, "Spam");
  assert.equal(badgeForPrediction("HAM").label, "Safe");
  assert.equal(badgeForPrediction("smishing").label, "Smishing");
  assert.equal(badgeForPrediction("offensive").label, "Offensive");
});

test("badgeForPrediction falls back to Unknown for unrecognized labels", () => {
  assert.equal(badgeForPrediction("something-else").label, "Unknown");
  assert.equal(badgeForPrediction(undefined).label, "Unknown");
});
