const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const { validateCSVUpload } = require('../middleware/fileValidation');
const { bulkPredictLimiter } = require('../middleware/rateLimiter');
const { processBulkPrediction } = require('../controllers/bulkPredictController');

/**
 * @route   POST /api/bulk-predict
 * @desc    Upload CSV for bulk prediction
 * @access  Private
 */
router.post(
    '/bulk-predict',
    protect,
    bulkPredictLimiter,
    validateCSVUpload, // <-- NEW: File validation middleware
    async (req, res) => {
        try {
            // Access parsed CSV data
            const { headers, rows, totalRows, filename, size } = req.parsedCSV;
            
            // Process predictions
            const results = await processBulkPrediction(rows);
            
            res.json({
                success: true,
                totalRows: totalRows,
                filename: filename,
                size: size,
                results: results
            });
            
        } catch (error) {
            console.error('Bulk prediction error:', error);
            res.status(500).json({
                success: false,
                error: 'Failed to process bulk prediction',
                details: error.message
            });
        }
    }
);

/**
 * @route   GET /api/bulk-predict/template
 * @desc    Download CSV template
 * @access  Private
 */
router.get('/bulk-predict/template', protect, (req, res) => {
    const template = 'text,label\n"Your message here",""\n"Another message",""';
    
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="bulk_predict_template.csv"');
    res.send(template);
});

module.exports = router;