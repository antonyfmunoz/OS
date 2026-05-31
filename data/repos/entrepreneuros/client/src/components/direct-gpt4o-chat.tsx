import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { callLLM } from "@/lib/llmApi";

export function DirectGPT4OChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant", content: string }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    // Add user message to UI
    setMessages(prev => [...prev, { role: "user", content: input }]);
    
    // Clear input field
    const userMessage = input;
    setInput("");
    
    // Set loading state
    setIsLoading(true);
    
    try {
      // Call the LLM API
      const aiResponse = await callLLM(userMessage);
      
      // Add AI response to messages
      setMessages(prev => [...prev, { role: "assistant", content: aiResponse }]);
    } catch (error) {
      console.error("Error calling LLM:", error);
      toast({
        title: "Error",
        description: "Failed to get a response from GPT-4o. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Format conversation for display
  const conversationText = messages.map((msg, index) => (
    <div key={index} className={`my-2 p-3 rounded-lg ${msg.role === "user" ? "bg-blue-50 ml-10" : "bg-gray-50 mr-10"}`}>
      <div className="font-medium mb-1">{msg.role === "user" ? "You" : "GPT-4o"}</div>
      <div className="whitespace-pre-wrap">{msg.content}</div>
    </div>
  ));

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="h-6 w-6 rounded-full bg-emerald-500 flex items-center justify-center text-white">
            <i className="ri-robot-line text-sm"></i>
          </span>
          GPT-4o Direct Chat
        </CardTitle>
      </CardHeader>
      
      <CardContent className="flex-grow overflow-auto mb-4">
        {conversationText.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-center p-4">
            <div>
              <div className="mb-2 text-4xl">🤖</div>
              <p>Start a conversation with OpenAI's GPT-4o model.</p>
              <p className="text-sm mt-1">This chat uses a direct connection to OpenAI's API.</p>
            </div>
          </div>
        ) : (
          conversationText
        )}
      </CardContent>
      
      <CardFooter className="pt-2 border-t">
        <div className="flex w-full gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            className="flex-grow"
          />
          <Button onClick={handleSendMessage} disabled={isLoading || !input.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send"}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}