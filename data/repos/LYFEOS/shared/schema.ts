import { pgTable, text, serial, integer, boolean, timestamp, jsonb, date, varchar, uuid, uniqueIndex } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
import { relations } from "drizzle-orm";

// Users table (Core Account Information)
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  // Original fields
  username: text("username").unique(),
  password: text("password"),
  displayName: text("display_name"),
  firstName: text("first_name"),
  lastName: text("last_name"),
  bio: text("bio"),
  avatarColor: text("avatar_color").default("#00e0ff"),
  title: text("title").default("COMMANDER"),
  profilePicture: text("profile_picture"),
  
  // New V2 fields
  email: text("email"), // Email (or blank if using OAuth)
  phoneNumber: text("phone_number"), // Phone number for contact
  authProvider: text("auth_provider").default("email"), // ("email", "google", "apple", "facebook")
  firebaseUid: text("firebase_uid"), // Firebase UID for Firebase-authenticated users
  termsAccepted: boolean("terms_accepted").default(false),
  emailVerified: boolean("email_verified").default(false),
  emailVerificationToken: text("email_verification_token"),
  emailVerificationExpiry: timestamp("email_verification_expiry"),
  passwordResetToken: text("password_reset_token"),
  passwordResetExpiry: timestamp("password_reset_expiry"),
  twoFactorEnabled: boolean("two_factor_enabled").default(false),
  phoneVerified: boolean("phone_verified").default(false),
  twoFactorEmailCode: text("two_factor_email_code"),
  twoFactorEmailExpiry: timestamp("two_factor_email_expiry"),
  twoFactorPhoneCode: text("two_factor_phone_code"),
  twoFactorPhoneExpiry: timestamp("two_factor_phone_expiry"),
  stripeCustomerId: text("stripe_customer_id"),
  stripeSubscriptionId: text("stripe_subscription_id"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  lastLoginAt: timestamp("last_login_at"),
});

// User Stats table
export const userStats = pgTable("user_stats", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id).unique(),
  timeTokensCurrent: integer("time_tokens_current").notNull().default(100),
  timeTokensMax: integer("time_tokens_max").notNull().default(100),
  energyPointsCurrent: integer("energy_points_current").notNull().default(100),
  energyPointsMax: integer("energy_points_max").notNull().default(100),
  healthPointsCurrent: integer("health_points_current").notNull().default(100),
  healthPointsMax: integer("health_points_max").notNull().default(100),
  wealthTokensCurrent: integer("wealth_tokens_current").notNull().default(100),
  wealthTokensMax: integer("wealth_tokens_max").notNull().default(100),
  attentionTokensCurrent: integer("attention_tokens_current").notNull().default(100),
  attentionTokensMax: integer("attention_tokens_max").notNull().default(100),
  experienceCurrent: integer("experience_current").notNull().default(0),
  experienceMax: integer("experience_max").notNull().default(1000), // Level 1 threshold is 1000 XP
  level: integer("level").notNull().default(1),
  streakDays: integer("streak_days").notNull().default(0),
  lastActiveDate: date("last_active_date"),
  previousDayEnergyUsed: integer("previous_day_energy_used").default(0),
  efficiencyScore: integer("efficiency_score").notNull().default(0),
  aiAssistantName: text("ai_assistant_name").default("NOVA").notNull(),
  // System settings
  notificationsEnabled: boolean("notifications_enabled").default(false).notNull(),
  darkThemeEnabled: boolean("dark_theme_enabled").default(true).notNull(),
  autoSyncEnabled: boolean("auto_sync_enabled").default(true).notNull(),
  aiAssistantEnabled: boolean("ai_assistant_enabled").default(true).notNull(),
  primaryColor: text("primary_color").default("#ffffff").notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// User Profile Table (All Onboarding Answers + Player Record)
