const express = require("express");
const router = express.Router();

const { checkModelDrift } = require('../controllers/mlopsController');


const {
  getSummary,
  getTrends,
  getBreakdown,
} = require("../controllers/analyticsController");

const { protect } = require("../middleware/authMiddleware");

router.use(protect);
router.get("/summary", getSummary);
router.get("/trends", getTrends);
router.get("/breakdown", getBreakdown);

router.get('/model-drift', checkModelDrift); 
module.exports = router;
