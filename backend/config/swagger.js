const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Spam Detection System API',
      version: '1.0.0',
      description: 'API documentation for Spam Detection System',
      contact: {
        name: 'Contributors',
        email: 'support@spamdetection.com'
      }
    },
    servers: [
      {
        url: 'http://localhost:3000/api/v1',
        description: 'Development Server'
      },
      {
        url: 'https://api.spamdetection.com/api/v1',
        description: 'Production Server'
      }
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT'
        }
      },
      schemas: {
        // Auth Schemas
        LoginRequest: {
          type: 'object',
          properties: {
            email: { type: 'string', example: 'user@example.com' },
            password: { type: 'string', example: 'password123' }
          },
          required: ['email', 'password']
        },
        RegisterRequest: {
          type: 'object',
          properties: {
            username: { type: 'string', example: 'john_doe' },
            email: { type: 'string', example: 'john@example.com' },
            password: { type: 'string', example: 'securePass123' }
          },
          required: ['username', 'email', 'password']
        },
        AuthResponse: {
          type: 'object',
          properties: {
            access_token: { type: 'string' },
            refresh_token: { type: 'string' },
            user: {
              type: 'object',
              properties: {
                id: { type: 'string' },
                username: { type: 'string' },
                email: { type: 'string' }
              }
            }
          }
        },
        // Prediction Schemas
        PredictionRequest: {
          type: 'object',
          properties: {
            text: { type: 'string', example: 'Congratulations! You won a prize!' },
            type: { type: 'string', enum: ['sms', 'email', 'url', 'message'], example: 'sms' },
            sender: { type: 'string', example: 'unknown@example.com' }
          },
          required: ['text', 'type']
        },
        PredictionResponse: {
          type: 'object',
          properties: {
            input: { type: 'string' },
            prediction: { 
              type: 'string',
              enum: ['spam', 'ham', 'smishing', 'offensive', 'safe', 'malicious']
            },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            confidence_level: { type: 'string', enum: ['high', 'medium', 'low'] },
            level_color: { type: 'string', enum: ['red', 'green', 'orange'] },
            level_emoji: { type: 'string' }
          }
        },
        ErrorResponse: {
          type: 'object',
          properties: {
            error: { type: 'string' }
          }
        }
      }
    },
    security: [
      {
        bearerAuth: []
      }
    ],
    tags: [
      { name: 'Auth', description: 'Authentication endpoints' },
      { name: 'Predictions', description: 'Spam prediction endpoints' },
      { name: 'History', description: 'Prediction history endpoints' },
      { name: 'Analytics', description: 'Analytics and insights endpoints' }
    ]
  },
  apis: ['./routes/*.js', './controllers/*.js'] // Files with annotations
};

module.exports = swaggerJsdoc(options);