// config/axios.js
const axios = require('axios');

/**
 * Configures the global Axios instance with default timeout and internal API headers.
 */
const configureAxios = () => {
  axios.interceptors.request.use(
    (config) => {
      config.timeout = 15000; // 15 seconds timeout
      // No hardcoded fallback: INTERNAL_SECRET is validated as mandatory at
      // startup (see utils/validateEnv.js), so it is guaranteed present here.
      config.headers["X-Internal-Secret"] = process.env.INTERNAL_SECRET;
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
};

module.exports = { configureAxios };