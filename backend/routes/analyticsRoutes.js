const express = require("express");
const router = express.Router();

const { checkModelDrift } = require('../controllers/mlopsController');


const {
  getSummary,
  getTrends,
  getBreakdown,
  getPersonalSummary,
} = require("../controllers/analyticsController");

const { protect } = require("../middleware/authMiddleware");
const History = require("../models/History");

router.use(protect);
router.get("/summary", getSummary);
router.get("/trends", getTrends);
router.get("/breakdown", getBreakdown);
router.get('/model-drift', checkModelDrift); 
router.get("/me", getPersonalSummary);

router.get('/analytics', protect, async (req, res) => {
  try {
    const feedbacks = await History.find({ user: req.user.id, "feedback.label": { $exists: true } });
    const { startDate, endDate } = req.query;
    
    const filter = { userId: req.user.id };
    
    if (startDate) {
      filter.createdAt = { $gte: new Date(startDate) };
    }
    if (endDate) {
      filter.createdAt = { ...filter.createdAt, $lte: new Date(endDate + 'T23:59:59') };
    }
    
    const correct = feedbacks.filter(f => 
      f.feedback.label === 'correct'
    ).length;
    const predictions = await Prediction.find(filter);
    
    const total = predictions.length;
    const spamCount = predictions.filter(p => p.result === 'spam' || p.result === 'smishing').length;
    const hamCount = predictions.filter(p => p.result === 'ham' || p.result === 'safe').length;
    
    res.json({
      total,
      spam: spamCount,
      ham: hamCount,
      spamRate: total > 0 ? Math.round((spamCount / total) * 100) : 0,
      startDate: startDate || null,
      endDate: endDate || null
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch analytics' });
  }
});

router.get('/accuracy', protect, async (req, res) => {
  try {
    const key = `rate_limit:${req.user.id}`;
    const current = await cache.get(key) || 0;
    const limit = 100;
    const remaining = Math.max(0, limit - current);
    
    res.json({
      limit,
      used: current,
      remaining,
      percentage: Math.round((current / limit) * 100),
      reset: new Date(Date.now() + 3600 * 1000).toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch rate limit' });
  }
});


module.exports = router;
      
