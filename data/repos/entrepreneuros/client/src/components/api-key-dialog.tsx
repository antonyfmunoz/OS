import { useState } from "react";
import { AIModelProvider } from "@/hooks/use-ai-models";
import { useAIApiKeyStatus } from "@/hooks/use-ai-api-keys";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

interface ApiKeyDialogProps {
  isOpen: boolean;
  onClose: () => void;
  providers: AIModelProvider[];
}

const formSchema = z.object({
  keys: z.record(z.string().min(1, "API key is required")),
});

export function ApiKeyDialog({ isOpen, onClose, providers }: ApiKeyDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { refetch } = useAIApiKeyStatus();
  const { toast } = useToast();
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      keys: providers.reduce((acc, provider) => {
        acc[provider] = "";
        return acc;
      }, {} as Record<string, string>),
    },
  });
  
  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setIsSubmitting(true);
    
    try {
      const savePromises = Object.entries(values.keys).map(async ([provider, key]) => {
        const keyName = getKeyName(provider as AIModelProvider);
        
        if (!key || !keyName) return;
        
        await apiRequest("POST", "/api/keys/save", {
          keyName,
          value: key,
        });
      });
      
      await Promise.all(savePromises);
      
      // Refresh API key status
      await refetch();
      
      toast({
        title: "API keys saved",
        description: "Your API keys have been saved successfully.",
      });
      
      onClose();
    } catch (error) {
      toast({
        title: "Failed to save API keys",
        description: error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const getKeyName = (provider: AIModelProvider): string => {
    switch (provider) {
      case "openai": return "OPENAI_API_KEY";
      case "anthropic": return "ANTHROPIC_API_KEY";
      case "perplexity": return "PERPLEXITY_API_KEY";
      case "xai": return "XAI_API_KEY";
      case "gemini": return "GEMINI_API_KEY";
      default: return "";
    }
  };
  
  const getProviderName = (provider: AIModelProvider): string => {
    switch (provider) {
      case "openai": return "OpenAI";
      case "anthropic": return "Anthropic (Claude)";
      case "perplexity": return "Perplexity";
      case "xai": return "xAI (Grok)";
      case "gemini": return "Google Gemini";
      default: return provider;
    }
  };
  
  const getProviderDescription = (provider: AIModelProvider): string => {
    switch (provider) {
      case "openai": 
        return "Required for GPT-4o. Get your API key from OpenAI.";
      case "anthropic": 
        return "Required for Claude models. Get your API key from Anthropic.";
      case "perplexity": 
        return "Required for Perplexity models. Get your API key from Perplexity AI.";
      case "xai": 
        return "Required for Grok models. Get your API key from X.AI.";
      case "gemini": 
        return "Required for Gemini models. Get your API key from Google AI Studio.";
      default: 
        return "";
    }
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add API Keys</DialogTitle>
          <DialogDescription>
            Add your API keys to use the selected AI providers.
          </DialogDescription>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
            {providers.map((provider) => (
              <FormField
                key={provider}
                control={form.control}
                name={`keys.${provider}`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{getProviderName(provider)}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={`Enter your ${getProviderName(provider)} API key`}
                        type="password"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      {getProviderDescription(provider)}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ))}
            
            <DialogFooter className="pt-4">
              <Button 
                type="button" 
                variant="secondary" 
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button 
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Saving..." : "Save Keys"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}