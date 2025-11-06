# Email Domain Restriction Feature

## Overview

The web client now supports restricting user registration to specific email domains. This feature is useful for:
- Limiting access to internal users (e.g., company domains)
- Workshop/training environments with designated email providers
- Controlled pilot programs or beta testing

## How It Works

When the `VITE_ALLOWED_EMAIL_DOMAINS` environment variable is set, the signup form validates email addresses before submitting to Cognito. If the email domain is not in the allowed list, registration is blocked with a clear error message.

## Configuration

### Environment Variable

Add to `web_client/.env` or `deploy/config.env`:

```bash
# Email Domain Restriction Configuration
# Comma-separated list of allowed email domains for user registration
# Example: gmail.com,outlook.com,company.com
# Leave empty or unset to allow all email domains (no restriction)
VITE_ALLOWED_EMAIL_DOMAINS=gmail.com,outlook.com
```

### Deployment Configuration

For Amplify deployments, add to `deploy/config.env`:

```bash
# Email Domain Restriction (for Amplify frontend)
VITE_ALLOWED_EMAIL_DOMAINS=gmail.com,outlook.com,company.com
```

The deployment script (`03_deploy_amplify.sh`) automatically reads this from `web_client/.env` and applies it to the Amplify environment variables.

## Behavior

### When Not Configured (Default)

- No domain restriction is enforced
- Users can register with any valid email address
- Suitable for public-facing deployments

### When Configured

- Only email addresses from specified domains are accepted
- The signup form displays allowed domains below the email input field
- Invalid domains are rejected with a clear error message before contacting Cognito
- Case-insensitive domain matching (Gmail.com = gmail.com)

## User Experience

### Allowed Domain Hint

When domains are restricted, users see a hint below the email input field:

```
Email
[you@example.com]
Only these domains are allowed: gmail.com, outlook.com
```

### Validation Error

If a user attempts to register with a disallowed domain:

```
❌ Registration is restricted to specific email domains.
   Allowed domains: gmail.com, outlook.com
```

## Implementation Details

### Frontend Validation

Location: `web_client/src/components/Signup.jsx`

The validation occurs in the `handleSignup` function:

```javascript
// Validate email domain if restriction is enabled
const allowedDomains = import.meta.env.VITE_ALLOWED_EMAIL_DOMAINS
if (allowedDomains) {
  const domainList = allowedDomains.split(',').map(d => d.trim().toLowerCase())
  const emailDomain = email.split('@')[1]?.toLowerCase()

  if (!emailDomain || !domainList.includes(emailDomain)) {
    setError(
      `Registration is restricted to specific email domains. ` +
      `Allowed domains: ${domainList.join(', ')}`
    )
    return
  }
}
```

### Domain Parsing

- Domains are split by comma
- Whitespace is trimmed from each domain
- Comparison is case-insensitive
- Both the configured domains and user input are normalized to lowercase

## Security Considerations

### Client-Side Validation Only

⚠️ **Important**: This is frontend validation only. It improves user experience and prevents accidental registrations but does not provide security enforcement.

For security-critical applications, implement additional server-side validation:
- Cognito Pre-signup Lambda trigger
- Custom validation in the backend API
- AWS WAF rules on the Amplify endpoint

### Recommended Security Approach

For production deployments requiring strict domain enforcement:

1. **Frontend validation** (implemented): Fast feedback, good UX
2. **Cognito Pre-signup Lambda** (recommended): Server-side enforcement
3. **Backend API validation** (optional): Additional layer if using custom signup flow

Example Cognito Pre-signup Lambda:

```python
import os

def lambda_handler(event, context):
    allowed_domains = os.environ.get('ALLOWED_EMAIL_DOMAINS', '').split(',')
    email = event['request']['userAttributes']['email']
    domain = email.split('@')[1].lower()

    if allowed_domains and domain not in [d.strip().lower() for d in allowed_domains]:
        raise Exception(f"Registration restricted to domains: {', '.join(allowed_domains)}")

    return event
```

## Testing

### Test Cases

1. **No restriction** (VITE_ALLOWED_EMAIL_DOMAINS not set):
   - ✅ user@gmail.com → Allowed
   - ✅ user@company.com → Allowed
   - ✅ user@any-domain.com → Allowed

2. **Restricted to gmail.com,outlook.com**:
   - ✅ user@gmail.com → Allowed
   - ✅ user@outlook.com → Allowed
   - ✅ user@Gmail.com → Allowed (case-insensitive)
   - ❌ user@yahoo.com → Blocked
   - ❌ user@company.com → Blocked

3. **Edge cases**:
   - ❌ invalid-email → Blocked (no @ symbol)
   - ❌ @gmail.com → Blocked (missing local part)
   - ❌ user@ → Blocked (missing domain)

### Manual Testing

1. Set environment variable in `web_client/.env`:
   ```bash
   VITE_ALLOWED_EMAIL_DOMAINS=gmail.com,outlook.com
   ```

2. Start development server:
   ```bash
   cd web_client
   npm run dev
   ```

3. Open signup page and test:
   - Try registering with allowed domain → Should proceed
   - Try registering with disallowed domain → Should show error
   - Verify hint text appears below email input

## Maintenance

### Adding/Removing Domains

Update the environment variable and redeploy:

```bash
# Update config.env or .env
VITE_ALLOWED_EMAIL_DOMAINS=gmail.com,outlook.com,newdomain.com

# Rebuild and redeploy Amplify
cd deploy
./03_deploy_amplify.sh
```

### Disabling Restriction

Remove or comment out the environment variable:

```bash
# VITE_ALLOWED_EMAIL_DOMAINS=gmail.com,outlook.com
```

Then rebuild and redeploy.

## Related Files

- `web_client/.env` - Local development configuration
- `web_client/src/components/Signup.jsx` - Signup component with validation
- `deploy/config.env.template` - Deployment configuration template
- `deploy/03_deploy_amplify.sh` - Amplify deployment script
