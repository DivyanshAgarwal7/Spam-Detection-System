const express = require('express');
const { exportReport } = require('../controllers/reportController');
const router = express.Router();
const {protect} = require("../middleware/authMiddleware");

// Simple route - no missing handler
router.get('/export-pdf', protect ,exportReport);

module.exports = router;
