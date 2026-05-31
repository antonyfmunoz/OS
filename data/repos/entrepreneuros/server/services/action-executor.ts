import { storage } from "../storage";
import * as gmail from "../integrations/gmail";
import type { AgentAction } from "@shared/schema";

export async function executeAction(action: AgentAction): Promise<{
  success: boolean;
  result?: any;
  error?: string;
}> {
  try {
    await storage.updateAction(action.id, {
      status: "executing",
      executedAt: new Date(),
    });

    let result: any;

    switch (action.actionType) {
      case "send_email":
        result = await executeSendEmail(action);
        break;
      case "create_task":
        result = await executeCreateTask(action);
        break;
      case "create_document":
        result = await executeCreateDocument(action);
        break;
      default:
        throw new Error(`Unknown action type: ${action.actionType}`);
    }

    await storage.updateAction(action.id, {
      status: "completed",
      completedAt: new Date(),
      executionResult: result,
    });

    await storage.incrementMetric(action.agentId, action.userId, "actionsExecuted");
    if (action.estimatedTimeSaved) {
      await storage.incrementMetric(action.agentId, action.userId, "estimatedTimeSavedMinutes", action.estimatedTimeSaved);
    }

    return { success: true, result };
  } catch (error: any) {
    const retryCount = (action.retryCount || 0) + 1;
    const maxRetries = action.maxRetries || 3;

    await storage.updateAction(action.id, {
      status: retryCount < maxRetries ? "pending" : "failed",
      failedAt: new Date(),
      errorMessage: error.message,
      retryCount,
    });

    return { success: false, error: error.message };
  }
}

async function executeSendEmail(action: AgentAction): Promise<any> {
  const params = action.parameters as any;
  if (!params.to || !params.subject || !params.body) {
    throw new Error("Email requires 'to', 'subject', and 'body' parameters");
  }

  const connected = await gmail.isConnected(action.userId);
  if (!connected) {
    throw new Error("Gmail not connected. Please connect Gmail in the integrations page.");
  }

  const result = await gmail.sendEmail(action.userId, {
    to: params.to,
    subject: params.subject,
    body: params.body,
    cc: params.cc,
    bcc: params.bcc,
  });

  return { messageId: result.messageId, sentTo: params.to };
}

async function executeCreateTask(action: AgentAction): Promise<any> {
  const params = action.parameters as any;
  const task = await storage.createTask({
    title: params.title || "Untitled Task",
    description: params.description || "",
    status: params.status || "todo",
    priority: params.priority || "medium",
    agentId: action.agentId,
    dueDate: params.dueDate,
  });

  return { taskId: task.id, title: task.title };
}

async function executeCreateDocument(action: AgentAction): Promise<any> {
  const params = action.parameters as any;
  const doc = await storage.createDocument({
    title: params.title || "Untitled Document",
    content: params.content || "",
    userId: action.userId,
    folderId: params.folderId,
    tags: params.tags,
  });

  return { documentId: doc.id, title: doc.title };
}
