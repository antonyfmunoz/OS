import { AIServiceInterface, AIMessage, AIModelConfig } from "./index";
import { GoogleGenerativeAI, GenerativeModel } from "@google/generative-ai";

export class GeminiService implements AIServiceInterface {
  private client: GoogleGenerativeAI | null = null;

  constructor() {
    try {
      const apiKey = process.env.GEMINI_API_KEY;
      if (apiKey) {
        this.client = new GoogleGenerativeAI(apiKey);
      }
    } catch (error) {
      console.error("Error initializing Gemini service:", error);
      this.client = null;
    }
  }

  isAvailable(): boolean {
    return this.client !== null;
  }

  async generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string> {
    if (!this.client) {
      throw new Error("Gemini service is not available");
    }

    try {
      const modelName = config?.modelName || "gemini-2.5-pro";
      const model = this.client.getGenerativeModel({ model: modelName });

      // Format messages for Gemini
      const formattedMessages = this.formatMessages(messages);
      
      // Set generation config
      const generationConfig = {
        temperature: config?.temperature ?? 0.7,
        topK: 40,
        topP: 0.95,
        maxOutputTokens: config?.maxTokens ?? 2048,
      };

      // Create chat session and send message
      const chat = model.startChat({
        generationConfig,
        history: formattedMessages.slice(0, -1),
      });

      const result = await chat.sendMessage(formattedMessages[formattedMessages.length - 1].parts[0].text || "");
      const response = result.response;
      return response.text();
    } catch (error) {
      console.error("Gemini API error:", error);
      throw new Error(`Failed to generate response from Gemini: ${error}`);
    }
  }

  async analyzeImage(base64Image: string, prompt: string): Promise<string> {
    if (!this.client) {
      throw new Error("Gemini service is not available");
    }

    try {
      // Gemini 2.5 Pro supports multimodal content
      const model = this.client.getGenerativeModel({ model: "gemini-2.5-pro-vision" });

      const result = await model.generateContent([
        prompt,
        {
          inlineData: {
            mimeType: "image/jpeg",
            data: base64Image
          }
        }
      ]);

      return result.response.text();
    } catch (error) {
      console.error("Gemini image analysis error:", error);
      throw new Error(`Failed to analyze image with Gemini: ${error}`);
    }
  }

  private formatMessages(messages: AIMessage[]) {
    return messages.map(message => {
      if (message.role === "system") {
        // Gemini doesn't have a system role, so we'll convert it to a user message
        return {
          role: "user",
          parts: [{ text: `${message.content}\n\nPlease acknowledge the above instructions.` }]
        };
      } else {
        return {
          role: message.role === "user" ? "user" : "model",
          parts: [{ text: message.content }]
        };
      }
    });
  }
}