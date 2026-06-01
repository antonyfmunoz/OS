import OpenAI from "openai";
import { AIServiceInterface, AIMessage, AIModelConfig } from "./index";

export class OpenAIService implements AIServiceInterface {
  private openai: OpenAI | null = null;
  
  constructor() {
    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY,
      });
    }
  }
  
  isAvailable(): boolean {
    return this.openai !== null;
  }
  
  async generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string> {
    if (!this.openai) {
      throw new Error("OpenAI API key is not configured");
    }
    
    try {
      // the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
      const modelName = config?.modelName || "gpt-4o";
      const maxTokens = config?.maxTokens || 1000;
      const temperature = config?.temperature || 0.7;
      
      const openaiMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const response = await this.openai.chat.completions.create({
        model: modelName,
        messages: openaiMessages,
        max_tokens: maxTokens,
        temperature: temperature,
      });
      
      return response.choices[0].message.content || "No response generated";
    } catch (error) {
      console.error("Error generating OpenAI response:", error);
      throw new Error(`Failed to generate response: ${error.message}`);
    }
  }
  
  async generateImage(prompt: string): Promise<string> {
    if (!this.openai) {
      throw new Error("OpenAI API key is not configured");
    }
    
    try {
      const response = await this.openai.images.generate({
        model: "dall-e-3",
        prompt: prompt,
        n: 1,
        size: "1024x1024",
        quality: "standard",
      });
      
      return response.data[0].url || "";
    } catch (error) {
      console.error("Error generating image:", error);
      throw new Error(`Failed to generate image: ${error.message}`);
    }
  }
  
  async analyzeImage(base64Image: string, prompt: string): Promise<string> {
    if (!this.openai) {
      throw new Error("OpenAI API key is not configured");
    }
    
    try {
      const visionResponse = await this.openai.chat.completions.create({
        model: "gpt-4o",
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
      console.error("Error analyzing image:", error);
      throw new Error(`Failed to analyze image: ${error.message}`);
    }
  }
}