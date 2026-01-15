# Frontend Update Guide - User ID = Customer ID Alignment

## Overview

The backend has been updated so that **User ID = Customer ID** for all users. This ensures proper alignment between users, customers, and conversations.

## Key Changes

### 1. Customer ID Now Equals User ID

**Before:**
- Customer ID was auto-incremented (could be 1, 2, 3, etc.)
- User ID was separate (could be 5, 6, 7, etc.)
- Misalignment: `customer.id != user.id`

**After:**
- Customer ID = User ID (via `customer.user.id`)
- When fetching customer data, `customer_id` field returns `user.id`
- Perfect alignment: `customer.user.id == user.id`

### 2. API Response Changes

#### Login Response (`POST /api/auth/login/`)
```json
{
  "success": true,
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": 11,                    // User ID
    "email": "user@user.com",
    "name": "User One",
    "role": "user",
    "is_staff": false,
    "is_superuser": false
  }
}
```

**Frontend Action:** Store `user.id` - this is now your `customer_id` for all API calls.

#### Get Customer (`GET /api/customers/me/`)
```json
{
  "id": 16,                      // Database customer ID (internal)
  "customer_id": 11,            // ← This equals user.id (use this!)
  "name": "User One",
  "phone": "user_11",
  "email": "user@user.com",
  ...
}
```

**Frontend Action:** Use `customer_id` field (not `id`) when referencing the customer. `customer_id == user.id`.

#### Conversation Response (`GET /api/conversations/`)
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,                   // Conversation ID
      "customer_id": 11,         // ← This equals user.id
      "customer_name": "User One",
      "customer_email": "user@user.com",
      ...
    }
  ]
}
```

**Frontend Action:** `conversation.customer_id == user.id` for the logged-in user's conversations.

## Frontend Code Changes

### 1. Store User ID After Login

```javascript
// After successful login
const loginResponse = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ email, password })
});

const data = await loginResponse.json();
const userId = data.user.id;  // ← This is your customer_id

// Store in state/localStorage
localStorage.setItem('userId', userId);
localStorage.setItem('user', JSON.stringify(data.user));
```

### 2. Use User ID for Customer Operations

```javascript
// Get customer info (automatically linked to user)
const customerResponse = await fetch('/api/customers/me/', {
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include'
});

const customer = await customerResponse.json();
const customerId = customer.customer_id;  // ← Use this, equals user.id

// Verify alignment
console.assert(customerId === userId, 'Customer ID should equal User ID');
```

### 3. Create Conversations (Simplified)

```javascript
// Create conversation - customer_id is optional (backend uses user.id automatically)
const conversationResponse = await fetch('/api/conversations/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    customer_phone: phoneNumber,
    message: messageText,
    // customer_id is optional - backend uses logged-in user's ID
    // customer_id: userId,  // ← Can omit this, backend handles it
    customer_name: name,
    customer_email: email
  })
});
```

**Note:** For regular users, `customer_id` is ignored - backend uses `request.user.id`. Admins can still specify `customer_id` to create conversations for other users.

### 4. Filter Conversations by User ID

```javascript
// List conversations - backend automatically filters by user.id
const conversationsResponse = await fetch('/api/conversations/', {
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include'
});

const data = await conversationsResponse.json();
// All conversations in data.results have customer_id === user.id
```

**Note:** Regular users only see their own conversations. Admins see all conversations.

### 5. Access Conversation Messages

```javascript
// Get messages for a conversation
const conversationId = 1;  // Conversation ID (not user ID)
const messagesResponse = await fetch(`/api/conversations/${conversationId}/messages/`, {
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include'
});

// Backend ensures conversation.customer.user.id === request.user.id
```

### 6. Update Customer Profile

```javascript
// Update customer - automatically linked to logged-in user
const updateResponse = await fetch('/api/customers/me/', {
  method: 'PUT',  // or PATCH
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    name: 'Updated Name',
    phone: '+1234567890',
    email: 'newemail@example.com'
  })
});
```

## Important Notes

### ✅ What Works Automatically

1. **Customer Creation**: When users sign up or access `/api/customers/me/`, customers are automatically linked to their user account.

2. **Conversation Filtering**: Regular users automatically see only their own conversations. No need to filter by `customer_id` on the frontend.

3. **Access Control**: Backend ensures users can only access conversations where `conversation.customer.user.id == user.id`.

### ⚠️ What to Avoid

1. **Don't use `customer.id`**: Use `customer.customer_id` instead (which equals `user.id`).

2. **Don't hardcode customer IDs**: Always use `user.id` from the login response.

3. **Don't filter conversations by customer_id on frontend**: Backend handles this automatically.

### 🔄 Migration Checklist

- [ ] Update login handler to store `user.id` as `customerId`
- [ ] Replace all `customer.id` references with `customer.customer_id`
- [ ] Remove any frontend filtering by `customer_id` (backend handles it)
- [ ] Update conversation creation to omit `customer_id` (or keep it for admin users)
- [ ] Verify `customer_id === user.id` in all API responses
- [ ] Test that users only see their own conversations
- [ ] Test that admins can see all conversations

## Example: Complete Flow

```javascript
// 1. Login
const loginData = await login(email, password);
const userId = loginData.user.id;  // e.g., 11

// 2. Get customer (optional - for display)
const customer = await getCustomer();  // GET /api/customers/me/
console.assert(customer.customer_id === userId);  // Should be true

// 3. Create conversation
const conversation = await createConversation({
  customer_phone: '+1234567890',
  message: 'Hello!'
});
console.assert(conversation.customer_id === userId);  // Should be true

// 4. List conversations (only user's own)
const conversations = await listConversations();
conversations.results.forEach(conv => {
  console.assert(conv.customer_id === userId);  // All should be true
});

// 5. Get conversation messages
const messages = await getConversationMessages(conversation.id);
// Backend ensures access - no need to check customer_id
```

## Testing

1. **Login as user@user.com** (User ID: 11)
2. **Verify customer_id = 11** in `/api/customers/me/` response
3. **Create a conversation** - verify `customer_id = 11` in response
4. **List conversations** - verify all have `customer_id = 11`
5. **Login as user2@user.com** (User ID: 12)
6. **Verify customer_id = 12** in `/api/customers/me/` response
7. **List conversations** - should only see conversations with `customer_id = 12`
8. **Try to access conversation with customer_id = 11** - should be denied (403)

## Summary

**Key Takeaway:** `user.id == customer.customer_id == conversation.customer_id` for all user operations. The frontend should use `user.id` from the login response as the primary identifier for all customer-related operations.
