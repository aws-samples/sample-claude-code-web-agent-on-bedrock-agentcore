# Authentication Quick Start Guide

## 🚀 Getting Started with AWS Cognito Authentication

The web client now requires authentication. Here's how to get started:

## Prerequisites

- Node.js and npm installed
- AWS Cognito user pool configured (already done)
- Email address for signup

## Step 1: Install Dependencies

```bash
npm install
```

Dependencies are already in `package.json`:
- `aws-amplify` - AWS authentication SDK
- `@aws-amplify/ui-react` - React UI components

## Step 2: Start the Application

```bash
# Development mode
npm run dev

# Or build for production
npm run build
npm run preview
```

The app will open at `http://localhost:8080`

## Step 3: Create Your Account

### First Time Users

1. **Click "Sign Up"** on the login screen

2. **Enter your details**:
   - Email address (must be valid)
   - Password (minimum 8 characters)
   - Confirm password

3. **Submit registration**
   - Click "Sign Up" button
   - You'll see: "Account created! Check your email for verification code."

4. **Check your email**:
   - Subject: "Your verification code"
   - From: no-reply@verificationemail.com
   - Contains a 6-digit code

5. **Verify your email**:
   - Enter the 6-digit code
   - Click "Verify Email"
   - You'll be redirected to login

6. **Log in**:
   - Enter your email and password
   - Click "Sign In"
   - You're in! 🎉

### Verification Code Not Received?

- Check spam/junk folder
- Click "Resend Code" button
- Wait 1-2 minutes for delivery

## Step 4: Using the Application

Once logged in, you'll see:

- **User email** displayed in header
- **Logout button** in header
- **Session list** in sidebar
- **Chat interface** in main area

Everything works the same as before, just with authentication!

## Common Operations

### Login

```
1. Enter email
2. Enter password
3. Click "Sign In"
```

### Logout

```
Click the logout button (🚪 icon) in the header
```

### Switch Between Login/Signup

```
Use the "Sign In" / "Sign Up" link at the bottom of the form
```

## Troubleshooting

### "Incorrect username or password"

- Double-check email and password
- Ensure you verified your email
- Passwords are case-sensitive

### "User does not exist"

- Complete the signup process
- Verify your email with the code

### Email not received

1. Check spam folder
2. Verify email address is correct
3. Click "Resend Code"
4. Wait a few minutes

### Cannot login after signup

- You MUST verify your email first
- Check for verification code email
- Use the verification screen

## Configuration Details

### Environment Variables

Cognito configuration is loaded from environment variables in the `.env` file:

```bash
# AWS Cognito Configuration
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_Sw8yyFfBT
VITE_COGNITO_CLIENT_ID=2d2cqqjvpf1ecqjg6gh1u6fivl
```

**Default configuration is already set!** Just start using it.

### Using Your Own Cognito Pool

If you want to use a different Cognito user pool:

1. Copy `.env.example` to `.env`
2. Update the Cognito variables with your pool details:
   - `VITE_COGNITO_REGION`: Your AWS region
   - `VITE_COGNITO_USER_POOL_ID`: Your user pool ID
   - `VITE_COGNITO_CLIENT_ID`: Your client ID
3. Restart the dev server

The configuration is in `src/config/cognito.js` and automatically loads from environment variables.

## Security Notes

✅ **Passwords are secure**:
- Minimum 8 characters
- Hashed and encrypted by AWS
- Never stored in plain text

✅ **Email verification required**:
- Prevents fake accounts
- Ensures valid contact info

✅ **Session tokens**:
- Stored securely in memory
- Automatic refresh
- Cleared on logout

## Architecture

```
User → Login Screen → AWS Cognito → Verify Email → Main App
                         ↓
                   Secure Session
                         ↓
                   User Authenticated
```

## Testing Credentials

**For testing, create your own account:**

1. Use any valid email you have access to
2. Create a secure password (min 8 chars)
3. Verify with the code sent to your email
4. Start using the app!

## Need Help?

### Check These Files:

- **AUTHENTICATION.md** - Detailed authentication guide
- **README.md** - General application guide
- **package.json** - Installed dependencies

### Console Errors:

Open browser DevTools (F12) → Console tab for error messages

### Still Stuck?

The authentication is standard AWS Cognito. Any AWS Cognito documentation applies here.

## What's Next?

After logging in:

1. Configure your API server settings (⚙️ button)
2. Create or load a session
3. Start chatting with Claude Agent!

---

**Happy coding! 🚀**