export const userProfile = pgTable("user_profile", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id).unique(),
  
  // === MISSION 0: ACCESS & QUICKSTART ===
  ageRange: text("age_range"), // ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
  birthday: text("birthday"), // ISO date string "YYYY-MM-DD"
  location: text("location"), // Optional location text
  timezone: text("timezone"), // IANA timezone string
  
  // === MISSION 1: ARCHETYPE CALIBRATION ===
  archetypePrimary: text("archetype_primary"), // ("Warrior", "Architect", "Creator", "Monarch", "Oracle", "Alchemist")
  archetypeSecondary: text("archetype_secondary"),
  archetypeShadow: text("archetype_shadow"),
  archetypeScores: jsonb("archetype_scores").default({}), // { warrior: X, architect: X, creator: X, monarch: X, oracle: X, alchemist: X }
  
  // === SECTION 1: IDENTITY ===
  primaryInstincts: jsonb("primary_instincts").default([]), // Array of instincts
  keyDrivers: jsonb("key_drivers").default([]), // Array of drivers
  shadowDistortions: jsonb("shadow_distortions").default([]), // Array of shadow patterns
  
  // === SECTION 2: PERSONALITY ===
  coreBelief: text("core_belief"),
  limitingBelief: text("limiting_belief"),
  empoweringBelief: text("empowering_belief"),
  primaryValues: jsonb("primary_values").default([]), // Array of top 3 values
  supportingValues: jsonb("supporting_values").default([]), // Additional values
  selfStandards: text("self_standards"), // Standards held for self
  othersStandards: text("others_standards"), // Standards expected of others
  typicalPatterns: text("typical_patterns"), // Behavioral patterns
  habits: jsonb("habits").default([]), // Array of habits
  urges: text("urges"), // Urges/impulses
  traitToReprogram: text("trait_to_reprogram"),
  desiredTrait: text("desired_trait"),
  strengths: jsonb("strengths").default([]), // Array of strengths
  weaknesses: jsonb("weaknesses").default([]), // Array of weaknesses
  
  // === SECTION 3: VISION & GOALS ===
  lifeStage: text("life_stage"), // ("Awakening", "Building", "Mastering", "Leading")
  desiredEmotion: text("desired_emotion"), // ("Flow", "Peace", "Joy", "Power", "Love", "Purpose")
  vision90Day: text("vision_90_day"),
  vision90DayMetric: text("vision_90_day_metric"),
  vision18Month: text("vision_18_month"),
  vision18MonthMetric: text("vision_18_month_metric"),
  vision5Year: text("vision_5_year"),
  vision5YearChip: text("vision_5_year_chip"),
  vision10Year: text("vision_10_year"),
  vision10YearLegacy: text("vision_10_year_legacy"),
  legacyMetric: text("legacy_metric"),
  mortalityInsights: jsonb("mortality_insights").default({}), // { reflection: "", takeaway: "" }
  lifeDomains: jsonb("life_domains").default([]), // Ordered array of domain strings
  currentGoals: jsonb("current_goals").default([]), // Array of current goals
  
  // === SECTION 4: LEARNING & SKILLS ===
  learningStyle: jsonb("learning_style").default({}), // { visual: X, auditory: X, reading: X, kinesthetic: X }
  integrationMethod: text("integration_method"),
  pastDeepDives: jsonb("past_deep_dives").default([]), // Array of past research topics
  domainsOfCompetence: jsonb("domains_of_competence").default([]),
  currentDeepDive: jsonb("current_deep_dive").default({}), // { question: "", purpose: "", successCriteria: "" }
  skillStackingPyramid: jsonb("skill_stacking_pyramid").default({}), // { vocational: "", evolutionary: [], resonant: [], staticFoundational: [], seasonalFoundational: [] }
  knowledgeAreas: jsonb("knowledge_areas").default([]),
  skillsToAcquire: jsonb("skills_to_acquire").default([]),
  practiceCadence: jsonb("practice_cadence").default({}), // { hoursPerWeek: X, note: "" }
  
  // === SECTION 5: PROJECTS & CREATIONS ===
  currentProjects: jsonb("current_projects").default([]), // Array of { name, doneWhen }
  projectDefinition: text("project_definition"),
  activePhase: text("active_phase"),
  primaryCraft: text("primary_craft"),
  primaryCraftWhy: text("primary_craft_why"),
  
  // === SECTION 6: BODY & HEALTH ===
  physicalMetrics: jsonb("physical_metrics").default({}), // { height: "", weight: "", bodyType: "", distinctiveFeatures: "" }
  fitnessMovement: jsonb("fitness_movement").default({}), // { trainingStyle: "", movementPractices: [] }
  nutritionRecovery: jsonb("nutrition_recovery").default({}), // { nutritionalApproach: "", recoveryPractices: [], stressRecoveryStyle: "" }
  healthVitality: jsonb("health_vitality").default({}), // { conditions: [], energyPatterns: "", somaticAwareness: "", longevityFocus: [] }
  healthBaseline: jsonb("health_baseline").default({}), // { sleep: X, exercise: X, nutrition: X, priority: "" }
  injuries: text("injuries"),
  
  // === SECTION 7: WEALTH & WORK ===
  careerVocation: text("career_vocation"),
  activeVentures: jsonb("active_ventures").default([]),
  financialPosition: jsonb("financial_position").default({}), // { income: "", expenses: "", savings: "", debt: "" }
  financialConstraints: jsonb("financial_constraints").default([]),
  moneyConfidence: jsonb("money_confidence").default({}), // { score: 1-10, habitShift: "" }
  moneyRelationship: text("money_relationship"),
  weeklyCapacity: jsonb("weekly_capacity").default({}), // { hours: X, cap: "" }
  energyDrains: jsonb("energy_drains").default([]),
  resources: jsonb("resources").default({}), // { skills: bool, tools: bool, network: bool, financial: bool, time: bool }
  physicalEnvironment: text("physical_environment"),
  physicalEnvironmentImpact: text("physical_environment_impact"),
  digitalEnvironment: jsonb("digital_environment").default([]),
  
  // === SECTION 8: PERFORMANCE & CONTRIBUTION ===
  collaborationStyle: text("collaboration_style"),
  roleOrientation: text("role_orientation"),
  decisionOrientation: text("decision_orientation"),
  stressResponse: text("stress_response"),
  optimalEnvironment: text("optimal_environment"),
  greatestContribution: text("greatest_contribution"),
  
  // === SECTION 9: STYLE & EXPRESSION ===
  aesthetic: text("aesthetic"),
  signatureExpression: text("signature_expression"),
  creativeOutlets: jsonb("creative_outlets").default([]),
  
  // === HISTORY & ROOTS ===
  shadowPatterns: jsonb("shadow_patterns").default({}), // { pattern: "", lesson: "" }
  historicalContext: jsonb("historical_context").default([]), // Timeline with age markers
  upbringing: text("upbringing"),
  culturalContext: text("cultural_context"),
  keyExperiences: jsonb("key_experiences").default({}), // { experience: "", outcomes: "" }
  
  // === SYSTEMS & RITUALS ===
  idealDay: text("ideal_day"),
  lockedHabit: text("locked_habit"),
  idealWeek: jsonb("ideal_week").default({}),
  yearlyCycles: jsonb("yearly_cycles").default([]),
  morningRituals: jsonb("morning_rituals").default([]),
  eveningRituals: jsonb("evening_rituals").default([]),
  groundingRitual: text("grounding_ritual"),
  boundaries: jsonb("boundaries").default({}), // { techOffTime: "", workHours: "", recoveryTime: "" }
  
  // === EMOTIONS & COPING ===
  emotionsToCultivate: jsonb("emotions_to_cultivate").default([]),
  copingPractices: text("coping_practices"),
  copingEssential: text("coping_essential"),
  traitsToCultivate: jsonb("traits_to_cultivate").default([]),
  beliefSystem: jsonb("belief_system").default({}), // { empowering: [], limiting: [], core: "", strongest: "" }
  dominantInstinct: jsonb("dominant_instinct").default({}), // { type: "", description: "", influence: "" }
  decisionMakingStyles: jsonb("decision_making_styles").default([]),
  decisionMakingPrimary: text("decision_making_primary"),
  lifeRoles: jsonb("life_roles").default([]),
  definingRole: text("defining_role"),
  relationshipDrains: text("relationship_drains"),
  conflictStyle: text("conflict_style"),
  moneyMemory: jsonb("money_memory").default({}), // { memory: "", impact: "" }
  financialSecurity: jsonb("financial_security").default({}), // { reflection: "", eliminate: "" }
  financialHabits: jsonb("financial_habits").default({}), // { current: [], toReprogram: [] }
  
  // === CHARACTER AFFIRMATION ===
  characterAffirmation: text("character_affirmation"), // AI-generated third-person narrative
  
  // === CUSTOM REFLECTION PROMPTS ===
  customReflectionPrompts: jsonb("custom_reflection_prompts").default({
    wentWell: "What went well today?",
    couldBeBetter: "What could have been better?",
    learned: "What did I learn?"
  }),

  // === DISPLAY SETTINGS ===
  blueLightFilter: boolean("blue_light_filter").default(false),
  hapticFeedback: boolean("haptic_feedback").default(true),
  soundEffects: boolean("sound_effects").default(true),

  // === ONBOARDING TRACKING ===
  onboardingMission: integer("onboarding_mission").default(0), // Current mission (0-7)
  onboardingStep: integer("onboarding_step").default(0), // Current step within mission
  
  // === LEGACY FIELDS ===
  startStage: text("start_stage"), // ("Awakening", "Building", "Mastering", "Leading")
  targetArchetype: text("target_archetype"), // Legacy field
  flowStyle: jsonb("flow_style").default({}),
  coreMotivation: text("core_motivation"),
  setupMissionStatus: jsonb("setup_mission_status").default({
    archetype: "incomplete", 
    integrations: "incomplete", 
    future_self: "incomplete", 
    rituals: "incomplete", 
    pillars: "incomplete"
  }),
  primaryThemeColor: text("primary_theme_color").default("#00e0ff"),
  futureSelfSummary: text("future_self_summary"),
  aiPersonalityProfile: jsonb("ai_personality_profile").default({}),
  totalXP: integer("total_xp").notNull().default(0),
  onboardingCompleted: boolean("onboarding_completed").default(false).notNull(),
  completedOnboardingMissions: integer("completed_onboarding_missions").array().default([]),
  completedTutorials: text("completed_tutorials").array().default([]),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// User Daily Logs Table (Daily Initialization)
