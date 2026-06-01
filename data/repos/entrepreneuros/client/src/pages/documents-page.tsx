import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Loader2, 
  Plus, 
  FileText, 
  Edit2, 
  Trash2, 
  Folder, 
  FolderPlus, 
  ChevronRight, 
  Home,
  FolderEdit,
  ArrowLeft
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { apiRequest, queryClient } from "@/lib/queryClient";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Textarea } from "@/components/ui/textarea";
import { SearchXIcon } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { CreateAgentModal } from "@/components/create-agent-modal";
import { Layout } from "@/components/layout";

// Define agent type for the component
type Agent = {
  id: string;
  name: string;
  role: string;
  icon: string;
  activeTasks: number;
};

// Define folder type
type Folder = {
  id: string;
  name: string;
  parentId: string | null;
  userId: string;
  createdAt: Date;
  updatedAt: Date;
};

// Define document type based on our schema
type Document = {
  id: string;
  title: string;
  content: string;
  folderId: string | null;
  tags: string[];
  userId: string;
  createdAt: Date;
  updatedAt: Date;
};

// Folder form schema
const folderFormSchema = z.object({
  name: z.string().min(1, "Folder name is required"),
  parentId: z.string().optional().nullable(),
});

type FolderFormData = z.infer<typeof folderFormSchema>;

// Document form schema (derived from insertDocumentSchema)
const documentFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  content: z.string(),
  folderId: z.string().optional().nullable(),
  tags: z.string().optional().transform(tags => 
    tags 
      ? tags.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0) 
      : []
  ) as unknown as z.ZodType<string[]>,
});

type DocumentFormData = z.infer<typeof documentFormSchema>;

