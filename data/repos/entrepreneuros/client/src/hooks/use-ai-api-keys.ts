import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AIModelProvider } from "./use-ai-models";

// Hook to check which AI providers have API keys configured
export function useAIApiKeyStatus() {
  const { data, isLoading, error, refetch } = useQuery<Record<AIModelProvider, boolean>>({
    queryKey: ["/api/ai/provider-status"],
    queryFn: async () => {
      const response = await fetch("/api/ai/provider-status");
      if (!response.ok) {
        throw new Error("Failed to fetch API key status");
      }
      const data = await response.json();
      return data.providerStatus;
    },
    // Don't refetch on window focus to avoid unnecessary API calls
    refetchOnWindowFocus: false,
  });

  return {
    providerStatus: data || {} as Record<AIModelProvider, boolean>,
    isLoading,
    error,
    refetch,
  };
}

// Hook for requesting API keys when needed
export function useRequestAIKeys() {
  const { providerStatus, refetch } = useAIApiKeyStatus();
  const [requiredKeys, setRequiredKeys] = useState<AIModelProvider[]>([]);
  
  // Function to request missing API keys for specific providers
  const requestKeys = async (providers: AIModelProvider[]) => {
    // Filter out providers that already have keys
    const missingProviders = providers.filter(provider => {
      return !providerStatus || !providerStatus[provider];
    });
    
    if (missingProviders.length === 0) {
      return true;
    }
    
    setRequiredKeys(missingProviders);
    
    // Client code will handle showing a dialog to request keys
    return false;
  };
  
  // Generate an array of environment variable names based on provider
  const getKeyNames = (providers: AIModelProvider[]): string[] => {
    return providers.map(provider => {
      switch (provider) {
        case "openai": return "OPENAI_API_KEY";
        case "anthropic": return "ANTHROPIC_API_KEY";
        case "perplexity": return "PERPLEXITY_API_KEY";
        case "xai": return "XAI_API_KEY";
        case "gemini": return "GEMINI_API_KEY";
        default: return "";
      }
    }).filter(Boolean);
  };
  
  return {
    requiredKeys,
    requestKeys,
    getKeyNames,
    refetchStatus: refetch
  };
}