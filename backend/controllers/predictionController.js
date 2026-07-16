const axios = require('axios');
const { adversarialGuard, monitorConfidence } = require('../middleware/adversarialGuard');

/**
 * Make prediction with adversarial defense
 */
const predict = async (req, res) => {
    try {
        const { text, type = 'message' } = req.body;

        if (!text || typeof text !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'Text is required and must be a string'
            });
        }

        // Get adversarial analysis from guard
        const adversarialAnalysis = req.adversarialAnalysis || { isSuspicious: false, score: 0 };

        // Call ML API with internal secret
        const response = await axios.post(
            `${process.env.ML_API_URL || 'http://ml-api:5000'}/predict`,
            { text, type },
            {
                headers: {
                    'X-Internal-Secret': process.env.INTERNAL_SECRET,
                    'Content-Type': 'application/json',
                    'X-Request-ID': req.id || 'unknown'
                },
                timeout: 10000
            }
        );

        // Merge adversarial analysis with response
        const result = response.data;
        result.adversarial_analysis = adversarialAnalysis;
        
        // Check if needs review
        if (adversarialAnalysis.isSuspicious || result.confidence_score < 0.6) {
            result.needs_review = true;
        }

        res.json(result);
    } catch (error) {
        console.error('Prediction error:', error);
        res.status(500).json({
            success: false,
            error: 'Prediction failed',
            details: error.message
        });
    }
};

module.exports = { predict };