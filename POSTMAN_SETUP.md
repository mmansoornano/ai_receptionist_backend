# Postman Collection Setup Guide

## Import Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `postman_collection.json` from this directory
5. Click **Import**

## Collection Variables

The collection includes these variables (you can update them in Postman):

- `base_url`: `http://localhost:8000` (default)
- `customer_id`: `customer_1` (example customer ID)
- `conversation_id`: `1` (example conversation ID)
- `cart_id`: (will be set after creating a cart)
- `order_id`: (will be set after creating an order)

## Authentication

### Hybrid Authentication (JWT + Session)

The backend supports **both JWT tokens and Session cookies** for maximum flexibility:

- **JWT Tokens**: For API clients, mobile apps, and cross-domain requests
- **Session Cookies**: For web browsers and same-domain requests

### How It Works

1. **Login/Signup:**
   - Use `POST /api/auth/login/` or `POST /api/auth/signup/`
   - Response includes:
     - `access_token`: JWT token for API clients
     - `refresh_token`: JWT refresh token
     - Session cookie: Automatically set for web clients

2. **Authenticated Requests:**
   - **Option A (JWT)**: Include `Authorization: Bearer <token>` header
   - **Option B (Session)**: Use session cookie (automatic in browsers/Postman)
   - Both methods work simultaneously!

### Setting Up Authentication in Postman

#### Method 1: JWT Tokens (Recommended for API Testing)

1. **Login:**
   - Run `POST /api/auth/login/` with your credentials
   - The response will include `access_token` and `refresh_token`
   - Postman automatically extracts and stores these tokens

2. **Use Token:**
   - All authenticated requests automatically include `Authorization: Bearer {{auth_token}}`
   - Token is set automatically after login

3. **Refresh Token (if expired):**
   - Use `POST /api/auth/token/refresh/` with `refresh_token`
   - New access token is automatically updated

#### Method 2: Session Cookies (Alternative)

1. **Enable Cookies:**
   - Go to **Settings** (gear icon) → **General**
   - Enable **"Send cookies"** (should be enabled by default)

2. **Login:**
   - Run `POST /api/auth/login/` with your credentials
   - Postman automatically stores the session cookie

3. **Use Authenticated Endpoints:**
   - After login, all authenticated endpoints work via session cookie
   - No manual token management needed

### Which Method to Use?

- **JWT Tokens**: Use for API testing, mobile apps, or when you need explicit token control
- **Session Cookies**: Use for web browser testing or when you prefer automatic cookie handling
- **Both**: You can use either method - they both work!

## API Endpoints Included

### 1. Authentication
- `POST /api/auth/login/` - Login
- `POST /api/auth/signup/` - Signup
- `GET /api/auth/me/` - Get current user
- `POST /api/auth/logout/` - Logout

### 2. Customers
- `GET /api/customers/` - List customers
- `GET /api/customers/{id}/` - Get customer by ID
- `POST /api/customers/` - Create/update customer

### 3. Conversations
- `GET /api/conversations/` - List conversations
- `GET /api/conversations/{id}/` - Get conversation
- `GET /api/conversations/{id}/messages/` - Get messages
- `POST /api/conversations/` - Create/update conversation

### 4. Cart
- `POST /api/cart/add/` - Add item to cart
- `GET /api/cart/` - Get cart
- `PUT /api/cart/item/{id}/` - Update cart item
- `DELETE /api/cart/item/{id}/` - Remove item
- `DELETE /api/cart/` - Clear cart

### 5. Payment
- `POST /api/payment/otp/send/` - Send OTP
- `POST /api/payment/otp/verify/` - Verify OTP
- `POST /api/payment/easypaisa/confirm/` - Confirm payment

### 6. Orders
- `POST /api/orders/create/` - Create order
- `GET /api/orders/` - List orders
- `GET /api/orders/{id}/` - Get order by ID

### 7. Cancellations
- `POST /api/cancellations/submit/` - Submit cancellation
- `GET /api/cancellations/` - List cancellations

### 8. Analytics
- `GET /api/analytics/stats/` - Dashboard stats
- `GET /api/analytics/activity/` - Recent activity

### 9. Appointments
- `GET /api/appointments/` - List appointments
- `GET /api/appointments/upcoming/` - Get upcoming
- `POST /api/appointments/` - Create appointment

### 10. Webhooks
- `POST /webhooks/test-message/` - Test message (local)
- `POST /webhooks/tts/` - Text to speech

## Testing Workflow

### Example: Complete Order Flow

1. **Login:**
   ```
   POST /api/auth/login/
   Body: { "email": "admin@example.com", "password": "password123" }
   ```

2. **Add items to cart:**
   ```
   POST /api/cart/add/
   Body: {
     "product_id": "protein-bar-white-chocolate",
     "quantity": 2,
     "customer_id": "customer_1"
   }
   ```

3. **Get cart:**
   ```
   GET /api/cart/?customer_id=customer_1
   ```

4. **Send OTP:**
   ```
   POST /api/payment/otp/send/
   Body: {
     "mobile_number": "+1234567890",
     "amount": 450.00,
     "customer_id": "customer_1"
   }
   ```

5. **Verify OTP:**
   ```
   POST /api/payment/otp/verify/
   Body: {
     "mobile_number": "+1234567890",
     "otp": "123456"
   }
   ```

6. **Confirm payment:**
   ```
   POST /api/payment/easypaisa/confirm/
   Body: {
     "mobile_number": "+1234567890",
     "amount": 450.00,
     "transaction_id": "TXN123456789"
   }
   ```

7. **Create order:**
   ```
   POST /api/orders/create/
   Body: {
     "customer_id": "customer_1",
     "transaction_id": "TXN123456789",
     "cart_data": { ... }
   }
   ```

## Notes

- All endpoints return JSON
- Most endpoints require authentication (except login, signup, and some public endpoints)
- Use `credentials: 'include'` in frontend code to send cookies
- Update collection variables as needed for your testing
- Some endpoints support pagination with `page` and `page_size` query parameters

## Troubleshooting

### 401 Unauthorized
- Make sure you've logged in first
- Check that cookies are being sent (Postman settings)
- Verify session hasn't expired

### 404 Not Found
- Check the base URL is correct
- Verify the endpoint path matches the API spec
- Ensure the server is running

### 500 Internal Server Error
- Check server logs
- Verify request body format matches the API spec
- Check database connection
