# Database Configuration for Deployment

## Problem
If you see the error: `"Can't connect to MySQL server on 'localhost' (Connection refused)"`, this means your application is trying to connect to a database on localhost, which won't work in production.

## Solution: Set Environment Variables

### For Render.com:

1. **Go to your Render Dashboard**
   - Navigate to your Web Service
   - Click on "Environment" in the left sidebar

2. **Add these Environment Variables:**
   ```
   MYSQL_HOST=your-database-host.render.com
   MYSQL_USER=your-database-user
   MYSQL_PASSWORD=your-database-password
   MYSQL_DB=bus_management
   MYSQL_PORT=3306
   ```

   **OR** (alternative names also supported):
   ```
   DB_HOST=your-database-host.render.com
   DB_USER=your-database-user
   DB_PASSWORD=your-database-password
   DB_NAME=bus_management
   DB_PORT=3306
   ```

3. **If using Render's Managed MySQL:**
   - Go to your MySQL database service on Render
   - Copy the "Internal Database URL" or "External Database URL"
   - The format is usually: `mysql://user:password@hostname:port/database`
   - Extract the values and set them as environment variables

4. **After adding environment variables:**
   - Click "Save Changes"
   - Render will automatically redeploy your service

### For Vercel:

1. **Go to your Vercel Project Dashboard**
   - Select your project
   - Go to "Settings" → "Environment Variables"

2. **Add the same environment variables as above**

3. **For each environment (Production, Preview, Development):**
   - Add: `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `MYSQL_PORT`

## Getting Database Connection Details

### If using Render Managed MySQL:
1. Go to your MySQL database service
2. Under "Connections", you'll find:
   - **Internal Database URL** (for services on Render)
   - **External Database URL** (for external connections)
3. Parse the URL to get individual values:
   - Format: `mysql://user:password@hostname:port/database`
   - Example: `mysql://user:pass@dpg-xxxxx-a.render.com:5432/bus_management`

### If using external MySQL (like PlanetScale, AWS RDS, etc.):
- Use the connection details provided by your database service
- Make sure the database allows connections from your deployment platform

## Testing the Connection

After setting environment variables, check the deployment logs to see:
- `Successfully connected to MySQL at hostname:port` (success)
- Or error messages that will help diagnose the issue

## Common Issues:

1. **Still connecting to localhost:**
   - Make sure environment variables are set correctly
   - Check for typos in variable names
   - Restart/redeploy your service after adding variables

2. **Connection timeout:**
   - Check if your database allows external connections
   - Verify firewall/security group settings
   - Use Internal Database URL if both services are on Render

3. **Authentication failed:**
   - Double-check username and password
   - Ensure the user has proper permissions
   - Verify the database name is correct

## Local Development

For local development, you can:
1. Create a `.env` file in the project root:
   ```
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=1239
   MYSQL_DB=bus_management
   MYSQL_PORT=3306
   ```

2. Or use the default values (localhost) when running locally

