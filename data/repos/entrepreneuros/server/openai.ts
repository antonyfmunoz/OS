import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY,
  baseURL: process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL,
});

export type AgentBrain = {
  instructions: string;
  knowledgeBase?: string;
  role: string;
  name: string;
};

export async function generateAgentResponse(
  message: string,
  brain: AgentBrain,
  history: { role: string; content: string }[]
): Promise<string> {
  try {
    const systemContent = `You are ${brain.name}, an AI assistant with the role of ${brain.role}. 
          ${brain.instructions}
          ${brain.knowledgeBase ? `Use this knowledge base: ${brain.knowledgeBase}` : ""}
          Respond in a helpful, concise, and professional manner. Focus on your specific role.`;

    const anthropicMessages = [
      ...history.filter(m => m.role !== "system").map(m => ({
        role: (m.role === "user" ? "user" : "assistant") as "user" | "assistant",
        content: m.content,
      })),
      { role: "user" as const, content: message },
    ];

    const response = await anthropic.messages.create({
      model: "claude-haiku-4-5",
      max_tokens: 8192,
      system: systemContent,
      messages: anthropicMessages,
    });

    const firstBlock = response.content[0];
    return firstBlock.type === "text" ? firstBlock.text : "I'm sorry, I couldn't generate a response.";
  } catch (error) {
    console.error("Error generating response from Claude:", error);
    return "I'm having trouble connecting to my knowledge base. Please try again in a moment.";
  }
}

export async function generateTaskSuggestion(
  agentBrain: AgentBrain,
  currentTasks: { title: string; description: string; status: string }[]
): Promise<{ title: string; description: string } | null> {
  try {
    const response = await anthropic.messages.create({
      model: "claude-haiku-4-5",
      max_tokens: 8192,
      system: `You are ${agentBrain.name}, an AI assistant with the role of ${agentBrain.role}.
          Based on your role and the current tasks, suggest a new task that would be valuable to work on.
          Current tasks: ${JSON.stringify(currentTasks)}
          
          Respond in JSON format with:
          {
            "title": "Task title - keep it short and specific",
            "description": "Brief description of what needs to be done and why it's important"
          }`,
      messages: [
        { role: "user", content: "Suggest a new task based on current priorities." }
      ],
    });

    const firstBlock = response.content[0];
    const content = firstBlock.type === "text" ? firstBlock.text : null;
    if (!content) return null;
    
    return JSON.parse(content);
  } catch (error) {
    console.error("Error generating task suggestion:", error);
    return null;
  }
}
