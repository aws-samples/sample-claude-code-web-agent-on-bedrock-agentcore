# Quick Start Guide

Get up and running with the Claude Agent Web Client in 4 simple steps!

## Step 1: Start the API Server

In a terminal, navigate to the api_server directory and start the server:

```bash
cd /path/to/claude-agent-sdk-python/api_server
python -m uvicorn src.server:app --host 127.0.0.1 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Important**: The server includes CORS middleware to allow web browser access. If you previously started the server, please restart it to pick up the CORS configuration.

## Step 2: Install Dependencies

In a new terminal, navigate to the web_client directory and install dependencies:

```bash
cd web_client
npm install
```

## Step 3: Start the Web Client

Start the Vite development server:

```bash
npm run dev
```

You should see:
```
  VITE v7.1.12  ready in XXX ms

  ➜  Local:   http://localhost:8080/
  ➜  press h + enter to show help
```

## Step 4: Open in Browser

Open your web browser and go to:
```
http://localhost:8080
```

## First Time Configuration

When you first open the web client, you'll see the configuration panel:

### For Claude Models:
1. **Server URL**: Leave as `http://127.0.0.1:8000`
2. **Main Model**: Enter `claude-3-5-sonnet-20241022`
3. **Background Model**: Enter `claude-3-5-haiku-20241022`
4. **Proxy Mode**: Check this box ✓
5. Click **Connect**

### For OpenAI Models:
1. **Server URL**: Leave as `http://127.0.0.1:8000`
2. **Main Model**: Enter `gpt-4`
3. **Background Model**: Enter `gpt-3.5-turbo`
4. **Proxy Mode**: Check this box ✓
5. Click **Connect**

## Start Chatting!

Once connected, you'll see:
- ✅ Green "Connected" indicator in the header
- The chat interface with message area
- An input box at the bottom

Just type your message and press Enter (or click Send)!

## Tips

- **New Session**: Click "New Session" button to start fresh
- **Disconnect**: Click "Disconnect" to go back to configuration
- **Permissions**: If Claude needs to use a tool, you'll see a dialog to approve/deny
- **Multiline**: Use Shift+Enter to add line breaks in your message

## Troubleshooting

### Connection Failed?
- Make sure the API server is running (Step 1)
- Check that the URL is `http://127.0.0.1:8000` (not https, not localhost)
- Look at the browser console (F12) for error details

### Can't Access Web Client?
- Make sure `serve.py` is running (Step 2)
- Try a different port: `python serve.py 3000`
- Check if another application is using port 8080

### Messages Not Sending?
- Check the connection status (should show green dot)
- Refresh the page and reconnect
- Verify the API server is still running

## Need Help?

Check out the full documentation:
- [Web Client README](README.md) - Complete features and configuration
- [API Server README](../README.md) - Server setup and API details

Enjoy using Claude Agent! 🎉
