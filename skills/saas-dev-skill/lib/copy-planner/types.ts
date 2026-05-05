import { z } from "zod";

export const PageCopySchema = z.object({
  pageName: z.string().min(1),
  pageHeading: z.string().min(1),
  pageSubheading: z.string().optional(),
  sections: z.array(z.object({
    name: z.string(),
    heading: z.string(),
    body: z.string().optional(),
  })).default([]),
  ctas: z.array(z.object({
    id: z.string(),
    label: z.string(),
    context: z.string(),
  })).default([]),
  emptyState: z.string().default(""),
  errorMessages: z.record(z.string()).default({}),
  placeholders: z.record(z.string()).default({}),
  helperText: z.record(z.string()).default({}),
  successMessages: z.record(z.string()).default({}),
  navLabel: z.string().min(1),
});
export type PageCopy = z.infer<typeof PageCopySchema>;

export const ProjectCopySchema = z.object({
  pages: z.array(PageCopySchema).min(1),
  generatedAt: z.string(),
  brandVoiceHash: z.string(),
});
export type ProjectCopy = z.infer<typeof ProjectCopySchema>;
