import { useState, useEffect } from "react";
import type { AIModelProvider, AIModelName, AIModelConfig, AIModelInfo } from "@/hooks/use-ai-models";
import { useAIModels } from "@/hooks/use-ai-models";
import { useAIApiKeyStatus } from "@/hooks/use-ai-api-keys";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

interface AIModelSelectorProps {
  onSelectModel: (config: AIModelConfig | null) => void;
  defaultProvider?: AIModelProvider;
  defaultModel?: AIModelName;
}

export function AIModelSelector({ 
  onSelectModel,
  defaultProvider = "anthropic",
  defaultModel = "claude-haiku-4-5"
}: AIModelSelectorProps) {
  const { models, isLoading } = useAIModels();
  const { providerStatus } = useAIApiKeyStatus();
  
  const [selectedProvider, setSelectedProvider] = useState<AIModelProvider>(defaultProvider);
  const [selectedModel, setSelectedModel] = useState<AIModelName>(defaultModel);
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxTokens, setMaxTokens] = useState<number>(1024);
  
  // Reset selection if the models change
  useEffect(() => {
    const currentProviderModels = models.find((p: AIModelInfo) => p.provider === selectedProvider);
    
    // Reset model selection if the current model isn't available in the new provider
    if (currentProviderModels && 
        !currentProviderModels.models.some((m: { name: AIModelName }) => m.name === selectedModel)) {
      setSelectedModel(currentProviderModels.models[0]?.name || defaultModel);
    }
  }, [models, selectedProvider, selectedModel, defaultModel]);
  
  const handleProviderChange = (provider: AIModelProvider) => {
    setSelectedProvider(provider);
    // Set the default model for the selected provider
    const providerModels = models.find(p => p.provider === provider);
    if (providerModels && providerModels.models.length > 0) {
      setSelectedModel(providerModels.models[0].name);
    }
  };
  
  const handleModelChange = (model: AIModelName) => {
    setSelectedModel(model);
  };
  
  const handleSubmit = () => {
    onSelectModel({
      provider: selectedProvider,
      modelName: selectedModel,
      temperature,
      maxTokens
    });
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Select AI Model</h3>
      
      <Tabs defaultValue={selectedProvider} onValueChange={(value) => handleProviderChange(value as AIModelProvider)}>
        <TabsList className="grid grid-cols-5 h-9">
          <TabsTrigger 
            value="openai" 
            className="text-xs py-0" 
            disabled={!models.find((p: AIModelInfo) => p.provider === "openai")?.isAvailable}
          >
            OpenAI
            {!models.find((p: AIModelInfo) => p.provider === "openai")?.isAvailable && (
              <Badge variant="outline" className="ml-1 text-xs">Unavailable</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger 
            value="anthropic" 
            className="text-xs py-0" 
            disabled={!models.find((p: AIModelInfo) => p.provider === "anthropic")?.isAvailable}
          >
            Claude
            {!models.find((p: AIModelInfo) => p.provider === "anthropic")?.isAvailable && (
              <Badge variant="outline" className="ml-1 text-xs">Unavailable</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger 
            value="perplexity" 
            className="text-xs py-0" 
            disabled={!models.find((p: AIModelInfo) => p.provider === "perplexity")?.isAvailable}
          >
            Perplexity
            {!models.find((p: AIModelInfo) => p.provider === "perplexity")?.isAvailable && (
              <Badge variant="outline" className="ml-1 text-xs">Unavailable</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger 
            value="xai" 
            className="text-xs py-0" 
            disabled={!models.find((p: AIModelInfo) => p.provider === "xai")?.isAvailable}
          >
            Grok
            {!models.find((p: AIModelInfo) => p.provider === "xai")?.isAvailable && (
              <Badge variant="outline" className="ml-1 text-xs">Unavailable</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger 
            value="gemini" 
            className="text-xs py-0" 
            disabled={!models.find((p: AIModelInfo) => p.provider === "gemini")?.isAvailable}
          >
            Gemini
            {!models.find((p: AIModelInfo) => p.provider === "gemini")?.isAvailable && (
              <Badge variant="outline" className="ml-1 text-xs">Unavailable</Badge>
            )}
          </TabsTrigger>
        </TabsList>
        
        {Object.keys(providerStatus).length > 0 && !providerStatus[selectedProvider] && (
          <Alert variant="destructive" className="mt-2 py-2">
            <AlertDescription>
              API key required. Add an API key to use this model.
            </AlertDescription>
          </Alert>
        )}
        
        {models.map((provider) => (
          <TabsContent key={provider.provider} value={provider.provider} className="space-y-4 mt-2">
            <div className="space-y-2">
              <label className="text-xs text-gray-500">Model</label>
              <Select 
                value={selectedModel} 
                onValueChange={(value) => handleModelChange(value as AIModelName)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {provider.models.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      <div className="flex flex-col">
                        <span>{model.name}</span>
                        <span className="text-xs text-gray-500">{model.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-xs text-gray-500">Temperature</label>
                <span className="text-xs font-medium">{temperature.toFixed(1)}</span>
              </div>
              <Slider
                value={[temperature]}
                min={0}
                max={1}
                step={0.1}
                onValueChange={(values) => setTemperature(values[0])}
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>More precise</span>
                <span>More creative</span>
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-xs text-gray-500">Max Tokens</label>
                <span className="text-xs font-medium">{maxTokens}</span>
              </div>
              <Slider
                value={[maxTokens]}
                min={256}
                max={4096}
                step={256}
                onValueChange={(values) => setMaxTokens(values[0])}
              />
            </div>
          </TabsContent>
        ))}
      </Tabs>
      
      <div className="flex justify-end gap-2 pt-2">
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => onSelectModel(null)}
        >
          Cancel
        </Button>
        <Button 
          size="sm" 
          onClick={handleSubmit}
          disabled={Object.keys(providerStatus).length > 0 && !providerStatus[selectedProvider]}
        >
          Select Model
        </Button>
      </div>
    </div>
  );
}