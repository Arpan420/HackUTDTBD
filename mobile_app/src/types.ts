export type Summary = {
    id: string;
    text: string; // AI generated summary text
    createdAt: string; // ISO timestamp 
    sources?: string[]; // ID of transcript chunks 
}

export type Interaction = {
    id: string;
    when: string; // ISO timestamp
    location?: string;
    notes?: string; // quick notes
    summaryId: string; // links to summary 
}

export type Person = {
    id: string; 
    Name: string;
    lastSeen?: string; 
    phoneNumber?: string;
    summaries: Summary[];
    interactions: Interaction[];
}