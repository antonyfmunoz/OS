import React, { useState } from "react";
import { Layout } from "@/components/layout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";
import { Loader2, Plus, Search, User, Building, DollarSign, PhoneCall, Calendar, Mail, Check, X } from "lucide-react";

// Type definitions for CRM entities
type Contact = {
  id: string;
  name: string;
  email: string;
  phone: string;
  company: string;
  title: string;
  status: "lead" | "prospect" | "customer" | "churned";
  lastContact: string;
  notes: string;
  avatar?: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
};

type Deal = {
  id: string;
  title: string;
  company: string;
  value: string;
  stage: "discovery" | "proposal" | "negotiation" | "closed-won" | "closed-lost";
  probability: number;
  expectedCloseDate: string;
  contactId: string;
  assignedAgentId: string;
  notes: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
};

type Activity = {
  id: string;
  type: "email" | "call" | "meeting" | "task" | "note";
  subject: string;
  date: string;
  relatedToType: "contact" | "deal";
  relatedToId: string;
  completed: boolean;
  notes: string;
  createdByAgentId: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
};

// Contact form schema
const contactFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email is required"),
  phone: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  status: z.enum(["lead", "prospect", "customer", "churned"]).default("lead"),
  notes: z.string().optional(),
});

// Deal form schema
const dealFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  company: z.string().min(1, "Company is required"),
  value: z.string().min(1, "Value is required"),
  stage: z.enum(["discovery", "proposal", "negotiation", "closed-won", "closed-lost"]).default("discovery"),
  probability: z.string(),
  expectedCloseDate: z.string().optional(),
  contactId: z.string(),
  notes: z.string().optional(),
});

// Activity form schema
const activityFormSchema = z.object({
  type: z.enum(["email", "call", "meeting", "task", "note"]),
  subject: z.string().min(1, "Subject is required"),
  date: z.string(),
  relatedToType: z.enum(["contact", "deal"]),
  relatedToId: z.string(),
  completed: z.boolean().default(false),
  notes: z.string().optional(),
});

