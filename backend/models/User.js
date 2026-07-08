const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

// ============================================
// ROLES & PERMISSIONS DEFINITIONS
// ============================================

const ROLES = {
  USER: 'user',
  MODERATOR: 'moderator',
  ADMIN: 'admin'
};

const PERMISSIONS = {
  // User permissions
  PREDICT: 'predict',
  BULK_PREDICT: 'bulk_predict',
  VIEW_ANALYTICS: 'view_analytics',
  MANAGE_WEBHOOKS: 'manage_webhooks',
  EXPORT_DATA: 'export_data',
  
  // Moderator permissions
  MANAGE_USERS: 'manage_users',
  VIEW_REPORTS: 'view_reports',
  
  // Admin permissions
  MANAGE_ROLES: 'manage_roles',
  VIEW_LOGS: 'view_logs',
  SYSTEM_CONFIG: 'system_config',
  MANAGE_ALL: 'manage_all'
};

// Role to permissions mapping
const ROLE_PERMISSIONS = {
  [ROLES.USER]: [
    PERMISSIONS.PREDICT,
    PERMISSIONS.BULK_PREDICT,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.MANAGE_WEBHOOKS,
    PERMISSIONS.EXPORT_DATA
  ],
  [ROLES.MODERATOR]: [
    PERMISSIONS.PREDICT,
    PERMISSIONS.BULK_PREDICT,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.MANAGE_WEBHOOKS,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.VIEW_REPORTS
  ],
  [ROLES.ADMIN]: [
    PERMISSIONS.PREDICT,
    PERMISSIONS.BULK_PREDICT,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.MANAGE_WEBHOOKS,
    PERMISSIONS.EXPORT_DATA,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.VIEW_REPORTS,
    PERMISSIONS.MANAGE_ROLES,
    PERMISSIONS.VIEW_LOGS,
    PERMISSIONS.SYSTEM_CONFIG,
    PERMISSIONS.MANAGE_ALL
  ]
};

// ============================================
// USER SCHEMA
// ============================================

const userSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: [true, 'Username is required'],
      unique: true,
      trim: true,
      minlength: 3,
      maxlength: 30,
      match: [/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores']
    },
    email: {
      type: String,
      required: [true, 'Email is required'],
      unique: true,
      lowercase: true,
      trim: true,
      match: [/^\S+@\S+\.\S+$/, 'Please enter a valid email']
    },
    password: {
      type: String,
      required: function() {
        return this.provider === 'local';
      },
      minlength: 6,
      select: false // Don't return password by default
    },
    googleId: {
      type: String,
      unique: true,
      sparse: true
    },
    avatarUrl: {
      type: String,
      default: null
    },
    provider: {
      type: String,
      enum: ['local', 'google'],
      default: 'local'
    },
    // ============================================
    // ROLE & PERMISSIONS (Zero Trust)
    // ============================================
    role: {
      type: String,
      enum: Object.values(ROLES),
      default: ROLES.USER
    },
    permissions: {
      type: [String],
      enum: Object.values(PERMISSIONS),
      default: ROLE_PERMISSIONS[ROLES.USER]
    },
    // ============================================
    // WEBHOOK URL (Existing)
    // ============================================
    webhookUrl: {
      type: String,
      trim: true,
      default: null,
      match: [/^https?:\/\/.+/, 'Please enter a valid HTTP or HTTPS URL']
    },
    // ============================================
    // ACCOUNT STATUS (Optional)
    // ============================================
    status: {
      type: String,
      enum: ['active', 'inactive', 'suspended'],
      default: 'active'
    },
    lastLogin: {
      type: Date,
      default: null
    },
    loginAttempts: {
      type: Number,
      default: 0
    },
    lockUntil: {
      type: Date,
      default: null
    }
  },
  { 
    timestamps: true 
  }
);

// ============================================
// INDEXES
// ============================================

userSchema.index({ email: 1 });
userSchema.index({ username: 1 });
userSchema.index({ role: 1 });
userSchema.index({ status: 1 });

// ============================================
// PRE-SAVE HOOKS
// ============================================

// Hash password before saving
userSchema.pre('save', async function (next) {
  if (!this.password || !this.isModified('password')) {
    return next();
  }
  this.password = await bcrypt.hash(this.password, 12);
  next();
});

// Set default permissions based on role
userSchema.pre('save', function (next) {
  if (this.isModified('role') || this.isNew) {
    this.permissions = ROLE_PERMISSIONS[this.role] || ROLE_PERMISSIONS[ROLES.USER];
  }
  next();
});

// ============================================
// INSTANCE METHODS
// ============================================

// Compare password
userSchema.methods.comparePassword = async function (candidatePassword) {
  if (!this.password) return false;
  return bcrypt.compare(candidatePassword, this.password);
};

// Check if user has specific permission
userSchema.methods.hasPermission = function (permission) {
  if (this.role === ROLES.ADMIN) return true;
  return this.permissions.includes(permission);
};

// Check if user has all required permissions
userSchema.methods.hasAllPermissions = function (requiredPermissions) {
  if (this.role === ROLES.ADMIN) return true;
  return requiredPermissions.every(p => this.permissions.includes(p));
};

// Update last login
userSchema.methods.updateLastLogin = function () {
  this.lastLogin = new Date();
  this.loginAttempts = 0;
  this.lockUntil = null;
  return this.save();
};

// Increment login attempts
userSchema.methods.incrementLoginAttempts = function () {
  this.loginAttempts += 1;
  if (this.loginAttempts >= 5) {
    this.lockUntil = new Date(Date.now() + 15 * 60 * 1000); // Lock for 15 minutes
  }
  return this.save();
};

// Check if account is locked
userSchema.methods.isLocked = function () {
  if (!this.lockUntil) return false;
  return this.lockUntil > new Date();
};

// ============================================
// STATIC METHODS
// ============================================

// Get permissions for a role
userSchema.statics.getPermissionsForRole = function (role) {
  return ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS[ROLES.USER];
};

// Get all available roles
userSchema.statics.getRoles = function () {
  return Object.values(ROLES);
};

// Get all available permissions
userSchema.statics.getPermissions = function () {
  return Object.values(PERMISSIONS);
};

// ============================================
// VIRTUAL PROPERTIES
// ============================================

// Check if user is admin
userSchema.virtual('isAdmin').get(function () {
  return this.role === ROLES.ADMIN;
});

// Check if user is moderator
userSchema.virtual('isModerator').get(function () {
  return this.role === ROLES.MODERATOR || this.role === ROLES.ADMIN;
});

// ============================================
// EXPORTS
// ============================================

// Export constants for use in other files
userSchema.statics.ROLES = ROLES;
userSchema.statics.PERMISSIONS = PERMISSIONS;
userSchema.statics.ROLE_PERMISSIONS = ROLE_PERMISSIONS;

module.exports = mongoose.model('User', userSchema);