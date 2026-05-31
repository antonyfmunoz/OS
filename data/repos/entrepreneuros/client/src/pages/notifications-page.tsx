import { useState } from "react";
import { useNotifications } from "@/hooks/use-notifications";
import { format } from "date-fns";
import { Check, Loader2, BellOff, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState("all");
  const { 
    notifications, 
    isLoading, 
    markAsRead, 
    markAllAsRead,
    deleteNotification,
    refresh,
    isMarkingAllAsRead,
    isDeletingNotification
  } = useNotifications();

  const readNotifications = notifications.filter(n => n.read);
  const unreadNotifications = notifications.filter(n => !n.read);

  const displayNotifications = activeTab === "all" 
    ? notifications 
    : activeTab === "unread" 
      ? unreadNotifications 
      : readNotifications;

  const handleMarkAsRead = (id: string) => {
    markAsRead(id);
  };
  
  const handleDeleteNotification = (id: string) => {
    console.log("Notification page - deleting notification:", id);
    
    // Optimistic UI update - remove the notification immediately from the displayed list
    // This will make the UI feel more responsive while the API call completes
    const updatedDisplayNotifications = displayNotifications.filter(n => n.id !== id);
    if (activeTab === "all") {
      // If we're in the "all" tab, manually update tab counts for visual feedback
      if (!readNotifications.some(n => n.id === id) && 
          !unreadNotifications.some(n => n.id === id)) {
        console.log("Notification not found in current lists");
      }
    }
    
    // Perform the actual deletion
    deleteNotification(id);
    
    // Force a refresh after deletion to ensure consistency
    setTimeout(() => {
      refresh();
    }, 300);
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Notifications" />
      <div className="p-6 flex-1">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">Notifications</h1>
            {unreadNotifications.length > 0 && (
              <Button 
                variant="outline" 
                onClick={() => markAllAsRead()}
                disabled={isMarkingAllAsRead}
              >
                <Check className="mr-2 h-4 w-4" />
                Mark all as read
                {isMarkingAllAsRead && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
              </Button>
            )}
          </div>

          <Tabs defaultValue="all" className="mb-8" value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-6">
              <TabsTrigger value="all">
                All
                <span className="ml-2 bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs">
                  {notifications.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="unread">
                Unread
                <span className="ml-2 bg-primary/10 text-primary rounded-full px-2 py-0.5 text-xs">
                  {unreadNotifications.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="read">
                Read
                <span className="ml-2 bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs">
                  {readNotifications.length}
                </span>
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value={activeTab}>
              {isLoading ? (
                <div className="flex justify-center items-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : displayNotifications.length === 0 ? (
                <Card>
                  <CardContent className="py-16 flex flex-col items-center justify-center text-center">
                    <BellOff className="h-16 w-16 mb-4 text-muted stroke-[1.25px]" />
                    <h3 className="text-xl font-medium mb-2">No notifications</h3>
                    <p className="text-muted-foreground max-w-md">
                      {activeTab === "all" 
                        ? "You don't have any notifications yet. Notifications will appear when there are updates from your agents or integrations." 
                        : activeTab === "unread" 
                          ? "You've read all your notifications. Nice work!" 
                          : "You haven't read any notifications yet."}
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  {displayNotifications.map((notification) => (
                    <NotificationCard 
                      key={notification.id}
                      notification={notification}
                      onMarkAsRead={handleMarkAsRead}
                      onDeleteNotification={handleDeleteNotification}
                    />
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

type NotificationCardProps = {
  notification: any;
  onMarkAsRead: (id: string) => void;
  onDeleteNotification?: (id: string) => void;
};

function NotificationCard({ notification, onMarkAsRead, onDeleteNotification }: NotificationCardProps) {
  const formattedDate = notification.createdAt
    ? format(new Date(notification.createdAt), "MMM d, yyyy 'at' h:mm a")
    : "";

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "integration-connected":
        return "ri-link-m";
      case "task-assigned":
        return "ri-task-line";
      case "agent-created":
        return "ri-robot-line";
      case "message-received":
        return "ri-message-3-line";
      case "system":
        return "ri-notification-4-line";
      default:
        return "ri-notification-4-line";
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case "integration-connected":
        return "text-blue-500 bg-blue-500/10";
      case "task-assigned":
        return "text-yellow-500 bg-yellow-500/10";
      case "agent-created":
        return "text-green-500 bg-green-500/10";
      case "message-received":
        return "text-[#5e17eb] bg-[#5e17eb]/10";
      case "system":
        return "text-gray-500 bg-gray-500/10";
      default:
        return "text-gray-500 bg-gray-500/10";
    }
  };

  // Auto-mark as read when the card is clicked
  const handleCardClick = () => {
    if (!notification.read) {
      onMarkAsRead(notification.id);
    }
  };

  return (
    <Card 
      className={cn(
        "transition-all duration-200 cursor-pointer",
        !notification.read && "border-primary/50 shadow-[0_0_0_1px] shadow-primary/10"
      )}
      onClick={handleCardClick}
    >
      <CardHeader className="p-4 pb-0">
        <div className="flex justify-between items-start">
          <div className="flex items-start gap-3">
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center",
              getNotificationColor(notification.type)
            )}>
              <i className={cn(
                getNotificationIcon(notification.type),
                "text-lg"
              )}></i>
            </div>
            <div>
              <CardTitle className="text-base">{notification.title}</CardTitle>
              <CardDescription className="mt-1 text-xs">
                {formattedDate}
              </CardDescription>
            </div>
          </div>
          {!notification.read && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 rounded-full"
              onClick={(e) => {
                e.stopPropagation(); // Prevent the card click handler
                onMarkAsRead(notification.id);
              }}
            >
              <Check className="mr-1 h-3.5 w-3.5" />
              Mark as read
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="flex justify-between items-start">
          <p className="text-sm text-muted-foreground mt-2">{notification.content}</p>
          {onDeleteNotification && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 ml-2 shrink-0"
              onClick={(e) => {
                e.stopPropagation(); // Prevent the card click handler
                onDeleteNotification(notification.id);
              }}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Delete
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}