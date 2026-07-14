// backend/config/multerConfig.js
const multer = require('multer');

// Centralized list of approved MIME types
const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'application/pdf', 
];

// Reusable file filter function
const fileFilter = (req, file, cb) => {
  if (ALLOWED_MIME_TYPES.includes(file.mimetype)) {
    cb(null, true); 
  } else {
    
    cb(new Error(`Invalid file type. Only ${ALLOWED_MIME_TYPES.join(', ')} are allowed.`), false);
  }
};

// Configure and export the multer instance
const upload = multer({
  fileFilter: fileFilter,
  limits: {
    fileSize: 5 * 1024 * 1024 // 
  }
});

module.exports = { upload, ALLOWED_MIME_TYPES, fileFilter };