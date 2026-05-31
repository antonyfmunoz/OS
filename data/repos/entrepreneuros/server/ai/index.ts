import { OpenAIService } from "./openai-service";
import { AnthropicService } from "./anthropic-service";
import { PerplexityService } from "./perplexity-service";
import { XAIService } from "./xai-service";
import { GeminiService } from "./gemini-service";
import { AgentBrain } from "../openai";

export type AIModelProvider = "openai" | "anthropic" | "perplexity" | "xai" | "gemini";
export type AIModelName = 
  | "gpt-4o" 
  | "gpt-4-turbo" 
  | "gpt-3.5-turbo"
  | "claude-haiku-4-5"
  | "claude-sonnet-4-5"
  | "llama-3.1-sonar-small-128k-online"
  | "llama-3.1-sonar-large-128k-online"
  | "grok-2-1212"
  | "grok-2-vision-1212"
  | "gemini-2.5-pro"
  | "gemini-2.5-pro-vision";

export interface AIModelConfig {
  provider: AIModelProvider;
  modelName: AIModelName;
  maxTokens?: number;
  temperature?: number;
}

export interface AIMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface AIServiceInterface {
  isAvailable(): boolean;
  generateResponse(messages: AIMessage[], config?: Partial<AIModelConfig>): Promise<string>;
  generateImage?(prompt: string): Promise<string>;
  analyzeImage?(base64Image: string, prompt: string): Promise<string>;
}

const defaultConfigs: Record<AIModelProvider, AIModelConfig> = {
  anthropic: {
    provider: "anthropic",
    modelName: "claude-haiku-4-5",
    maxTokens: 8192,
    temperature: 0.7
  },
  openai: {
    provider: "openai",
    modelName: "gpt-4o",
    maxTokens: 8192,
    temperature: 0.7
  },
  perplexity: {
    provider: "perplexity",
    modelName: "llama-3.1-sonar-small-128k-online",
    maxTokens: 8192,
    temperature: 0.7
  },
  xai: {
    provider: "xai",
    modelName: "grok-2-1212",
    maxTokens: 8192,
    temperature: 0.7
  },
  gemini: {
    provider: "gemini",
    modelName: "gemini-2.5-pro",
    maxTokens: 8192,
    temperature: 0.7
  }
};

let openAIService: OpenAIService | null = null;
let anthropicService: AnthropicService | null = null;
let perplexityService: PerplexityService | null = null;
let xaiService: XAIService | null = null;
let geminiService: GeminiService | null = null;

function getService(provider: AIModelProvider): AIServiceInterface | null {
  switch (provider) {
    case "anthropic":
      if (!anthropicService) {
        anthropicService = new AnthropicService();
      }
      return anthropicService;
    case "openai":
      if (!openAIService) {
        openAIService = new OpenAIService();
      }
      return openAIService;
    case "perplexity":
      if (!perplexityService) {
        perplexityService = new PerplexityService();
      }
      return perplexityService;
    case "xai":
      if (!xaiService) {
        xaiService = new XAIService();
      }
      return xaiService;
    case "gemini":
      if (!geminiService) {
        geminiService = new GeminiService();
      }
      return geminiService;
    default:
      return null;
  }
}

export function getAvailableProviders(): AIModelProvider[] {
  const providers: AIModelProvider[] = [];
  
  if (new AnthropicService().isAvailable()) {
    providers.push("anthropic");
  }
  
  if (new OpenAIService().isAvailable()) {
    providers.push("openai");
  }
  
  if (new PerplexityService().isAvailable()) {
    providers.push("perplexity");
  }
  
  if (new XAIService().isAvailable()) {
    providers.push("xai");
  }
  
  if (new GeminiService().isAvailable()) {
    providers.push("gemini");
  }
  
  return providers;
}

export async function generateAIResponse(
  messages: AIMessage[],
  config: Partial<AIModelConfig> = {}
): Promise<string> {
  const provider = config.provider || "anthropic";
  const service = getService(provider);
  
  if (!service || !service.isAvailable()) {
    throw new Error(`AI provider ${provider} is not available or properly configured`);
  }
  
  const fullConfig = {
    ...defaultConfigs[provider],
    ...config
  };
  
  return await service.generateResponse(messages, fullConfig);
}

