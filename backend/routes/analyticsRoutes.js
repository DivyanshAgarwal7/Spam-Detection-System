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

router.get('/accuracy', protect, async (req, res) => {
  try {
    const feedbacks = await History.find({ user: req.user.id, "feedback.label": { $exists: true } });
    
    if (!feedbacks.length) {
      return res.json({ accuracy: 0, total: 0, message: 'No feedback yet' });
    }
    
    const correct = feedbacks.filter(f => 
      f.feedback.label === 'correct'
    ).length;
    
    const accuracy = Math.round((correct / feedbacks.length) * 100);
    
    res.json({
      accuracy,
      total: feedbacks.length,
      correct,
      incorrect: feedbacks.length - correct
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch accuracy' });
  }
});

module.exports = router;
      
