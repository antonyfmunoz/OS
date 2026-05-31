import { useState, useEffect, useRef } from "react";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Drawer, DrawerContent, DrawerTrigger, DrawerClose } from "@/components/ui/drawer";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { sendMessageToAgent } from "@/lib/openai";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { callLLM } from "@/lib/llmApi";
import { useToast } from "@/hooks/use-toast";
import { AIModelSelector } from "@/components/ai-model-selector";
import { AIModelConfig, AIModelProvider, AIModelName } from "@/hooks/use-ai-models";
import { useRequestAIKeys } from "@/hooks/use-ai-api-keys";
import { ApiKeyDialog } from "@/components/api-key-dialog";
import { CreateAgentModal } from "@/components/create-agent-modal";
import { cn } from "@/lib/utils";
import { Settings, Info, Clipboard, Bot, Sparkles, Trash2 } from "lucide-react";
import { Link } from "wouter";

type Agent = {
  id: string;
  name: string;
  role: string;
  icon: string;
  instructions: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
};

type Task = {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in-progress" | "done";
};

type AgentChatProps = {
  params?: { agentId: string }
};

export default function AgentChat({ params }: AgentChatProps) {
  const agentId = params?.agentId || "";
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiModelConfig, setAIModelConfig] = useState<AIModelConfig>({ 
    provider: "anthropic", 
    modelName: "claude-haiku-4-5" 
  });
  const [aiSelectorOpen, setAiSelectorOpen] = useState(false);
  const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false);
  const [requiredApiProviders, setRequiredApiProviders] = useState<AIModelProvider[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState<{ id: string, title: string, messages: Message[] }[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const { requestKeys } = useRequestAIKeys();

  const { data: agent } = useQuery<Agent>({
    queryKey: [`/api/agents/${agentId}`],
    enabled: !!agentId, // Only run query if agentId exists
  });

  const { data: messages = [], refetch: refetchMessages } = useQuery<Message[]>({
    queryKey: [`/api/agents/${agentId}/messages`],
    enabled: !!agentId, // Only run query if agentId exists
  });

  const { data: tasks = [] } = useQuery<Task[]>({
    queryKey: [`/api/agents/${agentId}/tasks`],
    enabled: !!agentId, // Only run query if agentId exists
  });
  
  // Fetch all agents, but only to find the Executive Agent
  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ['/api/agents'],
  });
  
  // Find the Executive Agent from the fetched agents
  const executiveAgent = agents.find(a => a.role === 'executive') || agents[0];

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      setIsLoading(true);
      // Check if we're in direct GPT-4o mode (no agent selected or direct GPT-4o toggle is on)
      if (!agentId || agentId === "direct-claude") {
        try {
          // Use our direct llmApi with the selected model
          const aiResponse = await callLLM(message, aiModelConfig.modelName);
          return aiResponse;
        } catch (err) {
          console.error("Error calling direct GPT-4o:", err);
          throw err;
        }
      } else {
        // Use the regular agent response system
        const response = await sendMessageToAgent(agentId, message, aiModelConfig || null);
        return response;
      }
    },
    onSuccess: (response) => {
      // Show toast notification when AI response is complete
      const responder = !agentId || agentId === "direct-claude" ? "Claude" : (agent?.name || "Agent");
      toast({
        title: `${responder} responded`,
        description: response.substring(0, 60) + (response.length > 60 ? "..." : ""),
      });
      
      setMessage("");
      refetchMessages();
      setIsLoading(false);
    },
    onError: (error) => {
      // Display appropriate error messages based on the error type
      const errorObj = error as any;
      
      // For API quota exceeded errors
      if (error.message.includes("quota") || error.message.includes("rate limit")) {
        toast({
          title: "Rate Limit",
          description: "Too many requests. Please wait a moment and try again.",
          variant: "destructive",
        });
        
        if (aiModelConfig.modelName === "claude-sonnet-4-5") {
          setAIModelConfig({
            ...aiModelConfig,
            modelName: "claude-haiku-4-5"
          });
          
          toast({
            title: "Model Changed",
            description: "Switched to Haiku for faster responses.",
          });
        }
      }
      else if (error.message.includes("key") || error.message.includes("API key")) {
        toast({
          title: "AI Configuration Issue",
          description: "The AI service is not properly configured. Please contact support.",
          variant: "destructive",
        });
      }
      // For rate limiting
      else if (error.message.includes("rate limit") || error.message.includes("too many requests")) {
        toast({
          title: "Rate Limit Exceeded",
          description: "You've sent too many requests. Please wait a moment before trying again.",
          variant: "destructive",
        });
      }
      // Only show toast for critical errors, not AI-related ones
      else if (!error.message.includes("API") && !error.message.includes("AI")) {
        toast({
          title: "Error sending message",
          description: error.message,
          variant: "destructive",
        });
      }
      
      console.error("Message error:", error);
      setIsLoading(false);
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: async (taskData: { title: string; description: string }) => {
      const res = await apiRequest("POST", "/api/tasks", {
        ...taskData,
        agentId,
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/agents/${agentId}/tasks`] });
      // No toast for task creation
    },
  });

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize and group messages into conversations
  useEffect(() => {
    if (agent) {
      // Always have a current conversation
      const currentConversation = {
        id: "current",
        title: `Today's Chat with ${agent?.name || "Agent"} - ${new Date().toLocaleDateString()}`,
        messages: messages || []
      };
      
      // If this is a first load and we have no conversations yet, just set the current one
      if (conversations.length === 0) {
        setConversations([currentConversation]);
        setActiveConversationId("current");
        return;
      }
      
      // Update the current conversation with latest messages
      const updatedConversations = conversations.map(conv => 
        conv.id === "current" ? currentConversation : conv
      );
      
      // If the current conversation doesn't exist yet, add it
      if (!updatedConversations.some(conv => conv.id === "current")) {
        updatedConversations.unshift(currentConversation);
      }
      
      setConversations(updatedConversations);
      
      // If no active conversation is selected, default to current
      if (!activeConversationId) {
        setActiveConversationId("current");
      }
    }
  }, [messages, agent]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  // Handle opening a conversation
  const handleOpenConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    // In a real app, you would fetch the conversation's messages from the server here
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;
    
    try {
      // If no custom AI model is selected, we'll use the default (OpenAI)
      const providers: AIModelProvider[] = [aiModelConfig.provider];
      
      // Check if we have the required API keys
      const hasKeys = await requestKeys(providers);
      
      if (!hasKeys) {
        // Set required providers and open the API key dialog
        setRequiredApiProviders(providers);
        setApiKeyDialogOpen(true);
        return;
      }
      
      // Store the user message locally first for immediate UI update
      const userMessage: Message = {
        id: `user_${Date.now()}`,
        role: "user",
        content: message,
        timestamp: new Date().toISOString()
      };
      
      // Add to message cache immediately for UI responsiveness
      queryClient.setQueryData([`/api/agents/${agentId}/messages`], (oldData: Message[] = []) => [
        ...oldData,
        userMessage
      ]);
      
      // Then send the message to the API
      sendMessageMutation.mutate(message);
    } catch (error) {
      console.error("Error in handleSendMessage:", error);
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Layout title={agentId === "direct-claude" ? "Claude Chat" : (agent?.name || "Agent Chat")}>
      <div className="flex h-full overflow-hidden -mt-6 -mx-6">
        {/* API Key Dialog */}
        <ApiKeyDialog 
          isOpen={apiKeyDialogOpen} 
          onClose={() => {
            setApiKeyDialogOpen(false);
            if (message.trim()) {
              sendMessageMutation.mutate(message);
            }
          }}
          providers={requiredApiProviders} 
        />
        
        {/* Toggle Sidebar Button - Only visible when sidebar is collapsed, positioned at the edge */}
        {sidebarCollapsed && (
          <div className="h-full w-10 border-r border-gray-200 flex flex-col items-center py-4 bg-gray-50">
            <Button 
              variant="ghost" 
              size="icon" 
              className="rounded-md mt-2"
              onClick={() => setSidebarCollapsed(false)}
            >
              <i className="ri-menu-line"></i>
            </Button>
          </div>
        )}
        
        {/* Left Sidebar - ChatGPT Style */}
        <div className={cn(
          "border-r border-gray-200 flex flex-col bg-gray-50 overflow-hidden transition-all duration-300",
          sidebarCollapsed ? "w-0 opacity-0" : "w-64 opacity-100"
        )}>
          {/* Sidebar Header */}
          <div className="p-4 flex justify-between items-center border-b border-gray-200">
            <div className="flex items-center w-full gap-2">
              {/* New Agent Button */}
              <Button 
                variant="outline" 
                size="sm" 
                className="flex justify-start items-center gap-1 w-1/2 py-1 h-8"
                onClick={() => setIsModalOpen(true)}
              >
                <Bot size={14} />
                <span className="text-xs font-medium">New Agent</span>
              </Button>

              {/* New Chat Button */}
              <Button 
                variant="outline" 
                size="sm" 
                className="flex justify-start items-center gap-1 w-1/2 py-1 h-8"
                onClick={async () => {
                  try {
                    // First, create a history entry from current conversation if it has messages
                    if (messages.length > 0) {
                      // Generate a unique ID for the current conversation moving to history
                      const pastConvId = `past_${Date.now()}`;
                      
                      // Create a history entry with the current messages
                      const pastConversation = {
                        id: pastConvId,
                        title: `Chat with ${agent?.name || "Agent"} - ${new Date().toLocaleDateString()}`,
                        messages: [...messages] // Store a copy of the current messages
                      };
                      
                      // Add the past conversation to history
                      const currentConversations = [...conversations];
                      
                      // Remove current conversation if it exists
                      const existingHistory = currentConversations.filter(c => c.id !== "current");
                      
                      // Create new empty current conversation
                      const newCurrentConversation = {
                        id: "current",
                        title: `Today's Chat with ${agent?.name || "Agent"} - ${new Date().toLocaleDateString()}`,
                        messages: [] // Empty message array
                      };
                      
                      // Update with new order: current first, then new archive, then existing history
                      setConversations([
                        newCurrentConversation, 
                        pastConversation, 
                        ...existingHistory
                      ]);
                    }
                    
                    // Set active conversation to the new empty one
                    setActiveConversationId("current");
                    
                    // Clear input field
                    setMessage("");
                    
                    // Scroll to bottom
                    scrollToBottom();
                    
                    // Clear the server-side messages
                    await apiRequest("POST", `/api/agents/${agentId}/clear-messages`);
                    
                    // Clear the messages in the React Query cache so it won't be reloaded
                    queryClient.setQueryData([`/api/agents/${agentId}/messages`], []);
                    
                    // Refetch to refresh any state
                    refetchMessages();
                    
                  } catch (error) {
                    console.error("Error creating new chat:", error);
                  }
                }}
              >
                <i className="ri-add-line text-sm" />
                <span className="text-xs font-medium">New Chat</span>
              </Button>
            </div>
            <Drawer>
              <DrawerTrigger asChild>
                <span className="hidden">Hidden Trigger</span>
              </DrawerTrigger>
              <DrawerContent className="p-4 max-w-sm mx-auto">
                <div className="space-y-4">
                  <div className="flex items-center">
                    <div className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center mr-4">
                      <i className={`${agent?.icon || "ri-robot-line"} text-xl`}></i>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">{agent?.name || "Agent"}</h3>
                      <Badge variant="outline">{agent?.role || "Assistant"}</Badge>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium mb-2">Agent Instructions</h4>
                    <p className="text-sm text-gray-600 border border-gray-200 rounded-md p-3 bg-gray-50">
                      {agent?.instructions || "This agent will help you with tasks and answer questions."}
                    </p>
                  </div>

                  {tasks.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">Active Tasks</h4>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {tasks.map(task => (
                          <div key={task.id} className="text-sm p-2 border border-gray-200 rounded-md">
                            <div className="flex justify-between">
                              <span className="font-medium">{task.title}</span>
                              <Badge variant="outline" className="ml-2">
                                {task.status === "todo" ? "To Do" : 
                                task.status === "in-progress" ? "In Progress" : 
                                "Done"}
                              </Badge>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">{task.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <DrawerClose asChild>
                    <Button className="w-full">Close</Button>
                  </DrawerClose>
                </div>
              </DrawerContent>
            </Drawer>
          </div>
          
          {/* Agent Chats List */}
          <div className="flex-1 overflow-y-auto py-2">
            {/* All Agents */}
            <div className="px-3 py-2">
              <h3 className="text-xs font-medium text-gray-500 mb-2">YOUR AGENTS</h3>
              <div className="space-y-1">
                {agents.map((agentItem) => (
                  <Link key={agentItem.id} href={`/chat/${agentItem.id}`}>
                    <div className={cn(
                      "flex items-center gap-3 p-3 rounded-md cursor-pointer",
                      agentId === agentItem.id ? "bg-primary/10 text-primary" : "hover:bg-gray-100 text-gray-700"
                    )}>
                      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                        <i className={agentItem.icon || "ri-robot-line"}></i>
                      </div>
                      <div className="flex-1 truncate">
                        <div className="text-sm font-medium">{agentItem.name}</div>
                        <div className="text-xs text-gray-500 truncate">
                          {agentItem.role === "executive" ? "Chief Executive Officer" : 
                           agentItem.role === "assistant" ? "Executive Assistant" : 
                           agentItem.role === "marketing" ? "Marketing Director" :
                           agentItem.role === "operations" ? "Operations Manager" :
                           agentItem.role === "content" ? "Content Strategist" :
                           agentItem.role === "support" ? "Support Specialist" :
                           agentItem.role}
                        </div>
                      </div>
                      {(agentItem.id === "agent_executive" || agentItem.role === "assistant") && (
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-6 w-6 rounded-full ml-1"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            window.location.href = `/agent-programming/${agentItem.id}`;
                          }}
                        >
                          <Info size={14} />
                        </Button>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
            
            {/* Current Conversation */}
            <div className="px-3 py-2">
              <h3 className="text-xs font-medium text-gray-500 mb-2">CURRENT CHAT</h3>
              <div className="space-y-1">
                {/* Active Conversation */}
                {conversations.length > 0 && (
                  <div 
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-md cursor-pointer",
                      activeConversationId === "current" ? "bg-primary/10 text-primary" : "hover:bg-gray-100 text-gray-700"
                    )}
                    onClick={() => handleOpenConversation("current")}
                  >
                    <Bot size={18} />
                    <div className="flex-1 truncate">
                      <div className="text-sm font-medium">Current Chat</div>
                      <div className="text-xs text-gray-500 truncate">
                        {messages.length > 0 
                          ? messages[messages.length - 1].content.slice(0, 30) + "..." 
                          : "Start a new conversation"}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
          {/* Previous conversations */}
            <div className="px-3 py-2">
              <h3 className="text-xs font-medium text-gray-500 mb-2">CONVERSATION HISTORY</h3>
              <div className="space-y-1">
                {conversations.length > 1 ? (
                  // Show past conversations (skip the current one, which is at index 0)
                  conversations.slice(1).map((conversation) => (
                    <div 
                      key={conversation.id}
                      className={cn(
                        "text-xs p-3 rounded-md cursor-pointer transition-colors",
                        activeConversationId === conversation.id ? "bg-primary/10 text-primary" : "hover:bg-gray-100 text-gray-700"
                      )}
                      onClick={() => handleOpenConversation(conversation.id)}
                    >
                      <div className="flex flex-col gap-2 mt-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className={cn(
                            "text-gray-500",
                            activeConversationId === conversation.id ? "text-primary/80" : ""
                          )}>
                            {conversation.title.split(' - ')[1]} {/* Just the date part */}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-4 w-4 rounded-sm p-0"
                            onClick={(e) => {
                              e.stopPropagation(); // Prevent opening the conversation
                              
                              // Remove this conversation from history
                              const updatedConversations = conversations.filter(c => c.id !== conversation.id);
                              setConversations(updatedConversations);
                              
                              // If this was the active conversation, switch to current
                              if (activeConversationId === conversation.id) {
                                setActiveConversationId("current");
                              }
                              
                              // No toast for conversation deletion
                            }}
                          >
                            <Trash2 size={10} className="text-gray-400 hover:text-red-500" />
                          </Button>
                        </div>
                        <div className={cn(
                          "text-xs",
                          activeConversationId === conversation.id ? "text-primary/80" : "text-gray-600"
                        )}>
                          {conversation.messages && conversation.messages.length > 0 
                            ? conversation.messages[0].content.substring(0, 40) + "..."
                            : "Empty conversation"}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-500 italic p-3">
                    No conversation history yet
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Settings Footer */}
          {/* AI Model Settings button removed as requested */}
          <div className="border-t border-gray-200 p-3">
            <div className="flex flex-col space-y-1">
              {/* Settings have been moved to the model selector dropdown in the chat interface */}
            </div>
          </div>
        </div>
        
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-white">
          {/* Chat Header */}
          <div className="border-b border-gray-200 p-4 flex items-center justify-between">
            <div className="flex items-center">
              {!sidebarCollapsed && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="mr-2"
                  onClick={() => setSidebarCollapsed(true)}
                >
                  <i className="ri-menu-line"></i>
                </Button>
              )}
              <div>
                <h1 className="font-medium text-lg">
                  {agent ? agent.name : "Agent Chat"}
                </h1>
                {activeConversationId !== "current" && conversations.find(c => c.id === activeConversationId) && (
                  <div className="text-xs text-gray-500 flex items-center gap-1">
                    <i className="ri-history-line"></i>
                    Viewing: {conversations.find(c => c.id === activeConversationId)?.title || "Past Conversation"}
                    <Button 
                      variant="link" 
                      size="sm" 
                      className="h-auto p-0 text-xs text-primary" 
                      onClick={() => handleOpenConversation("current")}
                    >
                      Return to current chat
                    </Button>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {aiModelConfig && (
                <Badge variant="outline" className="gap-1.5">
                  <Sparkles size={14} className="text-amber-500" />
                  {aiModelConfig.provider === "openai" ? "OpenAI" :
                   aiModelConfig.provider === "anthropic" ? "Claude" :
                   aiModelConfig.provider === "perplexity" ? "Perplexity" :
                   aiModelConfig.provider === "xai" ? "Grok" : 
                   aiModelConfig.provider}
                </Badge>
              )}
              
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  createTaskMutation.mutate({
                    title: "New task",
                    description: "Task suggested by agent"
                  });
                }}
              >
                <i className="ri-add-line mr-1"></i> Add Task
              </Button>
            </div>
          </div>
          
          {/* Chat Header with Model Selector */}
          <div className="border-b border-gray-200 p-4 flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center mr-3">
                <i className={agentId === "direct-claude" ? "ri-robot-2-line text-primary" : (agent?.icon || "ri-robot-line text-primary")}></i>
              </div>
              <div>
                <h2 className="text-base font-medium">{agentId === "direct-claude" ? "Claude Chat" : (agent?.name || "Agent Chat")}</h2>
                <p className="text-xs text-gray-500">
                  {agentId === "direct-claude" 
                    ? `Using ${aiModelConfig.modelName === "claude-sonnet-4-5" ? "Sonnet (deep thinking)" : "Haiku (fast)"}` 
                    : agent?.role === "executive" 
                      ? "Chief Executive Agent" 
                      : agent?.role === "assistant" 
                        ? "Assistant Agent" 
                        : agent?.role || "AI Assistant"}
                </p>
              </div>
            </div>
            
            {/* Model selector dropdown */}
            <div className="flex items-center">
              <div className="relative">
                <select 
                  className="text-sm border border-gray-200 rounded-md pl-8 pr-3 py-1.5 bg-white appearance-none shadow-sm focus:border-primary focus:ring-1 focus:ring-primary cursor-pointer pointer-events-auto z-10 relative"
                  value={agentId}
                  onChange={(e) => {
                    const selectedId = e.target.value;
                    window.location.href = `/chat/${selectedId}`;
                  }}
                >
                  <option value="direct-claude">Claude Direct</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                <div className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
                  <i className={agentId === "direct-claude" ? "ri-robot-2-line" : "ri-user-line"}></i>
                </div>
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
                  <i className="ri-arrow-down-s-line"></i>
                </div>
              </div>
            </div>
          </div>

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 md:px-8 space-y-8">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                  <Bot size={32} className="text-primary" />
                </div>
                {agentId === "direct-claude" ? (
                  <>
                    <h2 className="text-xl font-medium">Hello! I'm Claude</h2>
                    <p className="text-gray-500 max-w-md">
                      I'm your AI assistant powered by Anthropic's Claude. Simple questions use Haiku for fast responses, 
                      and complex tasks automatically escalate to Sonnet for deeper thinking.
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="text-xl font-medium">Hello! I'm {agent?.name || "your AI assistant"}</h2>
                    <p className="text-gray-500 max-w-md">
                      {agent?.instructions 
                        ? `I'm here to ${agent.instructions.toLowerCase().slice(0, 60)}...` 
                        : "How can I help you today? Feel free to ask me anything."}
                    </p>
                  </>
                )}
              </div>
            ) : (
              // Show messages from the active conversation
              (activeConversationId === "current" ? messages : 
                conversations.find(c => c.id === activeConversationId)?.messages || messages)
                .map((message) => (
                <div 
                  key={message.id} 
                  className={cn(
                    "relative group max-w-3xl mx-auto",
                    message.role === "user" ? "text-right" : "border-l-4 border-l-primary/20 pl-4"
                  )}
                >
                  <div className="flex items-start">
                    {message.role !== "user" && (
                      <div className="w-9 h-9 flex-shrink-0 rounded-full bg-primary/20 mr-4 flex items-center justify-center">
                        <i className={cn(`${agentId === "direct-claude" ? "ri-robot-2-line" : (agent?.icon || "ri-robot-line")} text-primary`)}></i>
                      </div>
                    )}
                    
                    <div className="flex-1">
                      <div className="mb-1 text-xs font-medium text-gray-500">
                        {message.role === "user" ? "You" : agentId === "direct-claude" ? "Claude" : (agent?.name || "Assistant")}
                      </div>
                      <div className={cn(
                        "prose prose-sm max-w-none",
                        message.role === "user" ? "text-left" : ""
                      )}>
                        {message.content}
                      </div>
                    </div>
                    
                    {message.role === "user" && (
                      <div className="w-9 h-9 flex-shrink-0 rounded-full bg-primary/20 ml-4 flex items-center justify-center">
                        <i className="ri-user-line text-primary"></i>
                      </div>
                    )}
                  </div>
                  
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute right-0 top-0 flex items-center space-x-2">
                    <Button variant="ghost" size="icon" className="w-7 h-7">
                      <Clipboard size={14} />
                    </Button>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input Area - ChatGPT style */}
          <div className="p-4 pb-8">
            <div className="mx-auto max-w-3xl">
              <form onSubmit={handleSendMessage} className="relative">
                <div className="border border-gray-300 rounded-xl overflow-hidden shadow-sm focus-within:ring-2 focus-within:ring-primary focus-within:border-primary">
                  <div className="flex">
                    <Textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage(e);
                        }
                      }}
                      placeholder={activeConversationId !== "current" 
                        ? "Viewing past conversation... Return to current chat to send messages" 
                        : agentId === "direct-claude"
                          ? "Message Claude..."
                          : `Message ${agent?.name || "your agent"}...`}
                      disabled={isLoading || activeConversationId !== "current"}
                      className="border-0 rounded-none shadow-none focus-visible:ring-0 text-base py-6 min-h-[60px] max-h-[200px] resize-none pointer-events-auto"
                    />
                    <Button 
                      type="submit" 
                      disabled={isLoading || !message.trim() || activeConversationId !== "current"}
                      className="rounded-none bg-transparent hover:bg-transparent mr-2 self-end mb-2 pointer-events-auto cursor-pointer"
                      size="icon"
                      onClick={(e) => {
                        if (!isLoading && message.trim() && activeConversationId === "current") {
                          handleSendMessage(e);
                        }
                      }}
                    >
                      {isLoading ? (
                        <i className="ri-loader-4-line animate-spin text-primary"></i>
                      ) : (
                        <i className="ri-send-plane-fill text-primary hover:text-primary/80"></i>
                      )}
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between items-center mt-2">
                  <div className="flex items-center">
                    {agentId === "direct-claude" && (
                      <div className="relative mr-2">
                        <select 
                          className="text-xs border border-gray-200 rounded-md pl-6 pr-8 py-1 bg-white appearance-none shadow-sm focus:border-primary focus:ring-1 focus:ring-primary cursor-pointer pointer-events-auto"
                          value={aiModelConfig.modelName}
                          onChange={(e) => {
                            const selectedModel = e.target.value as AIModelName;
                            const provider: AIModelProvider = "anthropic";
                            setAIModelConfig({ provider, modelName: selectedModel });
                          }}
                        >
                          <option value="claude-haiku-4-5">Haiku (Fast)</option>
                          <option value="claude-sonnet-4-5">Sonnet (Deep Thinking)</option>
                        </select>
                        <div className="absolute left-1.5 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
                          <i className="ri-ai-generate text-xs"></i>
                        </div>
                        <div className="absolute right-1.5 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none">
                          <i className="ri-arrow-down-s-line text-xs"></i>
                        </div>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 flex-1 text-center">
                    {agentId === "direct-claude" 
                      ? `Using Claude ${aiModelConfig.modelName === "claude-sonnet-4-5" ? "Sonnet - deep thinking mode" : "Haiku - fast responses"}`
                      : `${agent?.name || "The agent"} helps with ${agent?.role || "tasks"} based on current knowledge`}
                  </p>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
      
      {/* Create Agent Modal */}
      <CreateAgentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </Layout>
  );
}