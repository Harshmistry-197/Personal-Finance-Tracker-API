# Personal Finance Tracker API

A high-performance, **asynchronous REST API** engineered with **FastAPI** and **MongoDB**. This system delivers a robust financial management backend, leveraging **asynchronous drivers** for real-time insights and **full-text search** for efficient data discovery.

## Key Capabilities

- **Transaction Engine**: Complete CRUD operations for tracking income and expenditures.
- **Granular Filtering**: Multi-dimensional filtering by tags, category, type, and date ranges.
- **Financial Analytics**: Automated monthly health reports via advanced MongoDB aggregation pipelines.
- **Smart Search**: Integrated keyword search capabilities across all transaction titles and descriptions.
- **Strict Integrity**: Powered by **Pydantic v2** for rigorous schema enforcement and data validation.

---

## Tech Stack

- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com) (Asynchronous execution)
- **Data Store**: [MongoDB](https://www.mongodb.com) (Document-based storage)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev) (Type-safe data handling)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org) (Lightning-fast deployment)

---

## Data Modeling & Logic

### 1. Transactions Collection
- **Temporal Data**: Uses native `datetime` objects to optimize range queries and enable built-in aggregation operators like `$month` and `$year`.
- **Category Management**: Employs string-based denormalization. By storing names directly, the API avoids expensive `$lookup` joins, significantly speeding up "List" views.
- **Tagging System**: Utilizes string arrays with **multikey indexing** to facilitate rapid "contains" queries.

### 2. Categories Collection
- **Data Integrity**: Enforces a **unique constraint** on the `name` field to prevent duplicate entries and logical conflicts.
- **Categorization Logic**: The `type` field ("income", "expense", "both") provides a strict blueprint for front-end classification.

---

## Optimized Indexing Strategy
Indexes are automatically provisioned on startup via the [Motor Driver](https://motor.readthedocs.io) to ensure peak query performance.

| Index Configuration | Collection | Type | Primary Use Case |
| :--- | :--- | :--- | :--- |
| `date: -1` | `transactions` | Single Field | Powers chronological feeds and "most recent" sorting. |
| `{ category: 1, date: -1 }` | `transactions` | Compound | Accelerates filtered views by category and date. |
| `{ type: 1, date: -1 }` | `transactions` | Compound | Optimizes the generation of type-specific financial reports. |
| `{ title: "text", desc: "text" }` | `transactions` | Text | Enables sophisticated keyword search across records. |
| `name: 1` | `categories` | Unique | Guaranteed protection against duplicate category names. |


### Advanced Financial Intelligence
The `/transactions/summary` endpoint leverages a high-performance **`$facet`** pipeline, enabling multi-dimensional analysis in a single database round-trip:
- **Financial Totals**: Computes real-time sums for both `income` and `expense` types.
- **Categorical Insights**: Groups expenditures by category and calculates their percentage relative to total monthly spend.
- **Peak Expense Tracking**: Employs `$sort` and `$limit` logic to pinpoint the highest single transaction of the period.

---

### Project Architecture
```text
personal-finance-tracker-api/
├── .venv/                          # Isolated Python environment
├── personal_finance_tracker_api/   # Core application logic
│   ├── api/                        # Presentation layer
│   │   ├── __init__.py         
│   │   ├── app.py                  # Pydantic v2 schemas & strict validation
│   │   └── schemas.py              # Endpoint definitions & aggregation logic
│   ├── database/                   # Data persistence layer
│   │   ├── __init__.py         
│   │   └── data.py                 # Motor client & async CRUD operations
│   └── __init__.py             
├── .env                            # Local configuration (Secrets/URIs)
├── .gitignore                      # Version control exclusions
├── main.py                         # Entry point & startup index provisioning
├── poetry.lock                     # Deterministic dependency lock
├── pyproject.toml                  # Build system & package metadata
└── README.md                       # System documentation

```
---
## Quick Start Guide

1.  **Configure Environment**:
    Initialize a `.env` file in your project root with your database credentials:
    ```env
    MONGO_URI=mongodb://localhost:27017
    DATABASE_NAME=Finance
    ```

2.  **Initialize Project**:
    Install all required dependencies using [Poetry](https://python-poetry.org):
    ```bash
    poetry install
    ```

3.  **Launch the API**:
    Start the development server with hot-reload enabled:
    ```bash
    uvicorn main:app --reload
    ```

4.  **Explore the API**:
    Access the interactive [Swagger UI](https://fastapi.tiangolo.com) documentation at:
    [http://127.0.0.1](http://127.0.0.1)

---

## Summary

The **Personal Finance Tracker API** is engineered for high-performance data integrity and asynchronous scalability. By offloading complex reporting to the [MongoDB Aggregation Framework](https://www.mongodb.com), the system remains lightweight while delivering deep financial insights in real-time.

**Planned Roadmap:**
- **Secure Access**: Integrate [JWT Authentication](https://fastapi.tiangolo.com) for multi-tenant support.
- **Reporting Engine**: Add export functionality for **CSV/PDF** financial statements.
- **Latency Optimization**: Implement **Redis Caching** for high-frequency analytical queries.

