# E-14 OCR & Scraper API Endpoints

Complete reference for all E-14 related endpoints in Castor.

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Electoral Control (`/api/electoral/`)

### Core OCR Processing

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/electoral/health` | Health check | No |
| `POST` | `/api/electoral/e14/process` | Process E-14 (upload or URL) | Yes |
| `POST` | `/api/electoral/e14/process-url` | Process E-14 from URL | Yes |
| `POST` | `/api/electoral/e14/process-v2` | Process E-14 with v2 payload | Yes |
| `POST` | `/api/electoral/e14/validate` | Validate E-14 extraction | Yes |
| `GET` | `/api/electoral/stats` | Get processing statistics | Yes |
| `GET` | `/api/electoral/usage` | Get user usage stats | Yes |
| `GET` | `/api/electoral/metrics` | Prometheus metrics | Yes |
| `GET` | `/api/electoral/metrics/json` | Metrics as JSON | Yes |
| `GET` | `/api/electoral/metrics/slo` | SLO compliance | Yes |

### Process E-14 (Upload)
```http
POST /api/electoral/e14/process
Content-Type: multipart/form-data

file: <PDF file>
```

### Process E-14 (URL)
```http
POST /api/electoral/e14/process
Content-Type: application/json

{
  "file_url": "https://...",
  "election_id": "optional",
  "force_reprocess": false
}
```

---

## Ingestion Pipeline (`/api/electoral/ingestion/`)

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/pipeline/status` | Pipeline status | Any |
| `POST` | `/pipeline/start` | Start pipeline | Admin |
| `POST` | `/pipeline/stop` | Stop pipeline | Admin |
| `POST` | `/pipeline/pause` | Pause pipeline | Admin |
| `POST` | `/pipeline/resume` | Resume pipeline | Admin |
| `POST` | `/queue/table` | Queue specific table | Operator |
| `POST` | `/queue/department` | Queue all tables in dept | Operator |

### Start Pipeline
```http
POST /api/electoral/ingestion/pipeline/start
Content-Type: application/json

{
  "election_type": "CONGRESO_2022",
  "copy_type": "CLAVEROS",
  "download_workers": 2,
  "ocr_workers": 4
}
```

---

## HITL Review (`/api/electoral/review/`)

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/queue` | Get review queue | Operator+ |
| `GET` | `/queue/stats` | Queue statistics | Any |
| `POST` | `/queue/next` | Claim next item | Validator |
| `GET` | `/item/<id>` | Get review item | Operator+ |
| `POST` | `/item/<id>/assign` | Assign to user | Validator |
| `POST` | `/item/<id>/complete` | Complete review | Validator |
| `POST` | `/item/<id>/reject` | Reject/skip item | Validator |

### Get Review Queue
```http
GET /api/electoral/review/queue?priority=HIGH&status=PENDING&limit=50
```

---

## Scraper & Batch Processing (`/api/scraper/`)

### Dashboard & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | Comprehensive dashboard data |
| `GET` | `/status` | Pipeline & queue status |
| `GET` | `/metrics` | OCR & processing metrics |

### Dashboard Response
```http
GET /api/scraper/dashboard

Response:
{
  "success": true,
  "timestamp": "2025-02-01T12:00:00Z",
  "data": {
    "pipeline": {
      "status": "RUNNING",
      "total_queued": 100,
      "downloaded": 50,
      "ocr_completed": 45,
      "validated": 40,
      "needs_review": 5,
      "completed": 35,
      "failed": 2
    },
    "scraper_queue": {...},
    "ocr": {
      "total_processed": 1000,
      "errors": 10,
      "avg_confidence": 0.92,
      "avg_duration_seconds": 8.5
    },
    "review": {
      "pending": 15,
      "in_progress": 3,
      "completed_today": 20
    }
  }
}
```

### Batch Processing

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/batch/info` | Info about PDFs to process | Any |
| `POST` | `/batch/process` | Start batch processing | Operator |
| `GET` | `/batch/status/<id>` | Batch job status | Any |
| `GET` | `/batch/results` | List batch results | Any |

### Get Batch Info
```http
GET /api/scraper/batch/info?pdf_dir=/path/to/pdfs

Response:
{
  "success": true,
  "data": {
    "pdf_dir": "/Users/.../actas_e14_masivo/pdfs_congreso_2022",
    "total_pdfs": 486,
    "total_size_mb": 138.5,
    "estimated_cost_usd": 48.60,
    "sample_files": ["2043318_E14_SEN_...", ...]
  }
}
```

### Start Batch Processing
```http
POST /api/scraper/batch/process
Content-Type: application/json

{
  "pdf_dir": "/path/to/pdfs",
  "limit": 10,
  "dry_run": false,
  "corporacion_hint": "SENADO"
}

Response:
{
  "success": true,
  "data": {
    "batch_id": "batch_20250201_120000",
    "total_pdfs": 10,
    "estimated_cost_usd": 1.00,
    "status_endpoint": "/api/scraper/batch/status/batch_20250201_120000"
  }
}
```

### Single PDF Processing

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/process-single` | Process single PDF from path | Operator |

```http
POST /api/scraper/process-single
Content-Type: application/json

{
  "file_path": "/path/to/file.pdf",
  "corporacion_hint": "SENADO"
}
```

### Pipeline Integration

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/pipeline/queue-from-folder` | Queue folder to pipeline | Admin |

```http
POST /api/scraper/pipeline/queue-from-folder
Content-Type: application/json

{
  "pdf_dir": "/path/to/pdfs",
  "limit": 100,
  "priority": "NORMAL"
}
```

### CAPTCHA Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/captcha/balance` | 2Captcha balance |

```http
GET /api/scraper/captcha/balance

Response:
{
  "success": true,
  "data": {
    "configured": true,
    "balance": 8.50,
    "low_balance_warning": false
  }
}
```

---

## Roles

| Role | Description |
|------|-------------|
| `USER` | Basic user, can view results |
| `OPERATOR` | Can process E-14s, queue tables |
| `VALIDATOR` | Can review and correct extractions |
| `ADMIN` | Full access, can start/stop pipeline |

---

## Response Format

All endpoints return JSON with this structure:

```json
{
  "success": true|false,
  "data": {...},        // On success
  "error": "...",       // On failure
  "code": "ERROR_CODE"  // On failure
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `MISSING_FILE` | No file provided |
| `INVALID_PDF` | PDF validation failed |
| `MISSING_URL` | URL not provided |
| `PROCESSING_ERROR` | OCR processing failed |
| `NOT_FOUND` | Resource not found |
| `PIPELINE_NOT_RUNNING` | Pipeline must be started |
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | Insufficient permissions |

---

## Frontend Integration Examples

### Dashboard Widget (React)
```javascript
// Fetch dashboard data
const fetchDashboard = async () => {
  const response = await fetch('/api/scraper/dashboard', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  return data.data;
};

// Start batch processing
const startBatch = async (limit = 10) => {
  const response = await fetch('/api/scraper/batch/process', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ limit, dry_run: false })
  });
  return response.json();
};
```

### Upload E-14 (React)
```javascript
const uploadE14 = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/electoral/e14/process', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  return response.json();
};
```

---

## Cost Limits

| Limit | Default Value |
|-------|---------------|
| Cost per E-14 | $0.10 USD |
| Hourly limit per user | $2.00 USD |
| Daily limit per user | $5.00 USD |
| Max file size | 10 MB |
| Max pages | 20 |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/e14/process` | 20/hour, 100/day |
| `/e14/process-url` | 20/hour, 100/day |
| Other endpoints | 120/minute |

---

*Last updated: 2025-02-01*
