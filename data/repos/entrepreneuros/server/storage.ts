import { 
  agents as agentsTable, 
  tasks as tasksTable, 
  messages as messagesTable,
  integrations as integrationsTable,
  users as usersTable,
  notifications as notificationsTable,
  aiMessages,
  crmContacts as crmContactsTable,
  crmDeals as crmDealsTable,
  crmActivities as crmActivitiesTable,
  documents as documentsTable,
  folders as foldersTable,
  agentActions as agentActionsTable,
  oauthTokens as oauthTokensTable,
  agentMetrics as agentMetricsTable,
  type Agent, 
  type Task, 
  type InsertAgent, 
  type InsertTask, 
  type UpdateTask,
  type Message,
  type InsertMessage,
  type Integration,
  type InsertIntegration,
  type User,
  type InsertUser,
  type Notification,
  type InsertNotification,
  type AiMessage,
  type InsertAiMessage,
  type CrmContact,
  type InsertCrmContact,
  type CrmDeal,
  type InsertCrmDeal,
  type CrmActivity,
  type InsertCrmActivity,
  type Document,
  type InsertDocument,
  type Folder,
  type InsertFolder,
  type AgentAction,
  type InsertAgentAction,
  type OauthToken,
  type InsertOauthToken,
  type AgentMetric,
  type InsertAgentMetric,
} from "@shared/schema";
import { db, client } from './db';
import { eq, and, desc, asc, sql } from 'drizzle-orm';
import session from 'express-session';
import connectPg from 'connect-pg-simple';

export interface IStorage {
  // User operations
  getUsers(): Promise<User[]>;
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  getUserByFirebaseUid(firebaseUid: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  updateUser(id: string, updates: Partial<InsertUser>): Promise<User>;
  
  // Agent operations
  getAgents(): Promise<Agent[]>;
  getAgent(id: string): Promise<Agent | undefined>;
  createAgent(agent: InsertAgent): Promise<Agent>;
  updateAgent(id: string, updates: Partial<InsertAgent>): Promise<Agent | undefined>;
  updateAgentActivity(id: string, activity: string): Promise<Agent | undefined>;

  // Task operations
  getTasks(): Promise<Task[]>;
  getTask(id: string): Promise<Task | undefined>;
  createTask(task: InsertTask): Promise<Task>;
  updateTask(id: string, updates: UpdateTask): Promise<Task>;
  deleteTask(id: string): Promise<void>; // Delete a task and its subtasks
  getAgentTasks(agentId: string): Promise<Task[]>;
  getCollaborativeTasks(agentId: string): Promise<Task[]>; // Tasks where agent is a collaborator
  getTasksByType(taskType: string): Promise<Task[]>; // Get tasks by type (standard, collaboration, etc.)
  getSubtasks(parentTaskId: string): Promise<Task[]>; // Get all subtasks for a parent task

  // Message operations
  getAgentMessages(agentId: string): Promise<Message[]>;
  getTaskMessages(taskId: string): Promise<Message[]>; // Get all messages for a specific task
  getConversationMessages(conversationId: string): Promise<Message[]>; // Get all messages for a conversation
  getAllMessages(): Promise<Message[]>; // Get all messages in the system
  clearAgentMessages(agentId: string): Promise<void>; // Clear all messages for an agent (New Chat functionality)
  addAgentMessage(message: InsertMessage): Promise<Message>;
  addCollaborativeMessage(message: InsertMessage): Promise<Message>; // Special handling for collaborative messages

  // Agent collaboration operations
  addAgentCollaborator(taskId: string, agentId: string): Promise<Task>; // Add an agent as collaborator to a task
  assignTaskToAgent(taskId: string, agentId: string, assignedById: string): Promise<Task>; // Assign task to a different agent
  createSubtask(parentTaskId: string, subtask: InsertTask): Promise<Task>; // Create a subtask linked to parent

  // Integration operations
  getIntegrations(): Promise<Integration[]>;
  connectIntegration(type: string): Promise<Integration>;
  
  // Notification operations
  getNotifications(userId: string): Promise<Notification[]>;
  getUnreadNotificationsCount(userId: string): Promise<number>;
  createNotification(notification: InsertNotification): Promise<Notification>;
  markNotificationAsRead(id: string): Promise<Notification | undefined>;
  markAllNotificationsAsRead(userId: string): Promise<void>;
  deleteNotification(id: string): Promise<void>;
  
  // AI Assistant operations
  getAiMessages(userId: string): Promise<AiMessage[]>;
  addAiMessage(message: InsertAiMessage): Promise<AiMessage>;
  clearAiMessages(userId: string): Promise<void>;
  
  // CRM operations
  getCrmContacts(userId: string): Promise<CrmContact[]>;
  getCrmContact(id: string): Promise<CrmContact | undefined>;
  createCrmContact(contact: InsertCrmContact): Promise<CrmContact>;
  updateCrmContact(id: string, updates: Partial<InsertCrmContact>): Promise<CrmContact | undefined>;
  
  getCrmDeals(userId: string): Promise<CrmDeal[]>;
  getCrmDeal(id: string): Promise<CrmDeal | undefined>;
  createCrmDeal(deal: InsertCrmDeal): Promise<CrmDeal>;
  updateCrmDeal(id: string, updates: Partial<InsertCrmDeal>): Promise<CrmDeal | undefined>;
  
  getCrmActivities(userId: string): Promise<CrmActivity[]>;
  getCrmActivity(id: string): Promise<CrmActivity | undefined>;
  createCrmActivity(activity: InsertCrmActivity): Promise<CrmActivity>;
  updateCrmActivity(id: string, updates: Partial<InsertCrmActivity>): Promise<CrmActivity | undefined>;
  
  // Folder operations
  getFolders(userId: string): Promise<Folder[]>;
  getFolder(id: string): Promise<Folder | undefined>;
  createFolder(folder: InsertFolder): Promise<Folder>;
  updateFolder(id: string, updates: Partial<InsertFolder>): Promise<Folder | undefined>;
  deleteFolder(id: string): Promise<void>;
  
  // Document operations
  getDocuments(userId: string, folderId?: string): Promise<Document[]>;
  getDocument(id: string): Promise<Document | undefined>;
  createDocument(document: InsertDocument): Promise<Document>;
  updateDocument(id: string, updates: Partial<InsertDocument>): Promise<Document | undefined>;
  deleteDocument(id: string): Promise<void>;
  
  // Agent Action operations
  getActions(userId: string, filters?: { status?: string; agentId?: string }): Promise<AgentAction[]>;
  getAction(id: string): Promise<AgentAction | undefined>;
  getPendingActions(userId: string): Promise<AgentAction[]>;
  createAction(action: InsertAgentAction): Promise<AgentAction>;
  updateAction(id: string, updates: Partial<AgentAction>): Promise<AgentAction | undefined>;

  // OAuth Token operations
  getOauthToken(userId: string, provider: string): Promise<OauthToken | undefined>;
  upsertOauthToken(token: InsertOauthToken): Promise<OauthToken>;
  deleteOauthToken(userId: string, provider: string): Promise<void>;

  // Agent Metrics operations
  getAgentMetrics(agentId: string, userId: string): Promise<AgentMetric[]>;
  upsertAgentMetric(metric: InsertAgentMetric): Promise<AgentMetric>;
  incrementMetric(agentId: string, userId: string, field: string, amount?: number): Promise<void>;

  // Session store
  sessionStore: session.Store;
}

export class DatabaseStorage implements IStorage {
  // Define the session store property
  sessionStore: session.Store;
  
