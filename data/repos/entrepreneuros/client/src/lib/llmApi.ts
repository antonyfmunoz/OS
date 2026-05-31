import { apiRequest } from "./queryClient";

export async function callLLM(prompt: string, model: string = "claude-haiku-4-5", systemMessage?: string): Promise<string> {
  try {
    const response = await apiRequest("POST", "/api/llm/chat", {
      prompt,
      model,
      systemMessage
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      const error = new Error(data.message || "Failed to get response from AI");
      (error as any).status = response.status;
      (error as any).code = data.code || 'unknown_error';
      (error as any).details = data.error || '';
      throw error;
    }
    
    return data.response;
  } catch (error) {
    console.error("Error calling LLM API:", error);
    
    if ((error as any).status === 429 || 
        ((error as Error).message && (error as Error).message.includes('rate limit'))) {
      throw new Error("Rate limit exceeded. Please try again later.");
    } else if ((error as any).status === 401 || 
               ((error as Error).message && (error as Error).message.includes('API key'))) {
      throw new Error("AI service configuration issue. Please contact support.");
    }
    
    throw error;
  }
}
