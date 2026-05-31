import pg from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import bcrypt from 'bcrypt';
import * as schema from '../shared/schema';
import { eq } from 'drizzle-orm';

const { Pool } = pg;

async function seedDemoUser() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  const db = drizzle({ client: pool, schema });

  const DEMO_EMAIL = 'alex.chen@demo.lyfeos.com';
  const DEMO_PASSWORD = 'demo123456';
  const DEMO_USERNAME = 'AlexChen';

  const existing = await db.select().from(schema.users).where(eq(schema.users.email, DEMO_EMAIL));
  if (existing.length > 0) {
    console.log('Demo user already exists, cleaning up...');
    const userId = existing[0].id;
    await db.delete(schema.quests).where(eq(schema.quests.userId, userId));
    await db.delete(schema.userDailyLogs).where(eq(schema.userDailyLogs.userId, userId));
    await db.delete(schema.visionGoals).where(eq(schema.visionGoals.userId, userId));
    await db.delete(schema.userProfile).where(eq(schema.userProfile.userId, userId));
    await db.delete(schema.userStats).where(eq(schema.userStats.userId, userId));
    await db.delete(schema.userIntegrations).where(eq(schema.userIntegrations.userId, userId));
    await db.delete(schema.aiMessages).where(eq(schema.aiMessages.userId, userId));
    await db.delete(schema.users).where(eq(schema.users.id, userId));
    console.log('Cleaned up existing demo user');
  }

  const hashedPassword = await bcrypt.hash(DEMO_PASSWORD, 10);

  const [user] = await db.insert(schema.users).values({
    username: DEMO_USERNAME,
    password: hashedPassword,
    email: DEMO_EMAIL,
    displayName: 'Alex Chen',
    firstName: 'Alex',
    lastName: 'Chen',
    bio: 'Building a creative studio while mastering the craft of storytelling.',
    avatarColor: '#00e0ff',
    title: 'ARCHITECT',
    authProvider: 'email',
    termsAccepted: true,
    emailVerified: true,
  }).returning();

  console.log('Created demo user:', user.id);

  await db.insert(schema.userStats).values({
    userId: user.id,
    timeTokensCurrent: 72,
    timeTokensMax: 100,
    energyPointsCurrent: 85,
    energyPointsMax: 100,
    healthPointsCurrent: 91,
    healthPointsMax: 100,
    attentionTokensCurrent: 64,
    attentionTokensMax: 100,
    experienceCurrent: 4250,
    experienceMax: 5500,
    level: 12,
    streakDays: 18,
    lastActiveDate: new Date().toISOString().split('T')[0],
    efficiencyScore: 76,
    primaryColor: '#00e0ff',
  });

  await db.insert(schema.userProfile).values({
    userId: user.id,
    ageRange: '25-34',
    archetypePrimary: 'Architect',
    archetypeSecondary: 'Creator',
    archetypeShadow: 'Oracle',
    archetypeScores: { warrior: 6, architect: 9, creator: 8, monarch: 5, oracle: 7, alchemist: 4 },
    primaryInstincts: ['Strategic Planning', 'Pattern Recognition', 'Creative Execution'],
    keyDrivers: ['Mastery', 'Impact', 'Freedom'],
    coreBelief: 'I build systems that outlast me.',
    primaryValues: ['Discipline', 'Creativity', 'Integrity'],
    supportingValues: ['Growth', 'Autonomy', 'Excellence'],
    lifeStage: 'Building',
    desiredEmotion: 'Flow',
    vision90Day: 'Launch the first version of my creative studio website and secure 3 clients.',
    vision18Month: 'Build a 6-figure creative studio with a 3-person team.',
    vision5Year: 'Run a globally recognized creative studio known for premium storytelling.',
    vision10Year: 'Create a media company that shapes culture through original content.',
    lifeDomains: ['Career', 'Health', 'Creativity', 'Relationships', 'Finance'],
    currentGoals: ['Launch studio website', 'Daily fitness routine', 'Read 2 books per month'],
    characterAffirmation: `Alex Chen is a builder at heart — methodical, creative, and relentlessly focused on impact. As a primary Architect with Creator tendencies, Alex approaches life as a system to be designed and optimized. Every morning begins with intention: a workout to sharpen the body, journaling to sharpen the mind, and a strategic review of the day's missions.\n\nAlex's core belief — "I build systems that outlast me" — drives everything. From the creative studio being built from the ground up, to the daily habits that compound over time, every action feeds a larger vision. The 90-day target is clear: launch the studio, land 3 clients, prove the model.\n\nDiscipline, creativity, and integrity are the non-negotiable values. Alex doesn't chase trends — Alex builds foundations. The shadow pattern of over-planning is acknowledged but managed through action-forcing deadlines and accountability systems.\n\nIn 5 years, Alex sees a globally recognized creative studio. In 10, a media company that shapes culture. These aren't daydreams — they're engineering blueprints. Every mission completed, every log filed, every stat tracked is a data point in a larger experiment: how to build a life that matters.`,
    onboardingMission: 8,
    onboardingStep: 0,
    onboardingCompleted: true,
    completedOnboardingMissions: [0, 1, 2, 3, 4, 5, 6, 7],
    totalXP: 4250,
    strengths: ['Strategic thinking', 'Creative direction', 'Systems design'],
    weaknesses: ['Over-planning', 'Delegation', 'Impatience'],
    primaryCraft: 'Creative Direction & Brand Strategy',
    primaryCraftWhy: 'It combines my love of storytelling with my need to build something tangible.',
    morningRituals: ['Cold shower', 'Journal for 10 min', 'Review daily missions'],
    eveningRituals: ['Reflection log', 'Read for 30 min', 'Plan tomorrow'],
    idealDay: 'Wake 6AM, workout, deep work 8-12, meetings 1-3, creative work 3-6, evening routine.',
  });

  await db.insert(schema.userIntegrations).values({
    userId: user.id,
  });

  const today = new Date();
  const missions = [
    { title: 'Morning workout — 30 min strength training', description: 'Complete a 30-minute strength training session focused on upper body.', category: 'health', completed: true, completedAt: new Date(), energyCost: 3, attentionCost: 1, timeCost: 2, experienceReward: 35, difficulty: 'C', isRitualized: true, repeatFrequency: 'daily' },
    { title: 'Write studio landing page copy', description: 'Draft compelling copy for the hero section and about page of the creative studio website.', category: 'career', completed: true, completedAt: new Date(today.getTime() - 86400000), energyCost: 4, attentionCost: 3, timeCost: 3, experienceReward: 50, difficulty: 'B' },
    { title: 'Client proposal — Meridian Brands', description: 'Prepare and send a detailed project proposal to Meridian Brands for their rebrand.', category: 'career', completed: false, energyCost: 5, attentionCost: 4, timeCost: 4, experienceReward: 75, difficulty: 'A' },
    { title: 'Read 30 pages of "Thinking in Systems"', description: 'Continue reading Donella Meadows\'s book on systems thinking. Take notes on key concepts.', category: 'learning', completed: true, completedAt: new Date(), energyCost: 2, attentionCost: 3, timeCost: 2, experienceReward: 25, difficulty: 'D', isRitualized: true, repeatFrequency: 'daily' },
    { title: 'Design mood board for Apex project', description: 'Create a visual mood board with typography, color palette, and reference imagery for the Apex brand identity project.', category: 'creativity', completed: false, energyCost: 3, attentionCost: 4, timeCost: 3, experienceReward: 45, difficulty: 'B' },
    { title: 'Weekly financial review', description: 'Review income, expenses, and cash flow for the week. Update budget tracker.', category: 'finance', completed: true, completedAt: new Date(today.getTime() - 172800000), energyCost: 2, attentionCost: 2, timeCost: 1, experienceReward: 20, difficulty: 'D' },
    { title: 'Meditate — 15 min breathwork', description: 'Complete a guided breathwork session for focus and calm.', category: 'mindfulness', completed: true, completedAt: new Date(), energyCost: 1, attentionCost: 1, timeCost: 1, experienceReward: 15, difficulty: 'D', isRitualized: true, repeatFrequency: 'daily' },
    { title: 'Portfolio case study — NovaTech rebrand', description: 'Write up the NovaTech rebrand as a detailed case study for the studio portfolio.', category: 'career', completed: false, energyCost: 5, attentionCost: 5, timeCost: 4, experienceReward: 80, difficulty: 'A' },
    { title: 'Meal prep for the week', description: 'Prepare meals for Mon-Fri. Focus on high-protein, balanced nutrition.', category: 'health', completed: true, completedAt: new Date(today.getTime() - 259200000), energyCost: 3, attentionCost: 1, timeCost: 3, experienceReward: 30, difficulty: 'C' },
    { title: 'Draft email newsletter #4', description: 'Write and schedule the fourth issue of the studio newsletter on creative process.', category: 'creativity', completed: false, energyCost: 3, attentionCost: 3, timeCost: 2, experienceReward: 40, difficulty: 'C' },
    { title: 'Networking — reach out to 3 contacts', description: 'Send personalized messages to 3 potential collaborators or clients.', category: 'relationships', completed: true, completedAt: new Date(today.getTime() - 86400000), energyCost: 2, attentionCost: 2, timeCost: 1, experienceReward: 25, difficulty: 'C' },
    { title: 'Review and update OKRs for Q1', description: 'Evaluate progress on quarterly objectives and adjust key results as needed.', category: 'strategy', completed: false, energyCost: 4, attentionCost: 4, timeCost: 2, experienceReward: 55, difficulty: 'B' },
    { title: 'Evening reflection journal', description: 'Write reflections on today\'s wins, lessons, and areas for improvement.', category: 'mindfulness', completed: true, completedAt: new Date(), energyCost: 1, attentionCost: 2, timeCost: 1, experienceReward: 15, difficulty: 'D', isRitualized: true, repeatFrequency: 'daily' },
    { title: 'Deep work block — brand strategy for Apex', description: 'Focused 2-hour deep work session on the Apex brand strategy framework.', category: 'career', completed: false, energyCost: 5, attentionCost: 5, timeCost: 5, experienceReward: 90, difficulty: 'S' },
    { title: 'Run 5K — outdoor cardio', description: 'Complete a 5K run outdoors for cardiovascular health and mental clarity.', category: 'health', completed: true, completedAt: new Date(today.getTime() - 172800000), energyCost: 4, attentionCost: 1, timeCost: 2, experienceReward: 35, difficulty: 'C' },
    { title: 'Studio branding — finalize logo concepts', description: 'Narrow down to 3 logo concepts and prepare presentation for feedback.', category: 'creativity', completed: true, completedAt: new Date(today.getTime() - 345600000), energyCost: 4, attentionCost: 4, timeCost: 3, experienceReward: 60, difficulty: 'A' },
  ];

  for (const m of missions) {
    await db.insert(schema.quests).values({
      userId: user.id,
      title: m.title,
      description: m.description,
      category: m.category,
      completed: m.completed,
      completedAt: m.completedAt || null,
      energyCost: m.energyCost,
      attentionCost: m.attentionCost,
      timeCost: m.timeCost,
      experienceReward: m.experienceReward,
      difficulty: m.difficulty,
      isRitualized: m.isRitualized || false,
      repeatFrequency: m.repeatFrequency || null,
      startDate: today.toISOString().split('T')[0],
    });
  }
  console.log(`Inserted ${missions.length} missions`);

  const dailyLogs = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    const mental = Math.floor(Math.random() * 3) + 6;
    const physical = Math.floor(Math.random() * 3) + 6;
    const emotional = Math.floor(Math.random() * 3) + 5;
    dailyLogs.push({
      userId: user.id,
      date: dateStr,
      yesterdayXp: Math.floor(Math.random() * 150) + 100,
      todayPrimaryMission: ['Write studio copy', 'Client proposal', 'Deep work block', 'Portfolio case study', 'Design mood board'][i % 5],
      mentalState: mental,
      physicalState: physical,
      emotionalState: emotional,
      wakeTime: '06:00',
      sleepTime: '22:30',
      gratitude: ['Grateful for creative momentum today.', 'Thankful for a productive deep work session.', 'Appreciating the progress on the studio launch.', 'Grateful for health and energy.'][i % 4],
      wentWell: ['Completed all daily rituals.', 'Great client call.', 'Solid writing session.', 'Hit a new personal record on the run.'][i % 4],
      couldBeBetter: ['Could have started deep work earlier.', 'Need to improve delegation.', 'Spent too long on email.'][i % 3],
      learned: ['Systems thinking applies to brand strategy.', 'Consistency beats intensity.', 'Saying no creates space for better yeses.'][i % 3],
    });
  }
  await db.insert(schema.userDailyLogs).values(dailyLogs);
  console.log(`Inserted ${dailyLogs.length} daily logs`);

  const goals = [
    { category: '90day', title: 'Launch creative studio website', description: 'Complete design, copy, and deployment of the studio website.', completed: false, displayOrder: 0, rewardText: 'Celebrate with a nice dinner out', bonusXp: 200 },
    { category: '90day', title: 'Secure 3 paying clients', description: 'Close 3 brand strategy or creative direction projects.', completed: false, displayOrder: 1, rewardText: 'New monitor upgrade', bonusXp: 300 },
    { category: '90day', title: 'Establish morning ritual streak of 30 days', description: 'Complete the full morning ritual (workout, journal, review) for 30 consecutive days.', completed: true, completedAt: new Date(today.getTime() - 432000000), displayOrder: 2, bonusXp: 100 },
    { category: '18month', title: 'Build a 6-figure creative studio', description: 'Reach $100K ARR with a lean 3-person team.', completed: false, displayOrder: 0, bonusXp: 500 },
    { category: '18month', title: 'Publish 12 newsletter issues', description: 'Write and publish a monthly newsletter on creative process and brand building.', completed: false, displayOrder: 1, bonusXp: 150 },
    { category: '5year', title: 'Globally recognized creative studio', description: 'Build a studio known internationally for premium storytelling and brand strategy.', completed: false, displayOrder: 0, bonusXp: 500 },
    { category: '10year', title: 'Launch a media company', description: 'Create a media company that shapes culture through original content and storytelling.', completed: false, displayOrder: 0, bonusXp: 500 },
    { category: 'legacy', title: 'Change how people tell their stories', description: 'Leave a lasting impact on how individuals and brands communicate their identity.', completed: false, displayOrder: 0, bonusXp: 500 },
  ];

  for (const g of goals) {
    await db.insert(schema.visionGoals).values({
      userId: user.id,
      category: g.category,
      title: g.title,
      description: g.description,
      completed: g.completed,
      completedAt: g.completedAt || null,
      displayOrder: g.displayOrder,
      rewardText: g.rewardText || null,
      bonusXp: g.bonusXp,
    });
  }
  console.log(`Inserted ${goals.length} vision goals`);

  const aiMsgs = [
    { sender: 'ai', content: "Welcome back, Alex. Your streak is at 18 days — impressive consistency. You have 6 active missions today. I'd recommend starting with your deep work block on the Apex brand strategy while your attention tokens are highest. Want me to break it down into sub-tasks?" },
    { sender: 'user', content: "Yeah, help me plan out the Apex deep work session." },
    { sender: 'ai', content: "Here's a focused plan for your 2-hour Apex session:\n\n1. **Review brief & research** (20 min) — Revisit client brief, competitor analysis, and mood board\n2. **Brand positioning** (30 min) — Draft the positioning statement and key differentiators\n3. **Visual direction** (40 min) — Define color palette, typography, and visual language\n4. **Strategy deck outline** (30 min) — Structure the presentation flow\n\nThis aligns with your Architect archetype — systematic and thorough. Shall I set a timer for each block?" },
    { sender: 'user', content: "That's perfect. Also, how am I tracking on my 90-day goals?" },
    { sender: 'ai', content: "Here's your 90-day progress:\n\n✅ **Morning ritual streak** — Complete! 30 days locked in.\n🔄 **Launch studio website** — Copy is drafted, design is 70% done. You're on track if you maintain this week's pace.\n🔄 **Secure 3 clients** — 1 closed (NovaTech), 1 in proposal stage (Meridian), 1 pipeline lead. You need to close Meridian and convert one more.\n\nOverall you're at 60% completion with 45 days remaining. Your efficiency score of 76 tells me you're using your resources well. Keep the momentum." },
  ];

  for (const msg of aiMsgs) {
    await db.insert(schema.aiMessages).values({
      userId: user.id,
      sender: msg.sender,
      content: msg.content,
    });
  }
  console.log(`Inserted ${aiMsgs.length} AI messages`);

  console.log('\n✅ Demo user seeded successfully!');
  console.log(`Email: ${DEMO_EMAIL}`);
  console.log(`Username: ${DEMO_USERNAME}`);

  await pool.end();
}

seedDemoUser().catch(console.error);
