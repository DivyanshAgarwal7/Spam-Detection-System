// backend/routes/imapRoutes.js
const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const {
  connectImap,
  getImapStatus,
  updateImapSchedule,
  disconnectImap,
  scanNowImap,
  getScanResultsImap
} = require('../controllers/imapController');

router.post("/connect", protect, connectImap);
router.get("/status", protect, getImapStatus);
router.put("/schedule", protect, updateImapSchedule);
router.post("/disconnect", protect, disconnectImap);
router.post("/scan-now", protect, scanNowImap);
router.get("/scan-results", protect, getScanResultsImap);

module.exports = router;