// backend/config/corsConfig.js
const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:3000',
];

const corsOptions = {
  origin: allowedOrigins,
  credentials: true,
};

module.exports = { corsOptions, allowedOrigins };