  constructor() {
    // Create PostgreSQL session store
    const PostgresSessionStore = connectPg(session);
    
    // Initialize the session store with the PostgreSQL connection string
    this.sessionStore = new PostgresSessionStore({
      conObject: {
        connectionString: process.env.DATABASE_URL
      },
      createTableIfMissing: true,
      // Table configuration (optional)
      tableName: 'session',
      schemaName: 'public'
    });
    
    // Initialize with sample data if needed
    this.initSampleData().catch(err => {
      console.error("Error initializing sample data:", err);
    });
  }
  
  // User operations
  async getUsers(): Promise<User[]> {
    return await db.select().from(usersTable);
  }

  async getUser(id: string): Promise<User | undefined> {
    const users = await db.select().from(usersTable).where(eq(usersTable.id, id));
    return users.length > 0 ? users[0] : undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const users = await db.select().from(usersTable).where(eq(usersTable.username, username));
    return users.length > 0 ? users[0] : undefined;
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    const users = await db.select().from(usersTable).where(eq(usersTable.email, email));
    return users.length > 0 ? users[0] : undefined;
  }

  async getUserByFirebaseUid(firebaseUid: string): Promise<User | undefined> {
    if (!firebaseUid) return undefined;
    
    const users = await db.select().from(usersTable).where(eq(usersTable.firebaseUid, firebaseUid));
    return users.length > 0 ? users[0] : undefined;
  }

