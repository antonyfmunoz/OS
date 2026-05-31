import { useQuery } from "@tanstack/react-query";

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

export interface AIModelInfo {
  provider: AIModelProvider;
  models: {
    name: AIModelName;
    description: string;
    contextWindow: number;
    capabilities: string[];
  }[];
  isAvailable: boolean;
}

export function useAIModels() {
  const { data, isLoading, error } = useQuery<{providers: AIModelInfo[]}>({
    queryKey: ["/api/ai/models"],
    queryFn: async () => {
      const response = await fetch("/api/ai/models");
      if (!response.ok) {
        throw new Error("Failed to fetch AI models");
      }
      return await response.json();
    },
    refetchOnWindowFocus: false,
  });

  return {
    models: data?.providers || [],
    isLoading,
    error,
  };
}
