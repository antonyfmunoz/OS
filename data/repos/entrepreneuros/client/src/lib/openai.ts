import { AIModelConfig } from "@/hooks/use-ai-models";
import { apiRequest } from "./queryClient";

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export async function sendMessageToAgent(
  agentId: string,
  message: string,
  aiConfig: AIModelConfig | null = null
): Promise<string> {
  try {
    const response = await apiRequest("POST", `/api/agents/${agentId}/chat`, {
      message,
      aiConfig
    });
    
    const data = await response.json();
    return data.reply;
  } catch (error) {
    console.error("Error sending message to agent:", error);
    throw new Error(error instanceof Error ? error.message : "Failed to send message");
  }
}

export async function saveApiKey(keyName: string, value: string): Promise<void> {
  try {
    await apiRequest("POST", "/api/keys/save", {
      keyName,
      value
    });
  } catch (error) {
    console.error("Error saving API key:", error);
    throw new Error(error instanceof Error ? error.message : "Failed to save API key");
  }
}