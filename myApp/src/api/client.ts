import axios from 'axios';

const apiIp = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.105.64:8000';

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

export const getFiles = async (id: string) => {
  const response = await apiClient.get(`/analysis/${id}/files`);
  return response.data;
};

export const getGraph = async (id: string) => {
  const response = await apiClient.get(`/analysis/${id}/graph`);
  return response.data;
};

export const getExecutionFlow = async (id: string, startFunction: string, filePath: string) => {
  const response = await apiClient.post(`/analysis/${id}/execution-flow`, {
    start_function: startFunction,
    file_path: filePath,
  });
  return response.data;
};

export const explainElement = async (id: string, name: string, filePath: string, type: string) => {
  const response = await apiClient.post(`/analysis/${id}/explain-element`, {
    name,
    file_path: filePath,
    element_type: type,
  });
  return response.data;
};