export const userDailyLogs = pgTable("user_daily_logs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  date: date("date").notNull(),
  yesterdayXp: integer("yesterday_xp").default(0),
  todayPrimaryMission: text("today_primary_mission"),
  optionalBoostsShown: boolean("optional_boosts_shown").default(false),
  boostsData: jsonb("boosts_data").default({}), // Store daily boosts data
  // Energy log fields
  wakeTime: text("wake_time"), // Time user woke up (HH:MM format)
  sleepTime: text("sleep_time"), // Time user went to sleep (HH:MM format)
  mentalState: integer("mental_state").default(5), // 1-10 scale
  physicalState: integer("physical_state").default(5), // 1-10 scale
  emotionalState: integer("emotional_state").default(5), // 1-10 scale
  // Intention log fields
  gratitude: text("gratitude"), // What I'm grateful for today
  tomorrowGoals: text("tomorrow_goals"), // Goals for tomorrow
  annualGoals: text("annual_goals"), // Annual goals reminder
  thoughts: text("thoughts"), // Free-form thoughts/intentions
  // Data log fields
  contentConsumed: text("content_consumed"), // Information consumed today
  research: text("research"), // Research notes (legacy)
  todoIdeas: text("todo_ideas"), // Ideas for future todos
  // Research log fields
  sourceAuthor: text("source_author"), // Source author name
  sourceMaterial: text("source_material"), // Source material reference
  researchNote: text("research_note"), // Research note
  revisionNote: text("revision_note"), // Revision & summary note
  executionNote: text("execution_note"), // Execution note
  researchEntries: jsonb("research_entries").default([]), // Array of archived research entries for multiple entries per day
  todosConverted: boolean("todos_converted").default(false), // Whether todoIdeas have been converted to quests
  // Reflection log fields
  wentWell: text("went_well"), // What went well today
  couldBeBetter: text("could_be_better"), // What could be better
  learned: text("learned"), // What I learned today
  createdAt: timestamp("created_at").defaultNow().notNull(),
}, (table) => [
  uniqueIndex("user_daily_logs_user_date_idx").on(table.userId, table.date),
]);

