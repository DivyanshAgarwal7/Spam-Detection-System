module.exports = {
    port: 3000,
    logLevel: 'debug',
    corsOrigins: ['http://localhost:3000'],
    mongodbUri: process.env.MONGODB_URI || 'mongodb://localhost:27017/spam-dev',
    rateLimit: {
        windowsMs : 60000,
        max : 100
    },
    jwtSecret: process.env.JWT_SECRET || 'dev-secret-key'
};