  async createUser(user: InsertUser): Promise<User> {
    // Generate a unique ID
    const id = `user_${Date.now()}`;
    const now = new Date();
    
    // Convert preferences to string if present
    const preferences = user.preferences ? JSON.stringify(user.preferences) : null;
    
    // Create user with specific field mappings
    const [newUser] = await db.insert(usersTable)
      .values({
        id,
        username: user.username,
        password: user.password,
        email: user.email,
        fullName: user.fullName || null,
        avatar: user.avatar || null,
        company: user.company || null,
        role: user.role || "user",
        firebaseUid: user.firebaseUid || null,
        preferences: preferences,
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newUser;
  }

  async updateUser(id: string, updates: Partial<InsertUser>): Promise<User> {
    // Handle preferences conversion for update
    const updateData: Record<string, any> = { ...updates, updatedAt: new Date() };
    
    // Convert preferences to string if present
    if (updates.preferences) {
      updateData.preferences = JSON.stringify(updates.preferences);
    }
    
    const [updatedUser] = await db.update(usersTable)
      .set(updateData)
      .where(eq(usersTable.id, id))
      .returning();
    
    if (!updatedUser) {
      throw new Error(`User with id ${id} not found`);
    }
    
    return updatedUser;
  }

  private async initSampleData(): Promise<void> {
    // Check if there are any users in the database
    const existingUsers = await this.getUsers();
    
    // Create a demo user if no users exist
    if (existingUsers.length === 0) {
      try {
        const { hashPassword } = await import('./auth');
        const password = await hashPassword("password");

        await this.createUser({
          username: "demo",
          password,
          email: "demo@example.com",
          fullName: "Demo User",
          role: "admin"
        });

        console.log("Created demo user: username 'demo', password 'password'");
      } catch (error) {
        console.error("Error creating demo user:", error);
      }
    }
    
    // Check if there are any agents first
    const existingAgents = await this.getAgents();
    
    // If we already have agents, only continue if there's no executive agent
    const hasExecutiveAgent = existingAgents.some(agent => agent.role === 'executive');
    
    if (existingAgents.length > 0 && hasExecutiveAgent) {
      // Executive agent exists, no need to initialize
      return;
    }
    
    // Remove any existing agents if we're reinitializing
    if (existingAgents.length > 0) {
      // Delete all existing agents and their associated data
      for (const agent of existingAgents) {
        // Delete tasks associated with this agent
        await db.delete(tasksTable)
          .where(eq(tasksTable.agentId, agent.id));
          
        // Delete messages associated with this agent  
        await db.delete(messagesTable)
          .where(eq(messagesTable.agentId, agent.id));
      }
      
      // Now delete all the agents
      await db.delete(agentsTable);
    }

    try {
      // Use a single timestamp for all items
      const timestamp = new Date();
      
      // Create only the Executive Agent - which will manage all other agents
      const executiveAgent = await db.insert(agentsTable)
        .values({
          id: "agent_executive",
          name: "Executive Agent",
          role: "executive",
          roleLevel: "chief",
          department: "Management",
          icon: "ri-user-star-line",
          instructions: "Lead and manage the team of AI agents, create and assign specialized agents for different business functions, coordinate agent collaboration, and ensure alignment with business goals and strategy.",
          latestActivity: "Created agent",
          brainContent: "",
          createdAt: timestamp,
          updatedAt: timestamp
        })
        .returning()
        .then(rows => rows[0]);

      // Sample tasks for the Executive Agent
      await db.insert(tasksTable)
        .values([
          {
            id: "task_1",
            title: "Create a Business Plan",
            description: "Develop a comprehensive business plan for the executive AI that outlines the strategy, goals, and execution plan for all users.",
            status: "todo",
            dueDate: this.getFutureDate(1),
            agentId: executiveAgent.id,
            priority: "high",
            taskType: "standard",
            createdAt: timestamp,
            updatedAt: timestamp
          },
          {
            id: "task_2",
            title: "Create Marketing Agent",
            description: "Configure and deploy a specialized marketing agent to handle content strategy and social media management.",
            status: "todo",
            dueDate: this.getFutureDate(3),
            agentId: executiveAgent.id,
            priority: "high",
            taskType: "standard",
            createdAt: timestamp,
            updatedAt: timestamp
          },
          {
            id: "task_3",
            title: "Create Content Agent",
            description: "Configure and deploy a specialized content agent to handle blog posts, website copy, and product descriptions.",
            status: "todo", 
            dueDate: this.getFutureDate(4),
            agentId: executiveAgent.id,
            priority: "medium",
            taskType: "standard",
            createdAt: timestamp,
            updatedAt: timestamp
          },
          {
            id: "task_4",
            title: "Develop Business Strategy",
            description: "Analyze market trends and develop a comprehensive business strategy for Q2.",
            status: "in-progress",
            dueDate: this.getTodayDate(),
            agentId: executiveAgent.id,
            priority: "medium",
            taskType: "standard",
            createdAt: timestamp,
            updatedAt: timestamp
          },
          {
            id: "task_5",
            title: "Configure Agent Collaboration",
            description: "Set up collaboration protocols between specialized agents to ensure coordinated actions.",
            status: "in-progress",
            dueDate: this.getFutureDate(5),
            agentId: executiveAgent.id,
            priority: "low",
            taskType: "standard",
            createdAt: timestamp,
            updatedAt: timestamp
          }
        ]);

      // Update latest activity for Executive Agent
      await db.update(agentsTable)
        .set({ 
          latestActivity: "Established business goals and agent delegation strategy",
          updatedAt: timestamp
        })
        .where(eq(agentsTable.id, executiveAgent.id));

      // Sample integrations
      await db.insert(integrationsTable)
        .values([
          {
            id: "integration_1",
            name: "Notion",
            type: "notion",
            status: "connected",
            details: "3 workspaces",
            icon: "ri-notion-line",
          },
          {
            id: "integration_2",
            name: "Gmail",
            type: "gmail",
            status: "connected",
            details: "example@gmail.com",
            icon: "ri-mail-line",
          },
          {
            id: "integration_3",
            name: "Google Sheets",
            type: "google-sheets",
            status: "connected",
            details: "2 sheets",
            icon: "ri-file-list-3-line",
          }
        ]);
    } catch (error) {
      console.error("Error initializing sample data:", error);
    }
  }

  private getTodayDate(): string {
    return new Date().toISOString().split('T')[0];
  }

  private getFutureDate(days: number): string {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return date.toISOString().split('T')[0];
  }

  private getPastDate(days: number): string {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date.toISOString().split('T')[0];
  }

  // Agent operations
  async getAgents(): Promise<Agent[]> {
    return await db.select().from(agentsTable);
  }

  async getAgent(id: string): Promise<Agent | undefined> {
    const agents = await db.select().from(agentsTable).where(eq(agentsTable.id, id));
    return agents.length > 0 ? agents[0] : undefined;
  }

  async createAgent(agent: InsertAgent): Promise<Agent> {
    // Generate a unique ID
    const id = `agent_${Date.now()}`;
    const now = new Date();
    
    // Create agent with specific field mappings
    const [newAgent] = await db.insert(agentsTable)
      .values({
        id,
        name: agent.name,
        role: agent.role,
        icon: agent.icon || "ri-robot-line",
        instructions: agent.instructions || null,
        latestActivity: "Created agent",
        brainContent: "",
        createdAt: now
      })
      .returning();
    
    return newAgent;
  }

  async updateAgent(id: string, updates: Partial<InsertAgent> & { latestActivity?: string }): Promise<Agent | undefined> {
    try {
      // Get the current agent to make sure it exists
      const existingAgent = await this.getAgent(id);
      if (!existingAgent) {
        return undefined;
      }
      
      // Create update object with only the valid fields for the agents table
      const updateData: Record<string, any> = {};
      
      // Map scalar fields directly
      if (updates.name) updateData.name = updates.name;
      if (updates.role) updateData.role = updates.role;
      if (updates.icon) updateData.icon = updates.icon;
      if (updates.instructions) updateData.instructions = updates.instructions;
      
      // Handle latestActivity which is in the table schema but not in InsertAgent type
      if ('latestActivity' in updates) {
        updateData.latestActivity = updates.latestActivity;
      }
      
      // Note: We're not updating the updatedAt field until we migrate the database
      
      // Update the agent in the database
      const [agent] = await db.update(agentsTable)
        .set(updateData)
        .where(eq(agentsTable.id, id))
        .returning();
      
      return agent;
    } catch (error) {
      console.error("Error updating agent:", error);
      return undefined;
    }
  }

  async updateAgentActivity(id: string, activity: string): Promise<Agent | undefined> {
    const [agent] = await db.update(agentsTable)
      .set({ latestActivity: activity })
      .where(eq(agentsTable.id, id))
      .returning();
    return agent;
  }

  // Task operations
  async getTasks(): Promise<Task[]> {
    const allTasks = await db.select().from(tasksTable);
    
    // Create a map of tasks by ID for quick access
    const taskMap: Record<string, Task & { subtasks?: Task[] }> = {};
    allTasks.forEach(task => {
      taskMap[task.id] = { ...task, subtasks: [] };
    });
    
    // Assign subtasks to their parent tasks
    allTasks.forEach(task => {
      if (task.parentTaskId && taskMap[task.parentTaskId]) {
        taskMap[task.parentTaskId].subtasks!.push(task);
      }
    });
    
    // Return only top-level tasks (those without parent tasks)
    // and include their subtasks recursively
    return allTasks.filter(task => !task.parentTaskId).map(task => taskMap[task.id]);
  }
  
  async deleteTask(id: string): Promise<void> {
    // First, recursively delete all subtasks
    const subtasks = await this.getSubtasks(id);
    for (const subtask of subtasks) {
      // Recursively delete any nested subtasks
      await this.deleteTask(subtask.id);
    }
    
    // Then delete the task itself
    await db.delete(tasksTable).where(eq(tasksTable.id, id));
  }

  async getTask(id: string): Promise<Task | undefined> {
    const tasks = await db.select().from(tasksTable).where(eq(tasksTable.id, id));
    if (tasks.length === 0) {
      return undefined;
    }
    
    // Get the task and its subtasks
    const task = tasks[0];
    const subtasks = await this.getSubtasksRecursive(id);
    
    // Add subtasks to the task
    return {
      ...task,
      subtasks
    };
  }
  
  // Helper method to get subtasks recursively
  private async getSubtasksRecursive(parentTaskId: string): Promise<Task[]> {
    const directSubtasks = await this.getSubtasks(parentTaskId);
    
    // For each subtask, recursively get its subtasks
    const subtasksWithChildren = await Promise.all(
      directSubtasks.map(async (subtask) => {
        const childSubtasks = await this.getSubtasksRecursive(subtask.id);
        return {
          ...subtask,
          subtasks: childSubtasks
        };
      })
    );
    
    return subtasksWithChildren;
  }

  async createTask(task: InsertTask): Promise<Task> {
    // Generate a unique ID
    const id = `task_${Date.now()}`;
    const now = new Date();
    
    // Create task with specific field mappings
    const [newTask] = await db.insert(tasksTable)
      .values({
        id,
        title: task.title,
        description: task.description,
        status: task.status || "todo",
        priority: task.priority || "medium",
        dueDate: task.dueDate || null,
        agentId: task.agentId || null,
        assignedById: task.assignedById || null,
        collaboratorIds: task.collaboratorIds || null,
        taskType: task.taskType || "standard",
        parentTaskId: task.parentTaskId || null,
        metadata: task.metadata || null,
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newTask;
  }

  async updateTask(id: string, updates: UpdateTask): Promise<Task> {
    const [updatedTask] = await db.update(tasksTable)
      .set(updates)
      .where(eq(tasksTable.id, id))
      .returning();
    
    if (!updatedTask) {
      throw new Error(`Task with id ${id} not found`);
    }
    
    return updatedTask;
  }

  async getAgentTasks(agentId: string): Promise<Task[]> {
    return await db.select()
      .from(tasksTable)
      .where(eq(tasksTable.agentId, agentId));
  }

  async getCollaborativeTasks(agentId: string): Promise<Task[]> {
    // Get tasks where agent is in the collaboratorIds list
    const allTasks = await db.select().from(tasksTable);
    return allTasks.filter(task => 
      task.collaboratorIds && task.collaboratorIds.split(',').includes(agentId)
    );
  }

  async getTasksByType(taskType: string): Promise<Task[]> {
    return await db.select()
      .from(tasksTable)
      .where(eq(tasksTable.taskType, taskType));
  }

  async getSubtasks(parentTaskId: string): Promise<Task[]> {
    return await db.select()
      .from(tasksTable)
      .where(eq(tasksTable.parentTaskId, parentTaskId));
  }

  async addAgentCollaborator(taskId: string, agentId: string): Promise<Task> {
    const task = await this.getTask(taskId);
    if (!task) {
      throw new Error(`Task with id ${taskId} not found`);
    }
    
    // Create or update the list of collaboratorIds
    let collaborators: string[] = [];
    if (task.collaboratorIds) {
      collaborators = task.collaboratorIds.split(',');
      // Only add the agent if they're not already a collaborator
      if (!collaborators.includes(agentId)) {
        collaborators.push(agentId);
      }
    } else {
      collaborators = [agentId];
    }
    
    // Update the task with the new collaborators list
    const [updatedTask] = await db.update(tasksTable)
      .set({ 
        collaboratorIds: collaborators.join(','),
        taskType: "collaboration",
        updatedAt: new Date()
      })
      .where(eq(tasksTable.id, taskId))
      .returning();
    
    return updatedTask;
  }

  async assignTaskToAgent(taskId: string, agentId: string, assignedById: string): Promise<Task> {
    const [updatedTask] = await db.update(tasksTable)
      .set({ 
        agentId: agentId,
        assignedById: assignedById,
        taskType: "delegated",
        updatedAt: new Date()
      })
      .where(eq(tasksTable.id, taskId))
      .returning();

    if (!updatedTask) {
      throw new Error(`Task with id ${taskId} not found`);
    }
    
    return updatedTask;
  }

  async createSubtask(parentTaskId: string, subtask: InsertTask): Promise<Task> {
    // Generate a unique ID
    const id = `task_${Date.now()}`;
    const now = new Date();

    // Create the subtask with the parentTaskId reference
    const [newTask] = await db.insert(tasksTable)
      .values({
        id,
        title: subtask.title,
        description: subtask.description,
        status: subtask.status || "todo",
        priority: subtask.priority || "medium",
        dueDate: subtask.dueDate || null,
        agentId: subtask.agentId || null,
        assignedById: subtask.assignedById || null,
        parentTaskId: parentTaskId,
        taskType: "subtask",
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newTask;
  }

  // Message operations
  async getAgentMessages(agentId: string): Promise<Message[]> {
    return await db.select()
      .from(messagesTable)
      .where(eq(messagesTable.agentId, agentId))
      .orderBy(messagesTable.timestamp);
  }

  async getTaskMessages(taskId: string): Promise<Message[]> {
    return await db.select()
      .from(messagesTable)
      .where(eq(messagesTable.taskId, taskId))
      .orderBy(messagesTable.timestamp);
  }

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    return await db.select()
      .from(messagesTable)
      .where(eq(messagesTable.conversationId, conversationId))
      .orderBy(messagesTable.timestamp);
  }
  
  async getAllMessages(): Promise<Message[]> {
    return await db.select().from(messagesTable).orderBy(messagesTable.timestamp);
  }

  async clearAgentMessages(agentId: string): Promise<void> {
    // Delete all messages for the specified agent
    await db.delete(messagesTable)
      .where(eq(messagesTable.agentId, agentId));
  }

  async addAgentMessage(message: InsertMessage): Promise<Message> {
    // Generate a unique ID
    const id = `msg_${Date.now()}`;
    const now = new Date();
    
    // Create message with specific field mappings
    const [newMessage] = await db.insert(messagesTable)
      .values({
        id,
        role: message.role,
        content: message.content,
        agentId: message.agentId,
        taskId: message.taskId || null,
        conversationId: message.conversationId || null,
        metadata: message.metadata || null,
        referencedAgentIds: message.referencedAgentIds || null,
        timestamp: message.timestamp ? new Date(message.timestamp) : now
      })
      .returning();
    
    return newMessage;
  }

  async addCollaborativeMessage(message: InsertMessage): Promise<Message> {
    // Generate a unique ID
    const id = `msg_${Date.now()}`;
    const now = new Date();
    
    // If this is a collaborative message and no conversationId is provided,
    // generate one to group related messages together
    const conversationId = message.conversationId || `conv_${Date.now()}`;
    
    // Create collaborative message
    const [newMessage] = await db.insert(messagesTable)
      .values({
        id,
        role: message.role,
        content: message.content,
        agentId: message.agentId,
        taskId: message.taskId,
        conversationId: conversationId,
        metadata: message.metadata || null,
        referencedAgentIds: message.referencedAgentIds,
        timestamp: message.timestamp ? new Date(message.timestamp) : now
      })
      .returning();
    
    return newMessage;
  }

  // Integration operations
  async getIntegrations(): Promise<Integration[]> {
    return await db.select().from(integrationsTable);
  }

  async connectIntegration(type: string): Promise<Integration> {
    // In a real app, this would connect to the actual integration
    // For now, we'll just create a placeholder integration
    let name, details, icon, status;
    
    switch (type) {
      case "notion":
        name = "Notion";
        details = "Connected workspace";
        icon = "ri-notion-line";
        status = "connected";
        break;
      case "gmail":
        name = "Gmail";
        details = "Connected account";
        icon = "ri-mail-line";
        status = "connected";
        break;
      case "google-sheets":
        name = "Google Sheets";
        details = "Connected sheet";
        icon = "ri-file-list-3-line";
        status = "connected";
        break;
      case "zapier":
        name = "Zapier";
        details = "Connected account";
        icon = "ri-flashlight-line";
        status = "connected";
        break;
      default:
        name = "New Integration";
        details = "Connected service";
        icon = "ri-link";
        status = "connected";
    }
    
    // Generate a unique ID
    const id = `integration_${Date.now()}`;
    
    const [newIntegration] = await db.insert(integrationsTable)
      .values({
        id,
        name,
        type: type || "other",
        status,
        details,
        icon,
      })
      .returning();
    
    return newIntegration;
  }

  private async createIntegration(integration: InsertIntegration): Promise<Integration> {
    // Generate a unique ID
    const id = `integration_${Date.now()}`;
    
    const [newIntegration] = await db.insert(integrationsTable)
      .values({
        id,
        name: integration.name,
        type: integration.type,
        status: integration.status,
        details: integration.details || null,
        icon: integration.icon || null
      })
      .returning();
    
    return newIntegration;
  }

  // Notification operations
  async getNotifications(userId: string): Promise<Notification[]> {
    return await db.select()
      .from(notificationsTable)
      .where(eq(notificationsTable.userId, userId))
      .orderBy(desc(notificationsTable.createdAt));
  }

  async getUnreadNotificationsCount(userId: string): Promise<number> {
    const notifications = await db.select({ read: notificationsTable.read })
      .from(notificationsTable)
      .where(and(
        eq(notificationsTable.userId, userId),
        eq(notificationsTable.read, false)
      ));
    return notifications.length;
  }

  async createNotification(notification: InsertNotification): Promise<Notification> {
    const id = `notification_${Date.now()}`;
    
    const [newNotification] = await db.insert(notificationsTable)
      .values({
        id,
        userId: notification.userId,
        title: notification.title,
        content: notification.content,
        type: notification.type,
        read: notification.read || false,
        href: notification.href || null,
        relatedId: notification.relatedId || null,
        metadata: notification.metadata || null,
        createdAt: new Date()
      })
      .returning();
    
    return newNotification;
  }

  async markNotificationAsRead(id: string): Promise<Notification | undefined> {
    const [notification] = await db.update(notificationsTable)
      .set({ read: true })
      .where(eq(notificationsTable.id, id))
      .returning();
    
    return notification;
  }

  async markAllNotificationsAsRead(userId: string): Promise<void> {
    await db.update(notificationsTable)
      .set({ read: true })
      .where(eq(notificationsTable.userId, userId));
  }

  async deleteNotification(id: string): Promise<void> {
    console.log(`Server deleting notification with ID: ${id}`);
    try {
      // First check if the notification exists
      const existingNotification = await db.select()
        .from(notificationsTable)
        .where(eq(notificationsTable.id, id))
        .limit(1);
        
      if (existingNotification.length === 0) {
        console.log(`Notification with ID ${id} not found, nothing to delete`);
        return;
      }
      
      // Delete the notification
      await db.delete(notificationsTable)
        .where(eq(notificationsTable.id, id));
        
      console.log(`Successfully deleted notification with ID: ${id}`);
    } catch (error) {
      console.error(`Error deleting notification ${id}:`, error);
      throw error;
    }
  }

  // AI Assistant operations
  async getAiMessages(userId: string): Promise<AiMessage[]> {
    return await db.select().from(aiMessages)
      .where(eq(aiMessages.userId, userId))
      .orderBy(asc(aiMessages.timestamp));
  }

  async addAiMessage(message: InsertAiMessage): Promise<AiMessage> {
    const id = message.id || `ai_msg_${Date.now()}`;
    const timestamp = message.timestamp || new Date();
    
    const [newMessage] = await db.insert(aiMessages)
      .values({
        id,
        role: message.role,
        content: message.content,
        userId: message.userId,
        timestamp
      })
      .returning();
    
    return newMessage;
  }

  async clearAiMessages(userId: string): Promise<void> {
    await db.delete(aiMessages)
      .where(eq(aiMessages.userId, userId));
  }
  
  // CRM Contact operations
  async getCrmContacts(userId: string): Promise<CrmContact[]> {
    return await db.select().from(crmContactsTable)
      .where(eq(crmContactsTable.userId, userId))
      .orderBy(desc(crmContactsTable.createdAt));
  }

  async getCrmContact(id: string): Promise<CrmContact | undefined> {
    const contacts = await db.select().from(crmContactsTable).where(eq(crmContactsTable.id, id));
    return contacts.length > 0 ? contacts[0] : undefined;
  }

  async createCrmContact(contact: InsertCrmContact): Promise<CrmContact> {
    const id = `contact_${Date.now()}`;
    const now = new Date();
    
    const [newContact] = await db.insert(crmContactsTable)
      .values({
        id,
        name: contact.name,
        email: contact.email,
        phone: contact.phone || null,
        company: contact.company || null,
        title: contact.title || null,
        status: contact.status || "lead",
        lastContact: contact.lastContact || null,
        notes: contact.notes || null,
        avatar: contact.avatar || null,
        userId: contact.userId,
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newContact;
  }

  async updateCrmContact(id: string, updates: Partial<InsertCrmContact>): Promise<CrmContact | undefined> {
    const updateData: Record<string, any> = { ...updates, updatedAt: new Date() };
    
    const [updatedContact] = await db.update(crmContactsTable)
      .set(updateData)
      .where(eq(crmContactsTable.id, id))
      .returning();
    
    return updatedContact;
  }

  // CRM Deal operations
  async getCrmDeals(userId: string): Promise<CrmDeal[]> {
    return await db.select().from(crmDealsTable)
      .where(eq(crmDealsTable.userId, userId))
      .orderBy(desc(crmDealsTable.createdAt));
  }

  async getCrmDeal(id: string): Promise<CrmDeal | undefined> {
    const deals = await db.select().from(crmDealsTable).where(eq(crmDealsTable.id, id));
    return deals.length > 0 ? deals[0] : undefined;
  }

  async createCrmDeal(deal: InsertCrmDeal): Promise<CrmDeal> {
    const id = `deal_${Date.now()}`;
    const now = new Date();
    
    const [newDeal] = await db.insert(crmDealsTable)
      .values({
        id,
        title: deal.title,
        company: deal.company,
        value: String(deal.value), // Convert number to string for decimal column
        stage: deal.stage || "discovery",
        probability: deal.probability || 50,
        expectedCloseDate: deal.expectedCloseDate || null,
        contactId: deal.contactId,
        assignedAgentId: deal.assignedAgentId || null,
        notes: deal.notes || null,
        userId: deal.userId,
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newDeal;
  }

  async updateCrmDeal(id: string, updates: Partial<InsertCrmDeal>): Promise<CrmDeal | undefined> {
    const updateData: Record<string, any> = { ...updates, updatedAt: new Date() };
    
    // Convert value to string if present in updates
    if (typeof updates.value === 'number') {
      updateData.value = String(updates.value);
    }
    
    const [updatedDeal] = await db.update(crmDealsTable)
      .set(updateData)
      .where(eq(crmDealsTable.id, id))
      .returning();
    
    return updatedDeal;
  }

  // CRM Activity operations
  async getCrmActivities(userId: string): Promise<CrmActivity[]> {
    return await db.select().from(crmActivitiesTable)
      .where(eq(crmActivitiesTable.userId, userId))
      .orderBy(desc(crmActivitiesTable.date));
  }

  async getCrmActivity(id: string): Promise<CrmActivity | undefined> {
    const activities = await db.select().from(crmActivitiesTable).where(eq(crmActivitiesTable.id, id));
    return activities.length > 0 ? activities[0] : undefined;
  }

  async createCrmActivity(activity: InsertCrmActivity): Promise<CrmActivity> {
    const id = `activity_${Date.now()}`;
    const now = new Date();
    
    const [newActivity] = await db.insert(crmActivitiesTable)
      .values({
        id,
        type: activity.type,
        subject: activity.subject,
        date: activity.date,
        relatedToType: activity.relatedToType,
        relatedToId: activity.relatedToId,
        completed: activity.completed || false,
        notes: activity.notes || null,
        createdByAgentId: activity.createdByAgentId || null,
        userId: activity.userId,
        createdAt: now,
        updatedAt: now
      })
      .returning();
    
    return newActivity;
  }

  async updateCrmActivity(id: string, updates: Partial<InsertCrmActivity>): Promise<CrmActivity | undefined> {
    const updateData: Record<string, any> = { ...updates, updatedAt: new Date() };
    
    const [updatedActivity] = await db.update(crmActivitiesTable)
      .set(updateData)
      .where(eq(crmActivitiesTable.id, id))
      .returning();
    
    return updatedActivity;
  }

  // Folder operations
  async getFolders(userId: string): Promise<Folder[]> {
    try {
      return await db.select()
        .from(foldersTable)
        .where(eq(foldersTable.userId, userId))
        .orderBy(asc(foldersTable.name));
    } catch (error) {
      console.error('Error fetching folders:', error);
      return [];
    }
  }

  async getFolder(id: string): Promise<Folder | undefined> {
    try {
      const folders = await db.select()
        .from(foldersTable)
        .where(eq(foldersTable.id, id));
      return folders.length > 0 ? folders[0] : undefined;
    } catch (error) {
      console.error(`Error fetching folder ${id}:`, error);
      return undefined;
    }
  }

  async createFolder(folder: InsertFolder): Promise<Folder> {
    try {
      const id = `folder_${Date.now()}`;
      const now = new Date();
      
      const [newFolder] = await db.insert(foldersTable)
        .values({
          id,
          name: folder.name,
          parentId: folder.parentId || null,
          userId: folder.userId,
          createdAt: now,
          updatedAt: now
        })
        .returning();
      
      return newFolder;
    } catch (error) {
      console.error('Error creating folder:', error);
      throw error;
    }
  }

  async updateFolder(id: string, updates: Partial<InsertFolder>): Promise<Folder | undefined> {
    try {
      const updateData = { ...updates, updatedAt: new Date() };
      
      const [updatedFolder] = await db.update(foldersTable)
        .set(updateData)
        .where(eq(foldersTable.id, id))
        .returning();
        
      return updatedFolder;
    } catch (error) {
      console.error(`Error updating folder ${id}:`, error);
      return undefined;
    }
  }

  async deleteFolder(id: string): Promise<void> {
    try {
      // First move any documents in this folder to no folder (root)
      await db.update(documentsTable)
        .set({ folderId: null })
        .where(eq(documentsTable.folderId, id));
        
      // Then delete the folder
      await db.delete(foldersTable)
        .where(eq(foldersTable.id, id));
    } catch (error) {
      console.error(`Error deleting folder ${id}:`, error);
      throw error;
    }
  }

  // Document operations
  async getDocuments(userId: string, folderId?: string): Promise<Document[]> {
    try {
      // Base query to get documents for a user
      if (folderId) {
        // Filter documents by specific folder
        return await db.select()
          .from(documentsTable)
          .where(and(
            eq(documentsTable.userId, userId),
            eq(documentsTable.folderId, folderId)
          ))
          .orderBy(desc(documentsTable.updatedAt));
      } else {
        // Get documents without a folder (root documents)
        // We need to use SQL for the IS NULL check
        return await db.select()
          .from(documentsTable)
          .where(and(
            eq(documentsTable.userId, userId),
            // Use SQL.raw for NULL comparison
            sql`${documentsTable.folderId} IS NULL`
          ))
          .orderBy(desc(documentsTable.updatedAt));
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
      return [];
    }
  }

  async getDocument(id: string): Promise<Document | undefined> {
    try {
      const docs = await db.select()
        .from(documentsTable)
        .where(eq(documentsTable.id, id));
      return docs.length > 0 ? docs[0] : undefined;
    } catch (error) {
      console.error(`Error fetching document ${id}:`, error);
      return undefined;
    }
  }

  async createDocument(document: InsertDocument): Promise<Document> {
    try {
      const id = `doc_${Date.now()}`;
      const now = new Date();
      
      const [newDocument] = await db.insert(documentsTable)
        .values({
          id,
          title: document.title,
          content: document.content,
          folderId: document.folderId || null,
          tags: document.tags || [],
          userId: document.userId,
          createdAt: now,
          updatedAt: now
        })
        .returning();
      
      return newDocument;
    } catch (error) {
      console.error('Error creating document:', error);
      throw error;
    }
  }

  async updateDocument(id: string, updates: Partial<InsertDocument>): Promise<Document | undefined> {
    try {
      const updateData = { ...updates, updatedAt: new Date() };
      
      const [updatedDocument] = await db.update(documentsTable)
        .set(updateData)
        .where(eq(documentsTable.id, id))
        .returning();
        
      return updatedDocument;
    } catch (error) {
      console.error(`Error updating document ${id}:`, error);
      return undefined;
    }
  }

  async deleteDocument(id: string): Promise<void> {
    try {
      await db.delete(documentsTable)
        .where(eq(documentsTable.id, id));
    } catch (error) {
      console.error(`Error deleting document ${id}:`, error);
      throw error;
    }
  }

  async getActions(userId: string, filters?: { status?: string; agentId?: string }): Promise<AgentAction[]> {
    let conditions = [eq(agentActionsTable.userId, userId)];
    if (filters?.status) {
      conditions.push(eq(agentActionsTable.status, filters.status));
    }
    if (filters?.agentId) {
      conditions.push(eq(agentActionsTable.agentId, filters.agentId));
    }
    return await db.select().from(agentActionsTable)
      .where(and(...conditions))
      .orderBy(desc(agentActionsTable.createdAt));
  }

  async getAction(id: string): Promise<AgentAction | undefined> {
    const results = await db.select().from(agentActionsTable).where(eq(agentActionsTable.id, id));
    return results.length > 0 ? results[0] : undefined;
  }

  async getPendingActions(userId: string): Promise<AgentAction[]> {
    return await db.select().from(agentActionsTable)
      .where(and(
        eq(agentActionsTable.userId, userId),
        eq(agentActionsTable.status, "pending")
      ))
      .orderBy(desc(agentActionsTable.createdAt));
  }

  async createAction(action: InsertAgentAction): Promise<AgentAction> {
    const id = `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = new Date();
    const [newAction] = await db.insert(agentActionsTable)
      .values({
        id,
        agentId: action.agentId,
        userId: action.userId,
        actionType: action.actionType,
        actionName: action.actionName,
        description: action.description || null,
        parameters: action.parameters,
        status: action.status || "pending",
        requiresApproval: action.requiresApproval ?? true,
        taskId: action.taskId || null,
        conversationId: action.conversationId || null,
        estimatedTimeSaved: action.estimatedTimeSaved || null,
        priority: action.priority || "medium",
        tags: action.tags || null,
        metadata: action.metadata || null,
        createdAt: now,
        updatedAt: now,
      })
      .returning();
    return newAction;
  }

  async updateAction(id: string, updates: Partial<AgentAction>): Promise<AgentAction | undefined> {
    const updateData: Record<string, any> = { ...updates, updatedAt: new Date() };
    delete updateData.id;
    const [updated] = await db.update(agentActionsTable)
      .set(updateData)
      .where(eq(agentActionsTable.id, id))
      .returning();
    return updated;
  }

  async getOauthToken(userId: string, provider: string): Promise<OauthToken | undefined> {
    const results = await db.select().from(oauthTokensTable)
      .where(and(
        eq(oauthTokensTable.userId, userId),
        eq(oauthTokensTable.provider, provider)
      ));
    return results.length > 0 ? results[0] : undefined;
  }

  async upsertOauthToken(token: InsertOauthToken): Promise<OauthToken> {
    const existing = await this.getOauthToken(token.userId, token.provider);
    if (existing) {
      const [updated] = await db.update(oauthTokensTable)
        .set({
          accessToken: token.accessToken,
          refreshToken: token.refreshToken || existing.refreshToken,
          tokenType: token.tokenType || existing.tokenType,
          expiresAt: token.expiresAt || existing.expiresAt,
          scope: token.scope || existing.scope,
          updatedAt: new Date(),
        })
        .where(eq(oauthTokensTable.id, existing.id))
        .returning();
      return updated;
    }
    const id = `oauth_${Date.now()}`;
    const [newToken] = await db.insert(oauthTokensTable)
      .values({
        id,
        userId: token.userId,
        provider: token.provider,
        accessToken: token.accessToken,
        refreshToken: token.refreshToken || null,
        tokenType: token.tokenType || "Bearer",
        expiresAt: token.expiresAt || null,
        scope: token.scope || null,
        createdAt: new Date(),
        updatedAt: new Date(),
      })
      .returning();
    return newToken;
  }

  async deleteOauthToken(userId: string, provider: string): Promise<void> {
    await db.delete(oauthTokensTable)
      .where(and(
        eq(oauthTokensTable.userId, userId),
        eq(oauthTokensTable.provider, provider)
      ));
  }

  async getAgentMetrics(agentId: string, userId: string): Promise<AgentMetric[]> {
    return await db.select().from(agentMetricsTable)
      .where(and(
        eq(agentMetricsTable.agentId, agentId),
        eq(agentMetricsTable.userId, userId)
      ))
      .orderBy(desc(agentMetricsTable.date));
  }

  async upsertAgentMetric(metric: InsertAgentMetric): Promise<AgentMetric> {
    const existing = await db.select().from(agentMetricsTable)
      .where(and(
        eq(agentMetricsTable.agentId, metric.agentId),
        eq(agentMetricsTable.userId, metric.userId),
        eq(agentMetricsTable.date, metric.date)
      ));
    if (existing.length > 0) {
      const [updated] = await db.update(agentMetricsTable)
        .set({ ...metric, updatedAt: new Date() })
        .where(eq(agentMetricsTable.id, existing[0].id))
        .returning();
      return updated;
    }
    const id = `metric_${Date.now()}`;
    const [newMetric] = await db.insert(agentMetricsTable)
      .values({
        id,
        ...metric,
        createdAt: new Date(),
        updatedAt: new Date(),
      })
      .returning();
    return newMetric;
  }

  async incrementMetric(agentId: string, userId: string, field: string, amount: number = 1): Promise<void> {
    const today = new Date().toISOString().split("T")[0];
    const existing = await db.select().from(agentMetricsTable)
      .where(and(
        eq(agentMetricsTable.agentId, agentId),
        eq(agentMetricsTable.userId, userId),
        eq(agentMetricsTable.date, today)
      ));
    if (existing.length > 0) {
      const currentValue = (existing[0] as any)[field] || 0;
      await db.update(agentMetricsTable)
        .set({ [field]: currentValue + amount, updatedAt: new Date() })
        .where(eq(agentMetricsTable.id, existing[0].id));
    } else {
      const id = `metric_${Date.now()}`;
      await db.insert(agentMetricsTable)
        .values({
          id,
          agentId,
          userId,
          date: today,
          [field]: amount,
          createdAt: new Date(),
          updatedAt: new Date(),
        });
    }
  }
}

export const storage = new DatabaseStorage();
