# Phone Number Validation

## Overview
This document describes the phone number validation implementation to ensure phone numbers are always stored as strings throughout the application.

## Validation Points

### 1. Backend (FastAPI)

#### Pydantic Schema Validation (`backend/app/schemas.py`)
- Added `field_validator` to `OrderCreate` schema
- Validates `customer_phone` is converted to string and trimmed
- Prevents `None` values
- Location: `OrderCreate.validate_phone_is_string()`

```python
@field_validator('customer_phone')
@classmethod
def validate_phone_is_string(cls, v):
    if v is None:
        raise ValueError('customer_phone cannot be None')
    return str(v).strip()
```

#### API Endpoint Validation (`backend/app/routers/orders.py`)
- Additional validation in `create_order()` endpoint
- Ensures phone string is not empty after stripping
- Returns 400 error if phone is empty
- Phone is stored as string in database

### 2. Frontend (React/TypeScript)

#### Phone Validator Utility (`src/lib/phoneValidator.ts`)
Two helper functions:
- `sanitizePhoneNumber(phone: unknown): string` - Converts any value to trimmed string
- `validatePhoneNumber(phone: unknown)` - Validates and returns sanitized phone with status

#### Component Validation (`src/components/NewOrderDialog.tsx`)
- Input type set to `"tel"` for better mobile UX
- `onChange` handler ensures string conversion: `String(e.target.value)`
- Pre-submission validation using `validatePhoneNumber()`
- User-friendly error messages

#### API Client (`src/lib/apiClient.ts`)
- Sanitizes phone before sending to API
- Ensures phone is trimmed string in request payload

#### Inventory Service (`src/lib/inventoryService.ts`)
- Local storage implementation also validates phone
- Checks phone is not empty
- Converts to string before storage

## Database Schema

The database already stores phone numbers as `String` type:
- SQLAlchemy model: `customer_phone = Column(String, nullable=False)`
- TypeScript interface: `customer_phone: string`

## Benefits

1. **Type Safety**: Phone numbers are consistently strings across the stack
2. **Data Integrity**: Prevents numeric conversion issues (e.g., leading zeros)
3. **Validation**: Multiple layers ensure data quality
4. **User Experience**: Clear error messages for invalid inputs
5. **API Compatibility**: Works with both local storage and REST API modes

## Testing

To test phone validation:
1. Try creating an order with empty phone - should show error
2. Try phone with spaces - should trim correctly
3. Try numeric input - should convert to string
4. Check database/storage - phone should be stored as string

## Migration Note

Existing data: If there's any existing data with phone numbers stored as numbers, they will be automatically converted to strings on the next update or when fetched through the API/service layer.
