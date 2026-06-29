const express = require('express');
const router = express.Router();

const { exportPdfReport } = require('../controllers/reportController');
const { protect } = require('../middleware/authMiddleware');
const { exportLimiter } = require('../middleware/rateLimiter');

router.get('/export-pdf', protect, exportLimiter, exportPdfReport);

module.exports = router;
