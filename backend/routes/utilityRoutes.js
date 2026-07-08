// backend/routes/utilityRoutes.js
const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const {
  despamify,
  getStats,
  getActivity
} = require('../controllers/activityController');

// ===== DE-SPAMIFY ROUTE =====
router.post('/api/despamify', protect, despamify);

// ===== STATISTICS ROUTE =====
router.get('/api/stats', protect, getStats);

// ===== USER ACTIVITY HEATMAP ROUTE =====
router.get('/api/activity/:userId', protect, getActivity);

module.exports = router;