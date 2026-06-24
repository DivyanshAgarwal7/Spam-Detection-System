const rateLimit = require("express-rate-limit");

export  const loginLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  max: 5,
  message: {
    success: false,
    message: "Too many login attempts. Please try again after 5 minutes."
  }
});

export  const registerLimiter = rateLimit({
  windowMs: 5 * 60 * 1000,
  max: 10,
  message: {
    success: false,
    message: "Too many registration attempts. Please try again later."
  }
});