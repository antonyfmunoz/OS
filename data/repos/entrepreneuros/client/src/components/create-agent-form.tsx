import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useToast } from "@/hooks/use-toast";
import { InsertAgent } from "@shared/schema";
import { useAIModels } from "@/hooks/use-ai-models";
import { AIModelSelector } from "./ai-model-selector";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { apiRequest, queryClient } from "@/lib/queryClient";

// Extend the InsertAgent schema for frontend validation
const agentFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  role: z.string().min(1, "Role is required"),
  roleLevel: z.enum(["chief", "manager", "laborer"]).default("laborer"),
  department: z.string().min(1, "Department is required"),
  icon: z.string().optional(),
  instructions: z.string().optional(),
  kpis: z.array(z.string()).optional(),
  behavioralStyle: z.string().optional(),
  isActive: z.boolean().optional(),
  simulationMode: z.boolean().optional(),
  parentAgentId: z.string().optional(),
  brainSources: z
    .array(
      z.object({
        type: z.enum(["url", "text", "file", "auto-generate"]),
        url: z.string().optional(),
        content: z.string().optional(),
      })
    )
    .optional(),
});

type AgentFormValues = z.infer<typeof agentFormSchema>;

// Agent Icons
const agentIcons = [
  "ri-robot-line",
  "ri-user-voice-line",
  "ri-line-chart-line",
  "ri-mail-line",
  "ri-service-line",
  "ri-customer-service-2-line",
  "ri-shopping-cart-line",
  "ri-settings-line",
];

// Department options
const departments = [
  "Marketing",
  "Sales",
  "Operations",
  "Finance",
  "Customer Service",
  "Product",
  "Engineering",
  "Human Resources",
  "General",
];

// Role levels with descriptions
const roleLevels = [
  {
    value: "chief",
    label: "Chief",
    description: "Strategic decision-maker with authority over other agents",
  },
  {
    value: "manager",
    label: "Manager",
    description: "Coordinates tasks and oversees execution",
  },
  {
    value: "laborer",
    label: "Laborer",
    description: "Executes specific tasks and reports to managers",
  },
];

// Behavioral style options
const behavioralStyles = [
  {
    value: "analytical",
    label: "Analytical",
    description: "Data-driven, precise, and methodical in approach",
  },
  {
    value: "creative",
    label: "Creative",
    description: "Innovative, out-of-the-box thinker focused on new ideas",
  },
  {
    value: "efficient",
    label: "Efficient",
    description: "Quick, direct, and focused on optimal execution",
  },
  {
    value: "collaborative",
    label: "Collaborative",
    description: "Team-oriented, communicative, and consultative",
  },
];

