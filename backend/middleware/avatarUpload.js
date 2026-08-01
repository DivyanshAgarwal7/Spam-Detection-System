const multer = require('multer');
const { fileTypeFromBuffer } = require('file-type');

const MAX_AVATAR_BYTES = 5 * 1024 * 1024;
const ALLOWED_AVATAR_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

const storage = multer.memoryStorage();

const fileFilter = (req, file, cb) => {
  const mimeType = file.mimetype;
  if (!ALLOWED_AVATAR_MIME_TYPES.includes(mimeType)) {
    return cb(new Error('Invalid file type. Only JPEG, PNG, and WEBP images are allowed.'), false);
  }
  cb(null, true);
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_AVATAR_BYTES },
});

const handleAvatarUpload = (req, res, next) => {
  upload.single('avatar')(req, res, async (err) => {
    if (err) {
      if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          const maxMb = MAX_AVATAR_BYTES / (1024 * 1024);
          return res
            .status(400)
            .json({ error: `File too large. Maximum size is ${maxMb}MB.` });
        }
        return res.status(400).json({ error: err.message });
      }
      return res.status(400).json({ error: err.message || 'File upload failed.' });
    }

    if (!req.file || !req.file.buffer) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    try {
      await validateFileContent(req.file.buffer);
      
      // Also perform declared vs detected type mismatch check
      const detectedType = await fileTypeFromBuffer(req.file.buffer);
      if (detectedType && detectedType.mime !== req.file.mimetype) {
        return res.status(400).json({
          error: `MIME type mismatch: declared "${req.file.mimetype}" but detected "${detectedType.mime}"`
        });
      }

      next();
    } catch (validationError) {
      return res.status(400).json({ error: validationError.message });
    }
  });
};

const validateFileContent = async (fileBuffer) => {
  if (!fileBuffer || fileBuffer.length === 0) {
    throw new Error('File is empty');
  }

  if (fileBuffer.length > MAX_AVATAR_BYTES) {
    throw new Error(`File size exceeds ${MAX_AVATAR_BYTES / (1024 * 1024)}MB limit`);
  }

  const detectedType = await fileTypeFromBuffer(fileBuffer);
  if (!detectedType) {
    throw new Error('Unable to detect file type. Please upload a valid image.');
  }

  if (!ALLOWED_AVATAR_MIME_TYPES.includes(detectedType.mime)) {
    throw new Error(`Invalid image type: ${detectedType.mime}. Allowed: ${ALLOWED_AVATAR_MIME_TYPES.join(', ')}`);
  }

  return detectedType;
};

module.exports = {
  handleAvatarUpload,
  MAX_AVATAR_BYTES,
  ALLOWED_AVATAR_MIME_TYPES,
  validateFileContent,
};