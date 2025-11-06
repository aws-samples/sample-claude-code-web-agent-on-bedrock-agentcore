# Cognito User Registration - Quick Setup

This is a quick reference guide for configuring AWS Cognito user registration. For full details, see [cognito-signup-guide.md](cognito-signup-guide.md).

## ✅ What's Already Implemented

The user registration feature is **fully implemented** with:
- Sign up form (username, email, password)
- Email verification with code
- Code resend functionality
- Auto-redirect to login after verification
- Switch between login and signup pages

## 🔧 What You Need to Configure

### 1. Environment Variables

Edit `web_client/.env`:

```bash
# AWS Region (where your Cognito User Pool is located)
VITE_COGNITO_REGION=us-west-2

# Your Cognito User Pool ID (format: region_poolId)
VITE_COGNITO_USER_POOL_ID=us-west-2_XXXXXXXXX

# Your Cognito User Pool Client ID
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. Get Your Cognito Configuration Values

#### AWS Console → Cognito → User Pools:

1. **User Pool ID**:
   - Select your user pool
   - Copy the "User pool ID" from overview (e.g., `us-west-2_Sw8yyFfBT`)

2. **Client ID**:
   - In your user pool, go to "App integration" tab
   - Scroll to "App clients and analytics"
   - Copy the "Client ID" (e.g., `2d2cqqjvpf1ecqjg6gh1u6fivl`)

3. **Region**:
   - It's the first part of your User Pool ID (e.g., `us-west-2`)

## 🎯 Cognito User Pool Requirements

Your Cognito User Pool must have these settings:

### Essential Settings

✅ **Sign-up**: Self-registration enabled
✅ **Email**: Email verification required
✅ **App Client**: No secret (for public web client)
✅ **Auth Flows**: `USER_PASSWORD_AUTH` enabled

### Password Policy (Default)

- Minimum 8 characters
- Uppercase, lowercase, numbers, special characters

### Email Configuration

**Development**: Use Cognito's default email (50 emails/day free)

**Production**: Configure Amazon SES for higher limits

## 📋 Quick Test

1. Start web client:
   ```bash
   cd web_client
   npm run dev
   ```

2. Open http://localhost:8080

3. Click "Sign Up" link

4. Fill in registration form:
   - Username: `testuser`
   - Email: `your-email@example.com`
   - Password: Must meet policy (8+ chars, mixed case, numbers, symbols)

5. Check your email for verification code (6 digits)

6. Enter code and click "Verify Email"

7. Login with new credentials

## ⚠️ Common Issues

### Email not received?
- Check spam folder
- Verify email configuration in Cognito
- Check Cognito's 50/day email limit (default)

### Signup fails?
- Check browser console for errors
- Verify environment variables are set
- Ensure User Pool allows self-registration
- Check password meets policy requirements

### Cannot login after verification?
- Verify user status is "CONFIRMED" in Cognito console
- Check for account lockout due to failed attempts
- Try password reset

## 🔗 Related Files

**Configuration**:
- `web_client/.env` - Environment variables
- `web_client/src/config/cognito.js` - Cognito config

**Components**:
- `web_client/src/components/Signup.jsx` - Signup UI
- `web_client/src/components/Login.jsx` - Login UI
- `web_client/src/hooks/useAuth.jsx` - Auth logic

## 📚 Full Documentation

For complete details, see:
- [Cognito Signup Guide](cognito-signup-guide.md) - Full documentation
- [Web Client README](web-client/readme.md) - Web client overview
- [AWS Amplify Auth Docs](https://docs.amplify.aws/javascript/build-a-backend/auth/)

## 🚀 Production Checklist

Before deploying to production:

- [ ] Switch to Amazon SES for email (not Cognito default)
- [ ] Configure production `.env` file
- [ ] Test email deliverability
- [ ] Enable MFA (optional but recommended)
- [ ] Set up account recovery options
- [ ] Configure custom email templates
- [ ] Test full signup flow end-to-end
