# Database Setup

This directory contains scripts for setting up the Supabase (PostgreSQL) database.

## Quick Start

1. **Create a Supabase project**:

   - Go to https://supabase.com/
   - Sign up or log in
   - Create a new project
   - Save your database password

2. **Get your connection string**:

   - In Supabase Dashboard: **Settings** → **Database** → **Connection string** → **URI**
   - Copy the connection string

3. **Set DATABASE_URL** in your `.env` file (in project root):

   ```bash
   # Copy example file
   cp .env.example .env

   # Edit .env and set your Supabase connection string:
   DATABASE_URL=postgresql://postgres:your_password@db.your_project_ref.supabase.co:5432/postgres
   ```

4. **Install dependencies** (if not already installed):

   ```bash
   pip install -r database/requirements.txt
   ```

5. **Run the setup script**:
   ```bash
   python database/setup.py
   ```

## What the Setup Script Does

The setup script will:

- Check that `DATABASE_URL` is set
- Connect to your Supabase database
- Create all required tables:
  - `person_memories` - Stores memories about people
  - `todos` - Stores todo list items
  - `faces` - Stores face recognition data and person information
  - `summaries` - Stores conversation summaries
- Create indexes for efficient queries
- Set up triggers and functions

## Troubleshooting

### "DATABASE_URL not found"

Make sure you have a `.env` file in the project root with `DATABASE_URL` set.

### "Failed to connect to database"

- Verify your Supabase connection string is correct
- Check that your Supabase project is active (not paused)
- Make sure your IP is allowed in Supabase network restrictions
- Verify you replaced `[YOUR-PASSWORD]` with your actual password

### "psycopg2-binary not installed"

Install the required packages:

```bash
pip install -r database/requirements.txt
```

## Detailed Setup Guide

See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed instructions and troubleshooting.

## Manual Setup

If you prefer to set up the database manually, you can run the SQL migration directly in Supabase:

1. Go to **SQL Editor** in Supabase Dashboard
2. Copy the contents of `back_end/speech/conversation/migrations/init_schema.sql`
3. Paste and run it in the SQL Editor
