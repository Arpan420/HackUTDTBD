# Supabase Database Setup Guide

## Step 1: Create a Supabase Project

1. Go to https://supabase.com/
2. Sign up or log in
3. Click "New Project"
4. Fill in:
   - **Name**: Your project name (e.g., "mentra")
   - **Database Password**: Choose a strong password (save this!)
   - **Region**: Choose closest to you
5. Wait for project to be created (takes ~2 minutes)

## Step 2: Get Your Connection String

1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection string**
3. **Important**: Use the **Session Pooler** connection string (not Direct connection)
   - Direct connection may show "Not IPv4 compatible" - don't use this
   - Select **Session mode** or **Transaction mode** from the pooler dropdown
   - Copy the connection string from the **Connection pooling** section
4. The pooler connection string looks like:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with the password you set when creating the project

**Note**: If you see "Not IPv4 compatible" on the Direct connection, you MUST use the Session Pooler connection string instead.

## Step 3: Set DATABASE_URL

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Then edit `.env` and set your DATABASE_URL using the **Session Pooler** connection string:

```bash
# Use Session Pooler (recommended for IPv4 networks)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:your_password@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

**Important**:

- Use the **Session Pooler** connection string (not Direct connection)
- Replace `your_password` with your actual database password
- Replace `[PROJECT-REF]` with your project reference
- Replace `[REGION]` with your region (e.g., `us-east-1`, `eu-west-1`)
- The port for pooler is **6543** (not 5432)

## Step 4: Configure IP Allowlist (if needed)

If you get connection errors:

1. Go to **Settings** → **Database** → **Connection Pooling**
2. Check **Connection string** settings
3. For local development, you may need to add your IP to the allowlist:
   - Go to **Settings** → **Database** → **Network Restrictions**
   - Add your IP address or use `0.0.0.0/0` for development (not recommended for production)

## Step 5: Run the Setup Script

```bash
cd /Users/davis/Library/asdf/GitHub/HackUTDTBD
python database/setup.py
```

This will create all the required tables in your Supabase database.

## Connection String Format

### Session Pooler (Recommended - IPv4 compatible)

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

Where:

- `[PROJECT-REF]` = Your project reference (found in dashboard URL)
- `[PASSWORD]` = Your database password (set when creating project)
- `[REGION]` = Your region (e.g., `us-east-1`, `eu-west-1`)
- Port: **6543** (pooler port)

### Direct Connection (IPv6 only - may not work on all networks)

```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Note**: If you see "Not IPv4 compatible" on Direct connection, use Session Pooler instead.

## Troubleshooting

### "Failed to connect to database"

- **Check your password**: Make sure you replaced `[YOUR-PASSWORD]` with your actual password
- **Check project reference**: Verify the project ref in the connection string matches your dashboard URL
- **Check IP allowlist**: Your IP might need to be added to Supabase network restrictions
- **Check project status**: Make sure your Supabase project is active (not paused)

### "password authentication failed"

- Verify you're using the correct database password (not your Supabase account password)
- The password is the one you set when creating the project
- You can reset it in: **Settings** → **Database** → **Database password**

### "connection timeout"

- Check your internet connection
- Verify your IP is allowed in Supabase network restrictions
- Try using connection pooling mode (see below)

### Using Connection Pooling (Optional)

For better performance, you can use Supabase's connection pooling:

1. Go to **Settings** → **Database** → **Connection Pooling**
2. Select **Session mode** or **Transaction mode**
3. Copy the **Connection string** from the **Connection pooling** section
4. Use that connection string in your `.env` file

The pooled connection string looks like:

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

## Quick Test

Test your connection:

```bash
# Set your DATABASE_URL first
export DATABASE_URL="postgresql://postgres:password@db.project.supabase.co:5432/postgres"

# Test connection (if you have psql installed)
psql $DATABASE_URL -c "SELECT version();"
```

Or use the setup script which will test the connection for you.

## Security Notes

- **Never commit your `.env` file** - it contains sensitive credentials
- The `.env` file is already in `.gitignore`
- For production, use environment variables or a secrets manager
- Consider using connection pooling for production workloads
