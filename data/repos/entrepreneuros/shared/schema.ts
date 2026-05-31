import { pgTable, text, serial, integer, boolean, timestamp, jsonb, decimal } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Users
export const users = pgTable("users", {
  id: text("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  email: text("email").notNull(),
  fullName: text("full_name"),
  avatar: text("avatar"),
  company: text("company"),
  role: text("role"),
  firebaseUid: text("firebase_uid").unique(), // Firebase User ID for Google Auth
  preferences: text("preferences"), // JSON string for user preferences
  metadata: jsonb("metadata"), // For storing miscellaneous user data like notification preferences
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertUserSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  email: z.string().email("Invalid email address"),
  fullName: z.string().optional(),
  avatar: z.string().optional(),
  company: z.string().optional(),
  role: z.string().optional(),
  firebaseUid: z.string().optional(), // Firebase User ID for Google Auth
  preferences: z.record(z.unknown()).optional(),
  metadata: z.record(z.unknown()).optional(), // Store metadata like notification preferences
});

// Agents
export const agents = pgTable("agents", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  role: text("role").notNull(),                      // Job title (e.g., "Marketing Specialist")
  roleLevel: text("role_level").default("laborer"),  // Chief, Manager, Laborer
  department: text("department").default("general"), // Marketing, Sales, Operations, etc.
  icon: text("icon").default("ri-robot-line"),
  instructions: text("instructions"),
  brainContent: text("brain_content"),
  knowledgeBase: text("knowledge_base"),             // Generated or uploaded knowledge
  kpis: text("kpis"),                                // Key Performance Indicators as JSON
  behavioralStyle: text("behavioral_style"),         // Agent's work style/personality
  latestActivity: text("latest_activity"),
  isActive: boolean("is_active").default(true),      // Whether agent is active or disabled
  simulationMode: boolean("simulation_mode").default(false), // If agent is in simulation mode
  parentAgentId: text("parent_agent_id"),            // For hierarchy, manually create relation
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertAgentSchema = z.object({
  name: z.string().min(1, "Name is required"),
  role: z.string().min(1, "Role is required"),
  roleLevel: z.enum(["chief", "manager", "laborer"]).default("laborer"),
  department: z.string().min(1, "Department is required"),
  icon: z.string().optional(),
  instructions: z.string().optional(),
  kpis: z.array(z.string()).optional(),
  behavioralStyle: z.string().optional(),
  isActive: z.boolean().optional(),
  simulationMode: z.boolean().optional(),
  parentAgentId: z.string().optional(),
  brainSources: z.array(
    z.object({
      type: z.enum(["url", "text", "file", "auto-generate"]),
      url: z.string().optional(),
      content: z.string().optional(),
    })
  ).optional(),
});

// Define Tasks table
export const tasks = pgTable("tasks", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  status: text("status").default("todo"),
  priority: text("priority").default("medium"),
  startDate: text("start_date"),
  dueDate: text("due_date"),
  instructions: text("instructions"),
  agentId: text("agent_id").references(() => agents.id),
  assignedById: text("assigned_by_id").references(() => agents.id),
  collaboratorIds: text("collaborator_ids"), // Comma-separated list of agent IDs
  taskType: text("task_type").default("standard"), // standard, collaboration, delegated
  parentTaskId: text("parent_task_id"), // For subtasks
  metadata: text("metadata"), // JSON string for additional task data
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertTaskSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().min(1, "Description is required"),
  status: z.enum(["todo", "in-progress", "done"]).default("todo"),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  startDate: z.string().optional(),
  dueDate: z.string().optional(),
  instructions: z.string().optional(),
  agentId: z.string().optional(),
  assignedById: z.string().optional(),
  collaboratorIds: z.string().optional(), // Comma-separated agent IDs
  taskType: z.enum(["standard", "collaboration", "delegated"]).default("standard"),
  parentTaskId: z.string().optional(),
  metadata: z.string().optional(), // JSON string
});

export const updateTaskSchema = z.object({
  title: z.string().min(1, "Title is required").optional(),
  description: z.string().min(1, "Description is required").optional(),
  status: z.enum(["todo", "in-progress", "done"]).optional(),
  priority: z.enum(["low", "medium", "high", "urgent"]).optional(),
  startDate: z.string().optional(),
  dueDate: z.string().optional(),
  instructions: z.string().optional(),
  agentId: z.string().optional(),
  assignedById: z.string().optional(),
  collaboratorIds: z.string().optional(),
  taskType: z.enum(["standard", "collaboration", "delegated"]).optional(),
  parentTaskId: z.string().optional(),
  metadata: z.string().optional(),
});

// Messages
export const messages = pgTable("messages", {
  id: text("id").primaryKey(),
  agentId: text("agent_id").references(() => agents.id),
  taskId: text("task_id").references(() => tasks.id),  // Optional task context
  conversationId: text("conversation_id"),  // Group messages by conversation
  role: text("role").notNull(),
  content: text("content").notNull(),
  metadata: text("metadata"),  // Store additional message data (e.g., attachments, citations)
  referencedAgentIds: text("referenced_agent_ids"), // If message mentions/references other agents
  timestamp: timestamp("timestamp").defaultNow(),
});

export const insertMessageSchema = z.object({
  agentId: z.string(),
  taskId: z.string().optional(),
  conversationId: z.string().optional(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  metadata: z.string().optional(),
  referencedAgentIds: z.string().optional(), // Comma-separated list of agent IDs
  timestamp: z.string().optional(),
});

// Integrations
export const integrations = pgTable("integrations", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  type: text("type").notNull(),
  status: text("status").default("disconnected"),
  details: text("details"),
  icon: text("icon"),
});

export const insertIntegrationSchema = z.object({
  name: z.string(),
  type: z.string(),
  status: z.enum(["connected", "disconnected"]).default("disconnected"),
  details: z.string().optional(),
  icon: z.string().optional(),
});

// Export types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export type InsertAgent = z.infer<typeof insertAgentSchema>;
export type Agent = typeof agents.$inferSelect;

export type InsertTask = z.infer<typeof insertTaskSchema>;
export type UpdateTask = z.infer<typeof updateTaskSchema>;
export type Task = typeof tasks.$inferSelect & { subtasks?: Task[] };

export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type Message = typeof messages.$inferSelect;

export type InsertIntegration = z.infer<typeof insertIntegrationSchema>;
export type Integration = typeof integrations.$inferSelect;

// Notifications
export const notifications = pgTable("notifications", {
  id: text("id").primaryKey(),
  userId: text("user_id").references(() => users.id),
  title: text("title").notNull(),
  content: text("content").notNull(),
  type: text("type").notNull(), // task-assigned, agent-created, integration-connected, etc.
  read: boolean("read").default(false),
  href: text("href"), // URL path for navigation when clicking the notification
  relatedId: text("related_id"), // ID of the related entity (task, agent, integration)
  metadata: jsonb("metadata"), // Additional data as JSON
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertNotificationSchema = z.object({
  userId: z.string(),
  title: z.string().min(1, "Title is required"),
  content: z.string().min(1, "Content is required"),
  type: z.string().min(1, "Type is required"),
  read: z.boolean().optional(),
  href: z.string().optional(),
  relatedId: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type InsertNotification = z.infer<typeof insertNotificationSchema>;
export type Notification = typeof notifications.$inferSelect;

// AI Assistant Messages
export const aiMessages = pgTable("ai_messages", {
  id: text("id").primaryKey().notNull(),
  role: text("role").notNull(), // "user" or "assistant"
  content: text("content").notNull(),
  userId: text("user_id").references(() => users.id).notNull(),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const insertAiMessageSchema = z.object({
  id: z.string().optional(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  userId: z.string(),
  timestamp: z.date().optional(),
});

export type InsertAiMessage = z.infer<typeof insertAiMessageSchema>;
export type AiMessage = typeof aiMessages.$inferSelect;

// CRM - Contacts
export const crmContacts = pgTable("crm_contacts", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull(),
  phone: text("phone"),
  company: text("company"),
  title: text("title"),
  status: text("status").default("lead"), // lead, prospect, customer, churned
  lastContact: timestamp("last_contact"),
  notes: text("notes"),
  avatar: text("avatar"),
  userId: text("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertCrmContactSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email is required"),
  phone: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  status: z.enum(["lead", "prospect", "customer", "churned"]).default("lead"),
  lastContact: z.date().optional(),
  notes: z.string().optional(),
  avatar: z.string().optional(),
  userId: z.string(),
});

// CRM - Deals
export const crmDeals = pgTable("crm_deals", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  company: text("company").notNull(),
  value: decimal("value", { precision: 10, scale: 2 }).notNull(),
  stage: text("stage").default("discovery"), // discovery, proposal, negotiation, closed-won, closed-lost
  probability: integer("probability").default(50),
  expectedCloseDate: timestamp("expected_close_date"),
  contactId: text("contact_id").references(() => crmContacts.id),
  assignedAgentId: text("assigned_agent_id").references(() => agents.id),
  notes: text("notes"),
  userId: text("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertCrmDealSchema = z.object({
  title: z.string().min(1, "Title is required"),
  company: z.string().min(1, "Company is required"),
  value: z.number().positive("Value must be positive"),
  stage: z.enum(["discovery", "proposal", "negotiation", "closed-won", "closed-lost"]).default("discovery"),
  probability: z.number().min(0).max(100).default(50),
  expectedCloseDate: z.date().optional(),
  contactId: z.string(),
  assignedAgentId: z.string().optional(),
  notes: z.string().optional(),
  userId: z.string(),
});

// CRM - Activities
export const crmActivities = pgTable("crm_activities", {
  id: text("id").primaryKey(),
  type: text("type").notNull(), // email, call, meeting, task, note
  subject: text("subject").notNull(),
  date: timestamp("date").notNull(),
  relatedToType: text("related_to_type").notNull(), // contact, deal
  relatedToId: text("related_to_id").notNull(),
  completed: boolean("completed").default(false),
  notes: text("notes"),
  createdByAgentId: text("created_by_agent_id").references(() => agents.id),
  userId: text("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertCrmActivitySchema = z.object({
  type: z.enum(["email", "call", "meeting", "task", "note"]),
  subject: z.string().min(1, "Subject is required"),
  date: z.date(),
  relatedToType: z.enum(["contact", "deal"]),
  relatedToId: z.string(),
  completed: z.boolean().default(false),
  notes: z.string().optional(),
  createdByAgentId: z.string().optional(),
  userId: z.string(),
});

// Export CRM types
export type InsertCrmContact = z.infer<typeof insertCrmContactSchema>;
export type CrmContact = typeof crmContacts.$inferSelect;

export type InsertCrmDeal = z.infer<typeof insertCrmDealSchema>;
export type CrmDeal = typeof crmDeals.$inferSelect;

export type InsertCrmActivity = z.infer<typeof insertCrmActivitySchema>;
export type CrmActivity = typeof crmActivities.$inferSelect;

// Folders table
export const folders = pgTable("folders", {
  id: text("id").primaryKey().notNull(),
  name: text("name").notNull(),
  parentId: text("parent_id").references((): any => folders.id),
  userId: text("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertFolderSchema = z.object({
  name: z.string().min(1, "Folder name is required"),
  parentId: z.string().optional(),
  userId: z.string(),
});

export type InsertFolder = z.infer<typeof insertFolderSchema>;
export type Folder = typeof folders.$inferSelect;

// Documents table
export const documents = pgTable("documents", {
  id: text("id").primaryKey().notNull(),
  title: text("title").notNull(),
  content: text("content").notNull(),
  folderId: text("folder_id").references(() => folders.id),
  tags: text("tags").array(),
  userId: text("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertDocumentSchema = z.object({
  title: z.string().min(1, "Title is required"),
  content: z.string(),
  folderId: z.string().optional(),
  tags: z.array(z.string()).optional(),
  userId: z.string(),
});

export type InsertDocument = z.infer<typeof insertDocumentSchema>;
export type Document = typeof documents.$inferSelect;

export const agentActions = pgTable("agent_actions", {
  id: text("id").primaryKey(),
  agentId: text("agent_id").notNull().references(() => agents.id, { onDelete: "cascade" }),
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  actionType: text("action_type").notNull(),
  actionName: text("action_name").notNull(),
  description: text("description"),
  parameters: jsonb("parameters").notNull(),
  status: text("status").notNull().default("pending"),
  requiresApproval: boolean("requires_approval").notNull().default(true),
  approvedBy: text("approved_by").references(() => users.id),
  approvedAt: timestamp("approved_at"),
  executedAt: timestamp("executed_at"),
  completedAt: timestamp("completed_at"),
  failedAt: timestamp("failed_at"),
  executionResult: jsonb("execution_result"),
  errorMessage: text("error_message"),
  retryCount: integer("retry_count").default(0),
  maxRetries: integer("max_retries").default(3),
  taskId: text("task_id").references(() => tasks.id),
  conversationId: text("conversation_id"),
  estimatedTimeSaved: integer("estimated_time_saved"),
  priority: text("priority").default("medium"),
  tags: text("tags").array(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertAgentActionSchema = z.object({
  agentId: z.string(),
  userId: z.string(),
  actionType: z.string(),
  actionName: z.string(),
  description: z.string().optional(),
  parameters: z.record(z.unknown()),
  status: z.enum(["pending", "approved", "executing", "completed", "failed", "rejected"]).default("pending"),
  requiresApproval: z.boolean().default(true),
  taskId: z.string().optional(),
  conversationId: z.string().optional(),
  estimatedTimeSaved: z.number().optional(),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  tags: z.array(z.string()).optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type InsertAgentAction = z.infer<typeof insertAgentActionSchema>;
export type AgentAction = typeof agentActions.$inferSelect;

export const oauthTokens = pgTable("oauth_tokens", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(),
  accessToken: text("access_token").notNull(),
  refreshToken: text("refresh_token"),
  tokenType: text("token_type"),
  expiresAt: timestamp("expires_at"),
  scope: text("scope"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertOauthTokenSchema = z.object({
  userId: z.string(),
  provider: z.string(),
  accessToken: z.string(),
  refreshToken: z.string().optional(),
  tokenType: z.string().optional(),
  expiresAt: z.date().optional(),
  scope: z.string().optional(),
});

export type InsertOauthToken = z.infer<typeof insertOauthTokenSchema>;
export type OauthToken = typeof oauthTokens.$inferSelect;

export const agentMetrics = pgTable("agent_metrics", {
  id: text("id").primaryKey(),
  agentId: text("agent_id").notNull().references(() => agents.id, { onDelete: "cascade" }),
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  date: text("date").notNull(),
  messagesSent: integer("messages_sent").default(0),
  messagesReceived: integer("messages_received").default(0),
  tasksCompleted: integer("tasks_completed").default(0),
  actionsExecuted: integer("actions_executed").default(0),
  tokensUsed: integer("tokens_used").default(0),
  apiCost: text("api_cost").default("0"),
  estimatedTimeSavedMinutes: integer("estimated_time_saved_minutes").default(0),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertAgentMetricSchema = z.object({
  agentId: z.string(),
  userId: z.string(),
  date: z.string(),
  messagesSent: z.number().default(0),
  messagesReceived: z.number().default(0),
  tasksCompleted: z.number().default(0),
  actionsExecuted: z.number().default(0),
  tokensUsed: z.number().default(0),
  apiCost: z.string().default("0"),
  estimatedTimeSavedMinutes: z.number().default(0),
});

export type InsertAgentMetric = z.infer<typeof insertAgentMetricSchema>;
export type AgentMetric = typeof agentMetrics.$inferSelect;
