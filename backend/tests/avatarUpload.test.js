// Verifies avatar upload validation (issue #447): oversized files and
// disallowed MIME types are rejected with a 400 before reaching the handler,
// while valid JPEG/PNG/WEBP uploads under the limit pass through. Mounts only
// the upload middleware on a throwaway Express app, so no DB or auth is needed.

const test = require("node:test");
const assert = require("node:assert");
const express = require("express");

const {
  handleAvatarUpload,
  MAX_AVATAR_BYTES,
  ALLOWED_AVATAR_MIME_TYPES,
} = require("../middleware/avatarUpload");

function startServer() {
  const app = express();
  // Stand-in for updateAvatar: only reached when validation passes.
  app.post("/avatar", handleAvatarUpload, (req, res) => {
    res.json({ ok: true, size: req.file ? req.file.size : 0 });
  });
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve(server));
  });
}

function uploadFile(url, { bytes, mimetype, filename }) {
  const form = new FormData();
  let baseBuffer = Buffer.alloc(0);
  if (mimetype === 'image/jpeg') {
    baseBuffer = Buffer.from('ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4000f0001010000000000000000000000000000ffda0008010100003f0037ffd9', 'hex');
  } else if (mimetype === 'image/png') {
    baseBuffer = Buffer.from('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789cc3600000000200012705a6160000000049454e44ae426082', 'hex');
  } else if (mimetype === 'image/webp') {
    baseBuffer = Buffer.from('5249464620000000574542505650382014000000d001009d012a010001000225a40003c000000885848800', 'hex');
  }

  let buffer;
  if (baseBuffer.length >= bytes) {
    buffer = baseBuffer.subarray(0, bytes);
  } else {
    const padding = Buffer.alloc(bytes - baseBuffer.length, 1);
    buffer = Buffer.concat([baseBuffer, padding]);
  }

  const blob = new Blob([buffer], { type: mimetype });
  form.append("avatar", blob, filename);
  return fetch(url, { method: "POST", body: form });
}

test("rejects files larger than the size limit with a 400", async () => {
  const server = await startServer();
  const { port } = server.address();
  try {
    const res = await uploadFile(`http://127.0.0.1:${port}/avatar`, {
      bytes: MAX_AVATAR_BYTES + 1024,
      mimetype: "image/png",
      filename: "big.png",
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.match(body.error, /too large/i);
  } finally {
    server.close();
  }
});

test("rejects non-image MIME types with a clear 400 error", async () => {
  const server = await startServer();
  const { port } = server.address();
  try {
    const res = await uploadFile(`http://127.0.0.1:${port}/avatar`, {
      bytes: 1024,
      mimetype: "application/pdf",
      filename: "doc.pdf",
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.match(body.error, /invalid file type/i);
  } finally {
    server.close();
  }
});

test("rejects image types outside the allowed subset (e.g. gif)", async () => {
  const server = await startServer();
  const { port } = server.address();
  try {
    const res = await uploadFile(`http://127.0.0.1:${port}/avatar`, {
      bytes: 1024,
      mimetype: "image/gif",
      filename: "anim.gif",
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.match(body.error, /invalid file type/i);
  } finally {
    server.close();
  }
});

test("accepts valid JPEG/PNG/WEBP uploads under the limit", async () => {
  const server = await startServer();
  const { port } = server.address();
  try {
    for (const mimetype of ALLOWED_AVATAR_MIME_TYPES) {
      const ext = mimetype.split("/")[1];
      const res = await uploadFile(`http://127.0.0.1:${port}/avatar`, {
        bytes: 2048,
        mimetype,
        filename: `avatar.${ext}`,
      });
      assert.strictEqual(res.status, 200, `expected ${mimetype} to be accepted`);
      const body = await res.json();
      assert.strictEqual(body.ok, true);
      assert.strictEqual(body.size, 2048);
    }
  } finally {
    server.close();
  }
});