export async function generateAgentResponse(
  messages: AIMessage[],
  brain: AgentBrain,
  config: Partial<AIModelConfig> = {}
): Promise<string> {
  const systemMessage: AIMessage = {
    role: "system",
    content: `You are ${brain.name}, ${brain.role}. ${brain.instructions}`
  };
  
  if (brain.knowledgeBase) {
    systemMessage.content += `\n\nYou have the following knowledge base:\n${brain.knowledgeBase}`;
  }
  
  const allMessages = [systemMessage, ...messages];
  
  return await generateAIResponse(allMessages, config);
}

export async function generateImage(
  prompt: string,
  provider: AIModelProvider = "openai"
): Promise<string> {
  const service = getService(provider);
  
  if (!service || !service.isAvailable() || !service.generateImage) {
    throw new Error(`Image generation not available with provider ${provider}`);
  }
  
  return await service.generateImage(prompt);
}

export async function analyzeImage(
  base64Image: string,
  prompt: string,
  provider: AIModelProvider = "anthropic"
): Promise<string> {
  const service = getService(provider);
  
  if (!service || !service.isAvailable() || !service.analyzeImage) {
    throw new Error(`Image analysis not available with provider ${provider}`);
  }
  
  return await service.analyzeImage(base64Image, prompt);
}

interface ModelInfo {
  models: {
    name: AIModelName;
    description: string;
    contextWindow: number;
    capabilities: string[];
  }[];
}

export function getModelInfo(): Record<AIModelProvider, ModelInfo> {
  return {
    anthropic: {
      models: [
        {
          name: "claude-haiku-4-5",
          description: "Fast and efficient for everyday tasks",
          contextWindow: 200000,
          capabilities: ["Text generation", "Quick answers", "Basic reasoning", "Summarization"],
        },
        {
          name: "claude-sonnet-4-5",
          description: "Balanced performance for complex reasoning",
          contextWindow: 200000,
          capabilities: ["Advanced reasoning", "Code generation", "Deep analysis", "Complex tasks"],
        }
      ]
    },
    openai: {
      models: [
        {
          name: "gpt-4o",
          description: "Latest multimodal model with enhanced reasoning",
          contextWindow: 128000,
          capabilities: ["Text generation", "Image understanding", "Advanced reasoning"],
        },
        {
          name: "gpt-4-turbo",
          description: "Fast and efficient general purpose model",
          contextWindow: 128000,
          capabilities: ["Text generation", "Summarization", "Content creation"],
        },
        {
          name: "gpt-3.5-turbo",
          description: "Fast and cost-effective general purpose model",
          contextWindow: 16000,
          capabilities: ["Text generation", "Summarization", "Basic reasoning"],
        }
      ]
    },
    perplexity: {
      models: [
        {
          name: "llama-3.1-sonar-small-128k-online",
          description: "Efficient model with internet access",
          contextWindow: 128000,
          capabilities: ["Text generation", "Internet search", "Real-time information"],
        },
        {
          name: "llama-3.1-sonar-large-128k-online",
          description: "Larger model with advanced capabilities",
          contextWindow: 128000,
          capabilities: ["Advanced reasoning", "Internet search", "Long-form content"],
        }
      ]
    },
    xai: {
      models: [
        {
          name: "grok-2-1212",
          description: "General purpose text model",
          contextWindow: 131072,
          capabilities: ["Text generation", "Code generation", "Problem solving"],
        },
        {
          name: "grok-2-vision-1212",
          description: "Multimodal model for text and images",
          contextWindow: 8192,
          capabilities: ["Text generation", "Image understanding", "Visual reasoning"],
        }
      ]
    },
    gemini: {
      models: [
        {
          name: "gemini-2.5-pro",
          description: "Latest general purpose model",
          contextWindow: 131072,
          capabilities: ["Text generation", "Complex reasoning", "Creative writing"],
        },
        {
          name: "gemini-2.5-pro-vision",
          description: "Multimodal vision and language model",
          contextWindow: 131072,
          capabilities: ["Text generation", "Image understanding", "Visual reasoning"],
        }
      ]
    }
  };
}
