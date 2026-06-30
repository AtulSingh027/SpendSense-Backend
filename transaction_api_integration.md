# SpendSense Transaction APIs Integration Guide

This integration guide provides client-side developers with detailed documentation for integrating the **SpendSense Transaction APIs**.

All transaction endpoints require user authentication via a **JSON Web Token (JWT)**.

---

## Table of Contents
1. [Authentication Overview](#authentication-overview)
2. [API Reference](#api-reference)
   - [1. Get All Transactions (With Filtering & Pagination)](#1-get-all-transactions-with-filtering--pagination)
   - [2. Get Transaction by ID](#2-get-transaction-by-id)
   - [3. Create Transaction (Manual Entry)](#3-create-transaction-manual-entry)
   - [4. Partially Update Transaction](#4-partially-update-transaction)
   - [5. Delete Transaction](#5-delete-transaction)
3. [Error Handling](#error-handling)

---

## Authentication Overview

All requests to the transaction endpoints must include the authentication token in the request header.

* **Header Key**: `Authorization`
* **Header Value**: `Bearer <JWT_ACCESS_TOKEN>`

### Authentication Example Header
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## API Reference

### 1. Get All Transactions (With Filtering & Pagination)
Retrieves a paginated list of transactions for the authenticated user, sorted in descending order by `txn_timestamp` (newest first). Supports filtering by category, date range, source, and UPI app.

* **URL**: `/api/v1/transaction/`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `category_id` | `int` | No | `None` | Filter by unique Category ID. |
  | `month` | `int` | No | `None` | Filter by month number (`1` to `12`). |
  | `year` | `int` | No | `None` | Filter by year (minimum value: `2000`). |
  | `from_date` | `str` | No | `None` | Filter start date in `YYYY-MM-DD` format (inclusive). |
  | `to_date` | `str` | No | `None` | Filter end date in `YYYY-MM-DD` format (inclusive, will query up to 23:59:59 of that day). |
  | `source` | `str` | No | `None` | Filter by transaction origin: `manual` or `sms`. |
  | `upi_app` | `str` | No | `None` | Filter by UPI App name (e.g. `PhonePe`, `GPay`, `Paytm`). |
  | `limit` | `int` | No | `10` | Number of items to return (`1` to `100`). |
  | `offset` | `int` | No | `0` | Number of items to skip for pagination (minimum `0`). |

#### Response Fields (`TransactionListResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `total` | `int` | The total number of transactions matching the active filters. |
| `limit` | `int` | The active pagination page limit. |
| `offset` | `int` | The active pagination offset. |
| `items` | `List[TransactionResponse]` | Array of transaction details matching the filters. |

##### Transaction Item Fields
Refer to [2. Get Transaction by ID](#2-get-transaction-by-id) for details on the `TransactionResponse` fields.

#### cURL Request Examples

##### Example 1: Basic Paginated List
```bash
curl -X GET "http://localhost:8000/api/v1/transaction/?limit=10&offset=0" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

##### Example 2: List with Filters (Category and Date Range)
```bash
curl -X GET "http://localhost:8000/api/v1/transaction/?category_id=5&from_date=2026-06-01&to_date=2026-06-30&limit=5" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "total": 45,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 102,
      "user_id": 1,
      "sms_log_id": 482,
      "amount": "150.50",
      "txn_type": "debit",
      "merchant_raw": "Starbucks Coffee",
      "merchant_clean": "Starbucks",
      "category_id": 3,
      "category_name": "Food & Dining",
      "upi_app": "PhonePe",
      "app_label_source": "parsed",
      "app_label_confidence": 0.95,
      "source": "sms",
      "bank_ref_id": "TXN9876543210",
      "txn_timestamp": "2026-06-30T10:15:00+05:30",
      "notes": "Morning coffee run",
      "created_at": "2026-06-30T10:16:12Z",
      "updated_at": "2026-06-30T10:16:12Z"
    }
  ]
}
```

---

### 2. Get Transaction by ID
Retrieves details for a single, specific transaction by ID. Users can only query their own transactions.

* **URL**: `/api/v1/transaction/{id}`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Path Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `id` | `int` | Yes | The unique database ID of the transaction. |

#### Response Fields (`TransactionResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | `int` | Unique database identifier. |
| `user_id` | `int` | ID of the owner of this transaction. |
| `sms_log_id` | `int \| null` | Associated SMS Log entry ID, if transaction was parsed from an SMS. |
| `amount` | `Decimal` | The transaction amount (2 decimal places). |
| `txn_type` | `str` | Type of transaction: `debit` (expense) or `credit` (income). |
| `merchant_raw` | `str \| null` | Raw merchant description string extracted from the transaction. |
| `merchant_clean`| `str \| null` | Normalized/cleaned merchant name. |
| `category_id` | `int \| null` | ID of the assigned category. |
| `category_name` | `str \| null` | Resolved name of the assigned category (e.g. `Rent`, `Shopping`, `Uncategorized`). |
| `upi_app` | `str \| null` | Associated UPI App if applicable (e.g. `GPay`, `PhonePe`). |
| `app_label_source`| `str \| null`| Label origin type: `parsed`, `user_labeled`, `unlabeled`, `unknown`. |
| `app_label_confidence`| `float \| null`| Extraction confidence score (if AI/ML-assisted label). |
| `source` | `str` | Input channel of the transaction: `manual` or `sms`. |
| `bank_ref_id` | `str \| null` | Bank reference transaction ID (present only for SMS transactions). |
| `txn_timestamp`| `str` | ISO-8601 transaction timestamp. |
| `notes` | `str \| null` | Custom user-submitted description or notes. |
| `created_at` | `str` | ISO-8601 creation timestamp. |
| `updated_at` | `str` | ISO-8601 update timestamp. |

#### cURL Request
```bash
curl -X GET "http://localhost:8000/api/v1/transaction/102" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "id": 102,
  "user_id": 1,
  "sms_log_id": 482,
  "amount": "150.50",
  "txn_type": "debit",
  "merchant_raw": "Starbucks Coffee",
  "merchant_clean": "Starbucks",
  "category_id": 3,
  "category_name": "Food & Dining",
  "upi_app": "PhonePe",
  "app_label_source": "parsed",
  "app_label_confidence": 0.95,
  "source": "sms",
  "bank_ref_id": "TXN9876543210",
  "txn_timestamp": "2026-06-30T10:15:00+05:30",
  "notes": "Morning coffee run",
  "created_at": "2026-06-30T10:16:12Z",
  "updated_at": "2026-06-30T10:16:12Z"
}
```

---

### 3. Create Transaction (Manual Entry)
Creates a new manually entered transaction. Note that server-managed properties (like `bank_ref_id`, `app_label_confidence`, etc.) are auto-populated. The backend automatically recomputes the monthly and weekly summaries for the user in a background task after creation.

* **URL**: `/api/v1/transaction/`
* **Method**: `POST`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Content-Type**: `application/json`
* **Body Payload Fields (`TransactionCreate`)**:
  | Key | Type | Required | Validation / Rules | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `amount` | `float` | Yes | must be > 0 | Amount value. |
  | `txn_type` | `str` | Yes | must match `debit` or `credit` | Action classification. |
  | `merchant_raw` | `str` | No | maximum 255 chars | Raw merchant description. |
  | `category_id` | `int` | No | valid category ID | Category reference ID. |
  | `upi_app` | `str` | No | e.g. `GPay`, `PhonePe` | UPI application used. |
  | `source` | `str` | Yes | must match `manual` or `sms` | Source of transaction. Typically `manual` for this endpoint. |
  | `txn_timestamp`| `str` | Yes | ISO-8601 format | Transaction datetime string. |
  | `notes` | `str` | No | Text | Optional user notes. |

#### cURL Request
```bash
curl -X POST "http://localhost:8000/api/v1/transaction/" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d '{
       "amount": 1250.00,
       "txn_type": "debit",
       "merchant_raw": "Amazon Retail",
       "category_id": 4,
       "source": "manual",
       "txn_timestamp": "2026-06-30T12:00:00Z",
       "notes": "Bought home supplies"
     }'
```

#### Example Response (`201 Created`)
```json
{
  "id": 103,
  "user_id": 1,
  "sms_log_id": null,
  "amount": "1250.00",
  "txn_type": "debit",
  "merchant_raw": "Amazon Retail",
  "merchant_clean": null,
  "category_id": 4,
  "category_name": "Shopping",
  "upi_app": null,
  "app_label_source": "unknown",
  "app_label_confidence": null,
  "source": "manual",
  "bank_ref_id": null,
  "txn_timestamp": "2026-06-30T12:00:00Z",
  "notes": "Bought home supplies",
  "created_at": "2026-06-30T12:01:45Z",
  "updated_at": "2026-06-30T12:01:45Z"
}
```

---

### 4. Partially Update Transaction
Updates one or more fields of an existing transaction. If the `upi_app` attribute is updated, the server automatically promotes `app_label_source` to `user_labeled` and clears `app_label_confidence`. Summary recalculation occurs asynchronously in the background.

* **URL**: `/api/v1/transaction/{id}`
* **Method**: `PATCH`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Path Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `id` | `int` | Yes | Unique transaction ID. |
* **Content-Type**: `application/json`
* **Body Payload Fields (`TransactionUpdate`)**:
  All fields are optional. Only fields present in the payload will be modified.
  | Key | Type | Validation / Rules | Description |
  | :--- | :--- | :--- | :--- |
  | `amount` | `float` | must be > 0 (2 decimal places) | Update amount. |
  | `txn_type` | `str` | must be `debit` or `credit` | Update txn classification. |
  | `merchant_raw` | `str` | maximum 255 chars | Update merchant name. |
  | `category_id` | `int` | valid category ID | Update category reference. |
  | `upi_app` | `str` | e.g. `GPay`, `PhonePe` | Update UPI app. Automatically sets source to `user_labeled`. |
  | `source` | `str` | `manual` or `sms` | Update transaction source. |
  | `txn_timestamp`| `str` | ISO-8601 format | Update transaction datetime. |
  | `notes` | `str` | Text | Update notes. |

#### cURL Request
```bash
curl -X PATCH "http://localhost:8000/api/v1/transaction/102" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d '{
       "category_id": 5,
       "upi_app": "GPay",
       "notes": "Updated category to Transportation and confirmed payment via GPay"
     }'
```

#### Example Response (`200 OK`)
```json
{
  "id": 102,
  "user_id": 1,
  "sms_log_id": 482,
  "amount": "150.50",
  "txn_type": "debit",
  "merchant_raw": "Starbucks Coffee",
  "merchant_clean": "Starbucks",
  "category_id": 5,
  "category_name": "Transportation",
  "upi_app": "GPay",
  "app_label_source": "user_labeled",
  "app_label_confidence": null,
  "source": "sms",
  "bank_ref_id": "TXN9876543210",
  "txn_timestamp": "2026-06-30T10:15:00+05:30",
  "notes": "Updated category to Transportation and confirmed payment via GPay",
  "created_at": "2026-06-30T10:16:12Z",
  "updated_at": "2026-06-30T12:10:02Z"
}
```

---

### 5. Delete Transaction
Deletes the specified transaction. This triggers a background task to recalculate user transaction aggregates for the affected month and week.

* **URL**: `/api/v1/transaction/{id}`
* **Method**: `DELETE`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Path Parameters**:
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `id` | `int` | Yes | Unique ID of transaction to delete. |

#### Response Fields
| Key | Type | Description |
| :--- | :--- | :--- |
| `success` | `bool` | `true` indicating the deletion was successful. |
| `message` | `str` | User-friendly confirmation message. |
| `transaction_id`| `int` | The database ID of the deleted transaction. |

#### cURL Request
```bash
curl -X DELETE "http://localhost:8000/api/v1/transaction/103" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "success": true,
  "message": "Transaction deleted successfully",
  "transaction_id": 103
}
```

---

## Error Handling

The endpoints use standard HTTP status codes to communicate success or failure:

* **`200 OK`**: Request succeeded (or transaction deleted).
* **`201 Created`**: Transaction created successfully.
* **`401 Unauthorized`**: Missing, invalid, or expired authentication token.
  ```json
  {
    "detail": "Invalid or expired token"
  }
  ```
* **`403 Forbidden`**: User is not authorized to access or modify this transaction.
  ```json
  {
    "detail": "You are not authorized to update this transaction."
  }
  ```
* **`404 Not Found`**: Transaction ID does not exist in the database.
  ```json
  {
    "detail": "Transaction not found."
  }
  ```
* **`422 Unprocessable Entity`**: Payload parsing/validation error (e.g. invalid `txn_type` value or negative amount).
  ```json
  {
    "detail": [
      {
        "loc": ["body", "amount"],
        "msg": "value is not a valid float",
        "type": "type_error.float"
      }
    ]
  }
  ```
* **`500 Internal Server Error`**: Unexpected server error.
  ```json
  {
    "detail": "Failed to create transaction."
  }
  ```
