const express = require('express');
const helmet = require('helmet');
const dotenv = require('dotenv');
const path = require('path');
const logger = require('./logger');
const authRouter = require('./routes/auth');
const entriesRouter = require('./routes/entries');
const { authLimiter } = require('./middleware/rateLimit');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 4000;

// Security headers (adjusted for serving HTML)
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

// Body parsing
app.use(express.json());

// Serve static files (website)
app.use(express.static(path.join(__dirname, '../public')));

// Rate limiting on auth routes
app.use('/api/auth', authLimiter);

// API Routes
app.use('/api/auth', authRouter);
app.use('/api/entries', entriesRouter);

// API health check
app.get('/api', (req, res) => {
  res.json({ message: 'Secure Password Manager API', version: '0.1.0', status: 'healthy' });
});

// Serve index.html for all other routes (SPA support)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.listen(PORT, () => {
  logger.info(`Server running on port ${PORT}`);
});

module.exports = app;
