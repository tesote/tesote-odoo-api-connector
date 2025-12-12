# API Authentication

## HMAC-SHA256 Signature Authentication

All API endpoints require HMAC-SHA256 signature authentication.

### Authentication Headers

Every API request must include:

| Header | Description | Example |
|--------|-------------|---------|
| `X-Tesote-Signature` | HMAC-SHA256 signature (hex) | `abc123def456...` |
| `X-Tesote-Timestamp` | Unix timestamp (seconds) | `1702400000` |

### Signature Calculation

**Signed Payload Format:**
```
{timestamp}.{path}.{query_string}
```

**Algorithm:**
```
HMAC-SHA256(secret_key, signed_payload)
```

### Examples

#### Python

```python
import hmac
import hashlib
import time

def generate_signature(secret_key, path, query_string=""):
    """Generate HMAC-SHA256 signature for API request."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{path}.{query_string}"

    signature = hmac.new(
        secret_key.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature, timestamp

# Usage
secret = "your_webhook_secret"
path = "/tesote/api/v1/accounting/accounts"
query_string = "limit=10&cursor=0"

signature, timestamp = generate_signature(secret, path, query_string)

headers = {
    "X-Tesote-Signature": signature,
    "X-Tesote-Timestamp": timestamp
}
```

#### JavaScript

```javascript
const crypto = require('crypto');

function generateSignature(secretKey, path, queryString = '') {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signedPayload = `${timestamp}.${path}.${queryString}`;

  const signature = crypto
    .createHmac('sha256', secretKey)
    .update(signedPayload)
    .digest('hex');

  return { signature, timestamp };
}

// Usage
const secret = 'your_webhook_secret';
const path = '/tesote/api/v1/accounting/accounts';
const queryString = 'limit=10&cursor=0';

const { signature, timestamp } = generateSignature(secret, path, queryString);

const headers = {
  'X-Tesote-Signature': signature,
  'X-Tesote-Timestamp': timestamp
};
```

#### Go

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "fmt"
    "time"
)

func generateSignature(secretKey, path, queryString string) (string, string) {
    timestamp := fmt.Sprintf("%d", time.Now().Unix())
    signedPayload := fmt.Sprintf("%s.%s.%s", timestamp, path, queryString)

    h := hmac.New(sha256.New, []byte(secretKey))
    h.Write([]byte(signedPayload))
    signature := hex.EncodeToString(h.Sum(nil))

    return signature, timestamp
}

// Usage
secret := "your_webhook_secret"
path := "/tesote/api/v1/accounting/accounts"
queryString := "limit=10&cursor=0"

signature, timestamp := generateSignature(secret, path, queryString)

headers := map[string]string{
    "X-Tesote-Signature": signature,
    "X-Tesote-Timestamp": timestamp,
}
```

### Security Features

**1. Replay Attack Prevention**
- Timestamp must be within 5 minutes of server time
- Old signatures automatically rejected

**2. Constant-Time Comparison**
- Uses `hmac.compare_digest()` to prevent timing attacks

**3. Secure Secret Storage**
- Secret key stored in webhook configuration
- Never exposed in API responses
- Retrievable only by admin users

### Setup (One-Time)

**Option 1: Via Odoo UI**
1. Login to Odoo: http://localhost:8069
2. Go to: tesote.com → Configuration → Webhooks
3. Click "Generate Secret Key"
4. Copy and save the secret

**Option 2: Via API (XML-RPC)**

See [examples/setup-api-auth.md](../examples/setup-api-auth.md) for complete script.

```python
import xmlrpc.client
import secrets

# Connect to Odoo
common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
uid = common.authenticate('tesote_dev', 'admin', 'admin', {})
models = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')

# Create backend
backend_id = models.execute_kw('tesote_dev', uid, 'admin',
    'tesote.backend', 'create', [{
        'name': 'API Backend',
        'api_url': 'https://api.tesote.com',
        'api_token': 'your_token',
        'api_version': 'v2'
    }])

# Generate and save secret
secret_key = secrets.token_urlsafe(32)
models.execute_kw('tesote_dev', uid, 'admin',
    'tesote.webhook.config', 'create', [{
        'backend_id': backend_id,
        'enabled': True,
        'secret_key': secret_key
    }])

print(f"Your API secret: {secret_key}")
# IMPORTANT: Save this secret securely
```

### Troubleshooting

**"Invalid signature" error:**
- Check timestamp is current (within 5 minutes)
- Verify signed payload format: `{timestamp}.{path}.{query_string}`
- Ensure secret key matches webhook config
- Check query string includes `?` separator if present

**"Missing authentication headers" error:**
- Include both `X-Tesote-Signature` and `X-Tesote-Timestamp`
- Headers are case-sensitive

**"Timestamp out of tolerance" error:**
- Server and client clocks must be synchronized
- Tolerance is 5 minutes (300 seconds)
- Use NTP for clock synchronization

### Best Practices

1. **Store secret securely** - Use environment variables, not hardcode
2. **Generate fresh timestamp** - For each request (prevents replay)
3. **Use HTTPS** - In production (signature alone doesn't encrypt)
4. **Rotate secrets periodically** - Update webhook config as needed
5. **Log authentication failures** - Monitor for attack attempts