export function CreateAgentForm({
  onSuccess,
}: {
  onSuccess?: () => void;
}) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("basic");
  const [brainSource, setBrainSource] = useState<"manual" | "auto" | "upload">("manual");
  const [loading, setLoading] = useState(false);
  const [selectedAIModel, setSelectedAIModel] = useState<any>(null);
  const [kpiInputs, setKpiInputs] = useState<string[]>([""]);

  // Initialize form with default values
  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      name: "",
      role: "",
      roleLevel: "laborer",
      department: "General",
      instructions: "",
      behavioralStyle: "efficient",
      isActive: true,
      simulationMode: false,
      kpis: [],
      brainSources: [{ type: "text", content: "" }],
    },
  });

  const handleAddKpi = () => {
    setKpiInputs([...kpiInputs, ""]);
  };

  const handleKpiChange = (index: number, value: string) => {
    const newKpis = [...kpiInputs];
    newKpis[index] = value;
    setKpiInputs(newKpis);
    form.setValue("kpis", newKpis.filter(kpi => kpi.trim() !== ""));
  };

  const handleRemoveKpi = (index: number) => {
    const newKpis = kpiInputs.filter((_, i) => i !== index);
    setKpiInputs(newKpis);
    form.setValue("kpis", newKpis.filter(kpi => kpi.trim() !== ""));
  };

  const handleBrainSourceChange = (value: "manual" | "auto" | "upload") => {
    setBrainSource(value);
    
    // Update form values based on brain source type
    type BrainSource = {
      type: "text" | "auto-generate" | "url" | "file";
      content?: string;
      url?: string;
    };
    
    let brainSources: BrainSource[] = [];
    
    if (value === "manual") {
      brainSources = [{ type: "text", content: form.getValues("brainSources")?.[0]?.content || "" }];
    } else if (value === "auto") {
      brainSources = [{ type: "auto-generate", content: "" }];
    } else if (value === "upload") {
      brainSources = [{ type: "url", url: "" }];
    }
    
    form.setValue("brainSources", brainSources);
  };

  async function onSubmit(data: AgentFormValues) {
    setLoading(true);
    
    try {
      // Transform form data to match API expectations
      const agentData: InsertAgent = {
        ...data,
        kpis: kpiInputs.filter(kpi => kpi.trim() !== ""),
      };
      
      // If AI model selected, add it to the agent instructions
      if (selectedAIModel) {
        agentData.instructions = `${agentData.instructions || ""}\n\nAI Model: ${selectedAIModel.provider} - ${selectedAIModel.modelName}`;
      }
      
      // Make the API request
      const response = await apiRequest("POST", "/api/agents", agentData);
      
      if (!response.ok) {
        throw new Error("Failed to create agent");
      }
      
      // Show success message
      toast({
        title: "Agent Created",
        description: `${data.name} has been added to your team.`,
      });
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["/api/agents"] });
      
      // Call success callback if provided
      if (onSuccess) {
        onSuccess();
      }
      
    } catch (error) {
      console.error("Error creating agent:", error);
      toast({
        title: "Error",
        description: "Failed to create agent. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-4 mb-6">
            <TabsTrigger value="basic">Basic Info</TabsTrigger>
            <TabsTrigger value="brain">Agent Brain</TabsTrigger>
            <TabsTrigger value="kpis">Goals & KPIs</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>
          
          {/* Basic Info Tab */}
          <TabsContent value="basic" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Agent Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Jordan" {...field} />
                    </FormControl>
                    <FormDescription>
                      Give your agent a human-like name
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="department"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Department</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a department" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {departments.map((dept) => (
                          <SelectItem key={dept} value={dept}>
                            {dept}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Which department does this agent belong to
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Job Title</FormLabel>
                    <FormControl>
                      <Input placeholder="Marketing Specialist" {...field} />
                    </FormControl>
                    <FormDescription>
                      Specific role or job title
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="roleLevel"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role Level</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a role level" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {roleLevels.map((level) => (
                          <SelectItem key={level.value} value={level.value}>
                            {level.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Hierarchy level within the organization
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            <FormField
              control={form.control}
              name="icon"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Icon</FormLabel>
                  <div className="grid grid-cols-8 gap-2">
                    {agentIcons.map((icon) => (
                      <div
                        key={icon}
                        onClick={() => form.setValue("icon", icon)}
                        className={`w-12 h-12 flex items-center justify-center border rounded-md cursor-pointer hover:bg-gray-100 ${
                          field.value === icon ? "bg-blue-100 border-blue-500" : ""
                        }`}
                      >
                        <i className={`${icon} text-xl`}></i>
                      </div>
                    ))}
                  </div>
                  <FormDescription>
                    Select an icon to represent this agent
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </TabsContent>
          
          {/* Agent Brain Tab */}
          <TabsContent value="brain" className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-md mb-4">
              <h3 className="text-lg font-medium mb-2">Agent Brain</h3>
              <p className="text-sm text-gray-600 mb-4">
                An agent's brain determines what knowledge it has access to when responding to tasks and questions.
              </p>
              
              <div className="flex space-x-3 mb-4">
                <Button
                  type="button"
                  variant={brainSource === "manual" ? "default" : "outline"}
                  onClick={() => handleBrainSourceChange("manual")}
                >
                  Manual Input
                </Button>
                <Button
                  type="button"
                  variant={brainSource === "auto" ? "default" : "outline"}
                  onClick={() => handleBrainSourceChange("auto")}
                >
                  Auto-Generate
                </Button>
                <Button
                  type="button"
                  variant={brainSource === "upload" ? "default" : "outline"}
                  onClick={() => handleBrainSourceChange("upload")}
                >
                  Upload Source
                </Button>
              </div>
            </div>
            
            {brainSource === "manual" && (
              <FormField
                control={form.control}
                name="brainSources.0.content"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Knowledge Base</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter specific knowledge, procedures, guidelines, and information for this agent..."
                        className="min-h-[200px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Enter specific knowledge, procedures, guidelines, and information for this agent.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            
            {brainSource === "auto" && (
              <div>
                <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                  <h4 className="font-medium text-blue-700 mb-2">Auto-Generation</h4>
                  <p className="text-sm text-blue-600">
                    We'll use AI to research and build a comprehensive knowledge base for this agent based on best practices in their field.
                  </p>
                </div>
                
                <FormField
                  control={form.control}
                  name="role"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Research Terms</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="Add specific topics to research" 
                          value={`best practices for ${field.value || 'this role'}`}
                          disabled 
                        />
                      </FormControl>
                      <FormDescription>
                        We'll automatically research these topics to build the agent's brain
                      </FormDescription>
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="instructions"
                  render={({ field }) => (
                    <FormItem className="mt-4">
                      <FormLabel>Additional Instructions (Optional)</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Any specific areas to focus on or avoid..."
                          className="min-h-[100px]"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Add any specific guidance for the auto-generation process
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}
            
            {brainSource === "upload" && (
              <div>
                <FormField
                  control={form.control}
                  name="brainSources.0.url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Source URL</FormLabel>
                      <FormControl>
                        <Input placeholder="https://notion.so/your-page or https://docs.google.com/your-doc" {...field} />
                      </FormControl>
                      <FormDescription>
                        Link to a Notion page, Google Doc, or other knowledge source
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <div className="mt-4 p-4 bg-gray-100 rounded-md">
                  <h4 className="font-medium mb-2">Supported Integrations</h4>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-2 bg-white rounded border text-center text-sm">Notion</div>
                    <div className="p-2 bg-white rounded border text-center text-sm">Google Docs</div>
                    <div className="p-2 bg-white rounded border text-center text-sm">PDF Upload</div>
                  </div>
                </div>
              </div>
            )}
            
            {/* AI Model Selection */}
            <div className="mt-6 pt-6 border-t">
              <h3 className="text-lg font-medium mb-4">AI Model Selection</h3>
              <AIModelSelector 
                onSelectModel={setSelectedAIModel} 
                defaultProvider="openai"
                defaultModel="gpt-4o"
              />
            </div>
          </TabsContent>
          
          {/* Goals & KPIs Tab */}
          <TabsContent value="kpis" className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-md mb-4">
              <h3 className="text-lg font-medium mb-2">Agent Goals & KPIs</h3>
              <p className="text-sm text-gray-600">
                Define measurable outcomes and success criteria for this agent
              </p>
            </div>
            
            <div className="space-y-4">
              <h4 className="font-medium">Key Performance Indicators</h4>
              {kpiInputs.map((kpi, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    placeholder={`KPI #${index + 1} (e.g., "Increase conversion rate by 5%")`}
                    value={kpi}
                    onChange={(e) => handleKpiChange(index, e.target.value)}
                    className="flex-1"
                  />
                  {index > 0 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => handleRemoveKpi(index)}
                    >
                      <i className="ri-delete-bin-line"></i>
                    </Button>
                  )}
                </div>
              ))}
              
              <Button
                type="button"
                variant="outline"
                onClick={handleAddKpi}
                className="mt-2"
              >
                <i className="ri-add-line mr-2"></i>
                Add KPI
              </Button>
            </div>
            
            <FormField
              control={form.control}
              name="behavioralStyle"
              render={({ field }) => (
                <FormItem className="mt-6">
                  <FormLabel>Agent Work Style</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a work style" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {behavioralStyles.map((style) => (
                        <SelectItem key={style.value} value={style.value}>
                          {style.label} - {style.description}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Define how this agent approaches their work
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </TabsContent>
          
          {/* Advanced Tab */}
          <TabsContent value="advanced" className="space-y-4">
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="simulation">
                <AccordionTrigger>Simulation Mode</AccordionTrigger>
                <AccordionContent>
                  <FormField
                    control={form.control}
                    name="simulationMode"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">
                            Enable Simulation Mode
                          </FormLabel>
                          <FormDescription>
                            Agent will run in simulation mode, allowing you to test responses before deploying
                          </FormDescription>
                        </div>
                        <FormControl>
                          <input
                            type="checkbox"
                            checked={field.value}
                            onChange={field.onChange}
                            className="accent-blue-500 h-4 w-4"
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </AccordionContent>
              </AccordionItem>
              
              <AccordionItem value="hierarchy">
                <AccordionTrigger>Reporting Structure</AccordionTrigger>
                <AccordionContent>
                  <FormField
                    control={form.control}
                    name="parentAgentId"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Reports To</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select a parent agent" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="">No parent agent</SelectItem>
                            {/* Parent agents would be loaded dynamically here */}
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Select a parent agent for this agent to report to
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </AccordionContent>
              </AccordionItem>
              
              <AccordionItem value="activation">
                <AccordionTrigger>Agent Activation</AccordionTrigger>
                <AccordionContent>
                  <FormField
                    control={form.control}
                    name="isActive"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">
                            Active Agent
                          </FormLabel>
                          <FormDescription>
                            Agent is available for assignments and tasks
                          </FormDescription>
                        </div>
                        <FormControl>
                          <input
                            type="checkbox"
                            checked={field.value}
                            onChange={field.onChange}
                            className="accent-blue-500 h-4 w-4"
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </TabsContent>
        </Tabs>
        
        <div className="flex justify-between items-center pt-6 border-t">
          <Button 
            type="button" 
            variant="outline" 
            onClick={() => {
              if (activeTab === "basic") {
                onSuccess?.();
              } else if (activeTab === "brain") {
                setActiveTab("basic");
              } else if (activeTab === "kpis") {
                setActiveTab("brain");
              } else if (activeTab === "advanced") {
                setActiveTab("kpis");
              }
            }}
          >
            {activeTab === "basic" ? "Cancel" : "Back"}
          </Button>
          
          <div className="flex gap-2">
            {activeTab !== "advanced" ? (
              <Button 
                type="button"
                onClick={() => {
                  if (activeTab === "basic") {
                    setActiveTab("brain");
                  } else if (activeTab === "brain") {
                    setActiveTab("kpis");
                  } else if (activeTab === "kpis") {
                    setActiveTab("advanced");
                  }
                }}
              >
                Continue
              </Button>
            ) : (
              <Button type="submit" disabled={loading}>
                {loading ? "Creating..." : "Create Agent"}
              </Button>
            )}
          </div>
        </div>
      </form>
    </Form>
  );
}