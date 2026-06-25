module.exports = {
    port: process.env.PORT || 3000,
    logLevel: 'info',
    corsOrigins: process.env.ALLOWED_ORIGINS?.split(',') || [],
    mongodbUri: process.env.MONGODB_URI,
    rateLimit: {
        windowMs: 60000,
        max: 50
    },
    jwtSecret: process.env.JWT_SECRET
};