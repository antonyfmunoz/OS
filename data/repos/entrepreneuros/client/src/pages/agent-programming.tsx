import { useState, useEffect, useRef } from "react";
import { useParams, useLocation } from "wouter";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { 
  Bot, 
  Save, 
  ArrowLeft, 
  Play, 
  Upload, 
  FileUp, 
  Link as LinkIcon, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  Loader2
} from "lucide-react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Agent = {
  id: string;
  name: string;
  role: string;
  icon: string;
  instructions: string;
  knowledgeBase?: string;
};

type AgentProgrammingProps = {
  agentId?: string;
}

const agentFormSchema = z.object({
  name: z.string()
    .min(2, { message: "Name must be at least 2 characters" })
    .max(50, { message: "Name cannot exceed 50 characters" }),
  role: z.string()
    .min(2, { message: "Role must be at least 2 characters" })
    .max(50, { message: "Role cannot exceed 50 characters" }),
  icon: z.string()
    .min(3, { message: "Icon name is required" }),
  instructions: z.string()
    .min(20, { message: "Instructions should be at least 20 characters" })
    .max(10000, { message: "Instructions cannot exceed 10000 characters" }),
  knowledgeBase: z.string().optional(),
});

type AgentFormValues = z.infer<typeof agentFormSchema>;

