# Quick Setup Guide for Render.com

## Step-by-Step: Setting Up Database Environment Variables

### Step 1: Access Your Render Dashboard
1. Go to [render.com](https://render.com) and log in
2. Click on your **Web Service** (the Flask app)

### Step 2: Navigate to Environment Settings
1. In the left sidebar, click **"Environment"**
2. You'll see a list of current environment variables (might be empty)

### Step 3: Add Database Environment Variables

Click **"Add Environment Variable"** and add each of these:

#### Variable 1: MYSQL_HOST
- **Key:** `MYSQL_HOST`
- **Value:** Your database hostname
  - If using **Render Managed MySQL**: Go to your MySQL database service → Copy the hostname from "Internal Database URL" (looks like `dpg-xxxxx-a.render.com`)
  - If using **External MySQL**: Use your database provider's hostname

#### Variable 2: MYSQL_USER
- **Key:** `MYSQL_USER`
- **Value:** Your database username
  - From your database connection string or database settings

#### Variable 3: MYSQL_PASSWORD
- **Key:** `MYSQL_PASSWORD`
- **Value:** Your database password
  - From your database connection string or database settings

#### Variable 4: MYSQL_DB
- **Key:** `MYSQL_DB`
- **Value:** `bus_management`
  - (Or whatever your database name is)

#### Variable 5: MYSQL_PORT
- **Key:** `MYSQL_PORT`
- **Value:** `3306`
  - (Default MySQL port, change if your database uses a different port)

### Step 4: Save and Redeploy
1. Click **"Save Changes"** at the bottom
2. Render will automatically redeploy your service
3. Wait for deployment to complete (usually 2-5 minutes)

### Step 5: Verify Setup
1. After deployment, visit: `https://your-app-name.onrender.com/db-config`
2. Check that all variables show as "set"
3. Visit: `https://your-app-name.onrender.com/test-db`
4. Should show "status": "success"

---

## If Using Render Managed MySQL

### Finding Your Database Connection Details:

1. **Go to your MySQL Database Service** (separate from your Web Service)
2. **Click on "Connections"** tab
3. You'll see:
   - **Internal Database URL** - Use this if both services are on Render
   - **External Database URL** - Use this for external connections

### Parsing the Database URL:

The URL format is: `mysql://user:password@hostname:port/database`

Example: `mysql://user:abc123@dpg-xxxxx-a.render.com:5432/bus_management`

Break it down:
- **MYSQL_HOST** = `dpg-xxxxx-a.render.com`
- **MYSQL_USER** = `user`
- **MYSQL_PASSWORD** = `abc123`
- **MYSQL_PORT** = `5432` (or `3306` for MySQL)
- **MYSQL_DB** = `bus_management`

---

## Quick Checklist

- [ ] Logged into Render Dashboard
- [ ] Opened your Web Service
- [ ] Clicked "Environment" in sidebar
- [ ] Added `MYSQL_HOST` with database hostname
- [ ] Added `MYSQL_USER` with database username
- [ ] Added `MYSQL_PASSWORD` with database password
- [ ] Added `MYSQL_DB` with `bus_management`
- [ ] Added `MYSQL_PORT` with `3306`
- [ ] Clicked "Save Changes"
- [ ] Waited for redeploy to complete
- [ ] Tested with `/db-config` endpoint
- [ ] Tested with `/test-db` endpoint

---

## Troubleshooting

### Still seeing "connection settings are missing"?
- Make sure you saved the environment variables
- Wait for the redeploy to complete (check the "Events" tab)
- Verify variable names are exactly: `MYSQL_HOST`, `MYSQL_USER`, etc. (case-sensitive)

### Getting connection refused errors?
- Verify the hostname is correct (not `localhost`)
- Check if you're using Internal vs External Database URL
- Ensure database service is running (green status)

### Variables show as "set" but connection fails?
- Double-check the values (especially password - no extra spaces)
- Verify database name matches exactly
- Check if port is correct (3306 for MySQL, 5432 for PostgreSQL)

---

## Need Help?

1. Check Render logs: Dashboard → Your Service → "Logs" tab
2. Visit diagnostic endpoints:
   - `/db-config` - Shows configuration
   - `/test-db` - Tests connection
3. Check database service status in Render Dashboard

