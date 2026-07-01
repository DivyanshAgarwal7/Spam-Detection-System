const rateLimit = require("express-rate-limit");

const loginLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  max: 5,
  message: {
    success: false,
    message: "Too many login attempts. Please try again after 5 minutes."
  }
});

const registerLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  max: 10,
  message: {
    success: false,
    message: "Too many registration attempts. Please try again later."
  }
});

const resetLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  max: 5,
  message: {
    success: false,
    message: "Too many password reset requests. Please try again later."
  }
});

// Throttle the chat endpoint to prevent API exhaustion
const chatLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 15,
  message: {
    success: false,
    error: "Too many chat requests. Please slow down.",
  }
});

// Throttle the analyze/predict endpoint per client IP so a single client can't
// flood the ML inference service with rapid bursts.
const PREDICT_WINDOW_MS = Number(process.env.PREDICT_RATE_LIMIT_WINDOW_MS) || 60 * 1000;
const PREDICT_MAX = Number(process.env.PREDICT_RATE_LIMIT_MAX) || 30;

const predictLimiter = rateLimit({
  windowMs: PREDICT_WINDOW_MS,
  max: PREDICT_MAX,
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res, next, options) => {
    const retryAfterSeconds = Math.ceil(options.windowMs / 1000);
    // express-rate-limit sets Retry-After itself, but set it explicitly so the
    // contract is guaranteed regardless of header-mode configuration.
    res.setHeader("Retry-After", retryAfterSeconds);
    res.status(options.statusCode).json({
      success: false,
      error: "Too many analyze requests. Please slow down and try again shortly.",
      retryAfter: retryAfterSeconds,
    });
  },
});

module.exports = {
  loginLimiter,
  registerLimiter,
  resetLimiter,
  predictLimiter,
  chatLimiter,
  PREDICT_MAX,
  PREDICT_WINDOW_MS,
};
