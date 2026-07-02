const express = require("express");
const router = express.Router();

const { checkModelDrift } = require('../controllers/mlopsController');


const {
  getSummary,
  getTrends,
  getBreakdown,
} = require("../controllers/analyticsController");

const { protect } = require("../middleware/authMiddleware");

router.get("/summary", protect, getSummary);
router.get("/trends", protect, getTrends);
router.get("/breakdown", protect, getBreakdown);

router.get('/model-drift', checkModelDrift); 
module.exports = router;
