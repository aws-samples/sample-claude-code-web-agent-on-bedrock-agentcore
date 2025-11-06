# Cognito User Registration Guide

This guide explains how the user registration feature works in the web client and how to configure it.

## Features

The web client includes a complete user registration flow with:

1. **Sign Up Form**: Username, email, and password
2. **Email Verification**: 6-digit verification code sent via email
3. **Code Resend**: Option to resend verification code if not received
4. **Auto Login Redirect**: After verification, redirects to login page

## User Flow

### 1. Registration (Sign Up Page)

- User enters:
  - Username (minimum 3 characters)
  - Email address
  - Password (minimum 8 characters)
  - Password confirmation
- Client-side validation:
  - Passwords must match
  - Password must meet minimum length requirements
- On successful submission:
  - AWS Cognito creates user account in `UNCONFIRMED` state
  - Verification code is sent to email
  - UI switches to verification step

### 2. Email Verification (Confirm Page)

- User receives 6-digit code via email
- Enter code in verification form
- Click "Verify Email"
- On success:
  - Account status changes from `UNCONFIRMED` to `CONFIRMED`
  - User can now log in
  - Auto-redirects to login page after 2 seconds

### 3. Code Resend (Optional)

- If user doesn't receive code
- Click "Resend Code" button
- New verification code sent to email

## Environment Variables

Configure Cognito in `web_client/.env`:

```bash
# AWS region where your Cognito user pool is located
VITE_COGNITO_REGION=us-west-2

# Cognito User Pool ID (format: region_poolId)
VITE_COGNITO_USER_POOL_ID=us-west-2_XXXXXXXXX

# Cognito User Pool Client ID (alphanumeric string)
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: OAuth domain for hosted UI
VITE_COGNITO_OAUTH_DOMAIN=your-domain.auth.us-west-2.amazoncognito.com
```

### Finding Your Cognito Configuration

1. **AWS Console → Cognito → User Pools**
2. Select your user pool
3. **User Pool ID**: Found in "User pool overview"
4. **Client ID**: Found in "App integration" → "App clients"
5. **Region**: Part of the User Pool ID (e.g., `us-west-2`)

## Cognito User Pool Configuration

### Required Settings

For user registration to work, your Cognito User Pool must be configured with:

#### 1. Sign-up Settings

- **Allow self-registration**: Enabled
- **Verification method**: Email (recommended) or Phone

#### 2. Email Configuration

Option A: **Cognito Email (default)**
- Free tier: 50 emails/day
- Good for development and small deployments

Option B: **Amazon SES**
- Higher email limits
- Production-recommended
- Requires SES setup and verification

#### 3. Password Policy

Default Cognito password policy:
- Minimum length: 8 characters
- Requires: Uppercase, lowercase, numbers, special characters

You can customize this in User Pool settings.

#### 4. Required Attributes

Must include:
- `email` (required and verified)

Optional attributes:
- `preferred_username`
- Custom attributes as needed

#### 5. User Pool Client Settings

- **Authentication flows**: Allow `USER_PASSWORD_AUTH`
- **Prevent user existence errors**: Enabled (recommended for security)
- **No secret**: App client should NOT have a secret (for public web clients)

## Code Structure

### Components

**`web_client/src/components/Signup.jsx`**
- Main registration component
- Two-step flow: signup → verify
- Form validation
- Error handling

**`web_client/src/components/Login.jsx`**
- Login form
- Link to signup page

### Hooks

**`web_client/src/hooks/useAuth.jsx`**
- `signup(username, email, password)`: Create new user
- `confirmSignup(username, code)`: Verify email with code
- `resendCode(username)`: Resend verification code
- Uses AWS Amplify Auth SDK

### Configuration

**`web_client/src/config/cognito.js`**
- Loads environment variables
- Configures Amplify Auth
- Exports `authConfig` and `cognitoConfig`

## Error Handling

Common signup errors:

| Error | Meaning | Solution |
|-------|---------|----------|
| `UsernameExistsException` | Username already taken | Choose different username |
| `InvalidPasswordException` | Password doesn't meet policy | Follow password requirements |
| `CodeMismatchException` | Wrong verification code | Check email, enter correct code |
| `ExpiredCodeException` | Code expired (24h validity) | Click "Resend Code" |
| `UserNotFoundException` | User doesn't exist | Complete signup first |

## Testing

### Test Registration Flow

1. Start web client: `cd web_client && npm run dev`
2. Navigate to: `http://localhost:8080`
3. Click "Sign Up" link
4. Fill in registration form
5. Check email for verification code
6. Enter code and verify
7. Login with new credentials

### Development Tips

- Use a real email address (Cognito sends actual emails)
- For testing, use Gmail with `+` suffix: `youremail+test1@gmail.com`
- Verification codes expire after 24 hours
- Failed login attempts may temporarily lock account (check Cognito settings)

## Security Considerations

### Best Practices

1. **HTTPS Only**: Always use HTTPS in production
2. **Password Strength**: Enforce strong password policy in Cognito
3. **Rate Limiting**: Cognito provides built-in rate limiting
4. **User Existence Errors**: Enable "Prevent user existence errors" in Cognito
5. **MFA (Optional)**: Can enable Multi-Factor Authentication in Cognito settings

### Email Verification

- Email verification is REQUIRED to complete registration
- Unverified users cannot log in
- Verification codes are single-use
- Codes expire after 24 hours

## Customization

### Custom Email Templates

You can customize verification emails in Cognito:

1. AWS Console → Cognito → User Pools → [Your Pool]
2. "Messaging" tab
3. Edit "Verification message" templates
4. Customize subject, body, code format

### Custom Signup Fields

To add custom fields (e.g., first name, last name):

1. **Cognito**: Add custom attributes to User Pool schema
2. **Code**: Update `signup()` call in `useAuth.jsx`:

```javascript
const result = await signUp({
  username: username,
  password,
  options: {
    userAttributes: {
      email,
      given_name: firstName,  // Add custom fields
      family_name: lastName
    }
  }
})
```

3. **UI**: Add input fields to `Signup.jsx` form

## Troubleshooting

### Email Not Received

1. Check spam/junk folder
2. Verify email configuration in Cognito
3. Check Cognito email sending limits (50/day for default)
4. Consider upgrading to SES for higher limits

### Signup Fails Silently

1. Check browser console for errors
2. Verify environment variables are set correctly
3. Check Cognito User Pool Client settings
4. Ensure client has no secret configured

### Cannot Login After Verification

1. Verify email confirmation was successful
2. Check Cognito console - user status should be `CONFIRMED`
3. Try password reset if needed
4. Check for account lockouts due to failed attempts

## Production Deployment

### Checklist

- [ ] Use Amazon SES for email (not Cognito default)
- [ ] Enable MFA (optional but recommended)
- [ ] Configure custom email templates
- [ ] Set up CloudWatch alarms for Cognito metrics
- [ ] Enable advanced security features
- [ ] Configure account recovery options
- [ ] Set appropriate password policy
- [ ] Test email deliverability
- [ ] Set up backup admin user

### Environment Variables

Create `.env.production`:

```bash
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_PROD_POOL_ID
VITE_COGNITO_CLIENT_ID=prod_client_id_here
```

Build with production config:
```bash
cd web_client
npm run build
```

## Additional Resources

- [AWS Amplify Auth Documentation](https://docs.amplify.aws/javascript/build-a-backend/auth/)
- [AWS Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [Cognito Email Settings](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-email.html)
