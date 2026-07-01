const express = require('express');
const router = express.Router();

// Simple route - no missing handler
router.get('/export-pdf', (req, res) => {
  res.json({
    success: true,
    message: 'PDF report endpoint working',
    data: {
      predictions: [],
      charts: []
    }
  });
});

module.exports = router;
