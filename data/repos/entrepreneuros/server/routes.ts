import { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { setupAuth } from "./auth";
import { generateAgentResponse, generateTaskSuggestion } from "./openai";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY,
  baseURL: process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL,
});
import { z } from "zod";
import { 
  insertAgentSchema, 
  insertTaskSchema, 
  updateTaskSchema,
  messages as messagesTable,
  insertCrmContactSchema,
  insertCrmDealSchema,
  insertCrmActivitySchema,
  insertDocumentSchema,
  insertFolderSchema,
  insertAgentActionSchema,
} from "@shared/schema";
import { 
  getModelInfo, 
  generateAIResponse, 
  AIMessage, 
  getAvailableProviders, 
  AIModelProvider,
  AIModelName 
} from "./ai";
import { db } from "./db";
import * as gmail from "./integrations/gmail";
import { executeAction } from "./services/action-executor";

export async function registerRoutes(app: Express): Promise<Server> {
  // Set up authentication routes and middleware
  setupAuth(app);
  // AI Models API
  app.get("/api/ai/models", (_req, res) => {
    try {
      const modelInfo = getModelInfo();
      const availableProviders = getAvailableProviders();
      
      // Transform model info into the expected format for the frontend
      const providers = Object.entries(modelInfo).map(([providerKey, info]) => {
        const provider = providerKey as AIModelProvider;
        return {
          provider,
          models: info.models,
          isAvailable: availableProviders.includes(provider)
        };
      });
      
      res.json({ providers });
    } catch (error) {
      console.error("Error fetching AI model info:", error);
      res.status(500).json({ message: "Failed to fetch AI model information" });
    }
  });
  
  // API Key Management
  app.get("/api/ai/provider-status", (_req, res) => {
    try {
      const providerStatus = {
        anthropic: !!(process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY && process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL),
        openai: !!process.env.OPENAI_API_KEY,
        perplexity: !!process.env.PERPLEXITY_API_KEY,
        xai: !!process.env.XAI_API_KEY,
        gemini: !!process.env.GEMINI_API_KEY
      };
      
      res.json({ providerStatus });
    } catch (error) {
      console.error("Error checking AI provider status:", error);
      res.status(500).json({ message: "Failed to check AI provider status" });
    }
  });
  
  // Save API Key - this only works for development purposes
  // In production, you should use a proper secrets management system
  app.post("/api/keys/save", (req, res) => {
    try {
      const { keyName, value } = req.body;
      
      // Validate the key name to prevent security issues
      const allowedKeys = [
        "OPENAI_API_KEY", 
        "ANTHROPIC_API_KEY", 
        "PERPLEXITY_API_KEY",
        "XAI_API_KEY",
        "GEMINI_API_KEY"
      ];
      
      if (!allowedKeys.includes(keyName)) {
        return res.status(400).json({ message: "Invalid API key name" });
      }
      
      if (!value) {
        return res.status(400).json({ message: "API key value is required" });
      }
      
      // Set environment variable
      process.env[keyName] = value;
      
      console.log(`API key ${keyName} has been updated`);
      
      res.json({ success: true });
    } catch (error) {
      console.error("Error saving API key:", error);
      res.status(500).json({ message: "Failed to save API key" });
    }
  });
  
  app.post("/api/ai/generate", async (req, res) => {
    try {
      const { messages, config } = req.body;
      
      if (!messages || !Array.isArray(messages)) {
        return res.status(400).json({ message: "Messages array is required" });
      }
      
      const aiMessages: AIMessage[] = messages.map(m => ({
        role: m.role,
        content: m.content
      }));
      
      const response = await generateAIResponse(aiMessages, config || {});
      res.json({ response });
    } catch (error) {
      console.error("AI generation error:", error);
      res.status(500).json({ 
        message: "Failed to generate AI response",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  // Agents API
  app.get("/api/agents", async (_req, res) => {
    try {
      const agents = await storage.getAgents();
      
      // For each agent, fetch their tasks
      const agentsWithTasks = await Promise.all(
        agents.map(async (agent) => {
          const tasks = await storage.getAgentTasks(agent.id);
          return {
            ...agent,
            tasks: tasks.map(task => ({
              id: task.id,
              title: task.title,
              status: task.status
            }))
          };
        })
      );
      
      res.json(agentsWithTasks);
    } catch (error) {
      console.error("Error fetching agents with tasks:", error);
      res.status(500).json({ message: "Failed to fetch agents" });
    }
  });

  app.get("/api/agents/:id", async (req, res) => {
    try {
      const agentId = req.params.id;
      
      if (agentId === "direct-claude" || agentId === "direct-gpt4o") {
        return res.json({
          id: "direct-claude",
          name: "Claude Direct Chat",
          role: "AI Assistant",
          icon: "ri-robot-2-line",
          instructions: "You are Claude, an AI assistant. Answer helpfully, concisely, and professionally.",
          color: "#7C3AED",
          createdAt: new Date().toISOString(),
          tasks: []
        });
      }
      
      // Normal case - get agent from database
      const agent = await storage.getAgent(agentId);
      if (!agent) {
        return res.status(404).json({ message: "Agent not found" });
      }
      
      // Get the agent's tasks
      const tasks = await storage.getAgentTasks(agentId);
      
      // Return agent with tasks
      res.json({
        ...agent,
        tasks: tasks.map(task => ({
          id: task.id,
          title: task.title,
          status: task.status
        }))
      });
    } catch (error) {
      console.error("Error fetching agent:", error);
      res.status(500).json({ message: "Failed to fetch agent" });
    }
  });
  
  // Update an agent
  app.patch("/api/agents/:id", async (req, res) => {
    try {
      const agentId = req.params.id;
      
      // Verify the agent exists
      const existingAgent = await storage.getAgent(agentId);
      if (!existingAgent) {
        return res.status(404).json({ message: "Agent not found" });
      }
      
      // Update the agent with the provided fields
      const updatedAgent = await storage.updateAgent(agentId, req.body);
      
      res.json(updatedAgent);
    } catch (error) {
      console.error("Error updating agent:", error);
      res.status(500).json({ 
        message: "Failed to update agent",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });

  app.post("/api/agents", async (req, res) => {
    try {
      const agentData = insertAgentSchema.parse(req.body);
      const agent = await storage.createAgent(agentData);
      res.status(201).json(agent);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid agent data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create agent" });
    }
  });

  // Agent Messages API
  app.get("/api/agents/:id/messages", async (req, res) => {
    const agentId = req.params.id;
    
    if (agentId === "direct-claude" || agentId === "direct-gpt4o") {
      const messages = await storage.getAgentMessages(agentId);
      
      // If the agent exists in database, return its messages
      if (messages && messages.length > 0) {
        return res.json(messages);
      }
      
      // Otherwise return empty array for first-time use
      return res.json([]);
    }
    
    // Regular case
    const messages = await storage.getAgentMessages(agentId);
    res.json(messages);
  });
  
  // Clear agent messages (New Chat functionality)
  app.post("/api/agents/:id/clear-messages", async (req, res) => {
    try {
      const agentId = req.params.id;
      await storage.clearAgentMessages(agentId);
      res.json({ success: true, message: "Chat history cleared successfully" });
    } catch (error) {
      console.error("Error clearing agent messages:", error);
      res.status(500).json({ error: "Failed to clear agent messages" });
    }
  });

  app.post("/api/agents/:id/chat", async (req, res) => {
    try {
      const { message, aiConfig } = req.body;
      if (!message) {
        return res.status(400).json({ message: "Message is required" });
      }
      
      const agentId = req.params.id;
      
      if (agentId === "direct-claude") {
        const virtualClaudeAgent = {
          id: "direct-claude",
          name: "Claude Direct Chat",
          role: "AI Assistant",
          icon: "ri-robot-2-line",
          instructions: "You are Claude, an AI assistant made by Anthropic. Answer helpfully, concisely, and professionally.",
          brainContent: "",
        };
        
        await storage.addAgentMessage({
          agentId: agentId,
          role: "user",
          content: message,
          timestamp: new Date().toISOString(),
        });
        
        const selectedModel = aiConfig?.modelName || "claude-haiku-4-5";
        
        try {
          const response = await anthropic.messages.create({
            model: selectedModel,
            max_tokens: 8192,
            system: virtualClaudeAgent.instructions,
            messages: [
              {
                role: "user",
                content: message
              }
            ],
            temperature: 0.2,
          });
          
          const firstBlock = response.content[0];
          const reply = firstBlock.type === "text" ? firstBlock.text : "";
          
          const aiMessage = await storage.addAgentMessage({
            agentId: agentId,
            role: "assistant",
            content: reply,
            timestamp: new Date().toISOString(),
          });
          
          return res.json({ reply, messageId: aiMessage.id });
        } catch (error) {
          console.error("Error in direct Claude mode:", error);
          throw error;
        }
      }
      
      // Normal case - get agent from database for regular agents
      const agent = await storage.getAgent(agentId);
      if (!agent) {
        return res.status(404).json({ message: "Agent not found" });
      }

      // Add user message to storage
      await storage.addAgentMessage({
        agentId: req.params.id,
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
      });
      
      // Get all messages for context
      const dbMessages = await storage.getAgentMessages(req.params.id);
      
      // Setup agent brain info
      const brain = {
        instructions: agent.instructions || "",
        knowledgeBase: agent.brainContent || "",
        role: agent.role,
        name: agent.name,
      };
      
      let reply;
      
      const actionSystemPrompt = `\n\nYou can propose actions for the user to approve. When you want to take an action, include it in your response using this format:
[ACTION:SEND_EMAIL|to:recipient@example.com|subject:Email Subject|body:Email body text]
[ACTION:CREATE_TASK|title:Task Title|description:Task description|priority:medium]
[ACTION:CREATE_DOCUMENT|title:Document Title|content:Document content]
Only propose actions when the user explicitly asks you to do something actionable. Always explain what action you're proposing before the tag.`;

      if (aiConfig) {
        try {
          const aiMessages: AIMessage[] = dbMessages.map(m => ({
            role: m.role === "user" || m.role === "assistant" ? m.role : "user",
            content: m.content
          }));
          
          aiMessages.unshift({
            role: "system",
            content: `You are ${agent.name}, ${agent.role}. ${agent.instructions || ""}
                    ${agent.brainContent ? `\n\nReference knowledge:\n${agent.brainContent}` : ""}${actionSystemPrompt}`
          });
          
          reply = await generateAIResponse(aiMessages, aiConfig);
        } catch (aiError) {
          console.error("Error using unified AI service:", aiError);
          const history = dbMessages.map(msg => ({
            role: msg.role,
            content: msg.content,
          }));
          reply = await generateAgentResponse(message, brain, history);
        }
      } else {
        const history = dbMessages.map(msg => ({
          role: msg.role,
          content: msg.content,
        }));
        reply = await generateAgentResponse(message, brain, history);
      }

      const actionRegex = /\[ACTION:(\w+)\|([^\]]+)\]/g;
      let match;
      const extractedActions: any[] = [];
      let cleanReply = reply;

      while ((match = actionRegex.exec(reply)) !== null) {
        const actionType = match[1].toLowerCase();
        const paramsStr = match[2];
        const params: Record<string, string> = {};
        paramsStr.split("|").forEach(p => {
          const [key, ...valueParts] = p.split(":");
          if (key && valueParts.length > 0) {
            params[key.trim()] = valueParts.join(":").trim();
          }
        });

        const actionTypeMap: Record<string, string> = {
          send_email: "Send Email",
          create_task: "Create Task",
          create_document: "Create Document",
        };

        try {
          if (!req.isAuthenticated()) continue;
          const userId = (req.user as any).id;
          const action = await storage.createAction({
            agentId: req.params.id,
            userId,
            actionType,
            actionName: actionTypeMap[actionType] || actionType,
            description: `${actionTypeMap[actionType] || actionType} proposed by ${agent.name}`,
            parameters: params,
            estimatedTimeSaved: actionType === "send_email" ? 5 : 3,
          });
          extractedActions.push(action);
        } catch (actionErr) {
          console.error("Error creating action record:", actionErr);
        }

        cleanReply = cleanReply.replace(match[0], "");
      }

      cleanReply = cleanReply.trim();

      const aiMessage = await storage.addAgentMessage({
        agentId: req.params.id,
        role: "assistant",
        content: cleanReply,
        timestamp: new Date().toISOString(),
      });

      await storage.updateAgentActivity(req.params.id, "Responded to user message");

      res.json({ 
        reply: cleanReply, 
        messageId: aiMessage.id,
        actionsCreated: extractedActions.length,
        actions: extractedActions,
      });
    } catch (error) {
      console.error("Error in chat:", error);
      res.status(500).json({ 
        message: "Failed to process message",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });

  // Agent Tasks API
  app.get("/api/agents/:id/tasks", async (req, res) => {
    const agentId = req.params.id;
    
    if (agentId === "direct-claude" || agentId === "direct-gpt4o") {
      return res.json([]);
    }
    
    // Regular case
    const tasks = await storage.getAgentTasks(agentId);
    res.json(tasks);
  });

  app.post("/api/agents/:id/generate-response", async (req, res) => {
    try {
      const { taskId, aiConfig } = req.body;
      if (!taskId) {
        return res.status(400).json({ message: "Task ID is required" });
      }

      const agent = await storage.getAgent(req.params.id);
      if (!agent) {
        return res.status(404).json({ message: "Agent not found" });
      }

      const task = await storage.getTask(taskId);
      if (!task) {
        return res.status(404).json({ message: "Task not found" });
      }

      // Generate a response about the task
      const brain = {
        instructions: agent.instructions || "",
        knowledgeBase: agent.brainContent || "",
        role: agent.role,
        name: agent.name,
      };
      
      let response;
      
      // Try the unified AI service first if aiConfig is provided
      if (aiConfig) {
        try {
          // Create messages for AI
          const messages: AIMessage[] = [
            {
              role: "system",
              content: `You are ${agent.name}, ${agent.role}. ${agent.instructions || ""}
                      ${agent.brainContent ? `\n\nReference knowledge:\n${agent.brainContent}` : ""}`
            },
            {
              role: "user",
              content: `Please provide an update or next steps for this task: ${task.title} - ${task.description}`
            }
          ];
          
          response = await generateAIResponse(messages, aiConfig);
        } catch (aiError) {
          console.error("Error using unified AI service for task response:", aiError);
          // Fall back to OpenAI
          response = await generateAgentResponse(
            `Please provide an update or next steps for this task: ${task.title} - ${task.description}`,
            brain,
            []
          );
        }
      } else {
        // Use the original OpenAI implementation
        response = await generateAgentResponse(
          `Please provide an update or next steps for this task: ${task.title} - ${task.description}`,
          brain,
          []
        );
      }

      res.json({ response });
    } catch (error) {
      console.error("Error generating response:", error);
      res.status(500).json({ 
        message: "Failed to generate response",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });

  // Tasks API
  app.get("/api/tasks", async (_req, res) => {
    const tasks = await storage.getTasks();
    res.json(tasks);
  });

  app.get("/api/tasks/:id", async (req, res) => {
    const task = await storage.getTask(req.params.id);
    if (!task) {
      return res.status(404).json({ message: "Task not found" });
    }
    res.json(task);
  });

  app.post("/api/tasks", async (req, res) => {
    try {
      const taskData = insertTaskSchema.parse(req.body);
      const task = await storage.createTask(taskData);

      // If task is assigned to an agent, update the agent's tasks
      if (taskData.agentId) {
        await storage.updateAgentActivity(taskData.agentId, `Assigned new task: ${taskData.title}`);
      }

      res.status(201).json(task);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid task data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create task" });
    }
  });

  app.patch("/api/tasks/:id", async (req, res) => {
    try {
      const taskUpdate = updateTaskSchema.parse(req.body);
      const task = await storage.getTask(req.params.id);
      
      if (!task) {
        return res.status(404).json({ message: "Task not found" });
      }
      
      const updatedTask = await storage.updateTask(req.params.id, taskUpdate);

      // If task has an agent assigned, update the agent's activity
      if (task.agentId) {
        const statusText = taskUpdate.status === "done" 
          ? "completed" 
          : taskUpdate.status === "in-progress" 
            ? "started working on" 
            : "is planning";
            
        await storage.updateAgentActivity(
          task.agentId, 
          `${statusText} task: ${task.title}`
        );
      }

      res.json(updatedTask);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid task update", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to update task" });
    }
  });
  
  app.delete("/api/tasks/:id", async (req, res) => {
    try {
      const taskId = req.params.id;
      const task = await storage.getTask(taskId);
      
      if (!task) {
        return res.status(404).json({ message: "Task not found" });
      }
      
      await storage.deleteTask(taskId);
      res.status(200).json({ message: "Task deleted successfully" });
    } catch (error) {
      console.error("Error deleting task:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid request", errors: error.errors });
      }
      res.status(500).json({ 
        message: "Failed to delete task",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  // Task Collaboration Endpoints
  app.post("/api/tasks/:id/collaborators", async (req, res) => {
    try {
      const { agentId } = req.body;
      if (!agentId) {
        return res.status(400).json({ message: "Agent ID is required" });
      }
      
      const agent = await storage.getAgent(agentId);
      if (!agent) {
        return res.status(404).json({ message: "Agent not found" });
      }
      
      const updatedTask = await storage.addAgentCollaborator(req.params.id, agentId);
      
      // Update the agent's activity
      await storage.updateAgentActivity(
        agentId,
        `Added as collaborator on task: ${updatedTask.title}`
      );
      
      // If there's a primary agent assigned, notify them too
      if (updatedTask.agentId && updatedTask.agentId !== agentId) {
        await storage.updateAgentActivity(
          updatedTask.agentId,
          `${agent.name} joined as collaborator on task: ${updatedTask.title}`
        );
      }
      
      res.json(updatedTask);
    } catch (error) {
      console.error("Error adding collaborator:", error);
      res.status(500).json({ 
        message: "Failed to add collaborator",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.post("/api/tasks/:id/assign", async (req, res) => {
    try {
      const { agentId, assignedById } = req.body;
      
      if (!agentId) {
        return res.status(400).json({ message: "Agent ID is required" });
      }
      
      // Verify both agents exist
      const targetAgent = await storage.getAgent(agentId);
      if (!targetAgent) {
        return res.status(404).json({ message: "Target agent not found" });
      }
      
      let assigningAgent;
      if (assignedById) {
        assigningAgent = await storage.getAgent(assignedById);
        if (!assigningAgent) {
          return res.status(404).json({ message: "Assigning agent not found" });
        }
      }
      
      const updatedTask = await storage.assignTaskToAgent(req.params.id, agentId, assignedById);
      
      // Update the new agent's activity
      await storage.updateAgentActivity(
        agentId,
        `Assigned task: ${updatedTask.title}`
      );
      
      // If assigned by another agent, update their activity too
      if (assigningAgent) {
        await storage.updateAgentActivity(
          assignedById,
          `Delegated task "${updatedTask.title}" to ${targetAgent.name}`
        );
      }
      
      res.json(updatedTask);
    } catch (error) {
      console.error("Error assigning task:", error);
      res.status(500).json({ 
        message: "Failed to assign task",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.post("/api/tasks/:id/subtask", async (req, res) => {
    try {
      const subtaskData = insertTaskSchema.parse(req.body);
      const parentTask = await storage.getTask(req.params.id);
      
      if (!parentTask) {
        return res.status(404).json({ message: "Parent task not found" });
      }
      
      const subtask = await storage.createSubtask(req.params.id, subtaskData);
      
      // If subtask is assigned to an agent, update the agent's tasks
      if (subtaskData.agentId) {
        await storage.updateAgentActivity(
          subtaskData.agentId, 
          `Assigned new subtask: ${subtaskData.title}`
        );
      }
      
      res.status(201).json(subtask);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid subtask data", 
          errors: error.errors 
        });
      }
      console.error("Error creating subtask:", error);
      res.status(500).json({ 
        message: "Failed to create subtask",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.get("/api/tasks/:id/subtasks", async (req, res) => {
    try {
      const subtasks = await storage.getSubtasks(req.params.id);
      res.json(subtasks);
    } catch (error) {
      console.error("Error fetching subtasks:", error);
      res.status(500).json({ 
        message: "Failed to fetch subtasks",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.get("/api/tasks/:id/messages", async (req, res) => {
    try {
      const messages = await storage.getTaskMessages(req.params.id);
      res.json(messages);
    } catch (error) {
      console.error("Error fetching task messages:", error);
      res.status(500).json({ 
        message: "Failed to fetch task messages",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.post("/api/tasks/:id/messages", async (req, res) => {
    try {
      const { agentId, content, referencedAgentIds } = req.body;
      
      if (!agentId || !content) {
        return res.status(400).json({ 
          message: "Agent ID and message content are required" 
        });
      }
      
      // Create a new collaborative message associated with this task
      const message = await storage.addCollaborativeMessage({
        agentId,
        taskId: req.params.id,
        role: "assistant",
        content,
        referencedAgentIds: referencedAgentIds || null,
        timestamp: new Date().toISOString(),
      });
      
      // Update the agent's activity
      await storage.updateAgentActivity(
        agentId,
        `Added message to task: ${req.params.id}`
      );
      
      res.status(201).json(message);
    } catch (error) {
      console.error("Error adding task message:", error);
      res.status(500).json({ 
        message: "Failed to add task message",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  app.get("/api/agents/:id/collaborative-tasks", async (req, res) => {
    try {
      const tasks = await storage.getCollaborativeTasks(req.params.id);
      res.json(tasks);
    } catch (error) {
      console.error("Error fetching collaborative tasks:", error);
      res.status(500).json({ 
        message: "Failed to fetch collaborative tasks",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  // Conversations API
  app.get("/api/conversations/:id", async (req, res) => {
    try {
      const messages = await storage.getConversationMessages(req.params.id);
      res.json(messages);
    } catch (error) {
      console.error("Error fetching conversation:", error);
      res.status(500).json({ 
        message: "Failed to fetch conversation",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });
  
  // Multi-agent collaboration endpoint
  app.post("/api/ai/multi-agent", async (req, res) => {
    try {
      const { 
        mainAgentId, 
        collaboratorIds,
        prompt,
        taskId,
        aiConfig
      } = req.body;
      
      if (!mainAgentId || !collaboratorIds || !Array.isArray(collaboratorIds) || !prompt) {
        return res.status(400).json({ 
          message: "Main agent ID, collaborator IDs array, and prompt are required" 
        });
      }
      
      // Get all agent data
      const mainAgent = await storage.getAgent(mainAgentId);
      if (!mainAgent) {
        return res.status(404).json({ message: "Main agent not found" });
      }
      
      const collaborators = [];
      for (const id of collaboratorIds) {
        const agent = await storage.getAgent(id);
        if (agent) {
          collaborators.push(agent);
        }
      }
      
      // Create a conversation ID
      const conversationId = `conv_${Date.now()}`;
      
      // Build system prompt that introduces all the agents to each other
      let systemPrompt = `This is a collaborative discussion between the following AI agents:
      
      MAIN AGENT:
      Name: ${mainAgent.name}
      Role: ${mainAgent.role}
      Expertise: ${mainAgent.instructions || "Not specified"}
      
      COLLABORATING AGENTS:`;
      
      for (const agent of collaborators) {
        systemPrompt += `
      Name: ${agent.name}
      Role: ${agent.role}
      Expertise: ${agent.instructions || "Not specified"}`;
      }
      
      systemPrompt += `
      
      The agents should work together to solve the problem, each contributing their expertise.
      Each agent should clearly identify themselves before speaking by starting their response with "I am [Agent Name]:".
      The discussion should be constructive and focused on generating the best possible solution.`;
      
      // Add task context if provided
      if (taskId) {
        const task = await storage.getTask(taskId);
        if (task) {
          systemPrompt += `
          
          TASK DETAILS:
          Title: ${task.title}
          Description: ${task.description}
          Status: ${task.status}
          Priority: ${task.priority || "medium"}`;
        }
      }
      
      // Use AI service to generate a collaborative response
      let collaborationMessages: AIMessage[] = [
        { role: "system", content: systemPrompt },
        { role: "user", content: prompt }
      ];
      
      let response;
      if (aiConfig) {
        response = await generateAIResponse(collaborationMessages, aiConfig);
      } else {
        const availableProviders = getAvailableProviders();
        let provider: AIModelProvider = "anthropic";
        let modelName: AIModelName = "claude-sonnet-4-5";
        
        if (availableProviders.includes("anthropic")) {
          provider = "anthropic";
          modelName = "claude-sonnet-4-5";
        } else if (availableProviders.includes("openai")) {
          provider = "openai";
          modelName = "gpt-4o";
        } else if (availableProviders.includes("xai")) {
          provider = "xai";
          modelName = "grok-2-1212";
        }
        
        response = await generateAIResponse(collaborationMessages, { provider, modelName });
      }
      
      // Save the conversation
      await storage.addAgentMessage({
        agentId: mainAgentId,
        taskId: taskId || null,
        conversationId,
        role: "system",
        content: systemPrompt,
        referencedAgentIds: collaboratorIds.join(','),
        timestamp: new Date().toISOString(),
      });
      
      await storage.addAgentMessage({
        agentId: mainAgentId,
        taskId: taskId || null,
        conversationId,
        role: "user",
        content: prompt,
        referencedAgentIds: collaboratorIds.join(','),
        timestamp: new Date().toISOString(),
      });
      
      await storage.addAgentMessage({
        agentId: mainAgentId,
        taskId: taskId || null,
        conversationId,
        role: "assistant",
        content: response,
        referencedAgentIds: collaboratorIds.join(','),
        timestamp: new Date().toISOString(),
      });
      
      // Update the main agent's activity
      await storage.updateAgentActivity(
        mainAgentId,
        `Initiated collaboration with ${collaborators.map(a => a.name).join(', ')}`
      );
      
      // Update collaborator agents' activities
      for (const agent of collaborators) {
        await storage.updateAgentActivity(
          agent.id,
          `Participated in collaboration initiated by ${mainAgent.name}`
        );
      }
      
      res.json({ 
        response,
        conversationId,
        mainAgent: {
          id: mainAgent.id,
          name: mainAgent.name,
          role: mainAgent.role
        },
        collaboratingAgents: collaborators.map(agent => ({
          id: agent.id,
          name: agent.name,
          role: agent.role
        }))
      });
    } catch (error) {
      console.error("Error in multi-agent collaboration:", error);
      res.status(500).json({ 
        message: "Failed to process multi-agent collaboration",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });

  // Stats API
  app.get("/api/stats", async (_req, res) => {
    const agents = await storage.getAgents();
    const tasks = await storage.getTasks();
    
    const activeAgents = agents.length;
    const tasksCompleted = tasks.filter(task => task.status === "done").length;
    const activeTasks = tasks.filter(task => task.status !== "done").length;

    res.json({
      activeAgents: {
        title: "Active Agents",
        value: activeAgents,
        change: 1,
        changeText: "1 agent",
        icon: "ri-robot-line",
        iconBgColor: "bg-blue-100",
        iconColor: "text-primary",
      },
      tasksCompleted: {
        title: "Tasks Completed",
        value: tasksCompleted,
        change: 12,
        changeText: "12 tasks",
        icon: "ri-check-double-line",
        iconBgColor: "bg-green-100",
        iconColor: "text-success",
      },
      activeTasks: {
        title: "Active Tasks",
        value: activeTasks,
        change: -2,
        changeText: "2 tasks",
        icon: "ri-time-line",
        iconBgColor: "bg-indigo-100",
        iconColor: "text-secondary",
      },
    });
  });
  
  // Enhanced Analytics API
  app.get("/api/analytics", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const timeRange = req.query.timeRange as string || '7days';
      const showComparison = req.query.showComparison === 'true';
      const agents = await storage.getAgents();
      const tasks = await storage.getTasks();
      const allMessages = await storage.getAllMessages();
      
      // Calculate date range based on timeRange
      const now = new Date();
      const startDate = new Date();
      let daysToGenerate = 7;
      let comparisonLabel = 'vs previous week';
      
      if (timeRange === '7days') {
        startDate.setDate(now.getDate() - 7);
        daysToGenerate = 7;
        comparisonLabel = 'vs previous week';
      } else if (timeRange === '30days') {
        startDate.setDate(now.getDate() - 30);
        daysToGenerate = 30;
        comparisonLabel = 'vs previous month';
      } else if (timeRange === '90days') {
        startDate.setDate(now.getDate() - 90);
        daysToGenerate = 90;
        comparisonLabel = 'vs previous quarter';
      } else if (timeRange === '365days') {
        startDate.setDate(now.getDate() - 365);
        daysToGenerate = 365;
        comparisonLabel = 'vs previous year';
      }
      
      // Calculate start and end dates for previous period
      const previousPeriodEnd = new Date(startDate);
      previousPeriodEnd.setDate(previousPeriodEnd.getDate() - 1);
      
      const previousPeriodStart = new Date(previousPeriodEnd);
      previousPeriodStart.setDate(previousPeriodStart.getDate() - daysToGenerate);
      
      // Filter data within the selected time range
      const tasksInRange = tasks.filter(task => {
        if (!task.createdAt) return false;
        const createdDate = new Date(task.createdAt);
        return createdDate >= startDate && createdDate <= now;
      });
      
      const messagesInRange = allMessages.filter(message => {
        if (!message.timestamp) return false;
        const timestamp = new Date(message.timestamp);
        return timestamp >= startDate && timestamp <= now;
      });
      
      // Agent activity metrics
      const agentActivity: Record<string, number> = {};
      messagesInRange.forEach(message => {
        if (!message.agentId) return;
        agentActivity[message.agentId] = (agentActivity[message.agentId] || 0) + 1;
      });
      
      // Agent performance metrics
      const agentPerformance = agents.map(agent => {
        const agentTasks = tasksInRange.filter(task => task.agentId === agent.id);
        const completedTasks = agentTasks.filter(task => task.status === 'done');
        const inProgressTasks = agentTasks.filter(task => task.status === 'in-progress');
        const pendingTasks = agentTasks.filter(task => task.status === 'todo');
        
        // Calculate completion rate with actual data
        const completionRate = agentTasks.length > 0 ? completedTasks.length / agentTasks.length : 0;
        
        // Calculate accurate average completion time for completed tasks
        const averageCompletionTime = 
          completedTasks.length > 0 ? 
          completedTasks.reduce((sum, task) => {
            // Safely parse dates with fallbacks
            const createdDate = typeof task.createdAt === 'string' ? new Date(task.createdAt) : new Date();
            const updatedDate = typeof task.updatedAt === 'string' ? new Date(task.updatedAt) : new Date();
            const hoursDiff = Math.max(0, (updatedDate.getTime() - createdDate.getTime()) / (1000 * 60 * 60));
            return sum + hoursDiff;
          }, 0) / completedTasks.length : 0;
        
        // Count tasks by priority with proper fallbacks
        const highPriorityTasks = agentTasks.filter(task => task.priority === 'high').length;
        const mediumPriorityTasks = agentTasks.filter(task => task.priority === 'medium').length;
        const lowPriorityTasks = agentTasks.filter(task => task.priority === 'low' || !task.priority).length;
        
        // Calculate message activity
        const messageCount = agentActivity[agent.id] || 0;
        
        return {
          id: agent.id,
          name: agent.name,
          role: agent.role,
          icon: agent.icon,
          tasksCompleted: completedTasks.length,
          tasksInProgress: inProgressTasks.length,
          tasksPending: pendingTasks.length,
          totalTasks: agentTasks.length,
          messageCount,
          activityScore: messageCount + (completedTasks.length * 3),
          completionRate,
          averageCompletionTime: parseFloat(averageCompletionTime.toFixed(2)),
          tasksByPriority: {
            high: highPriorityTasks,
            medium: mediumPriorityTasks,
            low: lowPriorityTasks
          }
        };
      });
      
      // Sort agents by activity score for more meaningful display
      agentPerformance.sort((a, b) => b.activityScore - a.activityScore);
      
      // Generate accurate task completion trends with real data
      const taskCompletionTrends = [];
      
      for (let i = 0; i < daysToGenerate; i++) {
        const date = new Date();
        date.setDate(date.getDate() - (daysToGenerate - i - 1));
        const dateStr = date.toISOString().split('T')[0];
        const dateCopy = new Date(date);
        dateCopy.setHours(23, 59, 59, 999); // End of the day
        
        // Filter tasks created on this date
        const tasksCreatedOnDate = tasks.filter(task => {
          if (!task.createdAt) return false;
          const createdDate = new Date(task.createdAt);
          return createdDate.toISOString().split('T')[0] === dateStr;
        }).length;
        
        // Filter tasks completed on this date
        const tasksCompletedOnDate = tasks.filter(task => {
          if (task.status !== 'done' || !task.updatedAt) return false;
          const updatedDate = new Date(task.updatedAt);
          return updatedDate.toISOString().split('T')[0] === dateStr;
        }).length;
        
        taskCompletionTrends.push({
          date: dateStr,
          created: tasksCreatedOnDate,
          completed: tasksCompletedOnDate
        });
      }
      
      // Task distribution by status with accurate counts
      const todoCount = tasks.filter(task => task.status === 'todo').length;
      const inProgressCount = tasks.filter(task => task.status === 'in-progress').length;
      const doneCount = tasks.filter(task => task.status === 'done').length;
      
      const taskDistributionByStatus = [
        {
          name: "Completed",
          value: doneCount,
          color: "#22c55e" // green-500
        },
        {
          name: "In Progress",
          value: inProgressCount,
          color: "#f59e0b" // yellow-500 
        },
        {
          name: "To Do",
          value: todoCount,
          color: "#6b7280" // gray-500
        }
      ].filter(item => item.value > 0); // Only include non-zero values
      
      // Get accurate task types from actual data
      const taskTypes = Array.from(new Set(tasks.map(task => task.taskType || 'standard')));
      
      // Task distribution by type
      const taskDistributionByType = taskTypes.map(type => {
        const count = tasks.filter(task => (task.taskType || 'standard') === type).length;
        const colors: Record<string, string> = {
          'standard': "#3b82f6", // blue-500
          'collaboration': "#8b5cf6", // violet-500
          'delegated': "#ec4899", // pink-500
          'subtask': "#14b8a6", // teal-500
          'default': "#64748b" // slate-500
        };
        
        return {
          name: type.charAt(0).toUpperCase() + type.slice(1),
          value: count,
          color: colors[type as keyof typeof colors] || colors['default']
        };
      }).filter(item => item.value > 0); // Only include non-zero values
      
      // Task distribution by priority with accurate counts
      const highCount = tasks.filter(task => task.priority === 'high').length;
      const mediumCount = tasks.filter(task => task.priority === 'medium').length;
      const lowCount = tasks.filter(task => task.priority === 'low' || !task.priority).length;
      
      const taskDistributionByPriority = [
        {
          name: "High",
          value: highCount,
          color: "#ef4444" // red-500
        },
        {
          name: "Medium",
          value: mediumCount,
          color: "#f59e0b" // yellow-500
        },
        {
          name: "Low",
          value: lowCount,
          color: "#10b981" // emerald-500
        }
      ].filter(item => item.value > 0); // Only include non-zero values
      
      // Calculate overall stats with accurate data
      const totalAgents = agents.length;
      const totalTasks = tasks.length;
      const completedTasksCount = tasks.filter(task => task.status === 'done').length;
      const completionRate = totalTasks > 0 ? completedTasksCount / totalTasks : 0;
      
      // Calculate accurate average task age in days
      const averageTaskAge = tasks.length > 0 ? 
        tasks.reduce((sum, task) => {
          if (!task.createdAt) return sum;
          const createdDate = new Date(task.createdAt);
          const ageInDays = Math.max(0, (now.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
          return sum + ageInDays;
        }, 0) / tasks.length : 0;
      
      // Additional KPIs
      const totalMessages = allMessages.length;
      const averageTasksPerAgent = totalAgents > 0 ? totalTasks / totalAgents : 0;
      const messagesPerDay = daysToGenerate > 0 ? messagesInRange.length / daysToGenerate : 0;
      const tasksPerDay = daysToGenerate > 0 ? tasksInRange.length / daysToGenerate : 0;
      
      // Previous period data calculation
      const previousPeriodTasks = tasks.filter(task => {
        if (!task.createdAt) return false;
        const createdDate = new Date(task.createdAt);
        return createdDate >= previousPeriodStart && createdDate <= previousPeriodEnd;
      });
      
      const previousPeriodMessages = allMessages.filter(message => {
        if (!message.timestamp) return false;
        const timestamp = new Date(message.timestamp);
        return timestamp >= previousPeriodStart && timestamp <= previousPeriodEnd;
      });
      
      // Calculate task growth rate
      const taskGrowthRate = previousPeriodTasks.length > 0 ? 
        ((tasksInRange.length - previousPeriodTasks.length) / previousPeriodTasks.length) : 0;
        
      // Calculate completion rate change (if comparison is active)
      const previousPeriodCompletedTasks = previousPeriodTasks.filter(task => task.status === 'done').length;
      const previousCompletionRate = previousPeriodTasks.length > 0 ? 
        previousPeriodCompletedTasks / previousPeriodTasks.length : 0;
      const completionRateChange = completionRate - previousCompletionRate;
      
      // Only include previous period data if comparison is enabled
      const responseData: any = {
        agentPerformance,
        taskCompletionTrends,
        taskDistributionByStatus,
        taskDistributionByType,
        taskDistributionByPriority,
        overallStats: {
          totalAgents,
          totalTasks,
          completedTasks: completedTasksCount,
          totalMessages,
          averageTasksPerAgent: parseFloat(averageTasksPerAgent.toFixed(1)),
          messagesPerDay: parseFloat(messagesPerDay.toFixed(1)),
          tasksPerDay: parseFloat(tasksPerDay.toFixed(1)),
          completionRate: parseFloat(completionRate.toFixed(2)),
          averageTaskAge: parseFloat(averageTaskAge.toFixed(1)),
          taskGrowthRate: parseFloat(taskGrowthRate.toFixed(2))
        }
      };
      
      // Include comparison data if requested
      if (showComparison) {
        // Previous period task distributions
        const prevPeriodTodoCount = previousPeriodTasks.filter(task => task.status === 'todo').length;
        const prevPeriodInProgressCount = previousPeriodTasks.filter(task => task.status === 'in-progress').length;
        const prevPeriodDoneCount = previousPeriodTasks.filter(task => task.status === 'done').length;
        
        const prevTaskDistributionByStatus = [
          {
            name: "Completed",
            value: prevPeriodDoneCount,
            color: "#22c55e" // green-500
          },
          {
            name: "In Progress",
            value: prevPeriodInProgressCount,
            color: "#f59e0b" // yellow-500 
          },
          {
            name: "To Do",
            value: prevPeriodTodoCount,
            color: "#6b7280" // gray-500
          }
        ].filter(item => item.value > 0);
        
        // Add previous period data to response
        responseData.previousPeriod = {
          timeLabel: comparisonLabel,
          startDate: previousPeriodStart.toISOString(),
          endDate: previousPeriodEnd.toISOString(),
          taskCount: previousPeriodTasks.length,
          completedTasksCount: previousPeriodCompletedTasks,
          messageCount: previousPeriodMessages.length,
          completionRate: parseFloat(previousCompletionRate.toFixed(2)),
          taskDistributionByStatus: prevTaskDistributionByStatus
        };
        
        responseData.comparisons = {
          taskCountChange: tasksInRange.length - previousPeriodTasks.length,
          taskCountChangePercent: previousPeriodTasks.length > 0 ? 
            parseFloat(((tasksInRange.length - previousPeriodTasks.length) / previousPeriodTasks.length * 100).toFixed(1)) : 0,
          completedTasksChange: completedTasksCount - previousPeriodCompletedTasks,
          completionRateChange: parseFloat(completionRateChange.toFixed(2)),
          messageCountChange: messagesInRange.length - previousPeriodMessages.length
        };
      }
      
      res.json(responseData);
    } catch (error) {
      console.error("Error generating analytics:", error);
      res.status(500).json({ 
        message: "Failed to generate analytics",
        error: error instanceof Error ? error.message : String(error)
      });
    }
  });

  // Integrations API
  app.get("/api/integrations", async (_req, res) => {
    const integrations = await storage.getIntegrations();
    res.json(integrations);
  });

  app.post("/api/integrations/connect", async (req, res) => {
    try {
      const { type } = req.body;
      if (!type) {
        return res.status(400).json({ message: "Integration type is required" });
      }

      const integration = await storage.connectIntegration(type);
      
      // Create a notification for the user when integration is connected
      if (req.user && integration) {
        await storage.createNotification({
          userId: req.user.id,
          title: "Integration Connected",
          content: `${integration.name} integration has been successfully connected`,
          type: "integration-connected",
          href: "/integrations",
          relatedId: integration.id
        });
      }
      
      res.status(201).json(integration);
    } catch (error) {
      res.status(500).json({ message: "Failed to connect integration" });
    }
  });
  
  // Notification API Routes
  // Using user metadata to track notification preferences
  // This approach persists across server restarts, unlike the previous in-memory Set approach
  
  app.get("/api/notifications", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Check if there are any notifications for this user
      const existingNotifications = await storage.getNotifications(req.user.id);
      
      // Only create a welcome notification if this is the very first time
      // the user is visiting the site and has no notifications.
      // We'll add a special filter to avoid adding welcome notifications repeatedly
      const hasWelcomeNotification = existingNotifications.some(n => 
        n.type === "system" && n.title === "Welcome to AgentOS"
      );
      
      const user = await storage.getUser(req.user.id);
      // Safely check metadata which might be undefined or null
      const userMetadata = user?.metadata || {};
      const hasSeenWelcome = userMetadata.hasSeenWelcome === true;
      
      // Only show welcome notification if:
      // 1. User has no existing welcome notification 
      // 2. User has no flag indicating they've seen the welcome before
      if (existingNotifications.length === 0 && !hasWelcomeNotification && !hasSeenWelcome) {
        await storage.createNotification({
          userId: req.user.id,
          title: "Welcome to AgentOS",
          content: "Your notification system is now active. You'll receive updates here as agents complete tasks and integrations are connected.",
          type: "system",
          read: false
        });
        
        // Mark user as having seen welcome notification to prevent it from reappearing
        await storage.updateUser(req.user.id, {
          metadata: { 
            // Preserve existing metadata fields if any
            ...userMetadata,
            hasSeenWelcome: true 
          }
        });
      }
      
      const notifications = await storage.getNotifications(req.user.id);
      res.json(notifications);
    } catch (error) {
      console.error("Error fetching notifications:", error);
      res.status(500).json({ message: "Failed to fetch notifications" });
    }
  });
  
  app.get("/api/notifications/count", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const count = await storage.getUnreadNotificationsCount(req.user.id);
      res.json({ count });
    } catch (error) {
      console.error("Error fetching notification count:", error);
      res.status(500).json({ message: "Failed to fetch notification count" });
    }
  });
  
  app.post("/api/notifications/:id/read", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const notification = await storage.markNotificationAsRead(req.params.id);
      res.json(notification);
    } catch (error) {
      console.error("Error marking notification as read:", error);
      res.status(500).json({ message: "Failed to mark notification as read" });
    }
  });
  
  app.post("/api/notifications/read-all", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      await storage.markAllNotificationsAsRead(req.user.id);
      res.json({ success: true });
    } catch (error) {
      console.error("Error marking all notifications as read:", error);
      res.status(500).json({ message: "Failed to mark all notifications as read" });
    }
  });
  
  app.delete("/api/notifications/:id", async (req, res) => {
    const notificationId = req.params.id;
    console.log(`API request to delete notification: ${notificationId}`);
    
    try {
      // Authentication check
      if (!req.isAuthenticated()) {
        console.log("Authentication failed for delete notification request");
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Check if the notification exists and belongs to the user
      const notifications = await storage.getNotifications(req.user.id);
      const notificationExists = notifications.some(n => n.id === notificationId);
      
      if (!notificationExists) {
        console.log(`Notification ${notificationId} not found for user ${req.user.id}`);
        return res.status(404).json({ 
          success: false, 
          message: "Notification not found or doesn't belong to current user" 
        });
      }
      
      // Delete the notification
      await storage.deleteNotification(notificationId);
      console.log(`Successfully deleted notification: ${notificationId}`);
      
      // Check if this was the user's last notification
      const remainingNotifications = await storage.getNotifications(req.user.id);
      if (remainingNotifications.length === 0) {
        console.log(`User ${req.user.id} cleared all notifications, updating user metadata`);
        
        // Get current user data to preserve existing metadata
        const user = await storage.getUser(req.user.id);
        // Safely get metadata object, creating empty object if undefined
        const userMetadata = user?.metadata || {};
        
        // Update user metadata to track that they've seen and cleared notifications
        await storage.updateUser(req.user.id, {
          metadata: {
            // Preserve existing metadata fields if any
            ...userMetadata,
            hasSeenWelcome: true,
            hasManuallyCleared: true,
            lastClearedAt: new Date().toISOString()
          }
        });
      }
      
      // Return success response
      res.json({ 
        success: true,
        message: "Notification deleted successfully",
        id: notificationId
      });
    } catch (error) {
      console.error(`Error deleting notification ${notificationId}:`, error);
      res.status(500).json({ 
        success: false, 
        message: "Failed to delete notification",
        error: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });
  
  // AI Assistant API Routes
  app.get("/api/ai-assistant/messages", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const messages = await storage.getAiMessages(req.user.id);
      res.json(messages);
    } catch (error) {
      console.error("Error fetching AI assistant messages:", error);
      res.status(500).json({ message: "Failed to fetch AI assistant messages" });
    }
  });
  
  app.post("/api/ai-assistant/messages", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Create user message
      const userMessage = await storage.addAiMessage({
        role: "user",
        content: req.body.content,
        userId: req.user.id
      });
      
      // Generate assistant response
      // Usually this would involve an actual AI service call
      const assistantMessage = await storage.addAiMessage({
        role: "assistant",
        content: "I'm your AI assistant. I can help answer questions about the AgentOS platform and your agents. How can I assist you today?",
        userId: req.user.id
      });
      
      res.json(assistantMessage);
    } catch (error) {
      console.error("Error sending message to AI assistant:", error);
      res.status(500).json({ message: "Failed to send message to AI assistant" });
    }
  });
  
  app.delete("/api/ai-assistant/messages", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      await storage.clearAiMessages(req.user.id);
      res.json({ success: true });
    } catch (error) {
      console.error("Error clearing AI assistant messages:", error);
      res.status(500).json({ message: "Failed to clear AI assistant messages" });
    }
  });

  // CRM API - Contacts
  app.get("/api/crm/contacts", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const contacts = await storage.getCrmContacts(req.user.id);
      res.json(contacts);
    } catch (error) {
      console.error("Error fetching CRM contacts:", error);
      res.status(500).json({ message: "Failed to fetch CRM contacts" });
    }
  });

  app.get("/api/crm/contacts/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const contact = await storage.getCrmContact(req.params.id);
      if (!contact) {
        return res.status(404).json({ message: "Contact not found" });
      }
      
      // Ensure the contact belongs to the authenticated user
      if (contact.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to contact" });
      }
      
      res.json(contact);
    } catch (error) {
      console.error("Error fetching CRM contact:", error);
      res.status(500).json({ message: "Failed to fetch CRM contact" });
    }
  });

  app.post("/api/crm/contacts", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const contactData = insertCrmContactSchema.parse({
        ...req.body,
        userId: req.user.id
      });
      
      const contact = await storage.createCrmContact(contactData);
      res.status(201).json(contact);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid contact data", errors: error.errors });
      }
      console.error("Error creating CRM contact:", error);
      res.status(500).json({ message: "Failed to create CRM contact" });
    }
  });

  app.patch("/api/crm/contacts/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Check if contact exists and belongs to user
      const existingContact = await storage.getCrmContact(req.params.id);
      if (!existingContact) {
        return res.status(404).json({ message: "Contact not found" });
      }
      
      if (existingContact.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to contact" });
      }
      
      const updatedContact = await storage.updateCrmContact(req.params.id, req.body);
      res.json(updatedContact);
    } catch (error) {
      console.error("Error updating CRM contact:", error);
      res.status(500).json({ message: "Failed to update CRM contact" });
    }
  });

  // CRM API - Deals
  app.get("/api/crm/deals", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const deals = await storage.getCrmDeals(req.user.id);
      res.json(deals);
    } catch (error) {
      console.error("Error fetching CRM deals:", error);
      res.status(500).json({ message: "Failed to fetch CRM deals" });
    }
  });

  app.get("/api/crm/deals/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const deal = await storage.getCrmDeal(req.params.id);
      if (!deal) {
        return res.status(404).json({ message: "Deal not found" });
      }
      
      // Ensure the deal belongs to the authenticated user
      if (deal.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to deal" });
      }
      
      res.json(deal);
    } catch (error) {
      console.error("Error fetching CRM deal:", error);
      res.status(500).json({ message: "Failed to fetch CRM deal" });
    }
  });

  app.post("/api/crm/deals", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const dealData = insertCrmDealSchema.parse({
        ...req.body,
        userId: req.user.id
      });
      
      const deal = await storage.createCrmDeal(dealData);
      res.status(201).json(deal);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid deal data", errors: error.errors });
      }
      console.error("Error creating CRM deal:", error);
      res.status(500).json({ message: "Failed to create CRM deal" });
    }
  });

  app.patch("/api/crm/deals/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Check if deal exists and belongs to user
      const existingDeal = await storage.getCrmDeal(req.params.id);
      if (!existingDeal) {
        return res.status(404).json({ message: "Deal not found" });
      }
      
      if (existingDeal.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to deal" });
      }
      
      const updatedDeal = await storage.updateCrmDeal(req.params.id, req.body);
      res.json(updatedDeal);
    } catch (error) {
      console.error("Error updating CRM deal:", error);
      res.status(500).json({ message: "Failed to update CRM deal" });
    }
  });

  // CRM API - Activities
  app.get("/api/crm/activities", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const activities = await storage.getCrmActivities(req.user.id);
      res.json(activities);
    } catch (error) {
      console.error("Error fetching CRM activities:", error);
      res.status(500).json({ message: "Failed to fetch CRM activities" });
    }
  });

  app.get("/api/crm/activities/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const activity = await storage.getCrmActivity(req.params.id);
      if (!activity) {
        return res.status(404).json({ message: "Activity not found" });
      }
      
      // Ensure the activity belongs to the authenticated user
      if (activity.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to activity" });
      }
      
      res.json(activity);
    } catch (error) {
      console.error("Error fetching CRM activity:", error);
      res.status(500).json({ message: "Failed to fetch CRM activity" });
    }
  });

  app.post("/api/crm/activities", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const activityData = insertCrmActivitySchema.parse({
        ...req.body,
        userId: req.user.id
      });
      
      const activity = await storage.createCrmActivity(activityData);
      res.status(201).json(activity);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid activity data", errors: error.errors });
      }
      console.error("Error creating CRM activity:", error);
      res.status(500).json({ message: "Failed to create CRM activity" });
    }
  });

  app.patch("/api/crm/activities/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Check if activity exists and belongs to user
      const existingActivity = await storage.getCrmActivity(req.params.id);
      if (!existingActivity) {
        return res.status(404).json({ message: "Activity not found" });
      }
      
      if (existingActivity.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to activity" });
      }
      
      const updatedActivity = await storage.updateCrmActivity(req.params.id, req.body);
      res.json(updatedActivity);
    } catch (error) {
      console.error("Error updating CRM activity:", error);
      res.status(500).json({ message: "Failed to update CRM activity" });
    }
  });

  // Folders API
  app.get("/api/folders", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const folders = await storage.getFolders(req.user.id);
      res.json(folders);
    } catch (error) {
      console.error("Error fetching folders:", error);
      res.status(500).json({ message: "Failed to fetch folders" });
    }
  });

  app.get("/api/folders/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const folder = await storage.getFolder(req.params.id);
      if (!folder) {
        return res.status(404).json({ message: "Folder not found" });
      }
      
      // Ensure the folder belongs to the authenticated user
      if (folder.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to folder" });
      }
      
      res.json(folder);
    } catch (error) {
      console.error("Error fetching folder:", error);
      res.status(500).json({ message: "Failed to fetch folder" });
    }
  });

  app.post("/api/folders", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Validate folder data
      const folderData = insertFolderSchema.parse({
        ...req.body,
        userId: req.user.id
      });
      
      const folder = await storage.createFolder(folderData);
      res.status(201).json(folder);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid folder data", errors: error.errors });
      }
      console.error("Error creating folder:", error);
      res.status(500).json({ message: "Failed to create folder" });
    }
  });

  app.patch("/api/folders/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const folder = await storage.getFolder(req.params.id);
      if (!folder) {
        return res.status(404).json({ message: "Folder not found" });
      }
      
      // Ensure the folder belongs to the authenticated user
      if (folder.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to folder" });
      }
      
      const updatedFolder = await storage.updateFolder(req.params.id, req.body);
      res.json(updatedFolder);
    } catch (error) {
      console.error("Error updating folder:", error);
      res.status(500).json({ message: "Failed to update folder" });
    }
  });

  app.delete("/api/folders/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const folder = await storage.getFolder(req.params.id);
      if (!folder) {
        return res.status(404).json({ message: "Folder not found" });
      }
      
      // Ensure the folder belongs to the authenticated user
      if (folder.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to folder" });
      }
      
      await storage.deleteFolder(req.params.id);
      res.status(204).end();
    } catch (error) {
      console.error("Error deleting folder:", error);
      res.status(500).json({ message: "Failed to delete folder" });
    }
  });

  // Documents API
  app.get("/api/documents", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const { folderId } = req.query;
      const documents = await storage.getDocuments(req.user.id, folderId as string);
      res.json(documents);
    } catch (error) {
      console.error("Error fetching documents:", error);
      res.status(500).json({ message: "Failed to fetch documents" });
    }
  });

  app.get("/api/documents/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const document = await storage.getDocument(req.params.id);
      if (!document) {
        return res.status(404).json({ message: "Document not found" });
      }
      
      // Ensure the document belongs to the authenticated user
      if (document.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to document" });
      }
      
      res.json(document);
    } catch (error) {
      console.error("Error fetching document:", error);
      res.status(500).json({ message: "Failed to fetch document" });
    }
  });

  app.post("/api/documents", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      // Validate document data
      const documentData = insertDocumentSchema.parse({
        ...req.body,
        userId: req.user.id
      });
      
      const document = await storage.createDocument(documentData);
      res.status(201).json(document);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid document data", errors: error.errors });
      }
      console.error("Error creating document:", error);
      res.status(500).json({ message: "Failed to create document" });
    }
  });

  app.patch("/api/documents/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const document = await storage.getDocument(req.params.id);
      if (!document) {
        return res.status(404).json({ message: "Document not found" });
      }
      
      // Ensure the document belongs to the authenticated user
      if (document.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to document" });
      }
      
      const updatedDocument = await storage.updateDocument(req.params.id, req.body);
      res.json(updatedDocument);
    } catch (error) {
      console.error("Error updating document:", error);
      res.status(500).json({ message: "Failed to update document" });
    }
  });

  app.delete("/api/documents/:id", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Not authenticated" });
      }
      
      const document = await storage.getDocument(req.params.id);
      if (!document) {
        return res.status(404).json({ message: "Document not found" });
      }
      
      // Ensure the document belongs to the authenticated user
      if (document.userId !== req.user.id) {
        return res.status(403).json({ message: "Unauthorized access to document" });
      }
      
      await storage.deleteDocument(req.params.id);
      res.status(204).end();
    } catch (error) {
      console.error("Error deleting document:", error);
      res.status(500).json({ message: "Failed to delete document" });
    }
  });

  app.post("/api/llm/chat", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).json({ message: "Unauthorized" });
      }
      
      const { prompt, model, systemMessage } = req.body;
      
      if (!prompt) {
        return res.status(400).json({ message: "Prompt is required" });
      }
      
      const modelToUse = model && ["claude-haiku-4-5", "claude-sonnet-4-5"].includes(model) 
        ? model 
        : "claude-haiku-4-5";
        
      const response = await anthropic.messages.create({
        model: modelToUse,
        max_tokens: 8192,
        system: systemMessage || "You are an autonomous business agent designed to help build and manage businesses.",
        messages: [
          {
            role: "user",
            content: prompt
          }
        ],
        temperature: 0.2,
      });
      
      const firstBlock = response.content[0];
      const content = firstBlock.type === "text" ? firstBlock.text : "";
      
      if (req.user.id) {
        try {
          await storage.addAiMessage({
            userId: req.user.id,
            role: "user",
            content: prompt,
            timestamp: new Date().toISOString(),
          });
          
          await storage.addAiMessage({
            userId: req.user.id,
            role: "assistant",
            content: content || "",
            timestamp: new Date().toISOString(),
            metadata: { model: modelToUse }
          });
        } catch (logError) {
          console.warn("Failed to log AI conversation:", logError);
        }
      }
      
      res.json({ response: content });
    } catch (error) {
      console.error("Error calling LLM API:", error);
      
      let statusCode = 500;
      let errorMessage = "Failed to call LLM API";
      let errorCode = 'unknown_error';
      
      const errorObj = error as any;
      
      if (errorObj && typeof errorObj === 'object') {
        if (errorObj.status === 429 || 
            (errorObj.message && typeof errorObj.message === 'string' && errorObj.message.includes('rate limit'))) {
          statusCode = 429;
          errorMessage = "Rate limit exceeded. Please try again later.";
          errorCode = 'rate_limit_exceeded';
        } 
        else if (errorObj.status === 401 || 
                (errorObj.message && typeof errorObj.message === 'string' && errorObj.message.includes('API key'))) {
          statusCode = 401;
          errorMessage = "AI service configuration issue. Please contact support.";
          errorCode = 'configuration_error';
        }
      }
      
      res.status(statusCode).json({ 
        message: errorMessage,
        error: errorObj instanceof Error ? errorObj.message : String(errorObj),
        code: errorCode
      });
    }
  });

  // ==================== ACTION ROUTES ====================

  app.get("/api/actions", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const { status, agentId } = req.query;
      const actions = await storage.getActions(userId, {
        status: status as string | undefined,
        agentId: agentId as string | undefined,
      });
      res.json(actions);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/actions/pending", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const actions = await storage.getPendingActions(userId);
      res.json(actions);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/actions/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const action = await storage.getAction(req.params.id);
      if (!action) return res.status(404).json({ message: "Action not found" });
      res.json(action);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/actions/:id/approve", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const action = await storage.getAction(req.params.id);
      if (!action) return res.status(404).json({ message: "Action not found" });
      if (action.userId !== userId) return res.status(403).json({ message: "Not authorized" });

      await storage.updateAction(action.id, {
        status: "approved",
        approvedBy: userId,
        approvedAt: new Date(),
      });

      const result = await executeAction({ ...action, status: "approved" });
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/actions/:id/reject", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const action = await storage.getAction(req.params.id);
      if (!action) return res.status(404).json({ message: "Action not found" });
      if (action.userId !== userId) return res.status(403).json({ message: "Not authorized" });

      const updated = await storage.updateAction(action.id, {
        status: "rejected",
      });
      res.json(updated);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // ==================== GMAIL ROUTES ====================

  app.get("/api/integrations/gmail/auth", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      if (!gmail.isConfigured()) {
        return res.status(400).json({ message: "Gmail OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET." });
      }
      const authUrl = gmail.getAuthUrl();
      res.json({ authUrl });
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/auth/google/callback", async (req, res) => {
    if (!req.isAuthenticated()) return res.redirect("/integrations?error=not_authenticated");
    try {
      const code = req.query.code as string;
      if (!code) return res.redirect("/integrations?error=no_code");

      const userId = (req.user as any).id;
      const tokens = await gmail.exchangeCode(code);

      await storage.upsertOauthToken({
        userId,
        provider: "gmail",
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        expiresAt: tokens.expiresAt,
        scope: tokens.scope,
      });

      res.redirect("/integrations?gmail=connected");
    } catch (error: any) {
      console.error("Gmail OAuth callback error:", error);
      res.redirect(`/integrations?error=${encodeURIComponent(error.message)}`);
    }
  });

  app.get("/api/integrations/gmail/status", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const connected = await gmail.isConnected(userId);
      const configured = gmail.isConfigured();
      res.json({ connected, configured });
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/integrations/gmail/disconnect", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      await storage.deleteOauthToken(userId, "gmail");
      res.json({ success: true });
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // ==================== AGENT METRICS ROUTES ====================

  app.get("/api/agents/:id/metrics", async (req, res) => {
    if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });
    try {
      const userId = (req.user as any).id;
      const metrics = await storage.getAgentMetrics(req.params.id, userId);
      res.json(metrics);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
