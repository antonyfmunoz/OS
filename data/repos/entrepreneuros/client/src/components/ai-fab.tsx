import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sparkles, Send, X, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { format } from "date-fns";
import { AiMessage as Message } from "@shared/schema";

// Use this type if the schema import doesn't work
// type Message = {
//   id: string;
//   role: "user" | "assistant";
//   content: string;
//   timestamp: string;
// };

export function AiFab() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const queryClient = useQueryClient();

  // Fetch AI messages
  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: ["/api/ai-assistant/messages"],
    // If the endpoint doesn't exist, we'll gracefully handle it
    enabled: isOpen,
    staleTime: 10000,
    refetchOnWindowFocus: false,
    retry: false
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      // This will 404 if the endpoint doesn't exist yet, but the frontend will still work
      const res = await apiRequest("POST", "/api/ai-assistant/messages", { content });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/ai-assistant/messages"] });
      setInputValue("");
    },
    onError: (error) => {
      console.error("Error sending message:", error);
      // Add a simulated response if the API isn't implemented yet
      const simulatedResponse: Partial<Message> = {
        id: `msg_${Date.now()}`,
        role: "assistant",
        content: "The AI assistant is not fully implemented yet. Please check back later!",
        // Convert string to Date for schema compatibility
        timestamp: new Date(),
      };
      queryClient.setQueryData(["/api/ai-assistant/messages"], 
        (oldData: Message[] = []) => [...oldData, simulatedResponse as Message]);
    }
  });

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    
    // Add optimistic update
    const optimisticMessage: Partial<Message> = {
      id: `temp_${Date.now()}`,
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };
    
    queryClient.setQueryData(["/api/ai-assistant/messages"], 
      (oldData: Message[] = []) => [...oldData, optimisticMessage as Message]);
    
    sendMessageMutation.mutate(inputValue);
  };

  return (
    <>
      {/* Floating Button */}
      <Button
        className={cn(
          "fixed bottom-6 right-6 rounded-full w-12 h-12 shadow-lg z-50",
          "flex items-center justify-center",
          isOpen ? "bg-red-500 hover:bg-red-600" : "bg-primary hover:bg-primary/90"
        )}
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={20} /> : <Sparkles size={20} />}
      </Button>

      {/* AI Assistant Panel */}
      {isOpen && (
        <Card className="fixed bottom-20 right-6 w-80 lg:w-96 shadow-lg z-40 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles size={16} className="text-primary" />
              AI Assistant
            </CardTitle>
          </CardHeader>
          
          <CardContent className="p-3">
            <div className="h-64 overflow-y-auto space-y-3 mb-3 pr-2">
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground text-sm p-4">
                  How can I help you today?
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "p-3 rounded-lg max-w-[85%]",
                      message.role === "user"
                        ? "bg-primary/10 ml-auto"
                        : "bg-muted mr-auto"
                    )}
                  >
                    <div className="text-sm whitespace-pre-wrap">
                      {message.content}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {format(new Date(message.timestamp), "h:mm a")}
                    </div>
                  </div>
                ))
              )}
              {sendMessageMutation.isPending && (
                <div className="flex justify-center p-2">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>
          </CardContent>
          
          <CardFooter className="p-3 pt-0">
            <form onSubmit={handleSubmit} className="flex w-full gap-2">
              <Input
                placeholder="Ask a question..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="flex-1"
              />
              <Button 
                type="submit" 
                size="icon"
                disabled={sendMessageMutation.isPending || !inputValue.trim()}
              >
                <Send size={16} />
              </Button>
            </form>
          </CardFooter>
        </Card>
      )}
    </>
  );
}