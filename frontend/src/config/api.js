import axios from 'axios';

// Base URL for the API - adjust this according to your backend setup
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes timeout for long-running operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding common headers
apiClient.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
apiClient.interceptors.response.use(
  (response) => {
    console.log(`Response received: ${response.status}`);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient; 