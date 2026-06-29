// Verifies the analyze/predict rate limiter (issue #356): bursts from a single
// client are throttled with a 429 response carrying a Retry-After header.
// Mounts only the limiter on a throwaway Express app so the test needs no DB,
// auth, or ML service.

const test = require("node:test");
const assert = require("node:assert");
const express = require("express");

const {
  predictLimiter,
  PREDICT_MAX,
  PREDICT_WINDOW_MS,
} = require("../middleware/rateLimiter");

function startServer() {
  const app = express();
  app.post("/predict", predictLimiter, (req, res) => res.json({ ok: true }));
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve(server));
  });
}

test("allows requests up to the limit, then returns 429 with Retry-After", async () => {
  const server = await startServer();
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/predict`;

  try {
    let okCount = 0;
    let firstRejection = null;

    for (let i = 0; i < PREDICT_MAX + 5; i++) {
      const res = await fetch(url, { method: "POST" });
      if (res.status === 200) {
        okCount += 1;
      } else if (res.status === 429 && !firstRejection) {
        firstRejection = res;
        break;
      }
    }

    assert.strictEqual(
      okCount,
      PREDICT_MAX,
      `expected exactly ${PREDICT_MAX} requests to succeed before throttling`
    );
    assert.ok(firstRejection, "expected a 429 after exceeding the limit");

    const retryAfter = firstRejection.headers.get("retry-after");
    assert.ok(retryAfter, "expected a Retry-After header on the 429 response");
    assert.strictEqual(
      Number(retryAfter),
      Math.ceil(PREDICT_WINDOW_MS / 1000)
    );

    const body = await firstRejection.json();
    assert.strictEqual(body.success, false);
    assert.match(body.error, /too many/i);
  } finally {
    server.close();
  }
});
