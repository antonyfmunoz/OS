import { Button } from "@/components/ui/button";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

type Integration = {
  id: string;
  name: string;
  type: string;
  status: "connected" | "disconnected";
  details: string;
  icon: string;
};

export function Integrations() {
  const { toast } = useToast();
  
  const { data: integrations = [] } = useQuery<Integration[]>({
    queryKey: ["/api/integrations"],
  });

  const connectIntegrationMutation = useMutation({
    mutationFn: async (integrationType: string) => {
      const res = await apiRequest("POST", "/api/integrations/connect", { 
        type: integrationType 
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      toast({
        title: "Integration connected",
        description: "Your integration has been connected successfully.",
      });
    },
    onError: (error) => {
      toast({
        title: "Connection failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const getIconClass = (type: string) => {
    switch (type) {
      case "notion":
        return "ri-notion-line text-xl text-blue-600";
      case "gmail":
        return "ri-mail-line text-xl text-red-500";
      case "google-sheets":
        return "ri-file-list-3-line text-xl text-green-600";
      case "zapier":
        return "ri-flashlight-line text-xl text-orange-500";
      default:
        return "ri-link text-xl text-gray-600";
    }
  };

  const getIconBgClass = (type: string) => {
    switch (type) {
      case "notion":
        return "bg-blue-50";
      case "gmail":
        return "bg-red-50";
      case "google-sheets":
        return "bg-green-50";
      case "zapier":
        return "bg-orange-50";
      default:
        return "bg-gray-50";
    }
  };

  const handleConnect = (type: string) => {
    connectIntegrationMutation.mutate(type);
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {integrations.map((integration) => (
          <div key={integration.id} className="border border-gray-200 rounded-lg p-4 flex flex-col items-center">
            <div className={`w-12 h-12 ${getIconBgClass(integration.type)} rounded-full flex items-center justify-center mb-3`}>
              <i className={getIconClass(integration.type)}></i>
            </div>
            <h3 className="font-medium text-gray-800 mb-1">{integration.name}</h3>
            <p className="text-xs text-gray-500 text-center mb-3">
              {integration.status === "connected" 
                ? `Connected - ${integration.details}` 
                : "Not connected"}
            </p>
            <Button 
              variant="outline" 
              size="sm"
              className="text-xs"
            >
              {integration.status === "connected" ? "Manage" : "Connect"}
            </Button>
          </div>
        ))}
        
        <div className="border border-gray-200 border-dashed rounded-lg p-4 flex flex-col items-center">
          <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mb-3">
            <i className="ri-add-line text-xl text-gray-400"></i>
          </div>
          <h3 className="font-medium text-gray-800 mb-1">Add Integration</h3>
          <p className="text-xs text-gray-500 text-center mb-3">Connect more tools</p>
          <Button 
            size="sm"
            className="text-xs bg-primary hover:bg-blue-600 text-white"
            onClick={() => handleConnect("new")}
            disabled={connectIntegrationMutation.isPending}
          >
            Connect
          </Button>
        </div>
      </div>
    </div>
  );
}
