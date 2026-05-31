import { useState, useEffect } from "react";
import { Layout } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Loader2 } from "lucide-react";

// Types for agents and tasks
type Agent = {
  id: string;
  name: string;
  role: string;
  icon: string;
  instructions: string;
};

type Task = {
  id: string;
  title: string;
  description: string;
  status: string;
  agentId?: string;
};

export default function AgentOSDashboard() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [input, setInput] = useState("");
  const [memory, setMemory] = useState("");
  const { toast } = useToast();

  // Fetch agents
  const { data: agents = [], isLoading: agentsLoading } = useQuery<Agent[]>({
    queryKey: ['/api/agents'],
  });

  // Fetch tasks
  const { data: tasks = [], isLoading: tasksLoading } = useQuery<Task[]>({
    queryKey: ['/api/tasks'],
  });

  // Fetch messages for the selected agent
  const { data: messages = [], refetch: refetchMessages } = useQuery({
    queryKey: [`/api/agents/${selectedAgent?.id}/messages`],
    enabled: !!selectedAgent?.id,
  });

  // Create agent mutation
  const createAgentMutation = useMutation({
    mutationFn: async (agent: { name: string; role: string; instructions: string }) => {
      const res = await apiRequest("POST", "/api/agents", {
        ...agent,
        icon: "ri-robot-line"
      });
      return await res.json();
    },
    onSuccess: () => {
      toast({
        title: "Agent created",
        description: "New agent has been successfully created",
      });
      queryClient.invalidateQueries({ queryKey: ['/api/agents'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create agent",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Create task mutation
  const createTaskMutation = useMutation({
    mutationFn: async (task: { title: string; description: string; agentId?: string }) => {
      const res = await apiRequest("POST", "/api/tasks", {
        ...task,
        status: "todo",
        priority: "medium"
      });
      return await res.json();
    },
    onSuccess: () => {
      toast({
        title: "Task created",
        description: "New task has been successfully added",
      });
      queryClient.invalidateQueries({ queryKey: ['/api/tasks'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create task",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Send message to agent mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!selectedAgent) throw new Error("No agent selected");
      const res = await apiRequest("POST", `/api/agents/${selectedAgent.id}/chat`, { message });
      return await res.json();
    },
    onSuccess: () => {
      setInput("");
      refetchMessages();
      // Refetch memory/messages and reset input
      toast({
        title: "Message sent",
        description: "Agent is processing your message",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to send message",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleAgentCreate = () => {
    const name = prompt("Agent Name?");
    if (!name) return;
    
    const role = prompt("Agent Role?", "assistant");
    if (!role) return;
    
    const instructions = prompt("Instructions?", "Help the user with their tasks");
    if (!instructions) return;
    
    createAgentMutation.mutate({ name, role, instructions });
  };

  const handleTaskAdd = () => {
    const title = prompt("Task Title");
    if (!title) return;
    
    const description = prompt("Task Description", "");
    
    createTaskMutation.mutate({ 
      title, 
      description: description || "", 
      agentId: selectedAgent?.id 
    });
  };

  const handleSendMessage = () => {
    if (!input.trim()) return;
    sendMessageMutation.mutate(input);
  };

  // Update memory when selected agent or messages change
  useEffect(() => {
    if (messages && Array.isArray(messages) && messages.length > 0) {
      const formattedMemory = messages
        .map((msg: any) => `${msg.role === 'user' ? 'User' : 'AI'}: ${msg.content}`)
        .join('\n\n');
      setMemory(formattedMemory);
    } else {
      setMemory("");
    }
  }, [messages, selectedAgent]);

  const isLoading = agentsLoading || tasksLoading || 
                   createAgentMutation.isPending || 
                   createTaskMutation.isPending ||
                   sendMessageMutation.isPending;

  return (
    <Layout title="AgentOS Dashboard">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-2">
        {/* Sidebar */}
        <div className="col-span-1 bg-card p-4 rounded-lg">
          <h2 className="text-xl font-bold mb-2">Agents</h2>
          <Button onClick={handleAgentCreate} className="mb-3 w-full" disabled={isLoading}>
            {isLoading && createAgentMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            + New Agent
          </Button>
          
          {agentsLoading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : agents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center p-4">No agents yet. Create one to get started.</p>
          ) : (
            <div className="space-y-2">
              {agents.map((agent) => (
                <Card 
                  key={agent.id} 
                  className={`cursor-pointer hover:bg-accent transition-colors ${selectedAgent?.id === agent.id ? 'border-primary' : ''}`}
                  onClick={() => setSelectedAgent(agent)}
                >
                  <CardContent className="p-3 flex items-center">
                    <i className={`${agent.icon || 'ri-robot-line'} mr-2`}></i>
                    <div>
                      <div className="font-medium">{agent.name}</div>
                      <div className="text-xs text-muted-foreground">{agent.role}</div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Main Chat + Task View */}
        <div className="col-span-1 md:col-span-3 space-y-4">
          {selectedAgent ? (
            <>
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold">{selectedAgent.name} Workspace</h2>
                {isLoading && !createAgentMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
              </div>
              
              <div className="border rounded-lg p-2">
                <div className="text-sm font-medium mb-2">Memory & Conversation History</div>
                <Textarea 
                  value={memory} 
                  readOnly
                  className="min-h-[200px] bg-muted/50" 
                />
              </div>

              <div className="flex gap-2">
                <Input 
                  value={input} 
                  onChange={(e) => setInput(e.target.value)} 
                  placeholder="Ask something..." 
                  disabled={sendMessageMutation.isPending || !selectedAgent}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <Button 
                  onClick={handleSendMessage}
                  disabled={sendMessageMutation.isPending || !input.trim()}
                >
                  {sendMessageMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send"}
                </Button>
              </div>

              <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Task Board</h3>
                  <Button onClick={handleTaskAdd} disabled={createTaskMutation.isPending}>
                    {createTaskMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    + Add Task
                  </Button>
                </div>
                
                {tasksLoading ? (
                  <div className="flex justify-center p-4">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : tasks.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center p-4">No tasks yet. Add one to get started.</p>
                ) : (
                  <div className="space-y-2">
                    {tasks.map((task) => (
                      <Card key={task.id} className="mb-2">
                        <CardContent className="p-3">
                          <div className="flex justify-between">
                            <div>
                              <div className="font-medium">{task.title}</div>
                              <div className="text-sm text-muted-foreground">{task.description}</div>
                            </div>
                            <div className="text-xs px-2 py-1 rounded-full bg-muted">
                              {task.status}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                <i className="ri-robot-line text-4xl text-primary"></i>
              </div>
              <h2 className="text-xl font-medium">Select or create an agent to begin</h2>
              <p className="text-muted-foreground max-w-md">
                Choose an agent from the sidebar or create a new one to start interacting with the AgentOS platform.
              </p>
              <Button onClick={handleAgentCreate} className="mt-4">Create Your First Agent</Button>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}