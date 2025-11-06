# Cognito Error Handling Reference

This document lists all Cognito authentication errors and their user-friendly messages implemented in the web client.

## Error Mapping Implementation

All Cognito errors are automatically caught and converted to user-friendly messages in `web_client/src/hooks/useAuth.jsx`.

## Login Errors

| Cognito Error | Error Name | User-Friendly Message |
|---------------|------------|----------------------|
| User does not exist | `UserNotFoundException` | "User does not exist. Please check your username/email or sign up for a new account." |
| Incorrect credentials | `NotAuthorizedException` | "Incorrect username or password. Please try again." |
| Email not verified | `UserNotConfirmedException` | "Your email is not verified. Please check your email for the verification code." |
| Password reset required | `PasswordResetRequiredException` | "Password reset is required. Please reset your password." |
| Too many attempts | `TooManyRequestsException` | "Too many login attempts. Please try again later." |
| Too many attempts | `LimitExceededException` | "Too many login attempts. Please try again later." |
| Invalid format | `InvalidParameterException` | "Invalid username or password format." |

## Signup Errors

| Cognito Error | Error Name | User-Friendly Message |
|---------------|------------|----------------------|
| Username taken | `UsernameExistsException` | "Username already exists. Please choose a different username." |
| Weak password | `InvalidPasswordException` | "Password does not meet requirements. It must be at least 8 characters and include uppercase, lowercase, numbers, and special characters." |
| Invalid input | `InvalidParameterException` | "Invalid input. Please check your username, email, and password format." |
| Too many attempts | `TooManyRequestsException` | "Too many signup attempts. Please try again later." |
| Too many attempts | `LimitExceededException` | "Too many signup attempts. Please try again later." |
| Email sending failed | `CodeDeliveryFailureException` | "Failed to send verification email. Please contact support." |
| Validation failed | `UserLambdaValidationException` | "Signup validation failed. Please contact support." |

## Email Verification Errors

| Cognito Error | Error Name | User-Friendly Message |
|---------------|------------|----------------------|
| Wrong code | `CodeMismatchException` | "Invalid verification code. Please check the code and try again." |
| Expired code | `ExpiredCodeException` | "Verification code has expired. Please click 'Resend Code' to get a new one." |
| User not found | `UserNotFoundException` | "User not found. Please sign up first." |
| Already confirmed | `NotAuthorizedException` | "User is already confirmed or code is invalid." |
| Too many attempts | `TooManyRequestsException` | "Too many attempts. Please try again later." |
| Too many attempts | `LimitExceededException` | "Too many attempts. Please try again later." |
| Email conflict | `AliasExistsException` | "An account with this email already exists." |

## Configuration Errors

### Missing Email Delivery Details

**Symptom**: After signup, `codeDeliveryDetails` contains all `undefined` values:
```javascript
{
  destination: undefined,
  deliveryMedium: undefined,
  attributeName: undefined
}
```

**User Message**:
```
Account created but verification email was not sent.
Cognito email verification is not properly configured.
Please contact the administrator to enable email verification
in Cognito User Pool settings.
```

**Fix**:
1. AWS Console → Cognito → User Pools → [Your Pool]
2. Sign-up experience → Attribute verification
3. Enable "Email" as required verification attribute
4. Save changes

## Debug Logging

All authentication operations include detailed console logging:

### Login
```
🔐 Starting login for: username
✅ Login result: {...}
❌ Login error: {...}
```

### Signup
```
📝 Starting signup for: {username, email}
✅ Signup result: {...}
📧 Next step: {...}
🆔 User ID: xxx
❌ Signup error: {...}
```

### Email Confirmation
```
📧 Confirming signup for: username
✅ Email confirmed successfully
❌ Confirm signup error: {...}
```

## Error Response Structure

All auth functions return a consistent error structure:

```javascript
{
  success: false,
  error: "User-friendly error message",
  errorName: "CognitoErrorName"  // Original error name for debugging
}
```

## Adding New Error Mappings

To add a new error mapping, edit `web_client/src/hooks/useAuth.jsx`:

```javascript
// In login, signup, or confirmSignup function
if (err.name === 'NewErrorName') {
  userMessage = 'User-friendly message here'
}
```

## Testing Errors

### Test UserNotFoundException
1. Try to login with non-existent username
2. Should show: "User does not exist..."

### Test NotAuthorizedException
1. Login with correct username but wrong password
2. Should show: "Incorrect username or password..."

### Test CodeMismatchException
1. Enter wrong verification code
2. Should show: "Invalid verification code..."

### Test ExpiredCodeException
1. Wait 24 hours after signup
2. Try to verify with old code
3. Should show: "Verification code has expired..."

### Test UsernameExistsException
1. Try to signup with existing username
2. Should show: "Username already exists..."

### Test InvalidPasswordException
1. Try to signup with password "123"
2. Should show: "Password does not meet requirements..."

## Best Practices

1. **Always log errors**: Console logging helps with debugging
2. **User-friendly messages**: Never show raw Cognito error messages to users
3. **Actionable guidance**: Tell users what to do (e.g., "Please sign up first")
4. **Include error name**: Return `errorName` for debugging purposes
5. **Handle all cases**: Always have a default fallback message

## Related Files

- `web_client/src/hooks/useAuth.jsx` - Error handling implementation
- `web_client/src/components/Login.jsx` - Login error display
- `web_client/src/components/Signup.jsx` - Signup error display
- `web_client/src/style.css` - Error styling (`.auth-error` class)

## References

- [AWS Amplify Auth Errors](https://docs.amplify.aws/javascript/build-a-backend/auth/connect-your-frontend/sign-in/#auth-errors)
- [Cognito Error Codes](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_InitiateAuth.html#API_InitiateAuth_Errors)
