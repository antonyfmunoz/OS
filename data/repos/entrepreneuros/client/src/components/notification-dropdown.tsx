import React from "react";
import { Notification } from "@shared/schema";
import { useNotifications } from "@/hooks/use-notifications";
import { Bell, Check, BellOff, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Link } from "wouter";
import { format } from "date-fns";

export const NotificationDropdown = () => {
  const {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    isMarkingAllAsRead,
    isDeletingNotification,
  } = useNotifications();

  // This function is used by the NotificationItem component
  const handleMarkAsRead = (
    e: React.MouseEvent<HTMLButtonElement>,
    notificationId: string
  ) => {
    e.preventDefault();
    e.stopPropagation();
    markAsRead(notificationId);
  };
  
  // Handle deletion with optimistic UI update
  const handleDeleteNotification = (notificationId: string) => {
    // Add manual logging to diagnose the issue
    console.log("Dropdown deleting notification:", notificationId);
    
    // Close dropdown after deletion
    // This ensures the UI refreshes when reopened 
    const dropdown = document.querySelector("[data-state='open']");
    if (dropdown) {
      setTimeout(() => {
        const closeButton = document.querySelector("[role='menuitem']");
        if (closeButton) {
          (closeButton as HTMLElement).click();
        }
      }, 100);
    }
    
    // Perform the delete operation
    deleteNotification(notificationId);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 w-5 h-5 p-0 flex items-center justify-center text-xs"
            >
              {unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-80" align="end">
        <DropdownMenuLabel className="flex justify-between items-center">
          <span>Notifications</span>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              onClick={() => markAllAsRead()}
              disabled={isMarkingAllAsRead}
            >
              <Check className="mr-1 h-3 w-3" />
              Mark all as read
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <ScrollArea className="h-[400px]">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading notifications...
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-6 text-center text-muted-foreground flex flex-col items-center gap-2">
              <BellOff className="h-12 w-12 mb-2 opacity-20" />
              <span>No notifications yet</span>
              <span className="text-sm opacity-70">
                We'll notify you when something happens
              </span>
              <Button 
                variant="link" 
                size="sm" 
                asChild 
                className="mt-2"
              >
                <Link href="/notifications">View notification center</Link>
              </Button>
            </div>
          ) : (
            <div className="py-1">
              {notifications.slice(0, 5).map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={handleMarkAsRead}
                  onDeleteNotification={handleDeleteNotification}
                />
              ))}
              {notifications.length > 5 && (
                <DropdownMenuItem asChild className="justify-center text-primary font-medium">
                  <Link href="/notifications">
                    View all {notifications.length} notifications
                  </Link>
                </DropdownMenuItem>
              )}
            </div>
          )}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (
    e: React.MouseEvent<HTMLButtonElement>,
    id: string
  ) => void;
  onDeleteNotification?: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onMarkAsRead,
  onDeleteNotification,
}) => {
  const href = notification.href || "#";
  const formattedDate = notification.createdAt
    ? format(new Date(notification.createdAt), "MMM d, h:mm a")
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
      default:
        return "ri-notification-4-line";
    }
  };

  // Handle the notification click
  const handleNotificationClick = (e: React.MouseEvent) => {
    if (!notification.read) {
      // Create a button event to satisfy the type
      const buttonEvent = e as unknown as React.MouseEvent<HTMLButtonElement>;
      onMarkAsRead(buttonEvent, notification.id);
    }
  };

  return (
    <DropdownMenuItem
      asChild
      className={cn(
        "flex flex-col items-start p-3 cursor-pointer",
        !notification.read && "bg-accent/50"
      )}
    >
      <Link href={href} onClick={handleNotificationClick}>
        <div className="flex items-start gap-3 w-full">
          <div
            className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              !notification.read ? "bg-primary/10" : "bg-muted"
            )}
          >
            <i
              className={cn(
                getNotificationIcon(notification.type),
                !notification.read ? "text-primary" : "text-muted-foreground"
              )}
            ></i>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <h4
                className={cn(
                  "font-medium text-sm line-clamp-1",
                  !notification.read && "font-semibold"
                )}
              >
                {notification.title}
              </h4>
              <div className="flex">
                {!notification.read && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0 ml-1 rounded-full"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      onMarkAsRead(e, notification.id);
                    }}
                  >
                    <Check className="h-3 w-3" />
                    <span className="sr-only">Mark as read</span>
                  </Button>
                )}
                {onDeleteNotification && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0 ml-1 rounded-full text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      onDeleteNotification(notification.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                    <span className="sr-only">Delete notification</span>
                  </Button>
                )}
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              {notification.content}
            </p>
            <span className="text-xs text-muted-foreground mt-1 block">
              {formattedDate}
            </span>
          </div>
        </div>
      </Link>
    </DropdownMenuItem>
  );
};