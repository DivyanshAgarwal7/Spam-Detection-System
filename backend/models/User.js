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
  PREDICT: 'predict',
  BULK_PREDICT: 'bulk_predict',
  VIEW_ANALYTICS: 'view_analytics',
  MANAGE_WEBHOOKS: 'manage_webhooks',
  EXPORT_DATA: 'export_data',
  MANAGE_USERS: 'manage_users',
  VIEW_REPORTS: 'view_reports',
  MANAGE_ROLES: 'manage_roles',
  VIEW_LOGS: 'view_logs',
  SYSTEM_CONFIG: 'system_config',
  MANAGE_ALL: 'manage_all'
};

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
      trim: true,
      minlength: [3, 'Username must be at least 3 characters long'],
      maxlength: [30, 'Username cannot exceed 30 characters'],
      match: [/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores']
    },
    email: {
      type: String,
      required: [true, 'Email is required'],
      lowercase: true,
      trim: true,
      match: [/^\S+@\S+\.\S+$/, 'Please enter a valid email']
    },
    password: {
      type: String,
      required: false,
      minlength: [6, 'Password must be at least 6 characters long'],
      select: false
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
      enum: {
        values: ['local', 'google'],
        message: '{VALUE} is not a valid provider'
      },
      default: 'local'
    },
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
    webhookUrl: {
      type: String,
      trim: true,
      default: null,
      match: [/^https?:\/\/.+/, 'Please enter a valid HTTP or HTTPS URL'],
      maxlength: [2000, 'Webhook URL cannot exceed 2000 characters']
    },
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
// CASE-INSENSITIVE UNIQUE INDEXES
// ============================================

userSchema.index(
  { email: 1 },
  {
    unique: true,
    collation: {
      locale: 'en',
      strength: 2
    },
    name: 'email_case_insensitive_unique'
  }
);

userSchema.index(
  { username: 1 },
  {
    unique: true,
    collation: {
      locale: 'en',
      strength: 2
    },
    name: 'username_case_insensitive_unique'
  }
);

userSchema.index({ role: 1 });
userSchema.index({ status: 1 });
userSchema.index({ googleId: 1 });

// ============================================
// PRE-SAVE HOOKS
// ============================================

userSchema.pre('save', async function (next) {
  if (!this.password || !this.isModified('password')) {
    return next();
  }
  this.password = await bcrypt.hash(this.password, 12);
  next();
});

userSchema.pre('save', function (next) {
  if (this.isModified('role') || this.isNew) {
    this.permissions = ROLE_PERMISSIONS[this.role] || ROLE_PERMISSIONS[ROLES.USER];
  }
  next();
});

// ============================================
// INSTANCE METHODS
// ============================================

userSchema.methods.comparePassword = async function (candidatePassword) {
  if (!this.password) return false;
  return bcrypt.compare(candidatePassword, this.password);
};

userSchema.methods.hasPermission = function (permission) {
  if (this.role === ROLES.ADMIN) return true;
  return this.permissions.includes(permission);
};

userSchema.methods.hasAllPermissions = function (requiredPermissions) {
  if (this.role === ROLES.ADMIN) return true;
  return requiredPermissions.every(p => this.permissions.includes(p));
};

userSchema.methods.updateLastLogin = function () {
  this.lastLogin = new Date();
  this.loginAttempts = 0;
  this.lockUntil = null;
  return this.save();
};

userSchema.methods.incrementLoginAttempts = function () {
  this.loginAttempts += 1;
  if (this.loginAttempts >= 5) {
    this.lockUntil = new Date(Date.now() + 15 * 60 * 1000);
  }
  return this.save();
};

userSchema.methods.isLocked = function () {
  if (!this.lockUntil) return false;
  return this.lockUntil > new Date();
};

// ============================================
// STATIC METHODS
// ============================================

userSchema.statics.getPermissionsForRole = function (role) {
  return ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS[ROLES.USER];
};

userSchema.statics.getRoles = function () {
  return Object.values(ROLES);
};

userSchema.statics.getPermissions = function () {
  return Object.values(PERMISSIONS);
};

// ============================================
// VIRTUAL PROPERTIES
// ============================================

userSchema.virtual('isAdmin').get(function () {
  return this.role === ROLES.ADMIN;
});

userSchema.virtual('isModerator').get(function () {
  return this.role === ROLES.MODERATOR || this.role === ROLES.ADMIN;
});

// ============================================
// EXPORTS
// ============================================

userSchema.statics.ROLES = ROLES;
userSchema.statics.PERMISSIONS = PERMISSIONS;
userSchema.statics.ROLE_PERMISSIONS = ROLE_PERMISSIONS;

module.exports = mongoose.model('User', userSchema);