# SpendSense Dashboard APIs Integration Guide

This integration guide provides client-side developers with detailed documentation for integrating the **SpendSense Dashboard APIs**.

All dashboard endpoints require user authentication via a **JSON Web Token (JWT)**.

---

## Table of Contents
1. [Authentication Overview](#authentication-overview)
2. [API Reference](#api-reference)
   - [1. Get Today's Spend Summary](#1-get-todays-spend-summary)
   - [2. Get Current Month's Spend Summary](#2-get-current-months-spend-summary)
   - [3. Get Category Breakdown (Pie Chart)](#3-get-category-breakdown-pie-chart)
   - [4. Get UPI vs Manual Spend Summary](#4-get-upi-vs-manual-spend-summary)
   - [5. Get UPI Apps Breakdown](#5-get-upi-apps-breakdown)
3. [Error Handling](#error-handling)

---

## Authentication Overview

All requests to the dashboard endpoints must include the authentication token in the request header.

* **Header Key**: `Authorization`
* **Header Value**: `Bearer <JWT_ACCESS_TOKEN>`

### Authentication Example Header
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## API Reference

### 1. Get Today's Spend Summary
Retrieves the total debit amount and transaction count for the authenticated user for the current day (IST context, queried using UTC timestamps). It also compares today's spend with yesterday's spend to indicate the trend.

* **URL**: `/api/v1/dashboard/today`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**: None
* **Payload**: None

#### Response Fields (`DashboardTodayResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `total_amount` | `Decimal` | Total expense (debit) amount accumulated today. |
| `count` | `int` | Total number of debit transactions made today. |
| `difference` | `Decimal` | The difference between today's and yesterday's total spend (`today_total - yesterday_total`). |
| `diff_percent` | `float` | Percentage change compared to yesterday (rounded to 2 decimal places). |
| `is_higher` | `bool` | `true` if today's spend is higher than yesterday's, `false` otherwise. |

#### cURL Request
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/today" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "total_amount": "250.50",
  "count": 3,
  "difference": "50.00",
  "diff_percent": 25.0,
  "is_higher": true
}
```

---

### 2. Get Current Month's Spend Summary
Retrieves the total debit amount and transaction count for the current calendar month in IST, comparing it against the previous month.

* **URL**: `/api/v1/dashboard/current-month`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**: None
* **Payload**: None

#### Response Fields (`DashboardCurrentMonthResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `total_amount` | `Decimal` | Total expense (debit) amount accumulated during the current calendar month. |
| `count` | `int` | Total number of debit transactions made in the current month. |
| `last_month_total`| `Decimal` | Total expense (debit) amount accumulated in the previous calendar month. |
| `difference` | `Decimal` | The difference between the current month's and last month's spend (`current_month - last_month`). |
| `diff_percent` | `float` | Percentage change compared to last month (rounded to 2 decimal places). |
| `is_higher` | `bool` | `true` if this month's spend is higher than last month's, `false` otherwise. |

#### cURL Request
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/current-month" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "total_amount": "12450.00",
  "count": 45,
  "last_month_total": "11000.00",
  "difference": "1450.00",
  "diff_percent": 13.18,
  "is_higher": true
}
```

---

### 3. Get Category Breakdown (Pie Chart)
Fetches the category-wise spend breakdown for the current month or chosen filter period. This endpoint resolves category IDs to category names and returns categories sorted in descending order of spend.

* **URL**: `/api/v1/dashboard/breakdown`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `filter_type` | `str` | No | `month` | Granularity of the date range: `day`, `week`, `month`, `custom`. |
  | `custom_start`| `str` | Conditional | `None` | Start date string in ISO-8601 format (e.g. `2024-06-01`). Required if `filter_type=custom`. |
  | `custom_end`  | `str` | Conditional | `None` | End date string in ISO-8601 format (e.g. `2024-06-30`). Required if `filter_type=custom`. |

#### Response Fields (`DashboardBreakdownResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `total_amount` | `Decimal` | Total spent across all categories in the current period. |
| `categories` | `List[CategoryBreakdownItem]` | List of categorized spend details, sorted descending by amount. |

##### `CategoryBreakdownItem` Fields
| Key | Type | Description |
| :--- | :--- | :--- |
| `category_name` | `str` | Resolved human-readable category name (e.g. `Food & Dining`, `Rent`, `Uncategorized`). |
| `amount` | `Decimal` | Total amount spent in this category. |
| `percentage` | `float` | Percentage of total monthly spend this category represents (rounded to 2 decimal places). |

#### cURL Requests

##### Example 1: Default (Current Month)
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/breakdown" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

##### Example 2: Week-wise Filter
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/breakdown?filter_type=week" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "total_amount": "12450.00",
  "categories": [
    {
      "category_name": "Rent",
      "amount": "6000.00",
      "percentage": 48.19
    },
    {
      "category_name": "Food & Dining",
      "amount": "4500.00",
      "percentage": 36.14
    },
    {
      "category_name": "Shopping",
      "amount": "1200.00",
      "percentage": 9.64
    },
    {
      "category_name": "Uncategorized",
      "amount": "750.00",
      "percentage": 6.02
    }
  ]
}
```

---

### 4. Get UPI vs Manual Spend Summary
Fetches the aggregated total of UPI transactions (source = `sms`) and manual transactions (source = `manual`) for the chosen time period.

* **URL**: `/api/v1/dashboard/upi-manual-spend`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `filter_type` | `str` | No | `month` | Granularity of the date range: `day`, `week`, `month`, `custom`. |
  | `custom_start`| `str` | Conditional | `None` | Start date string in ISO-8601 format (e.g. `2024-06-01`). Required if `filter_type=custom`. |
  | `custom_end`  | `str` | Conditional | `None` | End date string in ISO-8601 format (e.g. `2024-06-30`). Required if `filter_type=custom`. |

#### Response Fields (`UPIManualSpendResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `upi_spend` | `Decimal` | Total amount spent via automated/SMS UPI transactions. |
| `manual_spend`| `Decimal` | Total amount spent via manual entries. |
| `filter_type` | `str` | The filter type applied to query the data (`day`, `week`, `month`, or `custom`). |
| `period_start`| `str` | Calculated starting timestamp of the period in IST (ISO-8601 format with timezone offset, e.g. `YYYY-MM-DDTHH:MM:SS+05:30`). |
| `period_end`  | `str` | Calculated ending timestamp of the period in IST (ISO-8601 format with timezone offset, e.g. `YYYY-MM-DDTHH:MM:SS+05:30`). |

#### cURL Requests

##### Example 1: Default (Current Month)
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/upi-manual-spend" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

##### Example 2: Custom Date Range Filter
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/upi-manual-spend?filter_type=custom&custom_start=2024-06-01&custom_end=2024-06-15" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "upi_spend": "8500.00",
  "manual_spend": "3950.00",
  "filter_type": "month",
  "period_start": "2026-06-01T00:00:00+05:30",
  "period_end": "2026-06-30T23:59:59+05:30"
}
```

---

### 5. Get UPI Apps Breakdown
Fetches a list of UPI apps used for debit transactions during the selected period, detailing the absolute spend per app and its relative percentage of total UPI spend.

* **URL**: `/api/v1/dashboard/upi-apps-breakdown`
* **Method**: `GET`
* **Auth Required**: Yes (`Bearer <token>`)

#### Request Details
* **Query Parameters**:
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `filter_type` | `str` | No | `month` | Granularity of the date range: `day`, `week`, `month`, `custom`. |
  | `custom_start`| `str` | Conditional | `None` | Start date string in ISO-8601 format (e.g. `2024-06-01`). Required if `filter_type=custom`. |
  | `custom_end`  | `str` | Conditional | `None` | End date string in ISO-8601 format (e.g. `2024-06-30`). Required if `filter_type=custom`. |

#### Response Fields (`DashboardUPIBreakdownResponse`)
| Key | Type | Description |
| :--- | :--- | :--- |
| `total_spend` | `Decimal` | Total spend accumulated across all UPI apps. |
| `items` | `List[UPIAppBreakdownItem]` | Breakdown of spend details per UPI app, sorted descending by amount. |
| `period_start`| `str` | Calculated starting timestamp of the period in IST (ISO-8601 format with timezone offset, e.g. `YYYY-MM-DDTHH:MM:SS+05:30`). |
| `period_end`  | `str` | Calculated ending timestamp of the period in IST (ISO-8601 format with timezone offset, e.g. `YYYY-MM-DDTHH:MM:SS+05:30`). |

##### `UPIAppBreakdownItem` Fields
| Key | Type | Description |
| :--- | :--- | :--- |
| `app` | `str` | Name of the UPI app (e.g. `PhonePe`, `GPay`, `Paytm`, `Unknown`). |
| `app_label_source`| `str` | Source identifier for the app's labeling category (e.g., `parsed`, `manual`, `unlabeled`, `unknown`). |
| `amount` | `Decimal` | Total amount spent using this app. |
| `percentage` | `float` | Percentage of total UPI spend this app accounts for (rounded to 2 decimal places). |

#### cURL Request
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/upi-apps-breakdown?filter_type=month" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`)
```json
{
  "total_spend": "8500.00",
  "items": [
    {
      "app": "PhonePe",
      "app_label_source": "parsed",
      "amount": "5000.00",
      "percentage": 58.82
    },
    {
      "app": "GPay",
      "app_label_source": "parsed",
      "amount": "2500.00",
      "percentage": 29.41
    },
    {
      "app": "Paytm",
      "app_label_source": "parsed",
      "amount": "1000.00",
      "percentage": 11.76
    }
  ],
  "period_start": "2026-06-01T00:00:00+05:30",
  "period_end": "2026-06-30T23:59:59+05:30"
}
```

---

## Error Handling

The endpoints use standard HTTP status codes to communicate success or failure:

* **`200 OK`**: Request succeeded and returned the requested dashboard data.
* **`401 Unauthorized`**: Missing, invalid, or expired authentication token.
  ```json
  {
    "detail": "Invalid or expired token"
  }
  ```
* **`422 Unprocessable Entity`**: Validation errors, e.g. custom date filter missing required dates or invalid query parameter values.
  ```json
  {
    "detail": [
      {
        "loc": ["query", "custom_start"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
  ```
* **`500 Internal Server Error`**: Unexpected server error.
  ```json
  {
    "detail": "Failed to retrieve today's dashboard data."
  }
  ```
