// backend/middleware/parseUploadedFile.js
const multer = require('multer');
const path = require('path');
const pdfParse = require('pdf-parse');
const mammoth = require('mammoth');

// Multer configuration to accept CSV, PDF, and DOCX
const storage = multer.memoryStorage();
const upload = multer({
  storage: storage,
  limits: { fileSize: 20 * 1024 * 1024 }, // 20MB limit
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    // ✅ Allow CSV, PDF, and DOCX
    if (ext === '.csv' || ext === '.pdf' || ext === '.docx') {
      return cb(null, true);
    }
    cb(new Error('Only CSV, PDF, and DOCX files are allowed'), false);
  }
}).single('file');

// Sanitize cell content (protects against formula injection)
function sanitizeCSVCell(value) {
  if (!value || typeof value !== 'string') return value;
  const dangerous = ['=', '+', '-', '@'];
  if (dangerous.includes(value.charAt(0))) {
    return "'" + value; // Neutralize formula injection
  }
  return value;
}

// --- Main Middleware Function ---
const parseUploadedFile = async (req, res, next) => {
  upload(req, res, async (err) => {
    // 1. Multer Error Check
    if (err) return res.status(400).json({ success: false, error: err.message });
    if (!req.file) return res.status(400).json({ success: false, error: 'No file uploaded' });

    // 2. File Size Check
    const maxSize = parseInt(process.env.MAX_CSV_FILE_SIZE, 10) || 5 * 1024 * 1024;
    if (req.file.size > maxSize) {
      return res.status(413).json({ success: false, error: `File too large. Max ${maxSize / (1024 * 1024)}MB` });
    }

    const ext = path.extname(req.file.originalname).toLowerCase();
    let extractedRows = [];

    try {
      // 3. Parsing based on file extension
      if (ext === '.csv') {
        // CSV Parse Logic
        const fileContent = req.file.buffer.toString('utf-8');
        const lines = fileContent.split(/\r?\n/).filter(line => line.trim());
        if (lines.length === 0) return res.status(400).json({ success: false, error: 'CSV file is empty' });

        // Extract first row as headers
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());

        // Loop through remaining lines
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',').map(v => v.trim());
          const row = {};
          headers.forEach((h, index) => {
            row[h] = sanitizeCSVCell(values[index] || '');
          });
          extractedRows.push(row);
        }
      }
      else if (ext === '.pdf') {
        // PDF Parse Logic
        let pdfData;
        try {
          pdfData = await pdfParse(req.file.buffer);
        } catch (pdfErr) {
          return res.status(400).json({ success: false, error: 'Failed to parse PDF file. Ensure it is not corrupted or password protected.' });
        }
        // PDF mein hum line-by-line text nikalte hain
        const lines = pdfData.text.split('\n').filter(line => line.trim());
        extractedRows = lines.map(line => ({ text: sanitizeCSVCell(line) }));
      }
      else if (ext === '.docx') {
        // DOCX Parse Logic
        let result;
        try {
          result = await mammoth.extractRawText({ buffer: req.file.buffer });
        } catch (docxErr) {
          return res.status(400).json({ success: false, error: 'Failed to parse DOCX file. Ensure it is not corrupted.' });
        }
        const lines = result.value.split('\n').filter(line => line.trim());
        extractedRows = lines.map(line => ({ text: sanitizeCSVCell(line) }));
      }

      // 4. Row limit check
      const maxRows = parseInt(process.env.MAX_CSV_ROWS, 10) || 100000;
      if (extractedRows.length > maxRows) {
        return res.status(413).json({ success: false, error: `File exceeds max row limit of ${maxRows}` });
      }

      // 5. Attach data to req.parsedFile (Controller isko use karega)
      req.parsedFile = {
        rows: extractedRows,
        filename: req.file.originalname,
        size: req.file.size,
        type: ext.replace('.', '')
      };

      next(); // Controller ko bhej do
    } catch (parseError) {
      console.error('File parsing error:', parseError);
      return res.status(500).json({ success: false, error: 'Failed to parse uploaded file' });
    }
  });
};

module.exports = { parseUploadedFile };