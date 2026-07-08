const express = require('express');
const router = express.Router();
const axios = require('axios');
const { protect } = require('../middleware/authMiddleware');
const User = require('../models/User');
const { applyRulesToEmails } = require('../utils/emailRules'); // Step 2 me banayenge
const validationMessages = require('../utils/validationMessages');

const ML_API_BASE = (process.env.API || "http://localhost:5000/predict").replace(/\/predict$/, "");

// Gmail Routes
router.get("/gmail/auth-url", protect, async (req, res) => {try {
    const response = await axios.get(`${ML_API_BASE}/gmail/auth-url`, {
      params: req.query,
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/gmail/callback", async (req, res) => {
  try {
    const { code } = req.query;
    if (!code) {
      return res.status(400).json({ error: "Authorization code is missing" });
    }
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:5173';
    res.redirect(`${frontendUrl}/app?provider=gmail&code=${code}`);
  } catch (error) {
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/gmail/connect", protect, async (req, res) => {  try {
    const { code } = req.query;
    if (!code) {
      return res.status(400).json({ error: "Authorization code is missing" });
    }
    const response = await axios.get(`${ML_API_BASE}/gmail/callback`, {
      params: { code },
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/gmail/emails", protect, async (req, res) => { try {
    const response = await axios.get(`${ML_API_BASE}/gmail/emails`, {
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      const status =
        error.response.status === 401 ? 400 : error.response.status;
      return res.status(status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });

// Outlook Routes
router.get("/outlook/auth-url", protect, async (req, res) => {  try {
    const response = await axios.get(`${ML_API_BASE}/outlook/auth-url`, {
      params: req.query,
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/outlook/callback", async (req, res) => {
  try {
    const { code } = req.query;
    if (!code) {
      return res.status(400).json({ error: "Authorization code is missing" });
    }
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:5173';
    res.redirect(`${frontendUrl}/app?provider=outlook&code=${code}`);
  } catch (error) {
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/outlook/connect", protect, async (req, res) => {try {
    const { code } = req.query;
    if (!code) {
      return res.status(400).json({ error: "Authorization code is missing" });
    }
    const response = await axios.get(`${ML_API_BASE}/outlook/callback`, {
      params: { code },
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/outlook/emails", protect, async (req, res) => {  try {
    const response = await axios.get(`${ML_API_BASE}/outlook/emails`, {
      headers: {
        "X-User-Username": req.user.username,
      },
    });
    res.json(response.data);
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      const status =
        error.response.status === 401 ? 400 : error.response.status;
      return res.status(status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });

router.post("/scan-emails", protect, async (req, res) => { try {
    const { provider } = req.body;
    if (!provider || (provider !== "gmail" && provider !== "outlook")) {
      return res
        .status(400)
        .json({
          success: false,
          message: "Validation failed",
          error: validationMessages.providerInvalid
         });
    }
    const response = await axios.post(
      `${ML_API_BASE}/scan-emails`,
      { provider },
      {
        headers: {
          "X-User-Username": req.user.username,
        },
      },
    );
    const ruleResults = await applyRulesToEmails(req.user.id, response.data.emails);
    res.json({
      ...response.data,
      emails: ruleResults.emails,
      spam_count: ruleResults.spamCount,
      safe_count: ruleResults.safeCount
    });
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      console.error("Flask ML API is unavailable:", error.message);
      return res.status(503).json({
        error: "Flask ML API is currently unavailable. Please try again later.",
      });
    }
    if (error.response) {
      const status =
        error.response.status === 401 ? 400 : error.response.status;
      return res.status(status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });

module.exports = router;