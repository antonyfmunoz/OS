import OpenAI from "openai";
import { AIServiceInterface, AIMessage, AIModelConfig } from "./index";

export class XAIService implements AIServiceInterface {
  private client: OpenAI | null = null;
  
  constructor() {
    if (process.env.XAI_API_KEY) {
      this.client = new OpenAI({
        baseURL: "https://api.x.ai/v1",
        apiKey: process.env.XAI_API_KEY,
      });
    }
  }
  
  isAvailable(): boolean {
    return this.client !== null;
  }
  
  async generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string> {
    if (!this.client) {
      throw new Error("xAI API key is not configured");
    }
    
    try {
      const modelName = config?.modelName || "grok-2-1212";
      const temperature = config?.temperature || 0.7;
      
      const xaiMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const response = await this.client.chat.completions.create({
        model: modelName,
        messages: xaiMessages,
        temperature: temperature,
        max_tokens: config?.maxTokens,
      });
      
      return response.choices[0].message.content || "No response generated";
    } catch (error) {
      console.error("Error generating xAI response:", error);
      throw new Error(`Failed to generate response from xAI: ${error.message}`);
    }
  }
  
  async analyzeImage(base64Image: string, prompt: string): Promise<string> {
    if (!this.client) {
      throw new Error("xAI API key is not configured");
    }
    
    try {
      const visionResponse = await this.client.chat.completions.create({
        model: "grok-2-vision-1212",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: prompt
              },
              {
                type: "image_url",
                image_url: {
                  url: `data:image/jpeg;base64,${base64Image}`
                }
              }
            ],
          },
        ],
        max_tokens: 500,
      });
      
      return visionResponse.choices[0].message.content || "No analysis generated";
    } catch (error) {
      console.error("Error analyzing image with xAI:", error);
      throw new Error(`Failed to analyze image: ${error.message}`);
    }
  }
}