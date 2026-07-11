const { processBulkPrediction } = require("../services/bulkPredictService");

/**
 * Extract a usable prediction text value from a CSV row.
 * Supports common bulk-predict column names such as "text" or "message".
 */
const getPredictionInputFromRow = (row) => {
  if (!row || typeof row !== "object") return null;

  const rowEntries = Object.entries(row);
  const textEntry = rowEntries.find(([key]) =>
    ["text", "message"].includes(key.trim().toLowerCase())
  );

  if (!textEntry) return null;

  const value = textEntry[1];
  if (typeof value !== "string") return null;

  const trimmedValue = value.trim();
  return trimmedValue ? trimmedValue : null;
};

/**
 * Validate parsed CSV rows before forwarding them to the bulk prediction service.
 * Returns normalized rows if valid, otherwise returns an error response.
 */
const validateBulkPredictionRows = (rows, res) => {
  if (!Array.isArray(rows) || rows.length === 0) {
    res.status(400).json({
      success: false,
      error: "CSV contains no prediction rows.",
    });
    return null;
  }

  const normalizedRows = [];

  for (let index = 0; index < rows.length; index++) {
    const row = rows[index];

    if (!row || typeof row !== "object" || Array.isArray(row)) {
      res.status(400).json({
        success: false,
        error: `Row ${index + 2} is not a valid CSV record.`,
      });
      return null;
    }

    const predictionInput = getPredictionInputFromRow(row);

    if (!predictionInput) {
      res.status(400).json({
        success: false,
        error: `Row ${index + 2} is missing valid text content.`,
      });
      return null;
    }

    normalizedRows.push({
      ...row,
      text: predictionInput,
    });
  }

  return normalizedRows;
};

exports.handleBulkPrediction = async (req, res) => {
  try {
    if (!req.parsedFile) {
      return res.status(400).json({
        success: false,
        error: 'File could not be parsed. Please ensure a valid CSV, PDF, or DOCX file is uploaded.'
      });
    }

    const { rows, filename, size } = req.parsedFile;

    // Process predictions
    const results = await processBulkPrediction(rows);

    res.json({
      success: true,
      totalRows: rows.length,
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

exports.downloadBulkPredictTemplate = (req, res) => {
  const template = 'text,label\n"Your message here",""\n"Another message",""';
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="bulk_predict_template.csv"');
  res.send(template);
};