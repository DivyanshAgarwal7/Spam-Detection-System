const BlacklistedToken = require('../models/BlacklistedToken');

/**
 * Validate internal service-to-service requests
 * Only Node.js backend can call ML API
 */
const validateInternalRequest = (req, res, next) => {
  const apiKey = req.headers['x-internal-api-key'];
  const internalSecret = process.env.INTERNAL_SECRET;

  if (!internalSecret) {
    console.error('❌ INTERNAL_SECRET not set in environment variables');
    return res.status(500).json({
      success: false,
      error: 'Internal server configuration error'
    });
  }

  if (!apiKey || apiKey !== internalSecret) {
    console.warn(`⚠️  Invalid internal API key attempt from ${req.ip}`);
    return res.status(401).json({
      success: false,
      error: 'Invalid internal API key'
    });
  }

  // Log internal request
  console.log(`🔐 [ZERO-TRUST] Internal request to ${req.path} from ${req.ip}`);
  
  next();
};

/**
 * IP Allowlisting - Restrict internal services to specific IPs
 */
const ipAllowlist = (req, res, next) => {
  const allowedIPs = process.env.SERVICE_IP_ALLOWLIST || '127.0.0.1,::1';
  const allowedList = allowedIPs.split(',').map(ip => ip.trim());
  
  const clientIP = req.ip || req.connection?.remoteAddress || req.socket?.remoteAddress;
  
  if (process.env.NODE_ENV === 'development') {
    // Skip IP check in development
    return next();
  }

  if (!allowedList.includes(clientIP)) {
    console.warn(`⚠️  Blocked request from unauthorized IP: ${clientIP}`);
    return res.status(403).json({
      success: false,
      error: 'Access denied from this IP address'
    });
  }

  next();
};

/**
 * Fine-grained RBAC - Check user permissions
 */
const checkPermission = (requiredPermissions) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: 'Authentication required'
      });
    }

    const userPermissions = req.user.permissions || [];
    
    // Check if user has all required permissions
    const hasAllPermissions = requiredPermissions.every(permission =>
      userPermissions.includes(permission) || req.user.role === 'admin'
    );

    if (!hasAllPermissions) {
      console.warn(`⚠️  User ${req.user.email} attempted unauthorized action: ${requiredPermissions}`);
      return res.status(403).json({
        success: false,
        error: 'Insufficient permissions',
        required: requiredPermissions
      });
    }

    next();
  };
};

/**
 * Audit Logging - Log every authenticated action
 */
const auditLog = (action, resourceType) => {
  return async (req, res, next) => {
    const startTime = Date.now();
    const originalSend = res.send;
    
    // Log request
    console.log(`📝 [AUDIT] ${action} - ${req.method} ${req.path} - User: ${req.user?.email || 'anonymous'}`);

    // Capture response
    res.send = function(data) {
      const duration = Date.now() - startTime;
      const status = res.statusCode;
      
      // Log response
      console.log(`📝 [AUDIT] ${action} - Status: ${status} - Duration: ${duration}ms`);
      
      // Store in database if needed
      // await AuditLog.create({ ... });
      
      originalSend.call(this, data);
    };

    next();
  };
};

/**
 * Validate every request - Assume breach mindset
 */
const validateRequest = (req, res, next) => {
  // Check for suspicious patterns
  const suspiciousPatterns = [
    /['"\\;]/g,  // SQL injection
    /<script.*?>/gi,  // XSS
    /..\/.*/g,  // Path traversal
    /\$.*\{.*\}/g  // Command injection
  ];

  // Check query parameters
  if (req.query) {
    for (const [key, value] of Object.entries(req.query)) {
      if (typeof value === 'string') {
        for (const pattern of suspiciousPatterns) {
          if (pattern.test(value)) {
            console.warn(`⚠️  Suspicious query param: ${key}=${value} from ${req.ip}`);
            return res.status(400).json({
              success: false,
              error: 'Invalid request parameters'
            });
          }
        }
      }
    }
  }

  // Check body
  if (req.body) {
    const bodyString = JSON.stringify(req.body);
    for (const pattern of suspiciousPatterns) {
      if (pattern.test(bodyString)) {
        console.warn(`⚠️  Suspicious request body from ${req.ip}`);
        return res.status(400).json({
          success: false,
          error: 'Invalid request body'
        });
      }
    }
  }

  // Add security headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  
  next();
};

module.exports = {
  validateInternalRequest,
  ipAllowlist,
  checkPermission,
  auditLog,
  validateRequest
};