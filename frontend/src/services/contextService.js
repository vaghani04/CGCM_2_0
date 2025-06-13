import apiClient from '../config/api.js';

export const contextService = {
  // Trigger context gathering for a codebase
  async gatherContext(codebasePath) {
    try {
      const response = await apiClient.post('/context-gather', {
        codebase_path: codebasePath
      });
      return response.data;
    } catch (error) {
      console.error('Error gathering context:', error);
      throw error;
    }
  },

  // Submit user query to get context response
  async submitUserQuery(query, codebasePath) {
    try {
      const response = await apiClient.post('/user-query', {
        query: query,
        codebase_path: codebasePath
      });
      return response.data;
    } catch (error) {
      console.error('Error submitting user query:', error);
      throw error;
    }
  }
};

export default contextService; 