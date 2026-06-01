import Anthropic from "@anthropic-ai/sdk";
import { AIServiceInterface, AIMessage, AIModelConfig } from "./index";

const COMPLEXITY_KEYWORDS = [
  "analyze", "analysis", "explain in detail", "compare", "evaluate",
  "debug", "refactor", "architect", "design", "strategy", "plan",
  "complex", "comprehensive", "in-depth", "thorough", "detailed",
  "write code", "generate code", "implement", "build", "create a",
  "summarize this document", "review", "optimize", "improve",
  "legal", "financial", "medical", "technical", "research",
  "step by step", "pros and cons", "trade-offs", "reasoning",
  "why does", "how does", "what causes", "root cause",
];

export function shouldEscalateToSonnet(messages: AIMessage[]): boolean {
  const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
  if (!lastUserMessage) return false;

  const content = lastUserMessage.content.toLowerCase();

  if (content.length > 500) return true;

  const matchCount = COMPLEXITY_KEYWORDS.filter(kw => content.includes(kw)).length;
  if (matchCount >= 2) return true;

  if (content.includes("?") && content.split("?").length > 3) return true;

  return false;
}

export class AnthropicService implements AIServiceInterface {
  private anthropic: Anthropic;
  
  constructor() {
    this.anthropic = new Anthropic({
      apiKey: process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY,
      baseURL: process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL,
    });
  }
  
  isAvailable(): boolean {
    return !!(process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY && process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL);
  }
  
  async generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string> {
    if (!this.isAvailable()) {
      throw new Error("Anthropic AI integration is not configured");
    }
    
    try {
      let modelName = config?.modelName || "claude-haiku-4-5";
      const maxTokens = config?.maxTokens || 8192;
      const temperature = config?.temperature || 0.7;

      if (modelName === "claude-haiku-4-5" && shouldEscalateToSonnet(messages)) {
        modelName = "claude-sonnet-4-5";
        console.log("[AI] Auto-escalating to Sonnet for complex task");
      }
      
      let systemMessage = "";
      const anthropicMessages: { role: "user" | "assistant"; content: string }[] = [];
      
      for (const message of messages) {
        if (message.role === "system") {
          systemMessage = message.content;
        } else {
          anthropicMessages.push({
            role: message.role as "user" | "assistant",
            content: message.content
          });
        }
      }

      if (anthropicMessages.length === 0) {
        anthropicMessages.push({ role: "user", content: "Hello" });
      }
      
      const response = await this.anthropic.messages.create({
        model: modelName,
        max_tokens: maxTokens,
        temperature: temperature,
        system: systemMessage || undefined,
        messages: anthropicMessages,
      });
      
      const firstBlock = response.content[0];
      return firstBlock.type === "text" ? firstBlock.text : "";
    } catch (error: any) {
      console.error("Error generating Anthropic response:", error);
      throw new Error(`Failed to generate response: ${error.message}`);
    }
  }
  
  async analyzeImage(base64Image: string, prompt: string): Promise<string> {
    if (!this.isAvailable()) {
      throw new Error("Anthropic AI integration is not configured");
    }
    
    try {
      const response = await this.anthropic.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 8192,
        messages: [{
          role: "user",
          content: [
            {
              type: "text",
              text: prompt
            },
            {
              type: "image",
              source: {
                type: "base64",
                media_type: "image/jpeg",
                data: base64Image
              }
            }
          ]
        }]
      });
      
      const firstBlock = response.content[0];
      return firstBlock.type === "text" ? firstBlock.text : "";
    } catch (error: any) {
      console.error("Error analyzing image with Anthropic:", error);
      throw new Error(`Failed to analyze image: ${error.message}`);
    }
  }
}
