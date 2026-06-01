import { Header } from "@/components/header";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PlayCircle, FileText, Bookmark, Code, ArrowLeft } from "lucide-react";
import { Link } from "wouter";

export default function TutorialsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Tutorials">
        <Button variant="ghost" size="sm" asChild className="mr-4">
          <Link href="/">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
      </Header>
      <div className="p-6 flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto">
          
          <h1 className="text-2xl font-bold mb-2">Tutorials & Learning Resources</h1>
          <p className="text-muted-foreground mb-6">
            Learn how to get the most out of AgentOS with these helpful resources.
          </p>
          
          <Tabs defaultValue="getting-started" className="mb-8">
            <TabsList className="mb-6">
              <TabsTrigger value="getting-started">Getting Started</TabsTrigger>
              <TabsTrigger value="agent-tutorials">Agent Creation</TabsTrigger>
              <TabsTrigger value="integration-guides">Integration Guides</TabsTrigger>
              <TabsTrigger value="advanced-topics">Advanced Topics</TabsTrigger>
            </TabsList>
            
            <TabsContent value="getting-started">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TutorialCard
                  title="Welcome to AgentOS"
                  description="An introduction to the platform and its core capabilities."
                  icon={<FileText className="h-5 w-5 text-blue-500" />}
                  duration="5 minutes"
                  level="Beginner"
                />
                <TutorialCard
                  title="Setting Up Your First Agent"
                  description="Learn how to create and configure your first AI agent."
                  icon={<PlayCircle className="h-5 w-5 text-green-500" />}
                  duration="10 minutes"
                  level="Beginner"
                />
                <TutorialCard
                  title="Understanding the Dashboard"
                  description="Navigate and use all the features of the AgentOS dashboard."
                  icon={<FileText className="h-5 w-5 text-blue-500" />}
                  duration="8 minutes"
                  level="Beginner"
                />
                <TutorialCard
                  title="Task Management"
                  description="Learn how to create, assign, and manage tasks for your agents."
                  icon={<PlayCircle className="h-5 w-5 text-green-500" />}
                  duration="12 minutes"
                  level="Beginner"
                />
              </div>
            </TabsContent>
            
            <TabsContent value="agent-tutorials">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TutorialCard
                  title="Creating a Marketing Agent"
                  description="Build a specialized agent to handle your marketing tasks."
                  icon={<PlayCircle className="h-5 w-5 text-green-500" />}
                  duration="15 minutes"
                  level="Intermediate"
                />
                <TutorialCard
                  title="Content Creation Agents"
                  description="Setup agents that can generate high-quality content for your business."
                  icon={<PlayCircle className="h-5 w-5 text-green-500" />}
                  duration="20 minutes"
                  level="Intermediate"
                />
                <TutorialCard
                  title="Programming Agents"
                  description="Configure sophisticated agents capable of writing and reviewing code."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="25 minutes"
                  level="Advanced"
                />
                <TutorialCard
                  title="Agent Collaboration"
                  description="Learn how to set up multiple agents that work together on complex tasks."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="30 minutes"
                  level="Advanced"
                />
              </div>
            </TabsContent>
            
            <TabsContent value="integration-guides">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TutorialCard
                  title="Integrating with Google Suite"
                  description="Connect your agents to Gmail, Google Sheets, and more."
                  icon={<FileText className="h-5 w-5 text-blue-500" />}
                  duration="15 minutes"
                  level="Intermediate"
                />
                <TutorialCard
                  title="Zapier & n8n Integration"
                  description="Automate workflows between your agents and other tools."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="20 minutes"
                  level="Intermediate"
                />
                <TutorialCard
                  title="Notion Knowledge Base Setup"
                  description="Connect your Notion workspace as a knowledge source for your agents."
                  icon={<PlayCircle className="h-5 w-5 text-green-500" />}
                  duration="18 minutes"
                  level="Intermediate"
                />
                <TutorialCard
                  title="Custom API Integrations"
                  description="Build custom integrations with any API or service."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="35 minutes"
                  level="Advanced"
                />
              </div>
            </TabsContent>
            
            <TabsContent value="advanced-topics">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TutorialCard
                  title="Creating Agent Teams"
                  description="Build hierarchical teams of agents that work together on complex projects."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="40 minutes"
                  level="Advanced"
                />
                <TutorialCard
                  title="Custom Agent Training"
                  description="Learn how to fine-tune your agents for specific business domains."
                  icon={<Code className="h-5 w-5 text-[#5e17eb]" />}
                  duration="45 minutes"
                  level="Advanced"
                />
                <TutorialCard
                  title="KPI Tracking Workflows"
                  description="Set up sophisticated KPI tracking and reporting with your agents."
                  icon={<FileText className="h-5 w-5 text-blue-500" />}
                  duration="30 minutes"
                  level="Advanced"
                />
                <TutorialCard
                  title="Agent Memory & Knowledge Management"
                  description="Advanced techniques for managing agent memory and knowledge bases."
                  icon={<Bookmark className="h-5 w-5 text-amber-500" />}
                  duration="35 minutes"
                  level="Advanced"
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

interface TutorialCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  duration: string;
  level: "Beginner" | "Intermediate" | "Advanced";
}

function TutorialCard({ title, description, icon, duration, level }: TutorialCardProps) {
  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            {icon}
            <CardTitle className="ml-2 text-lg">{title}</CardTitle>
          </div>
          <div className={`
            text-xs font-medium rounded-full px-2 py-1
            ${level === "Beginner" ? "bg-blue-100 text-blue-800" : 
              level === "Intermediate" ? "bg-amber-100 text-amber-800" : 
              "bg-[#5e17eb]/10 text-[#5e17eb]"}
          `}>
            {level}
          </div>
        </div>
        <CardDescription className="mt-2">{description}</CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="flex items-center text-sm text-muted-foreground">
          <span className="flex items-center">
            <i className="ri-time-line mr-1"></i> {duration}
          </span>
        </div>
      </CardContent>
      <CardFooter className="flex justify-end pt-2">
        <Button variant="ghost" size="sm" className="text-primary">
          View Tutorial
        </Button>
      </CardFooter>
    </Card>
  );
}