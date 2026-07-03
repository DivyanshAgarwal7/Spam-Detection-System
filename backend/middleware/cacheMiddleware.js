const Redis = require('ioredis');
const crypto = require('crypto');

// 1. Initialize Redis Connection (with Graceful Fallback)
const redisClient = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: 1,
  retryStrategy(times) {
    if (times > 3) {
      console.warn('⚠️ Redis connection failed. Falling back to direct ML API calls.');
      return null; // Stop retrying after 3 attempts
    }
    return Math.min(times * 50, 2000);
  }
});

redisClient.on('error', (err) => {
  console.error('Redis Error:', err.message);
});

// 2. Fast SHA-256 Hashing for Input Text
const generateCacheKey = (text) => {
  return crypto.createHash('sha256').update(text).digest('hex');
};

// 3. Cache Checking Middleware
const checkCache = async (req, res, next) => {
  try {
    const { text } = req.body; // Assuming the input is passed as 'text' in the body
    if (!text) return next();

    const key = `spam_cache:${generateCacheKey(text)}`;

    // Only query if Redis is healthy to prevent request hangs
    if (redisClient.status === 'ready') {
      const cachedResult = await redisClient.get(key);
      if (cachedResult) {
        console.log('🚀 Cache Hit! Returning data from Redis.');
        return res.status(200).json(JSON.parse(cachedResult));
      }
    }
    
    // Cache Miss: Attach key to request so the controller can save it later
    req.cacheKey = key;
    next();
  } catch (error) {
    console.error('Cache Middleware Error:', error.message);
    next(); // Ensure the app doesn't crash, just proceed to Flask API
  }
};

// 4. Utility to Save to Cache
const setCache = async (key, data) => {
  try {
    if (redisClient.status === 'ready' && key) {
      // Set TTL to 24 hours (86400 seconds)
      await redisClient.set(key, JSON.stringify(data), 'EX', 86400);
    }
  } catch (error) {
    console.error('Redis Set Cache Error:', error.message);
  }
};

module.exports = { checkCache, setCache, redisClient, generateCacheKey };