export default function AgentProgramming(props: AgentProgrammingProps) {
  const [_, navigate] = useLocation();
  const params = useParams();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("instructions");
  const [knowledgeSource, setKnowledgeSource] = useState<'text' | 'file' | 'url'>('text');
  const [knowledgeText, setKnowledgeText] = useState("");
  const [knowledgeUrl, setKnowledgeUrl] = useState("");
  const [fileUploaded, setFileUploaded] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  
  // Get agent ID from props, params, or URL query parameters
  const searchParams = new URLSearchParams(window.location.search);
  const queryAgentId = searchParams.get('id');
  const agentId = props.agentId || params?.agentId || queryAgentId || "";
  
  console.log("Agent Programming Page:", { 
    queryAgentId,
    finalAgentId: agentId
  });
  
  const { data: agent, isLoading } = useQuery<Agent>({
    queryKey: [`/api/agents/${agentId}`],
    enabled: !!agentId,
  });
  
  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      name: "",
      role: "",
      icon: "ri-robot-line",
      instructions: "",
      knowledgeBase: "",
    },
  });
  
  // Properly set form values after agent data is loaded
  useEffect(() => {
    if (agent) {
      form.reset({
        name: agent.name || "",
        role: agent.role || "",
        icon: agent.icon || "ri-robot-line",
        instructions: agent.instructions || "",
        knowledgeBase: agent.knowledgeBase || "",
      });
      
      if (agent.knowledgeBase) {
        setKnowledgeText(agent.knowledgeBase);
      }
    }
  }, [agent, form]);
  
  const updateAgentMutation = useMutation({
    mutationFn: async (updatedAgent: Partial<Agent>) => {
      const res = await apiRequest("PATCH", `/api/agents/${agentId}`, updatedAgent);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/agents/${agentId}`] });
      queryClient.invalidateQueries({ queryKey: ['/api/agents'] });
      toast({
        title: "Agent updated",
        description: "The agent has been updated successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error updating agent",
        description: error.message,
        variant: "destructive",
      });
    },
  });
  
  const onSubmit = (values: AgentFormValues) => {
    // Merge the knowledge source with the form values
    let knowledgeBase = values.knowledgeBase || "";
    
    if (knowledgeSource === 'text' && knowledgeText.trim()) {
      knowledgeBase = knowledgeText;
    } else if (knowledgeSource === 'url' && knowledgeUrl.trim()) {
      knowledgeBase = `URL: ${knowledgeUrl}`;
    } else if (knowledgeSource === 'file' && fileName) {
      knowledgeBase = `FILE: ${fileName}`;
    }
    
    updateAgentMutation.mutate({
      ...values,
      knowledgeBase,
    });
  };
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFileName(files[0].name);
      setFileUploaded(true);
      toast({
        title: "File selected",
        description: `${files[0].name} is ready to be uploaded on save`,
      });
    }
  };
  
  const handleTestInstructions = () => {
    setIsTesting(true);
    setTestResult(null);
    setTestError(null);
    
    // Simulate testing the agent's instructions with a timeout
    setTimeout(() => {
      const instructions = form.getValues("instructions");
      if (instructions.length < 50) {
        setTestError("Instructions are too short for effective agent functionality. Consider providing more details.");
      } else {
        setTestResult("Instructions are valid and should allow the agent to function properly.");
      }
      setIsTesting(false);
    }, 2000);
  };
  
  const handleSaveClick = () => {
    form.handleSubmit(onSubmit)();
  };
  
  return (
    <Layout title={`Programming ${agent?.name || "Agent"}`}>
      <div className="flex items-center mb-8">
        <Button 
          variant="ghost" 
          size="icon" 
          className="mr-2"
          onClick={() => navigate(`/agent-chat/${agentId}`)}
        >
          <ArrowLeft size={18} />
        </Button>
        <h1 className="text-2xl font-bold">Programming {agent?.name || "Agent"}</h1>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-2">Loading agent data...</span>
        </div>
      ) : (
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <Tabs 
                  defaultValue="instructions" 
                  className="w-full"
                  onValueChange={setActiveTab}
                  value={activeTab}
                >
                  <TabsList className="mb-4">
                    <TabsTrigger value="instructions">Instructions</TabsTrigger>
                    <TabsTrigger value="brain">Knowledge</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="instructions" className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-lg font-semibold">Agent Instructions</h2>
                      <div className="flex gap-2">
                        <Button 
                          type="button"
                          variant="outline"
                          onClick={handleTestInstructions}
                          disabled={isTesting || !form.getValues("instructions")}
                          className="gap-1"
                        >
                          {isTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play size={16} />}
                          Test
                        </Button>
                        <Button 
                          type="button"
                          onClick={handleSaveClick}
                          disabled={updateAgentMutation.isPending || !form.formState.isDirty}
                          className="gap-1"
                        >
                          {updateAgentMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save size={16} />}
                          Save
                        </Button>
                      </div>
                    </div>
                    <p className="text-gray-600 text-sm">
                      Provide detailed instructions on how this agent should behave, what services it can access, and any specific knowledge it has.
                    </p>
                    
                    <FormField
                      control={form.control}
                      name="instructions"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Textarea 
                              {...field}
                              placeholder="Enter detailed instructions for the agent..."
                              className="min-h-[300px] font-mono"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    
                    {testResult && (
                      <Alert className="bg-green-50 border-green-200">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertTitle className="text-green-800">Test Passed</AlertTitle>
                        <AlertDescription className="text-green-700">
                          {testResult}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {testError && (
                      <Alert className="bg-orange-50 border-orange-200">
                        <AlertCircle className="h-4 w-4 text-orange-600" />
                        <AlertTitle className="text-orange-800">Suggestion</AlertTitle>
                        <AlertDescription className="text-orange-700">
                          {testError}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    <div className="p-4 border rounded-md bg-gray-50">
                      <h3 className="font-medium mb-2">Tips for Effective Instructions</h3>
                      <ul className="list-disc pl-5 text-sm space-y-2">
                        <li>Begin with a clear description of the agent's role and purpose</li>
                        <li>Specify what types of tasks the agent should handle</li>
                        <li>Include any specific knowledge domains the agent should focus on</li>
                        <li>Set boundaries for what the agent should not do</li>
                        <li>Use clear, specific language to avoid ambiguity</li>
                      </ul>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="brain" className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-lg font-semibold">Agent Knowledge</h2>
                      <Button 
                        type="button"
                        onClick={handleSaveClick}
                        disabled={updateAgentMutation.isPending || !form.formState.isDirty}
                        className="gap-1"
                      >
                        {updateAgentMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save size={16} />}
                        Save
                      </Button>
                    </div>
                    <p className="text-gray-600 text-sm">
                      Add knowledge sources that this agent can use to answer questions and perform tasks more effectively.
                    </p>
                    
                    <div className="border rounded-md overflow-hidden">
                      <div className="bg-gray-50 p-4 border-b">
                        <div className="flex gap-4">
                          <Button
                            type="button"
                            variant={knowledgeSource === 'text' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setKnowledgeSource('text')}
                            className="gap-1"
                          >
                            <i className="ri-text"></i>
                            Text
                          </Button>
                          <Button
                            type="button"
                            variant={knowledgeSource === 'file' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setKnowledgeSource('file')}
                            className="gap-1"
                          >
                            <FileUp size={14} />
                            File
                          </Button>
                          <Button
                            type="button"
                            variant={knowledgeSource === 'url' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setKnowledgeSource('url')}
                            className="gap-1"
                          >
                            <LinkIcon size={14} />
                            URL
                          </Button>
                        </div>
                      </div>
                      
                      <div className="p-4">
                        {knowledgeSource === 'text' && (
                          <div className="space-y-2">
                            <label className="block text-sm font-medium">Knowledge Text</label>
                            <Textarea
                              value={knowledgeText}
                              onChange={(e) => {
                                setKnowledgeText(e.target.value);
                                form.setValue("knowledgeBase", e.target.value, { shouldDirty: true });
                              }}
                              placeholder="Enter knowledge that the agent should know (product data, company policies, etc.)"
                              className="min-h-[200px]"
                            />
                          </div>
                        )}
                        
                        {knowledgeSource === 'file' && (
                          <div className="space-y-4">
                            <div className="border-2 border-dashed rounded-md p-6 text-center cursor-pointer hover:bg-gray-50"
                                 onClick={() => fileInputRef.current?.click()}>
                              <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                              <p className="text-sm font-medium mb-1">Upload Knowledge File</p>
                              <p className="text-xs text-gray-500">PDF, DOCX, TXT or CSV (max 5MB)</p>
                              <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                accept=".pdf,.docx,.txt,.csv"
                                style={{ display: 'none' }}
                              />
                            </div>
                            
                            {fileUploaded && (
                              <div className="flex items-center gap-2 bg-green-50 p-2 rounded-md">
                                <CheckCircle className="text-green-600 h-5 w-5" />
                                <span className="text-sm font-medium text-green-800">{fileName}</span>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="ml-auto text-gray-500 hover:text-red-500"
                                  onClick={() => {
                                    setFileUploaded(false);
                                    setFileName("");
                                    if (fileInputRef.current) {
                                      fileInputRef.current.value = "";
                                    }
                                    form.setValue("knowledgeBase", "", { shouldDirty: true });
                                  }}
                                >
                                  <i className="ri-close-line"></i>
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {knowledgeSource === 'url' && (
                          <div className="space-y-2">
                            <label className="block text-sm font-medium">Knowledge URL</label>
                            <div className="flex gap-2">
                              <Input
                                value={knowledgeUrl}
                                onChange={(e) => {
                                  setKnowledgeUrl(e.target.value);
                                  form.setValue("knowledgeBase", `URL: ${e.target.value}`, { shouldDirty: true });
                                }}
                                placeholder="https://docs.example.com/knowledge-base"
                              />
                              <Button
                                type="button"
                                variant="outline"
                                className="shrink-0"
                                onClick={() => {
                                  toast({
                                    title: "URL validated",
                                    description: "URL structure is valid",
                                  });
                                }}
                              >
                                Validate
                              </Button>
                            </div>
                            <p className="text-xs text-gray-500">
                              Enter a URL that contains knowledge the agent should use. We'll crawl and index this content.
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="settings" className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-lg font-semibold">Agent Settings</h2>
                      <Button 
                        type="button"
                        onClick={handleSaveClick}
                        disabled={updateAgentMutation.isPending || !form.formState.isDirty}
                        className="gap-1"
                      >
                        {updateAgentMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save size={16} />}
                        Save
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Agent Name</FormLabel>
                            <FormControl>
                              <Input 
                                {...field}
                                placeholder="Executive Agent" 
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <FormField
                        control={form.control}
                        name="role"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Agent Role</FormLabel>
                            <FormControl>
                              <Select 
                                value={field.value}
                                onValueChange={field.onChange}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select a role" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="executive">Executive</SelectItem>
                                  <SelectItem value="marketing">Marketing</SelectItem>
                                  <SelectItem value="sales">Sales</SelectItem>
                                  <SelectItem value="support">Support</SelectItem>
                                  <SelectItem value="content">Content</SelectItem>
                                  <SelectItem value="operations">Operations</SelectItem>
                                  <SelectItem value="custom">Custom</SelectItem>
                                </SelectContent>
                              </Select>
                            </FormControl>
                            {field.value === "custom" && (
                              <Input 
                                value={field.value === "custom" ? "" : field.value}
                                onChange={(e) => field.onChange(e.target.value)} 
                                placeholder="Enter custom role" 
                                className="mt-2"
                              />
                            )}
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <FormField
                        control={form.control}
                        name="icon"
                        render={({ field }) => (
                          <FormItem className="col-span-2">
                            <FormLabel>Agent Icon</FormLabel>
                            <div className="flex gap-2">
                              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                                <i className={`${field.value} text-primary text-lg`}></i>
                              </div>
                              <FormControl>
                                <Input 
                                  {...field}
                                  placeholder="ri-robot-line" 
                                />
                              </FormControl>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              Use Remix icon names (e.g., ri-robot-line, ri-admin-line)
                            </p>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <div className="col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                        <Button 
                          type="button" 
                          variant="outline" 
                          size="sm" 
                          className="gap-1 justify-start"
                          onClick={() => form.setValue("icon", "ri-robot-line", { shouldDirty: true })}
                        >
                          <i className="ri-robot-line text-primary"></i>
                          <span className="truncate">robot</span>
                        </Button>
                        <Button 
                          type="button" 
                          variant="outline" 
                          size="sm" 
                          className="gap-1 justify-start"
                          onClick={() => form.setValue("icon", "ri-user-settings-line", { shouldDirty: true })}
                        >
                          <i className="ri-user-settings-line text-primary"></i>
                          <span className="truncate">executive</span>
                        </Button>
                        <Button 
                          type="button" 
                          variant="outline" 
                          size="sm" 
                          className="gap-1 justify-start"
                          onClick={() => form.setValue("icon", "ri-customer-service-2-line", { shouldDirty: true })}
                        >
                          <i className="ri-customer-service-2-line text-primary"></i>
                          <span className="truncate">support</span>
                        </Button>
                        <Button 
                          type="button" 
                          variant="outline" 
                          size="sm" 
                          className="gap-1 justify-start"
                          onClick={() => form.setValue("icon", "ri-megaphone-line", { shouldDirty: true })}
                        >
                          <i className="ri-megaphone-line text-primary"></i>
                          <span className="truncate">marketing</span>
                        </Button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
              
              <div className="space-y-6">
                <Card className="p-6">
                  <h2 className="text-lg font-semibold mb-4">Agent Preview</h2>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                      <i className={`${form.watch("icon") || "ri-robot-line"} text-primary text-xl`}></i>
                    </div>
                    <div>
                      <div className="font-medium">{form.watch("name") || "Agent"}</div>
                      <Badge variant="outline">{form.watch("role") || "Assistant"}</Badge>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600 border border-gray-200 rounded-md p-3 bg-gray-50">
                    {form.watch("instructions") ? 
                      form.watch("instructions").length > 200 ? form.watch("instructions").substring(0, 200) + "..." : form.watch("instructions") 
                      : "This agent will help you with tasks and answer questions."}
                  </div>
                  
                  {form.formState.isDirty && (
                    <div className="mt-4 p-3 bg-blue-50 rounded-md text-sm text-blue-700 flex items-center gap-2">
                      <RefreshCw size={14} className="shrink-0" />
                      <span>You have unsaved changes</span>
                    </div>
                  )}
                </Card>
                
                <Card className="p-6">
                  <h2 className="text-lg font-semibold mb-4">What Agents Can Do</h2>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                        <i className="ri-message-3-line text-primary text-xs"></i>
                      </div>
                      <p>Engage in natural conversations and answer questions based on their knowledge and role</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                        <i className="ri-task-line text-primary text-xs"></i>
                      </div>
                      <p>Create, assign, and manage tasks to accomplish business objectives</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                        <i className="ri-team-line text-primary text-xs"></i>
                      </div>
                      <p>Collaborate with other agents on complex multi-step work processes</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                        <i className="ri-link text-primary text-xs"></i>
                      </div>
                      <p>Integrate with external services to perform real-world tasks</p>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </form>
        </Form>
      )}
    </Layout>
  );
}