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
const Prediction = require('../models/Prediction');

router.use(protect);
router.get("/summary", getSummary);
router.get("/trends", getTrends);
router.get("/breakdown", getBreakdown);
router.get('/model-drift', checkModelDrift); 
router.get("/me", getPersonalSummary);
module.exports = router;


router.get('/trends', protect, async (req, res) => {
  try {
    const { days = 7 } = req.query;
    const userId = req.user.id;
    

    const predictions = await Prediction.find({
      userId: userId,
      createdAt: { $gte: new Date(Date.now() - days * 24 * 60 * 60 * 1000) }
    });
    
    const trends = {};
    predictions.forEach(p => {
      const date = p.createdAt.toISOString().split('T')[0];
      if (!trends[date]) trends[date] = { total: 0, spam: 0 };
      trends[date].total++;
      if (p.result === 'spam' || p.result === 'smishing') trends[date].spam++;
    });
    
    const result = Object.entries(trends).map(([date, d]) => ({
      date,
      total: d.total,
      spam: d.spam
    }));
    
    res.json(result);
  } catch (error) {
    console.error('Trends error:', error);
    res.status(500).json({ error: 'Failed to fetch trends' });
  }
});

module.exports = router;
      
