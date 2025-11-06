# AWS Cognito Authentication Guide

This document explains how AWS Cognito authentication is integrated into the Claude Agent Web Client.

## Overview

The web client now requires users to authenticate via AWS Cognito before accessing the application. This provides secure user management with email verification.

## Cognito Configuration

### Pool Details

- **Region**: `us-west-2`
- **User Pool ID**: `us-west-2_Sw8yyFfBT`
- **Client ID**: `2d2cqqjvpf1ecqjg6gh1u6fivl`
- **Discovery URL**: `https://cognito-idp.us-west-2.amazonaws.com/us-west-2_Sw8yyFfBT/.well-known/openid-configuration`

### Configuration File

Configuration is stored in `src/config/cognito.js`:

```javascript
export const cognitoConfig = {
  region: 'us-west-2',
  userPoolId: 'us-west-2_Sw8yyFfBT',
  userPoolClientId: '2d2cqqjvpf1ecqjg6gh1u6fivl'
}
```

## Architecture

### Components

1. **AuthProvider** (`src/hooks/useAuth.jsx`)
   - React Context Provider for authentication state
   - Wraps entire application
   - Manages user session

2. **Login Component** (`src/components/Login.jsx`)
   - Email/password login form
   - Error handling
   - Link to signup

3. **Signup Component** (`src/components/Signup.jsx`)
   - User registration form
   - Email verification flow
   - Password validation
   - Resend verification code

4. **App Integration** (`src/App.jsx`)
   - Shows auth screens when not logged in
   - Shows main app when authenticated
   - Loading state during auth check

5. **Header Updates** (`src/components/Header.jsx`)
   - Displays logged-in user email
   - Logout button

### Authentication Flow

```
┌─────────────────────────────────────────┐
│         User Opens Application          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    AuthProvider Checks Current User     │
└──────────────┬──────────────────────────┘
               │
      ┌────────┴─────────┐
      │                  │
      ▼                  ▼
┌──────────┐      ┌─────────────┐
│ Logged   │      │ Not Logged  │
│ In       │      │ In          │
└────┬─────┘      └──────┬──────┘
     │                   │
     ▼                   ▼
┌──────────┐      ┌─────────────┐
│ Show     │      │ Show Login/ │
│ Main App │      │ Signup      │
└──────────┘      └─────────────┘
```

## User Flows

### Sign Up Flow

1. User clicks "Sign Up" on login screen
2. Enters email and password (min 8 characters)
3. Confirms password matches
4. Submits registration
5. Receives verification code via email
6. Enters 6-digit verification code
7. Account is activated
8. Redirected to login

### Login Flow

1. User enters email and password
2. Clicks "Sign In"
3. Cognito validates credentials
4. Session tokens stored in memory
5. Main application loads

### Logout Flow

1. User clicks logout button in header
2. Cognito session is terminated
3. User state cleared
4. Redirected to login screen

## AWS Amplify Integration

### Dependencies

```json
{
  "aws-amplify": "^6.x.x",
  "@aws-amplify/ui-react": "^6.x.x"
}
```

### Amplify Configuration

Amplify is configured in `useAuth.jsx`:

```javascript
import { Amplify } from 'aws-amplify'
import { authConfig } from '../config/cognito'

Amplify.configure(authConfig)
```

### Auth Functions Used

- `signIn()` - Authenticate user
- `signUp()` - Register new user
- `signOut()` - Log out user
- `confirmSignUp()` - Verify email with code
- `resendSignUpCode()` - Resend verification code
- `getCurrentUser()` - Get current authenticated user
- `fetchAuthSession()` - Get session tokens

## Security Features

### Password Requirements

- Minimum 8 characters
- Enforced by both frontend and Cognito

### Email Verification

- All new accounts must verify email
- Verification code sent automatically
- Can resend code if not received

### Session Management

- Tokens stored in memory (not localStorage)
- Automatic session refresh
- Secure token handling by Amplify

### Protected Routes

- All main app features require authentication
- Automatic redirect to login if not authenticated
- User state checked on app load

## Customization

### Updating Cognito Pool

To use a different Cognito pool, update `src/config/cognito.js`:

```javascript
export const cognitoConfig = {
  region: 'YOUR_REGION',
  userPoolId: 'YOUR_POOL_ID',
  userPoolClientId: 'YOUR_CLIENT_ID'
}
```

### Styling

Authentication screens use custom CSS in `src/style.css`:

- `.auth-container` - Full-screen auth wrapper
- `.auth-card` - Login/signup card
- `.auth-form` - Form styling
- `.auth-error` - Error messages
- `.auth-success` - Success messages

Colors and layout can be customized via CSS variables.

## Troubleshooting

### "User does not exist" Error

- User may not have completed signup
- Check email for verification code
- Try resending verification code

### "Incorrect username or password"

- Verify email and password are correct
- Passwords are case-sensitive
- Ensure email is verified

### Email Not Received

- Check spam/junk folder
- Verify email address is correct
- Use "Resend Code" button

### Build Errors

If you see JSX parsing errors:
- Ensure auth files have `.jsx` extension
- Check imports reference `.jsx` extension

## Testing

### Manual Testing

1. **Signup Flow**:
   ```bash
   npm run dev
   # Click "Sign Up"
   # Enter email and password
   # Check email for verification code
   # Enter code and verify
   ```

2. **Login Flow**:
   ```bash
   # Enter verified email and password
   # Click "Sign In"
   # Should see main application
   ```

3. **Logout Flow**:
   ```bash
   # Click logout button in header
   # Should return to login screen
   ```

### Console Logging

The auth hook logs errors to console:
- Login errors: "Login error: ..."
- Signup errors: "Signup error: ..."
- Logout errors: "Logout error: ..."

## API Integration

The authentication system is separate from the Claude Agent API. After authentication:

1. User can configure server URL
2. User can create sessions
3. User can interact with Claude Agent API

Authentication tokens are NOT sent to the Claude Agent API server. The auth is purely for web client access control.

## Future Enhancements

Potential improvements:

- [ ] Social login (Google, GitHub)
- [ ] Password reset functionality
- [ ] Multi-factor authentication (MFA)
- [ ] Remember me functionality
- [ ] Session timeout warnings
- [ ] User profile management
- [ ] Role-based access control

## Support

For Cognito-related issues:
- Check AWS Cognito Console for user status
- Review CloudWatch logs for auth errors
- Verify Cognito pool configuration

For application issues:
- Check browser console for errors
- Verify Amplify configuration
- Test with different browsers
