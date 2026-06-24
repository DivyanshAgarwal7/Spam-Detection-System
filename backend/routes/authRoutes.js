const express = require('express');
const router = express.Router();
const { body } = require('express-validator');
const { register, login, getMe, googleLogin, forgotPassword, resetPassword } = require('../controllers/authController');
const { protect } = require('../middleware/authMiddleware');
const {  registerLimiter, loginLimiter } = require('../middleware/rateLimiter');

const registerValidation = [
  body('username').trim().isLength({ min: 3, max: 30 }).withMessage('Username must be 3–30 characters'),
  body('email').isEmail().withMessage('Please enter a valid email'),
  body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters'),
];

const loginValidation = [
  body('email').isEmail().withMessage('Please enter a valid email'),
  body('password').notEmpty().withMessage('Password is required'),
];

router.post('/', loginValidation,loginLimiter, login);
router.post('/register', registerValidation,registerLimiter, register);
router.post('/google', googleLogin);
router.get('/me', protect, getMe);

const forgotPasswordValidation = [
  body('email').isEmail().withMessage('Please enter a valid email'),
];

const resetPasswordValidation = [
  body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters'),
];

router.post('/forgot-password', forgotPasswordValidation, forgotPassword);
router.post('/reset-password/:id/:token', resetPasswordValidation, resetPassword);

module.exports = router;
