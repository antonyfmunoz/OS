import OpenAI from "openai";
import { AIServiceInterface, AIMessage, AIModelConfig } from "./index";

export class PerplexityService implements AIServiceInterface {
  private client: OpenAI | null = null;
  
  constructor() {
    if (process.env.PERPLEXITY_API_KEY) {
      this.client = new OpenAI({
        baseURL: "https://api.perplexity.ai",
        apiKey: process.env.PERPLEXITY_API_KEY,
      });
    }
  }
  
  isAvailable(): boolean {
    return this.client !== null;
  }
  
  async generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string> {
    if (!this.client) {
      throw new Error("Perplexity API key is not configured");
    }
    
    try {
      const modelName = config?.modelName || "llama-3.1-sonar-small-128k-online";
      const temperature = config?.temperature || 0.7;
      
      const perplexityMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const response = await this.client.chat.completions.create({
        model: modelName,
        messages: perplexityMessages,
        temperature: temperature,
        max_tokens: config?.maxTokens,
        stream: false,
        search_domain_filter: ["perplexity.ai"],
        return_images: false,
        return_related_questions: false,
        search_recency_filter: "month",
        top_k: 0,
        presence_penalty: 0,
        frequency_penalty: 1
      });
      
      return response.choices[0].message.content || "No response generated";
    } catch (error) {
      console.error("Error generating Perplexity response:", error);
      throw new Error(`Failed to generate response from Perplexity: ${error.message}`);
    }
  }
}