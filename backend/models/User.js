const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: [true, 'Username is required'],
      unique: true,
      trim: true,
      minlength: [3, 'Username must be at least 3 characters long'],
      maxlength: [30, 'Username cannot exceed 30 characters'],
    },
    email: {
      type: String,
      required: [true, 'Email is required'],
      unique: true,
      lowercase: true,
      trim: true,
      match: [/^\S+@\S+\.\S+$/, 'Please enter a valid email'],
    },
    password: {
      type: String,
      required: false,
      minlength: [6, 'Password must be at least 6 characters long'],
    },
    googleId: {
      type: String,
      unique: true,
      sparse: true,
    },
    avatarUrl: {
      type: String,
    },
    provider: {
      type: String,
      enum: {
        values: ['local', 'google'],
        message: '{VALUE} is not a valid provider'
      },
      default: 'local',
    },
    // --- NEW FIELD FOR ISSUE #430 ---
    webhookUrl: {
      type: String,
      trim: true,
      default: null,
      match: [/^https?:\/\/.+/, 'Please enter a valid HTTP or HTTPS URL'],
      maxlength: [2000, 'Webhook URL cannot exceed 2000 characters'],
    },
  },
  { timestamps: true }
);

userSchema.pre('save', async function () {
  if (!this.password || !this.isModified('password')) return;
  this.password = await bcrypt.hash(this.password, 12);
});

userSchema.methods.comparePassword = async function (candidatePassword) {
  if (!this.password) return false;
  return bcrypt.compare(candidatePassword, this.password);
};

module.exports = mongoose.model('User', userSchema);