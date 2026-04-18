import axios from 'axios';

const apiIp = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.110.201:8000';

export const apiClient = axios.create({
  baseURL: `${apiIp}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyzeRepo = async (url: string) => {
  const response = await apiClient.post('/analyze/github', { url });
  return response.data;
};

export const getUseCases = async (id: string) => {
  const response = await apiClient.get(`/analysis/${id}/use-cases`);
  return response.data;
};

export const getRepoExplanation = async (id: string) => {
  const response = await apiClient.get(`/analysis/${id}/explain-repo`);
  return response.data;
};
