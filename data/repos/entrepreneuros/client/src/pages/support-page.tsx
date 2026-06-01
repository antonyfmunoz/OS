import { useState } from "react";
import { Header } from "@/components/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Loader2, CheckCircle2, Mail, MessageSquare, Phone, ArrowLeft } from "lucide-react";
import { Link } from "wouter";

export default function SupportPage() {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulate form submission
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitted(true);
      toast({
        title: "Support request submitted",
        description: "We'll get back to you within 24 hours.",
      });
    }, 1500);
  };
  
  return (
    <div className="flex flex-col h-full">
      <Header title="Contact Support">
        <Button variant="ghost" size="sm" asChild className="mr-4">
          <Link href="/">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
      </Header>
      <div className="p-6 flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto">
          
          <h1 className="text-2xl font-bold mb-2">Contact Support</h1>
          <p className="text-muted-foreground mb-6">
            Get help with AgentOS or provide feedback. Our team is ready to assist you.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              {submitted ? (
                <Card>
                  <CardContent className="pt-6 flex flex-col items-center justify-center text-center p-10">
                    <CheckCircle2 className="h-16 w-16 text-green-500 mb-4" />
                    <h2 className="text-xl font-medium mb-2">Support Request Received</h2>
                    <p className="text-muted-foreground mb-6 max-w-md">
                      Thank you for reaching out. Our team has received your request and will get back to you within 24 hours.
                    </p>
                    <Button onClick={() => setSubmitted(false)}>
                      Submit Another Request
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Submit a Support Request</CardTitle>
                    <CardDescription>
                      Fill out the form below and our support team will respond promptly.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <label htmlFor="name" className="text-sm font-medium">
                            Name
                          </label>
                          <Input 
                            id="name" 
                            placeholder="Your name" 
                            required 
                          />
                        </div>
                        <div className="space-y-2">
                          <label htmlFor="email" className="text-sm font-medium">
                            Email
                          </label>
                          <Input 
                            id="email" 
                            type="email" 
                            placeholder="your@email.com" 
                            required 
                          />
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <label htmlFor="subject" className="text-sm font-medium">
                          Subject
                        </label>
                        <Select defaultValue="general">
                          <SelectTrigger>
                            <SelectValue placeholder="Select a subject" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="general">General Inquiry</SelectItem>
                            <SelectItem value="technical">Technical Support</SelectItem>
                            <SelectItem value="billing">Billing & Account</SelectItem>
                            <SelectItem value="feedback">Feature Request / Feedback</SelectItem>
                            <SelectItem value="other">Other</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-2">
                        <label htmlFor="message" className="text-sm font-medium">
                          Message
                        </label>
                        <Textarea 
                          id="message" 
                          placeholder="Describe your issue or question in detail..." 
                          required
                          rows={6}
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <label htmlFor="attachments" className="text-sm font-medium">
                          Attachments (optional)
                        </label>
                        <Input 
                          id="attachments" 
                          type="file" 
                          className="cursor-pointer"
                        />
                        <p className="text-xs text-muted-foreground">
                          You can upload screenshots or documents related to your issue.
                        </p>
                      </div>
                      
                      <Button type="submit" className="w-full" disabled={isSubmitting}>
                        {isSubmitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 
                            Submitting...
                          </>
                        ) : (
                          "Submit Support Request"
                        )}
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              )}
            </div>
            
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Contact Information</CardTitle>
                  <CardDescription>
                    Alternative ways to get in touch with us
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h3 className="font-medium">Email Support</h3>
                      <p className="text-sm text-muted-foreground">
                        For general inquiries and support
                      </p>
                      <a href="mailto:support@agentos.ai" className="text-sm text-primary hover:underline">
                        support@agentos.ai
                      </a>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <Phone className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h3 className="font-medium">Phone Support</h3>
                      <p className="text-sm text-muted-foreground">
                        Available Monday-Friday, 9am-5pm ET
                      </p>
                      <a href="tel:+1-555-123-4567" className="text-sm text-primary hover:underline">
                        +1 (555) 123-4567
                      </a>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <MessageSquare className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <h3 className="font-medium">Live Chat</h3>
                      <p className="text-sm text-muted-foreground">
                        Chat with our support team in real-time
                      </p>
                      <Button variant="link" className="h-auto p-0 text-primary">
                        Start Live Chat
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>Frequently Asked Questions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h3 className="font-medium">How do I reset my password?</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      You can reset your password from the login page by clicking "Forgot Password".
                    </p>
                  </div>
                  <div>
                    <h3 className="font-medium">How do I add more users to my account?</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      You can add team members from the Settings page under "Team Members".
                    </p>
                  </div>
                  <div>
                    <h3 className="font-medium">Can I upgrade my subscription?</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Yes, you can upgrade anytime from the Settings page under "Billing".
                    </p>
                  </div>
                  <Button variant="link" className="text-primary p-0 h-auto">
                    View all FAQs
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}