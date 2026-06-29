const express = require('express');
const router = express.Router();

const { exportPdfReport } = require('../controllers/reportController');
const { protect } = require('../middleware/authMiddleware');

router.get('/export-pdf', protect, exportPdfReport);

module.exports = router;
