import { apiRequest } from './client';
import { AIChatRequest, AIChatResponse } from '../types';

export const aiApi = {
  /**
   * Send a question or clinical explanation request to Groq LLM with live PostgreSQL context.
   */
  chat: async (payload: AIChatRequest): Promise<AIChatResponse> => {
    return apiRequest<AIChatResponse>('/api/v1/ai/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
