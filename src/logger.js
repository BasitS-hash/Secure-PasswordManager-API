const { createLogger, format, transports } = require('winston');
const { combine, timestamp, printf, colorize } = format;

const myFormat = printf(({ level, message, timestamp }) => {
  return `${timestamp} [${level}] ${message}`;
});

const logger = createLogger({
  level: 'info',
  format: combine(timestamp(), myFormat),
  transports: [
    new transports.Console({ format: combine(colorize(), timestamp(), myFormat) }),
    new transports.File({ filename: 'logs/app.log' }),
  ],
});

module.exports = logger;
