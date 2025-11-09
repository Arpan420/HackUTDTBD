-- Database schema for conversation agent system
-- Run this script to initialize the database tables

-- Table 1: person_memories
-- Stores memories about specific people
CREATE TABLE IF NOT EXISTS person_memories (
    id SERIAL PRIMARY KEY,
    person_id VARCHAR(255),
    memory_text TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conversation_id VARCHAR(255)
);

-- Table 2: todos
-- Stores todo list items
CREATE TABLE IF NOT EXISTS todos (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    person_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    conversation_id VARCHAR(255)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_person_memories_person_id ON person_memories(person_id);
CREATE INDEX IF NOT EXISTS idx_person_memories_conversation_id ON person_memories(conversation_id);
CREATE INDEX IF NOT EXISTS idx_todos_person_id ON todos(person_id);
CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_conversation_id ON todos(conversation_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_person_memories_updated_at BEFORE UPDATE ON person_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Table 3: faces
-- Stores face recognition data and person information
CREATE TABLE IF NOT EXISTS faces (
    person_id VARCHAR(255) PRIMARY KEY,
    person_name VARCHAR(255) DEFAULT 'Unknown',
    embedding BYTEA,
    count INTEGER DEFAULT 0,
    socials JSONB,
    recap TEXT
);

-- Table 4: summaries
-- Stores conversation summaries for each person
CREATE TABLE IF NOT EXISTS summaries (
    summary_id SERIAL PRIMARY KEY,
    person_id VARCHAR(255) NOT NULL,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_summaries_person_id ON summaries(person_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at);

