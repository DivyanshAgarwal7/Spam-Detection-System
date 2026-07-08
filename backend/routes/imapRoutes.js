const express = require('express');
const router = express.Router();
const axios = require('axios');
const { protect } = require('../middleware/authMiddleware');
const { applyRulesToEmails } = require('../utils/emailRules');
const validationMessages = require('../utils/validationMessages');

const ML_API_BASE = (process.env.API || "http://localhost:5000/predict").replace(/\/predict$/, "");

router.post("/imap/connect", protect, async (req, res) => {
  try {
    const { email, password, host, port } = req.body;

    if (!email || !password || !host) {
      return res.status(400).json({
        success: false,
        message: "Validation failed",
        error: validationMessages.imapFieldsRequired
      });
    }

    res.json({
      success: true,
      message: "IMAP connection configured successfully",
      data: { email, host, port: port || 993 }
    });
  } catch (error) {
    console.error("IMAP connection error:", error.message);
    res.status(500).json({
      success: false,
      error: "Failed to connect to IMAP server"
    });
  } });
router.get("/imap/status", protect, async (req, res) => {try {
    const response = await axios.get(`${ML_API_BASE}/imap/status`, {
      headers: { "X-User-Username": req.user.username },
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
router.put("/imap/schedule", protect, async (req, res) => { try {
    const response = await axios.put(`${ML_API_BASE}/imap/schedule`, req.body, {
      headers: { "X-User-Username": req.user.username },
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
router.post("/imap/disconnect", protect, async (req, res) => { try {
    const response = await axios.post(
      `${ML_API_BASE}/imap/disconnect`,
      {},
      { headers: { "X-User-Username": req.user.username } },
    );
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
router.post("/imap/scan-now", protect, async (req, res) => { try {
    const response = await axios.post(
      `${ML_API_BASE}/imap/scan-now`,
      {},
      { headers: { "X-User-Username": req.user.username } },
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
      const status = error.response.status === 401 ? 400 : error.response.status;
      return res.status(status).json(error.response.data);
    }
    console.error(error.message);
    res.status(500).json({ error: "Something went wrong" });
  } });
router.get("/imap/scan-results", protect, async (req, res) => { try {
    const response = await axios.get(`${ML_API_BASE}/imap/scan-results`, {
      params: req.query,
      headers: { "X-User-Username": req.user.username },
    });
    const ruleResults = await applyRulesToEmails(req.user.id, response.data.results);
    res.json({
      ...response.data,
      results: ruleResults.emails
    });
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

module.exports = router;