import { Header } from "@/components/header";
import { Integrations } from "@/components/integrations";
import { GmailConnectButton } from "@/components/gmail-connect-button";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { Link } from "wouter";

export default function IntegrationsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Integrations">
        <Button variant="ghost" size="sm" asChild className="mr-4">
          <Link href="/settings">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
      </Header>
      <div className="p-6 flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto">
          <Card className="p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">Connect Your Tools</h2>
            <p className="text-gray-600 mb-4">
              Enhance your agents' capabilities by connecting them to your favorite tools and services.
              Agents can fetch data, perform actions, and stay updated with real-time information.
            </p>
          </Card>

          <Card className="p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Active Integrations</h2>
            <div className="space-y-3">
              <GmailConnectButton />
            </div>
          </Card>
          
          <Integrations />
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <Card className="p-6">
              <h3 className="text-md font-semibold text-gray-800 mb-2">Integration Benefits</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-center">
                  <i className="ri-check-line text-green-500 mr-2"></i>
                  <span>Access knowledge bases in Notion</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-check-line text-green-500 mr-2"></i>
                  <span>Send emails through Gmail</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-check-line text-green-500 mr-2"></i>
                  <span>Update metrics in Google Sheets</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-check-line text-green-500 mr-2"></i>
                  <span>Trigger automations via webhooks</span>
                </li>
              </ul>
            </Card>
            
            <Card className="p-6">
              <h3 className="text-md font-semibold text-gray-800 mb-2">Coming Soon</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-center">
                  <i className="ri-time-line text-blue-500 mr-2"></i>
                  <span>Slack integration for team collaboration</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-time-line text-blue-500 mr-2"></i>
                  <span>Calendar access for scheduling</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-time-line text-blue-500 mr-2"></i>
                  <span>CRM integrations (Salesforce, HubSpot)</span>
                </li>
                <li className="flex items-center">
                  <i className="ri-time-line text-blue-500 mr-2"></i>
                  <span>Custom API connections</span>
                </li>
              </ul>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
