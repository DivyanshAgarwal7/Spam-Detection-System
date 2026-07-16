// backend/routes/emailIntegrationRoutes.js
const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
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