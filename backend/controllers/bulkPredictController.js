// backend/controllers/bulkPredictController.js
const { processBulkPrediction } = require('../services/bulkPredictService'); // NOTE: If the service path is different, please adjust this import accordingly.

/**
 * Handle bulk prediction request.
 * Processes the CSV rows and returns the prediction results.
 */
exports.handleBulkPrediction = async (req, res) => {
  try {
    // Access parsed CSV data (provided by validateCSVUpload middleware)
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
};

/**
 * Download CSV template for bulk prediction.
 */
exports.downloadBulkPredictTemplate = (req, res) => {
  const template = 'text,label\n"Your message here",""\n"Another message",""';

  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="bulk_predict_template.csv"');
  res.send(template);
};