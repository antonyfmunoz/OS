import { Button } from "@/components/ui/button";
import { UseFormReturn } from "react-hook-form";

interface TemplateButtonProps {
  form: UseFormReturn<any>;
  username?: string;
  type?: "sop" | "legal" | "meeting";
}

export function TemplateButton({ form, username, type = "sop" }: TemplateButtonProps) {
  const handleClick = () => {
    if (type === "sop") {
      form.setValue('title', 'Standard Operating Procedure: ');
      form.setValue('content', 
`# STANDARD OPERATING PROCEDURE

## 1. PURPOSE
[Describe the purpose of this procedure]

## 2. SCOPE
[Define what operations, processes, or departments this SOP applies to]

## 3. RESPONSIBILITIES
[List roles and their responsibilities in executing this procedure]

### Role 1: [e.g., Manager]
- Responsibility 1
- Responsibility 2

### Role 2: [e.g., Employee]
- Responsibility 1
- Responsibility 2

## 4. PROCEDURE
[Detail the step-by-step process]

### 4.1 [First Major Step]
1. Sub-step 1
2. Sub-step 2
3. Sub-step 3

### 4.2 [Second Major Step]
1. Sub-step 1
2. Sub-step 2
3. Sub-step 3

## 5. QUALITY CONTROL
[Describe how to verify the procedure was completed correctly]

## 6. EXCEPTIONS
[List any exceptions to this procedure and how to handle them]

## 7. REFERENCES
[List related documents, regulations, or other resources]

## 8. REVISION HISTORY

| Version | Date | Description of Change | Author |
|---------|------|---------------------|--------|
| 1.0 | ${new Date().toLocaleDateString()} | Initial creation | ${username || ''} |`);
      form.setValue('tags', 'sop, procedure, process' as any);
    } else if (type === "legal") {
      form.setValue('title', 'Legal Document: ');
      form.setValue('content', 
`# LEGAL DOCUMENT

## PARTIES
[List all parties involved in this agreement]

## EFFECTIVE DATE
${new Date().toLocaleDateString()}

## RECITALS
WHEREAS, [state the background facts and circumstances];

WHEREAS, [state the purpose or intent of the agreement];

NOW, THEREFORE, in consideration of the mutual covenants contained herein and other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the parties agree as follows:

## 1. DEFINITIONS
[Define key terms used throughout the document]

## 2. TERMS AND CONDITIONS
[Detail the specific terms of the agreement]

### 2.1 [First Term]
[Description of the term]

### 2.2 [Second Term]
[Description of the term]

## 3. REPRESENTATIONS AND WARRANTIES
[List any guarantees or promises made by the parties]

## 4. TERM AND TERMINATION
[Specify duration and conditions for ending the agreement]

## 5. CONFIDENTIALITY
[Outline requirements for handling sensitive information]

## 6. GOVERNING LAW
This Agreement shall be governed by the laws of [Jurisdiction].

## 7. MISCELLANEOUS
[Include any other provisions not covered above]

## 8. SIGNATURES

________________________
[Party 1 Name]
Date: 

________________________
[Party 2 Name]
Date:

Prepared by: ${username || '[Enter name]'}`);
      form.setValue('tags', 'legal, contract, agreement' as any);
    } else if (type === "meeting") {
      form.setValue('title', 'Meeting Minutes: ');
      form.setValue('content', 
`# MEETING MINUTES

## MEETING DETAILS
- **Date:** ${new Date().toLocaleDateString()}
- **Time:** ${new Date().toLocaleTimeString()}
- **Location:** [Virtual/Physical location]
- **Meeting Type:** [Regular/Special/Emergency]

## ATTENDEES
- [List of attendees with roles]
- [Indicate who was present and who was absent]

## AGENDA ITEMS
1. **Call to Order**
   - Meeting called to order at [time] by [name]

2. **Approval of Previous Minutes**
   - [Decision on previous meeting minutes]

3. **[Agenda Item 1]**
   - Discussion: [Summary of discussion]
   - Action Items:
     - [Action item 1] - Assigned to: [Name], Due: [Date]
     - [Action item 2] - Assigned to: [Name], Due: [Date]
   - Decisions:
     - [Decision made]

4. **[Agenda Item 2]**
   - Discussion: [Summary of discussion]
   - Action Items:
     - [Action item 1] - Assigned to: [Name], Due: [Date]
   - Decisions:
     - [Decision made]

## OTHER BUSINESS
- [Any additional items discussed]

## NEXT MEETING
- **Date:** [Next meeting date]
- **Time:** [Next meeting time]
- **Location:** [Next meeting location]
- **Agenda Items:** [Preliminary agenda for next meeting]

## ADJOURNMENT
- Meeting adjourned at [time]

## APPROVAL
These minutes were prepared by ${username || '[Preparer Name]'} and will be approved at the next meeting.`);
      form.setValue('tags', 'meeting, minutes, notes' as any);
    }
  };

  let icon = "ri-file-list-3-line";
  let label = "Use SOP Template";
  
  if (type === "legal") {
    icon = "ri-file-paper-2-line";
    label = "Use Legal Template";
  } else if (type === "meeting") {
    icon = "ri-calendar-check-line";
    label = "Use Meeting Template";
  }

  return (
    <Button 
      size="sm" 
      variant="secondary" 
      type="button"
      onClick={handleClick}
    >
      <i className={`${icon} mr-1.5`}></i>
      {label}
    </Button>
  );
}

export function SOPTemplateButton(props: Omit<TemplateButtonProps, 'type'>) {
  return <TemplateButton {...props} type="sop" />;
}

export function LegalTemplateButton(props: Omit<TemplateButtonProps, 'type'>) {
  return <TemplateButton {...props} type="legal" />;
}

export function MeetingTemplateButton(props: Omit<TemplateButtonProps, 'type'>) {
  return <TemplateButton {...props} type="meeting" />;
}