const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const { predictLimiter } = require('../middleware/rateLimiter');
const { adversarialGuard, monitorConfidence } = require('../middleware/adversarialGuard');
const { predict } = require('../controllers/predictionController');

// Apply adversarial guard and confidence monitoring
router.post('/',
    protect,
    predictLimiter,
    adversarialGuard,    // Detect adversarial patterns
    monitorConfidence,   // Monitor confidence
    predict
);

module.exports = router;