export default function DocumentsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [showDocumentDialog, setShowDocumentDialog] = useState(false);
  const [showFolderDialog, setShowFolderDialog] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false); // For the create agent modal
  const [editingDocument, setEditingDocument] = useState<Document | null>(null);
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [folderPath, setFolderPath] = useState<Folder[]>([]);
  
  // Initialize document form with useForm hook
  const form = useForm<DocumentFormData>({
    resolver: zodResolver(documentFormSchema),
    defaultValues: {
      title: "",
      content: "",
      folderId: null,
      tags: "" as any,
    },
  });
  
  // Initialize folder form with useForm hook
  const folderForm = useForm<FolderFormData>({
    resolver: zodResolver(folderFormSchema),
    defaultValues: {
      name: "",
      parentId: null,
    },
  });

  // Query for fetching documents
  const { 
    data: documents, 
    isLoading: documentsLoading, 
    isError: documentsError,
    error: documentsErrorData
  } = useQuery<Document[]>({
    queryKey: ["/api/documents", currentFolderId],
    queryFn: async () => {
      const url = currentFolderId 
        ? `/api/documents?folderId=${currentFolderId}` 
        : '/api/documents';
      const res = await apiRequest("GET", url);
      return await res.json();
    },
    enabled: !!user,
  });
  
  // Query for fetching folders
  const {
    data: folders,
    isLoading: foldersLoading,
    isError: foldersError,
    error: foldersErrorData
  } = useQuery<Folder[]>({
    queryKey: ["/api/folders"],
    enabled: !!user,
  });
  
  // Query for fetching agents
  const { 
    data: agents = [] 
  } = useQuery<Agent[]>({
    queryKey: ["/api/agents"],
    enabled: !!user,
  });

  // Create document mutation
  const createDocumentMutation = useMutation({
    mutationFn: async (document: DocumentFormData) => {
      const res = await apiRequest("POST", "/api/documents", document);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/documents"] });
      toast({
        title: "Document created",
        description: "Your document has been created successfully.",
      });
      setShowDocumentDialog(false);
      form.reset();
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create document",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Update document mutation
  const updateDocumentMutation = useMutation({
    mutationFn: async ({ id, document }: { id: string; document: DocumentFormData }) => {
      const res = await apiRequest("PATCH", `/api/documents/${id}`, document);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/documents"] });
      toast({
        title: "Document updated",
        description: "Your document has been updated successfully.",
      });
      setShowDocumentDialog(false);
      setEditingDocument(null);
      form.reset();
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to update document",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Delete document mutation
  const deleteDocumentMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/documents"] });
      toast({
        title: "Document deleted",
        description: "The document has been deleted successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to delete document",
        description: error.message,
        variant: "destructive",
      });
    },
  });
  
  // Create folder mutation
  const createFolderMutation = useMutation({
    mutationFn: async (folder: FolderFormData) => {
      // Add current folder as parent if we're inside a folder
      const folderData = {
        ...folder,
        parentId: folder.parentId || currentFolderId
      };
      const res = await apiRequest("POST", "/api/folders", folderData);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/folders"] });
      toast({
        title: "Folder created",
        description: "Your folder has been created successfully.",
      });
      setShowFolderDialog(false);
      folderForm.reset();
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create folder",
        description: error.message,
        variant: "destructive",
      });
    },
  });
  
  // Update folder mutation
  const updateFolderMutation = useMutation({
    mutationFn: async ({ id, folder }: { id: string; folder: FolderFormData }) => {
      const res = await apiRequest("PATCH", `/api/folders/${id}`, folder);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/folders"] });
      toast({
        title: "Folder updated",
        description: "Your folder has been updated successfully.",
      });
      setShowFolderDialog(false);
      setEditingFolder(null);
      folderForm.reset();
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to update folder",
        description: error.message,
        variant: "destructive",
      });
    },
  });
  
  // Delete folder mutation
  const deleteFolderMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/folders/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/folders"] });
      queryClient.invalidateQueries({ queryKey: ["/api/documents"] });
      
      // If we deleted the current folder, go back to parent
      if (currentFolderId) {
        const currentFolder = folders?.find(f => f.id === currentFolderId);
        if (currentFolder) {
          setCurrentFolderId(currentFolder.parentId);
        }
      }
      
      toast({
        title: "Folder deleted",
        description: "The folder and its contents have been deleted.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to delete folder",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Handle form submission
  const onSubmit = (data: DocumentFormData) => {
    if (editingDocument) {
      updateDocumentMutation.mutate({ id: editingDocument.id, document: data });
    } else {
      createDocumentMutation.mutate(data);
    }
  };

  // Handle edit document
  const handleEditDocument = (document: Document) => {
    setEditingDocument(document);
    form.setValue("title", document.title);
    form.setValue("content", document.content);
    form.setValue("folderId", document.folderId);
    form.setValue("tags", document.tags.join(", ") as any);
    setShowDocumentDialog(true);
  };

  // Handle new document
  const handleNewDocument = () => {
    setEditingDocument(null);
    form.reset();
    
    // If we're in a folder, set the folder ID for the new document
    if (currentFolderId) {
      form.setValue('folderId', currentFolderId);
    }
    
    setShowDocumentDialog(true);
  };

  // Filter documents based on search query and current folder
  const filteredDocuments = documents?.filter(doc => {
    // Filter by search query if present
    const matchesSearch = !searchQuery || 
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Filter by current folder if not searching
    const matchesFolder = searchQuery ? true : (
      currentFolderId 
        ? doc.folderId === currentFolderId 
        : true // When on root, show documents without folder
    );
    
    return matchesSearch && matchesFolder;
  });

  // Format date function
  const formatDate = (dateString: Date) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  // Helper function to build breadcrumb path
  const updateFolderPath = (folderId: string | null) => {
    if (folderId === null) {
      setFolderPath([]);
      return;
    }
    
    // Find the current folder
    const currentFolder = folders?.find(f => f.id === folderId);
    if (!currentFolder) return;
    
    // Build the path from root to current folder
    const path: Folder[] = [currentFolder];
    let parentId = currentFolder.parentId;
    
    while (parentId) {
      const parent = folders?.find(f => f.id === parentId);
      if (parent) {
        path.unshift(parent); // Add parent to beginning of path
        parentId = parent.parentId;
      } else {
        break;
      }
    }
    
    setFolderPath(path);
  };
  
  // Effect to update folder path whenever current folder changes
  useEffect(() => {
    updateFolderPath(currentFolderId);
  }, [currentFolderId, folders]);
  
  // Handle folder selection
  const handleFolderSelect = (folderId: string) => {
    setCurrentFolderId(folderId);
  };
  
  // Handle new folder creation
  const handleNewFolder = () => {
    setEditingFolder(null);
    folderForm.reset();
    folderForm.setValue('parentId', currentFolderId);
    setShowFolderDialog(true);
  };
  
  // Handle folder editing
  const handleEditFolder = (folder: Folder) => {
    setEditingFolder(folder);
    folderForm.setValue('name', folder.name);
    folderForm.setValue('parentId', folder.parentId);
    setShowFolderDialog(true);
  };
  
  // Handle folder form submission
  const onFolderSubmit = (data: FolderFormData) => {
    if (editingFolder) {
      updateFolderMutation.mutate({ id: editingFolder.id, folder: data });
    } else {
      createFolderMutation.mutate(data);
    }
  };

  // Loading and error states
  if (documentsLoading || foldersLoading) {
    return (
      <Layout title="Document Vault">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-border" />
        </div>
      </Layout>
    );
  }

  if (documentsError || foldersError) {
    const errorMessage = documentsErrorData?.message || foldersErrorData?.message;
    return (
      <Layout title="Document Vault">
        <div className="flex flex-col items-center justify-center h-full gap-4">
          <p className="text-destructive font-medium">Error loading data</p>
          <p>{errorMessage}</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Document Vault">
      <div className="flex flex-col h-full overflow-hidden -m-6">
        <div className="bg-white border-b px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex-1 max-w-2xl">
            <div className="relative">
              <Input
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 bg-gray-50 h-10 border-gray-200"
              />
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 6.5C10 8.433 8.433 10 6.5 10C4.567 10 3 8.433 3 6.5C3 4.567 4.567 3 6.5 3C8.433 3 10 4.567 10 6.5ZM9.30884 10.0159C8.53901 10.6318 7.56251 11 6.5 11C4.01472 11 2 8.98528 2 6.5C2 4.01472 4.01472 2 6.5 2C8.98528 2 11 4.01472 11 6.5C11 7.56251 10.6318 8.53901 10.0159 9.30884L12.8536 12.1464C13.0488 12.3417 13.0488 12.6583 12.8536 12.8536C12.6583 13.0488 12.3417 13.0488 12.1464 12.8536L9.30884 10.0159Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd"></path></svg>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleNewFolder} variant="outline" className="rounded-full h-10 px-4">
              <FolderPlus className="w-4 h-4 mr-2" />
              New Folder
            </Button>
            <Button 
              onClick={() => {
                form.reset();
                form.setValue('title', 'Standard Operating Procedure: ');
                form.setValue('tags', 'sop, procedure, process' as any);
                setShowDocumentDialog(true);
              }} 
              variant="outline" 
              className="rounded-full h-10 px-4"
            >
              <i className="ri-file-list-3-line mr-2"></i>
              Create SOP
            </Button>
            <Button onClick={handleNewDocument} className="rounded-full h-10 px-4 bg-primary">
              <Plus className="w-4 h-4 mr-2" />
              New Document
            </Button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Similar to Google Drive */}
        <div className="w-60 border-r bg-white p-4 overflow-y-auto">
          <div className="space-y-1">
            <Button 
              variant={!currentFolderId ? "secondary" : "ghost"} 
              className="w-full justify-start mb-1"
              onClick={() => setCurrentFolderId(null)}
            >
              <i className="ri-home-line mr-2"></i>
              My Drive
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start text-gray-600"
              onClick={() => setSearchQuery("business plan")}
            >
              <i className="ri-file-chart-line mr-2"></i>
              Business Plans
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start text-gray-600"
              onClick={() => setSearchQuery("marketing")}
            >
              <i className="ri-megaphone-line mr-2"></i>
              Marketing Docs
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start text-gray-600"
              onClick={() => setSearchQuery("financial")}
            >
              <i className="ri-money-dollar-circle-line mr-2"></i>
              Financial Reports
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start text-gray-600"
              onClick={() => setSearchQuery("sop")}
            >
              <i className="ri-file-list-3-line mr-2"></i>
              SOPs
            </Button>
            
            <div className="py-2">
              <div className="h-[1px] bg-gray-200 my-2"></div>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 px-3">My Folders</h3>
              
              {folders?.filter(folder => folder.parentId === null).map(folder => (
                <Button 
                  key={folder.id}
                  variant={currentFolderId === folder.id ? "secondary" : "ghost"}
                  className="w-full justify-start mb-1 text-gray-700"
                  onClick={() => handleFolderSelect(folder.id)}
                >
                  <Folder className="h-4 w-4 mr-2 text-gray-500" />
                  <span className="truncate">{folder.name}</span>
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center mb-4 text-sm text-gray-600">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 px-2" 
              onClick={() => setCurrentFolderId(null)}
            >
              <Home className="h-4 w-4 mr-1" />
              My Drive
            </Button>
            
            {folderPath.map((folder, index) => (
              <div key={folder.id} className="flex items-center">
                <ChevronRight className="h-3.5 w-3.5 mx-1 text-gray-400" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2"
                  onClick={() => setCurrentFolderId(folder.id)}
                >
                  <span>{folder.name}</span>
                </Button>
              </div>
            ))}
          </div>

          {!searchQuery && folders && folders.filter(folder => folder.parentId === currentFolderId).length > 0 && (
            <>
              <h2 className="text-sm font-medium text-gray-500 mb-3">Folders</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
                {folders?.filter(folder => folder.parentId === currentFolderId).map(folder => (
                  <div 
                    key={folder.id} 
                    className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                    onClick={() => handleFolderSelect(folder.id)}
                  >
                    <div className="p-4 flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="bg-blue-50 rounded-lg p-2 mr-3">
                          <Folder className="h-5 w-5 text-blue-500" />
                        </div>
                        <span className="font-medium truncate">{folder.name}</span>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
                          <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                              <circle cx="12" cy="12" r="1" />
                              <circle cx="19" cy="12" r="1" />
                              <circle cx="5" cy="12" r="1" />
                            </svg>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={(e) => {
                            e.stopPropagation();
                            handleEditFolder(folder);
                          }}>
                            <FolderEdit className="mr-2 h-4 w-4" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm("Are you sure you want to delete this folder? All documents inside will be moved to the root.")) {
                                deleteFolderMutation.mutate(folder.id);
                              }
                            }}
                            className="text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <h2 className="text-sm font-medium text-gray-500 mb-3">
            {searchQuery ? "Search Results" : currentFolderId ? "Documents" : "Recent Documents"}
          </h2>

          {filteredDocuments?.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 bg-white rounded-lg border border-gray-200">
              <div className="bg-gray-100 p-4 rounded-full mb-3">
                <FileText className="h-8 w-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium mb-1">No documents found</h3>
              <p className="text-gray-500 text-center max-w-md mb-4">
                {documents?.length === 0
                  ? "Create your first document to get started"
                  : "No documents match your search criteria"}
              </p>
              <Button onClick={handleNewDocument} className="rounded-full">
                <Plus className="w-4 h-4 mr-2" />
                New Document
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredDocuments?.map((document) => (
                <div 
                  key={document.id} 
                  className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex items-start p-4 cursor-pointer group"
                  onClick={() => handleEditDocument(document)}
                >
                  <div className="flex-shrink-0 mr-4">
                    <div className="bg-primary/10 p-2 rounded">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-medium text-gray-900 truncate">{document.title}</h3>
                    <div className="flex items-center mt-2 text-xs text-gray-500">
                      <span>Modified {formatDate(document.updatedAt)}</span>
                    </div>
                  </div>
                  <div className="flex-shrink-0 ml-2 opacity-0 group-hover:opacity-100">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                            <circle cx="12" cy="12" r="1" />
                            <circle cx="19" cy="12" r="1" />
                            <circle cx="5" cy="12" r="1" />
                          </svg>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          handleEditDocument(document);
                        }}>
                          <Edit2 className="mr-2 h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm("Are you sure you want to delete this document?")) {
                              deleteDocumentMutation.mutate(document.id);
                            }
                          }}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Document Creation/Editing Dialog */}
      <Dialog open={showDocumentDialog} onOpenChange={setShowDocumentDialog}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingDocument ? "Edit Document" : "Create New Document"}</DialogTitle>
            <DialogDescription>
              {editingDocument
                ? "Update the details of your document."
                : "Enter the details for your new document or use AI to generate content."}
            </DialogDescription>
          </DialogHeader>

          {!editingDocument && (
            <div className="bg-secondary/20 p-3 rounded-md flex items-start gap-3 mb-4">
              <div className="bg-primary/10 p-1.5 rounded-full mt-0.5">
                <i className="ri-robot-line text-primary text-lg"></i>
              </div>
              <div>
                <h4 className="text-sm font-medium">AI-Generated Business Documents</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  Your AI agents can generate various business documents like business plans, marketing strategies, 
                  product descriptions, and financial reports. You can store them here for future reference.
                </p>
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="mt-2"
                  type="button"
                  onClick={() => {
                    // In a real implementation, this would open the agent chat
                    // with instructions to create a document
                    if (agents.length > 0) {
                      window.location.href = `/chat/${agents[0].id}?prompt=Please create a business document`;
                    } else {
                      setIsModalOpen(true);
                      setShowDocumentDialog(false);
                    }
                  }}
                >
                  <i className="ri-chat-3-line mr-1.5"></i>
                  Ask an Agent to Create Document
                </Button>
              </div>
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title</FormLabel>
                    <FormControl>
                      <Input placeholder="Document Title" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="content"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Content</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Write your document content here..."
                        {...field}
                        className="min-h-[200px]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="folderId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Folder</FormLabel>
                    <Select
                      value={field.value || ""}
                      onValueChange={(value) => field.onChange(value === "null" ? null : value)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a folder (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="null">
                          <div className="flex items-center">
                            <Home className="mr-2 h-4 w-4" />
                            <span>Root (No folder)</span>
                          </div>
                        </SelectItem>
                        {folders?.map((folder) => (
                          <SelectItem key={folder.id} value={folder.id}>
                            <div className="flex items-center">
                              <Folder className="mr-2 h-4 w-4" />
                              <span>{folder.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tags</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="business, report, strategy (comma separated)"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowDocumentDialog(false);
                    form.reset();
                    setEditingDocument(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createDocumentMutation.isPending || updateDocumentMutation.isPending
                  }
                >
                  {(createDocumentMutation.isPending || updateDocumentMutation.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingDocument ? "Update Document" : "Create Document"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
      
      {/* Folder Creation/Editing Dialog */}
      <Dialog open={showFolderDialog} onOpenChange={setShowFolderDialog}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingFolder ? "Edit Folder" : "Create New Folder"}</DialogTitle>
            <DialogDescription>
              {editingFolder
                ? "Update the folder details."
                : "Enter a name for your new folder."}
            </DialogDescription>
          </DialogHeader>

          <Form {...folderForm}>
            <form onSubmit={folderForm.handleSubmit(onFolderSubmit)} className="space-y-6">
              <FormField
                control={folderForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Folder Name</FormLabel>
                    <FormControl>
                      <Input placeholder="My Folder" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={folderForm.control}
                name="parentId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Parent Folder</FormLabel>
                    <Select
                      value={field.value || ""}
                      onValueChange={(value) => field.onChange(value === "null" ? null : value)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a parent folder (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="null">
                          <div className="flex items-center">
                            <Home className="mr-2 h-4 w-4" />
                            <span>Root (No parent)</span>
                          </div>
                        </SelectItem>
                        {folders?.filter(f => f.id !== editingFolder?.id).map((folder) => (
                          <SelectItem key={folder.id} value={folder.id}>
                            <div className="flex items-center">
                              <Folder className="mr-2 h-4 w-4" />
                              <span>{folder.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowFolderDialog(false);
                    folderForm.reset();
                    setEditingFolder(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createFolderMutation.isPending || updateFolderMutation.isPending
                  }
                >
                  {(createFolderMutation.isPending || updateFolderMutation.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingFolder ? "Update Folder" : "Create Folder"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
      
      {/* Agent Creation Modal */}
      <CreateAgentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />

      {/* Document Creation/Editing Dialog */}
      <Dialog open={showDocumentDialog} onOpenChange={setShowDocumentDialog}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingDocument ? "Edit Document" : "Create New Document"}</DialogTitle>
            <DialogDescription>
              {editingDocument
                ? "Update the details of your document."
                : "Enter the details for your new document or use AI to generate content."}
            </DialogDescription>
          </DialogHeader>

          {!editingDocument && (
            <div className="bg-secondary/20 p-3 rounded-md flex items-start gap-3 mb-4">
              <div className="bg-primary/10 p-1.5 rounded-full mt-0.5">
                <i className="ri-robot-line text-primary text-lg"></i>
              </div>
              <div>
                <h4 className="text-sm font-medium">AI-Generated Business Documents</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  Your AI agents can generate various business documents like business plans, marketing strategies, 
                  product descriptions, and financial reports. You can store them here for future reference.
                </p>
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="mt-2"
                  type="button"
                  onClick={() => {
                    // In a real implementation, this would open the agent chat
                    // with instructions to create a document
                    if (agents.length > 0) {
                      window.location.href = `/chat/${agents[0].id}?prompt=Please create a business document`;
                    } else {
                      setIsModalOpen(true);
                      setShowDocumentDialog(false);
                    }
                  }}
                >
                  <i className="ri-chat-3-line mr-1.5"></i>
                  Ask an Agent to Create Document
                </Button>
              </div>
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title</FormLabel>
                    <FormControl>
                      <Input placeholder="Document Title" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="content"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Content</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Write your document content here..."
                        {...field}
                        className="min-h-[200px]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="folderId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Folder</FormLabel>
                    <Select
                      value={field.value || ""}
                      onValueChange={(value) => field.onChange(value === "null" ? null : value)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a folder (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="null">
                          <div className="flex items-center">
                            <Home className="mr-2 h-4 w-4" />
                            <span>Root (No folder)</span>
                          </div>
                        </SelectItem>
                        {folders?.map((folder) => (
                          <SelectItem key={folder.id} value={folder.id}>
                            <div className="flex items-center">
                              <Folder className="mr-2 h-4 w-4" />
                              <span>{folder.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="tags"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tags</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="business, report, strategy (comma separated)"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowDocumentDialog(false);
                    form.reset();
                    setEditingDocument(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createDocumentMutation.isPending || updateDocumentMutation.isPending
                  }
                >
                  {(createDocumentMutation.isPending || updateDocumentMutation.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingDocument ? "Update Document" : "Create Document"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
      
      {/* Folder Creation/Editing Dialog */}
      <Dialog open={showFolderDialog} onOpenChange={setShowFolderDialog}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingFolder ? "Edit Folder" : "Create New Folder"}</DialogTitle>
            <DialogDescription>
              {editingFolder
                ? "Update the folder details."
                : "Enter a name for your new folder."}
            </DialogDescription>
          </DialogHeader>

          <Form {...folderForm}>
            <form onSubmit={folderForm.handleSubmit(onFolderSubmit)} className="space-y-6">
              <FormField
                control={folderForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Folder Name</FormLabel>
                    <FormControl>
                      <Input placeholder="My Folder" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={folderForm.control}
                name="parentId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Parent Folder</FormLabel>
                    <Select
                      value={field.value || ""}
                      onValueChange={(value) => field.onChange(value === "null" ? null : value)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a parent folder (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="null">
                          <div className="flex items-center">
                            <Home className="mr-2 h-4 w-4" />
                            <span>Root (No parent)</span>
                          </div>
                        </SelectItem>
                        {folders?.filter(f => f.id !== editingFolder?.id).map((folder) => (
                          <SelectItem key={folder.id} value={folder.id}>
                            <div className="flex items-center">
                              <Folder className="mr-2 h-4 w-4" />
                              <span>{folder.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowFolderDialog(false);
                    folderForm.reset();
                    setEditingFolder(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createFolderMutation.isPending || updateFolderMutation.isPending
                  }
                >
                  {(createFolderMutation.isPending || updateFolderMutation.isPending) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingFolder ? "Update Folder" : "Create Folder"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
      
      {/* Agent Creation Modal */}
      <CreateAgentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      </div>
    </Layout>
  );
}