// backend/routes/emailIntegrationRoutes.js
const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const headerAnalyzer = require('../services/headerAnalyzer');

const {
  gmailAuthUrl,
  gmailCallback,
  gmailConnect,
  gmailEmails,
  outlookAuthUrl,
  outlookCallback,
  outlookConnect,
  outlookEmails,
  scanEmails
} = require('../controllers/emailController');

router.post('/analyze-headers', protect, async (req, res) => {
  try {
    const { headers } = req.body;
    
    if (!headers) {
      return res.status(400).json({ error: 'Headers required' });
    }

    const parsedHeaders = headerAnalyzer.parseHeaders(headers);
    const result = headerAnalyzer.analyzeHeaders(parsedHeaders);

    res.json(result);
  } catch (error) {
    res.status(500).json({ error: 'Failed to analyze headers' });
  }
});
// ==================== GMAIL ROUTES ====================
router.get("/gmail/auth-url", protect, gmailAuthUrl);
router.get("/gmail/callback", gmailCallback);
router.get("/gmail/connect", protect, gmailConnect);
router.get("/gmail/emails", protect, gmailEmails);

// ==================== OUTLOOK ROUTES ====================
router.get("/outlook/auth-url", protect, outlookAuthUrl);
router.get("/outlook/callback", outlookCallback);
router.get("/outlook/connect", protect, outlookConnect);
router.get("/outlook/emails", protect, outlookEmails);

// ==================== SCAN EMAILS ROUTE ====================
router.post("/scan-emails", protect, scanEmails);

module.exports = router;