// User Integrations Table (Connected Apps)
export const userIntegrations = pgTable("user_integrations", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  appleHealthConnected: boolean("apple_health_connected").default(false),
  googleCalendarConnected: boolean("google_calendar_connected").default(false),
  notionConnected: boolean("notion_connected").default(false),
  otherIntegrations: jsonb("other_integrations").default({}), // Future-proof for more apps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Quests table (Missions Management)
export const quests = pgTable("quests", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  title: text("title").notNull(),
  description: text("description").notNull(),
  category: text("category").default("general"), // "setup", "rituals", "life pillars", etc.
  completed: boolean("completed").notNull().default(false),
  completedAt: timestamp("completed_at"), // Timestamp when quest was completed
  energyCost: integer("energy_cost").notNull().default(1),
  attentionCost: integer("attention_cost").notNull().default(0),
  timeCost: integer("time_cost").notNull().default(0),
  experienceReward: integer("experience_reward").notNull().default(10),
  autoUnlockConditions: jsonb("auto_unlock_conditions").default({}), // e.g., { "setup_complete": true }
  startDate: text("start_date"), // format: "YYYY-MM-DD"
  startTime: text("start_time"), // format: "HH:MM"
  endDate: text("end_date"), // format: "YYYY-MM-DD"
  endTime: text("end_time"), // format: "HH:MM"
  dueDate: text("due_date"), // format: "YYYY-MM-DD", null means no due date (legacy, kept for compatibility)
  notificationEnabled: boolean("notification_enabled").default(false),
  notificationTime: text("notification_time"), // format: "HH:MM" or minutes before like "-15", "-30", "-60" (legacy)
  notifications: jsonb("notifications").default([]), // Array of { date: "YYYY-MM-DD", time: "HH:MM" }
  difficulty: text("difficulty").default("D"), // S, A, B, C, D ranks
  isRitualized: boolean("is_ritualized").default(false),
  ritualGroup: text("ritual_group"),
  repeatFrequency: text("repeat_frequency"), // "hourly", "daily", "weekly", "monthly", "yearly"
  repeatInterval: integer("repeat_interval").default(1), // every X hours/days/weeks/months/years
  repeatDays: text("repeat_days").array(), // for weekly: ["mon","tue","wed","thu","fri","sat","sun"]
  repeatEndDate: text("repeat_end_date"), // format: "YYYY-MM-DD", null means forever
  parentRitualId: integer("parent_ritual_id"), // links generated instances back to the original ritual
  visionGoalId: integer("vision_goal_id").references(() => visionGoals.id),
  linkedItems: jsonb("linked_items").default([]),
  sortOrder: integer("sort_order").default(0),
  externalId: text("external_id"),
  externalSource: text("external_source"),
  location: text("location"),
  allDay: boolean("all_day").default(false),
  timezone: text("timezone"),
  url: text("url"),
  attendees: jsonb("attendees").default([]),
  missionStatus: text("mission_status").default("confirmed"),
  viewId: integer("view_id"),
  viewColumn: text("view_column"),
  deletedAt: timestamp("deleted_at"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// AI Messages table
export const aiMessages = pgTable("ai_messages", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  sender: text("sender").notNull(), // 'ai' or 'user'
  content: text("content").notNull(),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

// Calendar Events table
export const calendarEvents = pgTable("calendar_events", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  title: text("title").notNull(),
  description: text("description").notNull(),
  startTime: text("start_time").notNull(), // format: "HH:MM"
  endTime: text("end_time"), // format: "HH:MM"
  duration: text("duration").notNull(),
  category: text("category").notNull(), // 'work', 'personal', or 'health'
  date: text("date").notNull(), // format: "YYYY-MM-DD"
  location: text("location"),
  allDay: boolean("all_day").default(false),
  externalId: text("external_id"),
  externalSource: text("external_source"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Mission Pages table
export const missionPages = pgTable("mission_pages", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  title: text("title").notNull(),
  slug: text("slug").notNull().unique(),
  content: text("content").notNull(),
  completed: boolean("completed").notNull().default(false),
  xpValue: integer("xp_value").notNull().default(5),
  tags: text("tags").array(),
  eventId: integer("event_id").references(() => calendarEvents.id),
  date: text("date"), // format: "YYYY-MM-DD" - used for filtering by day
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Contacts table
export const contacts = pgTable("contacts", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  alias: text("alias"),
  email: text("email"),
  phone: text("phone"),
  secondaryPhone: text("secondary_phone"),
  company: text("company"),
  jobTitle: text("job_title"),
  department: text("department"),
  industry: text("industry"),
  category: text("category").notNull().default("personal"),
  relationshipType: text("relationship_type"),
  notes: text("notes"),
  favorite: boolean("favorite").notNull().default(false),
  lastContacted: timestamp("last_contacted", { mode: "date" }),
  birthday: date("birthday"),
  address: text("address"),
  city: text("city"),
  country: text("country"),
  timezone: text("timezone"),
  linkedin: text("linkedin"),
  twitter: text("twitter"),
  instagram: text("instagram"),
  website: text("website"),
  howMet: text("how_met"),
  trustLevel: integer("trust_level"),
  strengths: text("strengths"),
  contactFrequency: text("contact_frequency"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Spreadsheets table
export const spreadsheets = pgTable("spreadsheets", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  content: jsonb("content").notNull(), // Store spreadsheet data as JSON
  favorite: boolean("favorite").notNull().default(false),
  category: text("category").notNull().default("general"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Relationships - Note: some tables are declared later but referenced here
export const usersRelations = relations(users, ({ one, many }) => ({
  stats: one(userStats, {
    fields: [users.id],
    references: [userStats.userId],
  }),
  profile: one(userProfile, {
    fields: [users.id],
    references: [userProfile.userId],
  }),
  dailyLogs: many(userDailyLogs),
  quests: many(quests),
  messages: many(aiMessages),
  events: many(calendarEvents),
  missionPages: many(missionPages),
  contacts: many(contacts),
  spreadsheets: many(spreadsheets),
  userIntegrations: one(userIntegrations, {
    fields: [users.id],
    references: [userIntegrations.userId],
  }),
}));

export const userStatsRelations = relations(userStats, ({ one }) => ({
  user: one(users, {
    fields: [userStats.userId],
    references: [users.id],
  }),
}));

export const userProfileRelations = relations(userProfile, ({ one }) => ({
  user: one(users, {
    fields: [userProfile.userId],
    references: [users.id],
  }),
}));

export const userDailyLogsRelations = relations(userDailyLogs, ({ one }) => ({
  user: one(users, {
    fields: [userDailyLogs.userId],
    references: [users.id],
  }),
}));

export const userIntegrationsRelations = relations(userIntegrations, ({ one }) => ({
  user: one(users, {
    fields: [userIntegrations.userId],
    references: [users.id],
  }),
}));

export const questsRelations = relations(quests, ({ one }) => ({
  user: one(users, {
    fields: [quests.userId],
    references: [users.id],
  }),
}));

export const aiMessagesRelations = relations(aiMessages, ({ one }) => ({
  user: one(users, {
    fields: [aiMessages.userId],
    references: [users.id],
  }),
}));

export const calendarEventsRelations = relations(calendarEvents, ({ one, many }) => ({
  user: one(users, {
    fields: [calendarEvents.userId],
    references: [users.id],
  }),
  missionPages: many(missionPages),
}));

export const missionPagesRelations = relations(missionPages, ({ one }) => ({
  user: one(users, {
    fields: [missionPages.userId],
    references: [users.id],
  }),
  event: one(calendarEvents, {
    fields: [missionPages.eventId],
    references: [calendarEvents.id],
  }),
}));

export const contactsRelations = relations(contacts, ({ one }) => ({
  user: one(users, {
    fields: [contacts.userId],
    references: [users.id],
  }),
}));

export const spreadsheetsRelations = relations(spreadsheets, ({ one }) => ({
  user: one(users, {
    fields: [spreadsheets.userId],
    references: [users.id],
  }),
}));

// Insert Schemas
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
  displayName: true,
  firstName: true,
  lastName: true,
  bio: true,
  avatarColor: true,
  title: true,
  profilePicture: true,
  email: true,
  phoneNumber: true,
  authProvider: true,
  firebaseUid: true,
  termsAccepted: true,
  lastLoginAt: true,
  stripeCustomerId: true,
  stripeSubscriptionId: true,
});

export const insertUserStatsSchema = createInsertSchema(userStats).pick({
  userId: true,
  timeTokensCurrent: true,
  timeTokensMax: true,
  energyPointsCurrent: true,
  energyPointsMax: true,
  healthPointsCurrent: true,
  healthPointsMax: true,
  attentionTokensCurrent: true,
  attentionTokensMax: true,
  experienceCurrent: true,
  experienceMax: true,
  level: true,
  streakDays: true,
  lastActiveDate: true,
  previousDayEnergyUsed: true,
  efficiencyScore: true,
  aiAssistantName: true,
  notificationsEnabled: true,
  darkThemeEnabled: true,
  autoSyncEnabled: true,
  aiAssistantEnabled: true,
  primaryColor: true,
});

export const insertQuestSchema = createInsertSchema(quests).pick({
  userId: true,
  title: true,
  description: true,
  category: true,
  completed: true,
  completedAt: true,
  energyCost: true,
  attentionCost: true,
  timeCost: true,
  experienceReward: true,
  startDate: true,
  startTime: true,
  endDate: true,
  endTime: true,
  dueDate: true,
  notificationEnabled: true,
  notificationTime: true,
  notifications: true,
  difficulty: true,
  isRitualized: true,
  ritualGroup: true,
  repeatFrequency: true,
  repeatInterval: true,
  repeatDays: true,
  repeatEndDate: true,
  parentRitualId: true,
  visionGoalId: true,
  linkedItems: true,
  createdAt: true,
  sortOrder: true,
  externalId: true,
  externalSource: true,
  location: true,
  allDay: true,
  timezone: true,
  url: true,
  attendees: true,
  missionStatus: true,
  deletedAt: true,
});

export const insertAIMessageSchema = createInsertSchema(aiMessages).pick({
  userId: true,
  sender: true,
  content: true,
});

export const insertCalendarEventSchema = createInsertSchema(calendarEvents).pick({
  userId: true,
  title: true,
  description: true,
  startTime: true,
  endTime: true,
  duration: true,
  category: true,
  date: true,
  location: true,
  allDay: true,
  externalId: true,
  externalSource: true,
});

export const insertMissionPageSchema = createInsertSchema(missionPages).pick({
  userId: true,
  title: true,
  slug: true,
  content: true,
  completed: true,
  xpValue: true,
  tags: true,
  eventId: true,
  date: true,
});

export const insertContactSchema = createInsertSchema(contacts).pick({
  userId: true,
  name: true,
  alias: true,
  email: true,
  phone: true,
  secondaryPhone: true,
  company: true,
  jobTitle: true,
  department: true,
  industry: true,
  category: true,
  relationshipType: true,
  notes: true,
  favorite: true,
  lastContacted: true,
  birthday: true,
  address: true,
  city: true,
  country: true,
  timezone: true,
  linkedin: true,
  twitter: true,
  instagram: true,
  website: true,
  howMet: true,
  trustLevel: true,
  strengths: true,
  contactFrequency: true,
});

export const insertSpreadsheetSchema = createInsertSchema(spreadsheets).pick({
  userId: true,
  title: true,
  description: true,
  content: true,
  favorite: true,
  category: true,
});

// Insert schemas for new V2 tables
export const insertUserProfileSchema = createInsertSchema(userProfile).pick({
  userId: true,
  startStage: true,
  targetArchetype: true,
  flowStyle: true,
  coreMotivation: true,
  setupMissionStatus: true,
  primaryThemeColor: true,
  futureSelfSummary: true,
  aiPersonalityProfile: true,
  totalXP: true,
  onboardingCompleted: true,
  completedOnboardingMissions: true,
  completedTutorials: true,
});

export const insertUserDailyLogsSchema = createInsertSchema(userDailyLogs).pick({
  userId: true,
  date: true,
  yesterdayXp: true,
  todayPrimaryMission: true,
  optionalBoostsShown: true,
  boostsData: true,
  // Energy log fields
  wakeTime: true,
  sleepTime: true,
  mentalState: true,
  physicalState: true,
  emotionalState: true,
  // Intention log fields
  gratitude: true,
  tomorrowGoals: true,
  annualGoals: true,
  thoughts: true,
  // Data log fields
  contentConsumed: true,
  research: true,
  todoIdeas: true,
  todosConverted: true,
  // Research log fields
  sourceAuthor: true,
  sourceMaterial: true,
  researchNote: true,
  revisionNote: true,
  executionNote: true,
  // Reflection log fields
  wentWell: true,
  couldBeBetter: true,
  learned: true,
});

export const insertUserIntegrationsSchema = createInsertSchema(userIntegrations).pick({
  userId: true,
  appleHealthConnected: true,
  googleCalendarConnected: true,
  notionConnected: true,
  otherIntegrations: true,
});

// Push Subscriptions table (FCM tokens)
export const pushSubscriptions = pgTable("push_subscriptions", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  fcmToken: text("fcm_token").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertPushSubscriptionSchema = createInsertSchema(pushSubscriptions).pick({
  userId: true,
  fcmToken: true,
});

// Types
export type PushSubscription = typeof pushSubscriptions.$inferSelect;
export type InsertPushSubscription = z.infer<typeof insertPushSubscriptionSchema>;

export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;

export type UserStats = typeof userStats.$inferSelect;
export type InsertUserStats = z.infer<typeof insertUserStatsSchema>;

export type UserProfile = typeof userProfile.$inferSelect;
export type InsertUserProfile = z.infer<typeof insertUserProfileSchema>;

export type UserDailyLog = typeof userDailyLogs.$inferSelect;
export type InsertUserDailyLog = z.infer<typeof insertUserDailyLogsSchema>;

export type UserIntegration = typeof userIntegrations.$inferSelect;
export type InsertUserIntegration = z.infer<typeof insertUserIntegrationsSchema>;

export type Quest = typeof quests.$inferSelect;
export type InsertQuest = z.infer<typeof insertQuestSchema>;

export type AIMessage = typeof aiMessages.$inferSelect;
export type InsertAIMessage = z.infer<typeof insertAIMessageSchema>;

export type CalendarEvent = typeof calendarEvents.$inferSelect;
export type InsertCalendarEvent = z.infer<typeof insertCalendarEventSchema>;

export type MissionPage = typeof missionPages.$inferSelect;
export type InsertMissionPage = z.infer<typeof insertMissionPageSchema>;

export type Contact = typeof contacts.$inferSelect;
export type InsertContact = z.infer<typeof insertContactSchema>;

export type Spreadsheet = typeof spreadsheets.$inferSelect;
export type InsertSpreadsheet = z.infer<typeof insertSpreadsheetSchema>;

// Canvas table
export const canvases = pgTable("canvases", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  title: text("title").notNull(),
  description: text("description"),
  content: jsonb("content").notNull().default({}), // Stores canvas elements like shapes, connections, text
  favorite: boolean("favorite").default(false).notNull(),
  category: text("category").default("general").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Canvas relations
export const canvasRelations = relations(canvases, ({ one }) => ({
  user: one(users, {
    fields: [canvases.userId],
    references: [users.id],
  }),
}));

// Insert schema for Canvas
export const insertCanvasSchema = createInsertSchema(canvases).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Graph table
export const graphs = pgTable("graphs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  title: text("title").notNull(),
  description: text("description"),
  content: jsonb("content").notNull().default({}), // Stores nodes, edges, and styling
  favorite: boolean("favorite").default(false).notNull(),
  category: text("category").default("general").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Graph relations
export const graphRelations = relations(graphs, ({ one }) => ({
  user: one(users, {
    fields: [graphs.userId],
    references: [users.id],
  }),
}));

// Insert schema for Graph
export const insertGraphSchema = createInsertSchema(graphs).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Folders table
export const folders = pgTable("folders", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  name: text("name").notNull(),
  description: text("description"),
  parentId: integer("parent_id"),
  favorite: boolean("favorite").default(false).notNull(),
  source: text("source").default("local").notNull(),
  externalId: text("external_id"),
  externalUrl: text("external_url"),
  deletedAt: timestamp("deleted_at"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Documents table
export const documents = pgTable("documents", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  folderId: integer("folder_id").references(() => folders.id),
  title: text("title").notNull(),
  content: text("content").notNull(),
  description: text("description"),
  format: text("format").default("markdown").notNull(),
  favorite: boolean("favorite").default(false).notNull(),
  tags: text("tags").array(),
  source: text("source").default("local").notNull(),
  externalId: text("external_id"),
  externalUrl: text("external_url"),
  lastSyncedAt: timestamp("last_synced_at"),
  fileType: text("file_type"),
  fileData: text("file_data"),
  fileSize: integer("file_size"),
  mimeType: text("mime_type"),
  thumbnailData: text("thumbnail_data"),
  deletedAt: timestamp("deleted_at"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Folder relations
export const folderRelations = relations(folders, ({ one, many }) => ({
  user: one(users, {
    fields: [folders.userId],
    references: [users.id],
  }),
  parent: one(folders, {
    fields: [folders.parentId],
    references: [folders.id],
  }),
  children: many(folders),
  documents: many(documents),
}));

// Document relations
export const documentRelations = relations(documents, ({ one }) => ({
  user: one(users, {
    fields: [documents.userId],
    references: [users.id],
  }),
  folder: one(folders, {
    fields: [documents.folderId],
    references: [folders.id],
  }),
}));

// Insert schema for Folder
export const insertFolderSchema = createInsertSchema(folders).omit({
  id: true,
  deletedAt: true,
  createdAt: true,
  updatedAt: true,
});

// Insert schema for Document
export const insertDocumentSchema = createInsertSchema(documents).omit({
  id: true,
  deletedAt: true,
  lastSyncedAt: true,
  createdAt: true,
  updatedAt: true,
});

export type Canvas = typeof canvases.$inferSelect;
export type InsertCanvas = z.infer<typeof insertCanvasSchema>;

export type Graph = typeof graphs.$inferSelect;
export type InsertGraph = z.infer<typeof insertGraphSchema>;

export type Folder = typeof folders.$inferSelect;
export type InsertFolder = z.infer<typeof insertFolderSchema>;

export type Document = typeof documents.$inferSelect;
export type InsertDocument = z.infer<typeof insertDocumentSchema>;

// Document Templates
export const templates = pgTable("templates", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  content: text("content").notNull(),
  format: text("format").default("markdown").notNull(),
  category: text("category").default("general").notNull(),
  tags: text("tags").array(),
  favorite: boolean("favorite").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Template relations
export const templateRelations = relations(templates, ({ one }) => ({
  user: one(users, {
    fields: [templates.userId],
    references: [users.id],
  }),
}));

// Insert schema for Template
export const insertTemplateSchema = createInsertSchema(templates).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type Template = typeof templates.$inferSelect;
export type InsertTemplate = z.infer<typeof insertTemplateSchema>;



// Keep original integrations table for backward compatibility with detailed provider info
export const integrations = pgTable("integrations", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(), // google, notion, etc.
  providerName: text("provider_name").notNull(), // Display name for the provider
  accessToken: text("access_token"), // Encrypted access token
  refreshToken: text("refresh_token"), // Encrypted refresh token
  tokenExpiry: timestamp("token_expiry"), // When the token expires
  scope: text("scope"), // Permissions scope
  connectedAt: timestamp("connected_at").defaultNow().notNull(),
  lastSyncedAt: timestamp("last_synced_at"),
  status: text("status").default("active").notNull(), // active, expired, revoked
  settings: jsonb("settings").default({}), // Provider-specific settings
});

// Integrations relations
export const integrationsRelations = relations(integrations, ({ one }) => ({
  user: one(users, {
    fields: [integrations.userId],
    references: [users.id],
  }),
}));

// Insert schema for Integration
export const insertIntegrationSchema = createInsertSchema(integrations).omit({
  id: true,
  connectedAt: true, 
  lastSyncedAt: true,
});

export type Integration = typeof integrations.$inferSelect;
export type InsertIntegration = z.infer<typeof insertIntegrationSchema>;

// Progress Trackers table
export const progressTrackers = pgTable("progress_trackers", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  category: text("category").default("general").notNull(),
  currentValue: integer("current_value").notNull().default(0),
  targetValue: integer("target_value").notNull(),
  unit: text("unit").default(""), // e.g., "kg", "steps", "hours", etc.
  startDate: timestamp("start_date").defaultNow().notNull(),
  endDate: timestamp("end_date"),
  color: text("color").default("#00e0ff"),
  favorite: boolean("favorite").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Progress Trackers relations
export const progressTrackerRelations = relations(progressTrackers, ({ one }) => ({
  user: one(users, {
    fields: [progressTrackers.userId],
    references: [users.id],
  }),
}));

// Insert schema for Progress Tracker
export const insertProgressTrackerSchema = createInsertSchema(progressTrackers).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type ProgressTracker = typeof progressTrackers.$inferSelect;
export type InsertProgressTracker = z.infer<typeof insertProgressTrackerSchema>;

// Kanban Board table
export const kanbanBoards = pgTable("kanban_boards", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  isDefault: boolean("is_default").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Kanban Column table
export const kanbanColumns = pgTable("kanban_columns", {
  id: serial("id").primaryKey(),
  boardId: integer("board_id").notNull().references(() => kanbanBoards.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  status: text("status").notNull(), // unique identifier for the column
  order: integer("order").notNull(), // position in the board
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Kanban Task table
export const kanbanTasks = pgTable("kanban_tasks", {
  id: serial("id").primaryKey(),
  boardId: integer("board_id").notNull().references(() => kanbanBoards.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status").notNull(), // Matches column status
  priority: text("priority").notNull().default("medium"), // low, medium, high
  startDate: text("start_date"),
  dueDate: text("due_date"),
  tags: text("tags").array(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Board relations
export const kanbanBoardRelations = relations(kanbanBoards, ({ one, many }) => ({
  user: one(users, {
    fields: [kanbanBoards.userId],
    references: [users.id],
  }),
  columns: many(kanbanColumns),
  tasks: many(kanbanTasks),
}));

// Column relations
export const kanbanColumnRelations = relations(kanbanColumns, ({ one }) => ({
  board: one(kanbanBoards, {
    fields: [kanbanColumns.boardId],
    references: [kanbanBoards.id],
  }),
}));

// Task relations
export const kanbanTaskRelations = relations(kanbanTasks, ({ one }) => ({
  board: one(kanbanBoards, {
    fields: [kanbanTasks.boardId],
    references: [kanbanBoards.id],
  }),
}));

// Insert schemas
export const insertKanbanBoardSchema = createInsertSchema(kanbanBoards).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertKanbanColumnSchema = createInsertSchema(kanbanColumns).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertKanbanTaskSchema = createInsertSchema(kanbanTasks).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type KanbanBoard = typeof kanbanBoards.$inferSelect;
export type InsertKanbanBoard = z.infer<typeof insertKanbanBoardSchema>;

export type KanbanColumn = typeof kanbanColumns.$inferSelect;
export type InsertKanbanColumn = z.infer<typeof insertKanbanColumnSchema>;

export type KanbanTask = typeof kanbanTasks.$inferSelect;
export type InsertKanbanTask = z.infer<typeof insertKanbanTaskSchema>;

// Media Albums table
export const mediaAlbums = pgTable("media_albums", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  coverImageId: integer("cover_image_id"),
  isSmartAlbum: boolean("is_smart_album").default(false).notNull(),
  smartAlbumRules: jsonb("smart_album_rules"), // Rules for automatically populating smart albums
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Media Items table (photos and videos)
export const mediaItems = pgTable("media_items", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  albumId: integer("album_id").references(() => mediaAlbums.id),
  fileName: text("file_name").notNull(),
  fileType: text("file_type").notNull(), // 'image' or 'video'
  mimeType: text("mime_type").notNull(), // 'image/jpeg', 'image/png', 'video/mp4', etc.
  fileUrl: text("file_url"), // URL to the stored file (S3 or similar)
  fileData: text("file_data"), // For base64 encoded images if not using external storage
  filePath: text("file_path"), // Local path if stored on server
  thumbnailUrl: text("thumbnail_url"), // Small thumbnail for preview
  title: text("title"),
  description: text("description"),
  tags: text("tags").array(),
  isFavorite: boolean("is_favorite").default(false).notNull(),
  dateTaken: timestamp("date_taken"),
  location: jsonb("location"), // { latitude, longitude, placeName }
  metadata: jsonb("metadata"), // Camera info, dimensions, etc.
  size: integer("size"), // File size in bytes
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Media Relations
export const mediaItemsRelations = relations(mediaItems, ({ one }) => ({
  user: one(users, {
    fields: [mediaItems.userId],
    references: [users.id],
  }),
  album: one(mediaAlbums, {
    fields: [mediaItems.albumId],
    references: [mediaAlbums.id],
  }),
}));

export const mediaAlbumsRelations = relations(mediaAlbums, ({ one, many }) => ({
  user: one(users, {
    fields: [mediaAlbums.userId],
    references: [users.id],
  }),
  items: many(mediaItems),
}));

// Insert schemas for media
export const insertMediaItemSchema = createInsertSchema(mediaItems).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertMediaAlbumSchema = createInsertSchema(mediaAlbums).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Media types
export type MediaItem = typeof mediaItems.$inferSelect;
export type InsertMediaItem = z.infer<typeof insertMediaItemSchema>;

export type MediaAlbum = typeof mediaAlbums.$inferSelect;
export type InsertMediaAlbum = z.infer<typeof insertMediaAlbumSchema>;

// ===============================
// AI Chat Conversations & Messages
// ===============================

export const conversations = pgTable("conversations", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  deletedAt: timestamp("deleted_at"),
});

export const messages = pgTable("messages", {
  id: serial("id").primaryKey(),
  conversationId: integer("conversation_id").notNull().references(() => conversations.id, { onDelete: "cascade" }),
  role: text("role").notNull(), // "user" or "assistant"
  content: text("content").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertConversationSchema = createInsertSchema(conversations).omit({
  id: true,
  createdAt: true,
});

export const insertMessageSchema = createInsertSchema(messages).omit({
  id: true,
  createdAt: true,
});

export type Conversation = typeof conversations.$inferSelect;
export type InsertConversation = z.infer<typeof insertConversationSchema>;
export type Message = typeof messages.$inferSelect;
export type InsertMessage = z.infer<typeof insertMessageSchema>;

export const dismissedKnowledge = pgTable("dismissed_knowledge", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  author: text("author").notNull(),
  sourceMaterial: text("source_material"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertDismissedKnowledgeSchema = createInsertSchema(dismissedKnowledge).omit({
  id: true,
  createdAt: true,
});

export type DismissedKnowledge = typeof dismissedKnowledge.$inferSelect;
export type InsertDismissedKnowledge = z.infer<typeof insertDismissedKnowledgeSchema>;

export const visionGoals = pgTable("vision_goals", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  category: text("category").notNull(), // 'legacy', '10year', '5year', '18month', '90day'
  title: text("title").notNull(),
  description: text("description"),
  rewardText: text("reward_text"),
  bonusXp: integer("bonus_xp").default(0).notNull(),
  completed: boolean("completed").default(false).notNull(),
  completedAt: timestamp("completed_at"),
  disconnectedMissionIds: integer("disconnected_mission_ids").array(),
  displayOrder: integer("display_order").default(0).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertVisionGoalSchema = createInsertSchema(visionGoals).omit({
  id: true,
  createdAt: true,
  completedAt: true,
  disconnectedMissionIds: true,
});

export type VisionGoal = typeof visionGoals.$inferSelect;
export type InsertVisionGoal = z.infer<typeof insertVisionGoalSchema>;

export const userCategories = pgTable("user_categories", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  value: text("value").notNull(),
  label: text("label").notNull(),
  description: text("description"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertUserCategorySchema = createInsertSchema(userCategories).omit({
  id: true,
  createdAt: true,
});

export type UserCategory = typeof userCategories.$inferSelect;
export type InsertUserCategory = z.infer<typeof insertUserCategorySchema>;

export const ritualGroups = pgTable("ritual_groups", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  value: text("value").notNull(),
  label: text("label").notNull(),
  description: text("description"),
  parentGroupValue: text("parent_group_value"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertRitualGroupSchema = createInsertSchema(ritualGroups).omit({
  id: true,
  createdAt: true,
});

export type RitualGroup = typeof ritualGroups.$inferSelect;
export type InsertRitualGroup = z.infer<typeof insertRitualGroupSchema>;

export const widgetStates = pgTable("widget_states", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id).unique(),
  states: jsonb("states").notNull().default({}),
});

export const insertWidgetStatesSchema = createInsertSchema(widgetStates).omit({
  id: true,
});

export type WidgetStates = typeof widgetStates.$inferSelect;
export type InsertWidgetStates = z.infer<typeof insertWidgetStatesSchema>;

export const userActivityEvents = pgTable("user_activity_events", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  eventType: text("event_type").notNull(),
  occurredAt: timestamp("occurred_at").notNull().defaultNow(),
  metadata: jsonb("metadata"),
});

export const insertUserActivityEventSchema = createInsertSchema(userActivityEvents).omit({
  id: true,
  occurredAt: true,
});

export type UserActivityEvent = typeof userActivityEvents.$inferSelect;
export type InsertUserActivityEvent = z.infer<typeof insertUserActivityEventSchema>;

export const smartReminders = pgTable("smart_reminders", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  reminderType: text("reminder_type").notNull(),
  enabled: boolean("enabled").notNull().default(true),
  source: text("source").notNull().default("default"),
  preferredHour: integer("preferred_hour").notNull().default(9),
  preferredDays: text("preferred_days").array().notNull().default(["mon", "tue", "wed", "thu", "fri", "sat", "sun"]),
  cooldownHours: integer("cooldown_hours").notNull().default(20),
  lastSentAt: timestamp("last_sent_at"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
}, (table) => [
  uniqueIndex("smart_reminders_user_type_idx").on(table.userId, table.reminderType),
]);

export const insertSmartReminderSchema = createInsertSchema(smartReminders).omit({
  id: true,
  createdAt: true,
});

export type SmartReminder = typeof smartReminders.$inferSelect;
export type InsertSmartReminder = z.infer<typeof insertSmartReminderSchema>;

export const missionViews = pgTable("mission_views", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  viewType: text("view_type").notNull(),
  filters: jsonb("filters").default({}),
  columns: jsonb("columns").default([]),
  sortBy: text("sort_by"),
  sortDirection: text("sort_direction"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const missionViewsRelations = relations(missionViews, ({ one }) => ({
  user: one(users, {
    fields: [missionViews.userId],
    references: [users.id],
  }),
}));

export const insertMissionViewSchema = createInsertSchema(missionViews).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type MissionView = typeof missionViews.$inferSelect;
export type InsertMissionView = z.infer<typeof insertMissionViewSchema>;

export const waitlistEmails = pgTable("waitlist_emails", {
  id: serial("id").primaryKey(),
  email: text("email").notNull().unique(),
  referralSource: text("referral_source"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertWaitlistEmailSchema = createInsertSchema(waitlistEmails).omit({
  id: true,
  createdAt: true,
});

export type WaitlistEmail = typeof waitlistEmails.$inferSelect;
export type InsertWaitlistEmail = z.infer<typeof insertWaitlistEmailSchema>;
