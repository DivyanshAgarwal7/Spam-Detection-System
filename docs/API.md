\# Spam Detection System - API Documentation



\## Base URL

http://localhost:3000/api/v1



\## Authentication

All protected endpoints require a Bearer token:

Authorization: Bearer <your\_token>



\## Auth Routes



| Method | Endpoint | Description | Auth |

|--------|----------|-------------|------|

| POST | `/auth/register` | Register new user | ❌ |

| POST | `/auth/login` | Login user | ❌ |

| GET | `/auth/profile` | Get user profile | ✅ |



\---



\## Prediction Routes



| Method | Endpoint | Description | Auth |

|--------|----------|-------------|------|

| POST | `/predict` | Predict spam/ham | ✅ |

| POST | `/bulk-predict` | Bulk spam detection | ✅ |

| POST | `/feedback` | Submit feedback | ✅ |

| POST | `/analyze-email-header` | Analyze email headers | ✅ |

| POST | `/bulk-predict/export` | Export predictions as CSV | ✅ |



\---



\## Analytics Routes



| Method | Endpoint | Description | Auth |

|--------|----------|-------------|------|

| GET | `/analytics/page-visits` | Page visit metrics | ✅ |

| GET | `/analytics/visits-by-role` | Visits by role | ✅ |



\---



\## Email Integration Routes



| Method | Endpoint | Description | Auth |

|--------|----------|-------------|------|

| GET | `/gmail/auth-url` | Get Gmail auth URL | ✅ |

| GET | `/gmail/emails` | Get Gmail emails | ✅ |

| GET | `/outlook/auth-url` | Get Outlook auth URL | ✅ |

| GET | `/outlook/emails` | Get Outlook emails | ✅ |

| POST | `/scan-emails` | Scan connected emails | ✅ |



\---



\## Public Routes



| Method | Endpoint | Description | Auth |

|--------|----------|-------------|------|

| GET | `/health` | Health check | ❌ |

| GET | `/api/wordcloud` | Word cloud data | ❌ |

| GET | `/importance` | Feature importance | ❌ |



\---



\## Response Format



\### Success Response

```json

{

&#x20; "success": true,

&#x20; "data": { ... }

}

```