function getStatusBadge(status: Contact["status"]) {
  const colors = {
    lead: "bg-blue-100 text-blue-800",
    prospect: "bg-yellow-100 text-yellow-800",
    customer: "bg-green-100 text-green-800",
    churned: "bg-red-100 text-red-800",
  };
  
  return (
    <Badge className={`${colors[status]} font-medium`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

function getDealStageBadge(stage: Deal["stage"]) {
  const colors = {
    discovery: "bg-blue-100 text-blue-800",
    proposal: "bg-[#5e17eb]/10 text-[#5e17eb]",
    negotiation: "bg-yellow-100 text-yellow-800",
    "closed-won": "bg-green-100 text-green-800",
    "closed-lost": "bg-red-100 text-red-800",
  };
  
  const labels = {
    discovery: "Discovery",
    proposal: "Proposal",
    negotiation: "Negotiation",
    "closed-won": "Closed (Won)",
    "closed-lost": "Closed (Lost)",
  };
  
  return (
    <Badge className={`${colors[stage]} font-medium`}>
      {labels[stage]}
    </Badge>
  );
}

function getActivityTypeIcon(type: Activity["type"]) {
  switch (type) {
    case "email":
      return <Mail className="w-4 h-4 mr-1" />;
    case "call":
      return <PhoneCall className="w-4 h-4 mr-1" />;
    case "meeting":
      return <Calendar className="w-4 h-4 mr-1" />;
    case "task":
      return <Check className="w-4 h-4 mr-1" />;
    case "note":
      return <Textarea className="w-4 h-4 mr-1" />;
    default:
      return null;
  }
}

export default function CRMPage() {
  const [activeTab, setActiveTab] = useState("contacts");
  const [isContactDialogOpen, setIsContactDialogOpen] = useState(false);
  const [isDealDialogOpen, setIsDealDialogOpen] = useState(false);
  const [isActivityDialogOpen, setIsActivityDialogOpen] = useState(false);
  const { toast } = useToast();

  // Get contacts
  const { 
    data: contacts = [], 
    isLoading: isLoadingContacts,
    error: contactsError
  } = useQuery<Contact[]>({
    queryKey: ["/api/crm/contacts"],
  });

  // Get deals
  const { 
    data: deals = [], 
    isLoading: isLoadingDeals,
    error: dealsError
  } = useQuery<Deal[]>({
    queryKey: ["/api/crm/deals"],
  });

  // Get activities
  const { 
    data: activities = [], 
    isLoading: isLoadingActivities,
    error: activitiesError
  } = useQuery<Activity[]>({
    queryKey: ["/api/crm/activities"],
  });

  // Create contact mutation
  const createContactMutation = useMutation({
    mutationFn: async (data: z.infer<typeof contactFormSchema>) => {
      const response = await apiRequest("POST", "/api/crm/contacts", data);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to create contact");
      }
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/crm/contacts"] });
      setIsContactDialogOpen(false);
      toast({
        title: "Contact created",
        description: "New contact has been added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error creating contact",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  // Create deal mutation
  const createDealMutation = useMutation({
    mutationFn: async (data: z.infer<typeof dealFormSchema>) => {
      const response = await apiRequest("POST", "/api/crm/deals", data);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to create deal");
      }
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/crm/deals"] });
      setIsDealDialogOpen(false);
      toast({
        title: "Deal created",
        description: "New deal has been added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error creating deal",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  // Create activity mutation
  const createActivityMutation = useMutation({
    mutationFn: async (data: z.infer<typeof activityFormSchema>) => {
      const response = await apiRequest("POST", "/api/crm/activities", data);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to create activity");
      }
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/crm/activities"] });
      setIsActivityDialogOpen(false);
      toast({
        title: "Activity created",
        description: "New activity has been added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error creating activity",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  // Contact form
  const contactForm = useForm<z.infer<typeof contactFormSchema>>({
    resolver: zodResolver(contactFormSchema),
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      company: "",
      title: "",
      status: "lead",
      notes: "",
    },
  });

  // Deal form
  const dealForm = useForm<z.infer<typeof dealFormSchema>>({
    resolver: zodResolver(dealFormSchema),
    defaultValues: {
      title: "",
      company: "",
      value: "",
      stage: "discovery",
      probability: "50",
      expectedCloseDate: "",
      contactId: "",
      notes: "",
    },
  });

  // Activity form
  const activityForm = useForm<z.infer<typeof activityFormSchema>>({
    resolver: zodResolver(activityFormSchema),
    defaultValues: {
      type: "email",
      subject: "",
      date: new Date().toISOString().split('T')[0],
      relatedToType: "contact",
      relatedToId: "",
      completed: false,
      notes: "",
    },
  });

  const onContactSubmit = (data: z.infer<typeof contactFormSchema>) => {
    createContactMutation.mutate(data);
  };

  const onDealSubmit = (data: z.infer<typeof dealFormSchema>) => {
    createDealMutation.mutate(data);
  };

  const onActivitySubmit = (data: z.infer<typeof activityFormSchema>) => {
    createActivityMutation.mutate(data);
  };

  const renderContactCards = () => {
    if (isLoadingContacts) {
      return (
        <div className="flex justify-center items-center h-32">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      );
    }

    if (contactsError) {
      return (
        <div className="text-center text-red-500 p-4">
          Error loading contacts. Please try again.
        </div>
      );
    }

    if (contacts.length === 0) {
      return (
        <div className="text-center p-6 bg-gray-50 rounded-lg">
          <User className="w-10 h-10 mx-auto text-gray-400 mb-2" />
          <h3 className="text-lg font-medium text-gray-700">No contacts yet</h3>
          <p className="text-gray-500 mb-4">Add your first contact to get started</p>
          <Button onClick={() => setIsContactDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" /> Add Contact
          </Button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {contacts.map((contact) => (
          <Card key={contact.id} className="h-full">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg">{contact.name}</CardTitle>
                  <CardDescription>
                    {contact.title ? `${contact.title}, ` : ""}
                    {contact.company || "No company"}
                  </CardDescription>
                </div>
                {getStatusBadge(contact.status)}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center text-sm">
                <Mail className="w-4 h-4 mr-2 text-gray-500" />
                <span className="text-gray-700">{contact.email}</span>
              </div>
              {contact.phone && (
                <div className="flex items-center text-sm">
                  <PhoneCall className="w-4 h-4 mr-2 text-gray-500" />
                  <span className="text-gray-700">{contact.phone}</span>
                </div>
              )}
              {contact.lastContact && (
                <div className="flex items-center text-sm">
                  <Calendar className="w-4 h-4 mr-2 text-gray-500" />
                  <span className="text-gray-700">
                    Last contact: {new Date(contact.lastContact).toLocaleDateString()}
                  </span>
                </div>
              )}
              {contact.notes && (
                <p className="text-sm text-gray-600 mt-2 border-t pt-2">
                  {contact.notes.length > 100
                    ? contact.notes.slice(0, 100) + "..."
                    : contact.notes}
                </p>
              )}
            </CardContent>
            <CardFooter className="pt-0">
              <div className="flex justify-between items-center w-full">
                <Button variant="outline" size="sm">
                  View Details
                </Button>
                <span className="text-xs text-gray-500">
                  Added {new Date(contact.createdAt).toLocaleDateString()}
                </span>
              </div>
            </CardFooter>
          </Card>
        ))}
      </div>
    );
  };

  const renderDealCards = () => {
    if (isLoadingDeals) {
      return (
        <div className="flex justify-center items-center h-32">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      );
    }

    if (dealsError) {
      return (
        <div className="text-center text-red-500 p-4">
          Error loading deals. Please try again.
        </div>
      );
    }

    if (deals.length === 0) {
      return (
        <div className="text-center p-6 bg-gray-50 rounded-lg">
          <DollarSign className="w-10 h-10 mx-auto text-gray-400 mb-2" />
          <h3 className="text-lg font-medium text-gray-700">No deals yet</h3>
          <p className="text-gray-500 mb-4">Add your first deal to get started</p>
          <Button onClick={() => setIsDealDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" /> Add Deal
          </Button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {deals.map((deal) => (
          <Card key={deal.id} className="h-full">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <CardTitle className="text-lg">{deal.title}</CardTitle>
                {getDealStageBadge(deal.stage)}
              </div>
              <CardDescription>{deal.company}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center text-sm font-medium">
                <DollarSign className="w-4 h-4 mr-2 text-green-600" />
                <span className="text-green-700">
                  ${parseFloat(deal.value).toLocaleString()}
                </span>
                <Badge className="ml-2 bg-gray-100 text-gray-800">
                  {deal.probability}% probability
                </Badge>
              </div>
              {deal.expectedCloseDate && (
                <div className="flex items-center text-sm">
                  <Calendar className="w-4 h-4 mr-2 text-gray-500" />
                  <span className="text-gray-700">
                    Expected close: {new Date(deal.expectedCloseDate).toLocaleDateString()}
                  </span>
                </div>
              )}
              {deal.notes && (
                <p className="text-sm text-gray-600 mt-2 border-t pt-2">
                  {deal.notes.length > 100
                    ? deal.notes.slice(0, 100) + "..."
                    : deal.notes}
                </p>
              )}
            </CardContent>
            <CardFooter className="pt-0">
              <div className="flex justify-between items-center w-full">
                <Button variant="outline" size="sm">
                  View Details
                </Button>
                <span className="text-xs text-gray-500">
                  Added {new Date(deal.createdAt).toLocaleDateString()}
                </span>
              </div>
            </CardFooter>
          </Card>
        ))}
      </div>
    );
  };

  const renderActivities = () => {
    if (isLoadingActivities) {
      return (
        <div className="flex justify-center items-center h-32">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      );
    }

    if (activitiesError) {
      return (
        <div className="text-center text-red-500 p-4">
          Error loading activities. Please try again.
        </div>
      );
    }

    if (activities.length === 0) {
      return (
        <div className="text-center p-6 bg-gray-50 rounded-lg">
          <Calendar className="w-10 h-10 mx-auto text-gray-400 mb-2" />
          <h3 className="text-lg font-medium text-gray-700">No activities yet</h3>
          <p className="text-gray-500 mb-4">Log your first activity to get started</p>
          <Button onClick={() => setIsActivityDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" /> Add Activity
          </Button>
        </div>
      );
    }

    const sortedActivities = [...activities].sort((a, b) => 
      new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    return (
      <div className="space-y-4">
        {sortedActivities.map((activity) => {
          // Find related contact or deal
          const relatedEntity = activity.relatedToType === "contact"
            ? contacts.find(c => c.id === activity.relatedToId)
            : deals.find(d => d.id === activity.relatedToId);
          
          const relatedName = relatedEntity
            ? activity.relatedToType === "contact"
              ? (relatedEntity as Contact).name
              : (relatedEntity as Deal).title
            : "Unknown";

          return (
            <Card key={activity.id} className="border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                  <div className="flex items-center">
                    {getActivityTypeIcon(activity.type)}
                    <CardTitle className="text-lg ml-1">
                      {activity.subject}
                    </CardTitle>
                  </div>
                  <Badge className={activity.completed ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}>
                    {activity.completed ? "Completed" : "Pending"}
                  </Badge>
                </div>
                <CardDescription>
                  Related to{" "}
                  <span className="font-medium">
                    {relatedName} ({activity.relatedToType})
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 pb-2">
                <div className="flex items-center text-sm">
                  <Calendar className="w-4 h-4 mr-2 text-gray-500" />
                  <span className="text-gray-700">
                    {new Date(activity.date).toLocaleDateString()}
                  </span>
                </div>
                {activity.notes && (
                  <p className="text-sm text-gray-600 mt-1">
                    {activity.notes}
                  </p>
                )}
              </CardContent>
              <CardFooter className="pt-0">
                <div className="flex justify-between items-center w-full">
                  {!activity.completed && (
                    <Button variant="outline" size="sm">
                      Mark as Complete
                    </Button>
                  )}
                  <span className="text-xs text-gray-500">
                    Added {new Date(activity.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </CardFooter>
            </Card>
          );
        })}
      </div>
    );
  };

  return (
    <Layout title="Customer Relationship Management">
      <div className="container mx-auto py-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Customer Relationship Management</h1>
          <div className="flex space-x-2">
            <Button onClick={() => setIsContactDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> Contact
            </Button>
            <Button onClick={() => setIsDealDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> Deal
            </Button>
            <Button onClick={() => setIsActivityDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> Activity
            </Button>
          </div>
        </div>

        <Tabs defaultValue="contacts" value={activeTab} onValueChange={setActiveTab}>
          <div className="border-b border-gray-200 mb-4">
            <TabsList className="bg-transparent border-b-0">
              <TabsTrigger value="contacts" className="px-6 py-2">Contacts</TabsTrigger>
              <TabsTrigger value="deals" className="px-6 py-2">Deals</TabsTrigger>
              <TabsTrigger value="activities" className="px-6 py-2">Activities</TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="contacts" className="mt-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Contacts</h2>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search contacts..."
                  className="pl-8 w-64"
                />
              </div>
            </div>
            {renderContactCards()}
          </TabsContent>
          
          <TabsContent value="deals" className="mt-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Deals</h2>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search deals..."
                  className="pl-8 w-64"
                />
              </div>
            </div>
            {renderDealCards()}
          </TabsContent>
          
          <TabsContent value="activities" className="mt-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Activities</h2>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search activities..."
                  className="pl-8 w-64"
                />
              </div>
            </div>
            {renderActivities()}
          </TabsContent>
        </Tabs>
      </div>

      {/* Contact Dialog */}
      <Dialog open={isContactDialogOpen} onOpenChange={setIsContactDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Add New Contact</DialogTitle>
            <DialogDescription>
              Enter the contact details below to add a new contact to your CRM.
            </DialogDescription>
          </DialogHeader>
          <Form {...contactForm}>
            <form onSubmit={contactForm.handleSubmit(onContactSubmit)} className="space-y-4">
              <FormField
                control={contactForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="John Doe" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={contactForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input placeholder="john@example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={contactForm.control}
                  name="phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone</FormLabel>
                      <FormControl>
                        <Input placeholder="+1 (555) 123-4567" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={contactForm.control}
                  name="status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <Select
                        defaultValue={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select status" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="lead">Lead</SelectItem>
                          <SelectItem value="prospect">Prospect</SelectItem>
                          <SelectItem value="customer">Customer</SelectItem>
                          <SelectItem value="churned">Churned</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={contactForm.control}
                  name="company"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company</FormLabel>
                      <FormControl>
                        <Input placeholder="Acme Inc." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={contactForm.control}
                  name="title"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Job Title</FormLabel>
                      <FormControl>
                        <Input placeholder="CEO" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={contactForm.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Notes</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Additional information about this contact..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="submit" disabled={createContactMutation.isPending}>
                  {createContactMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Add Contact
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Deal Dialog */}
      <Dialog open={isDealDialogOpen} onOpenChange={setIsDealDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Add New Deal</DialogTitle>
            <DialogDescription>
              Enter the deal details below to add a new opportunity to your CRM.
            </DialogDescription>
          </DialogHeader>
          <Form {...dealForm}>
            <form onSubmit={dealForm.handleSubmit(onDealSubmit)} className="space-y-4">
              <FormField
                control={dealForm.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Deal Title</FormLabel>
                    <FormControl>
                      <Input placeholder="New software license" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={dealForm.control}
                name="company"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Company</FormLabel>
                    <FormControl>
                      <Input placeholder="Acme Inc." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={dealForm.control}
                  name="value"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Value ($)</FormLabel>
                      <FormControl>
                        <Input placeholder="10000" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={dealForm.control}
                  name="stage"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Stage</FormLabel>
                      <Select
                        defaultValue={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select stage" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="discovery">Discovery</SelectItem>
                          <SelectItem value="proposal">Proposal</SelectItem>
                          <SelectItem value="negotiation">Negotiation</SelectItem>
                          <SelectItem value="closed-won">Closed (Won)</SelectItem>
                          <SelectItem value="closed-lost">Closed (Lost)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={dealForm.control}
                  name="probability"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Probability (%)</FormLabel>
                      <FormControl>
                        <Input placeholder="50" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={dealForm.control}
                  name="expectedCloseDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Expected Close Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={dealForm.control}
                name="contactId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Related Contact</FormLabel>
                    <Select
                      defaultValue={field.value}
                      onValueChange={field.onChange}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select contact" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {contacts.map((contact) => (
                          <SelectItem key={contact.id} value={contact.id}>
                            {contact.name} - {contact.company || "No company"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={dealForm.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Notes</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Additional information about this deal..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="submit" disabled={createDealMutation.isPending}>
                  {createDealMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Add Deal
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Activity Dialog */}
      <Dialog open={isActivityDialogOpen} onOpenChange={setIsActivityDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Add New Activity</DialogTitle>
            <DialogDescription>
              Log a new activity related to a contact or deal.
            </DialogDescription>
          </DialogHeader>
          <Form {...activityForm}>
            <form onSubmit={activityForm.handleSubmit(onActivitySubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={activityForm.control}
                  name="type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Activity Type</FormLabel>
                      <Select
                        defaultValue={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="email">Email</SelectItem>
                          <SelectItem value="call">Call</SelectItem>
                          <SelectItem value="meeting">Meeting</SelectItem>
                          <SelectItem value="task">Task</SelectItem>
                          <SelectItem value="note">Note</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={activityForm.control}
                  name="date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={activityForm.control}
                name="subject"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subject</FormLabel>
                    <FormControl>
                      <Input placeholder="Initial discovery call" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={activityForm.control}
                  name="relatedToType"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Related To</FormLabel>
                      <Select
                        defaultValue={field.value}
                        onValueChange={(value) => {
                          field.onChange(value);
                          // Reset the relatedToId when type changes
                          activityForm.setValue("relatedToId", "");
                        }}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="contact">Contact</SelectItem>
                          <SelectItem value="deal">Deal</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={activityForm.control}
                  name="relatedToId"
                  render={({ field }) => {
                    const relatedToType = activityForm.watch("relatedToType");
                    const options = relatedToType === "contact" ? contacts : deals;
                    
                    return (
                      <FormItem>
                        <FormLabel>Select {relatedToType === "contact" ? "Contact" : "Deal"}</FormLabel>
                        <Select
                          defaultValue={field.value}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={`Select ${relatedToType}`} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {options.map((option) => (
                              <SelectItem key={option.id} value={option.id}>
                                {relatedToType === "contact" 
                                  ? (option as Contact).name 
                                  : (option as Deal).title
                                }
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              </div>
              <FormField
                control={activityForm.control}
                name="completed"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        className="h-4 w-4 mt-1"
                      />
                    </FormControl>
                    <div className="space-y-1 leading-none">
                      <FormLabel>Mark as Completed</FormLabel>
                      <FormDescription>
                        Toggle if this activity has already been completed
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
              <FormField
                control={activityForm.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Notes</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Details about this activity..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="submit" disabled={createActivityMutation.isPending}>
                  {createActivityMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Add Activity
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}