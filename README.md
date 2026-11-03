# Django Document and Query API

A training project that provides a persistent Django REST Framework API for managing documents and recording queries. Data is stored in a local SQLite database. The API uses expiring token authentication and includes an interactive Swagger UI for exploring and testing endpoints.

## Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Set up the project

Run these commands from the project directory in PowerShell. `uv sync` creates `.venv`, installs the dependencies from `pyproject.toml`, and creates or updates `uv.lock`:

```powershell
uv sync
uv run python manage.py migrate
```

No environment activation is needed. Use `uv run` for project commands so they run with the project's managed environment and locked dependencies:

```powershell
uv run python manage.py runserver
uv run python manage.py check
uv run python manage.py test
```

`uv run` still runs Python: Django's management interface is the `manage.py` Python script, so the complete command is `uv run python manage.py <command>`. `uv` selects the project's Python environment and runs that script inside it.

The project also includes a standard `requirements.txt` for users who prefer pip or other tools:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
```

## Start the server

```powershell
uv run python manage.py runserver
```

The local server is available at `http://127.0.0.1:8000/`.

## Project structure

The project separates Django's project configuration from its installed app:

```text
manage.py
config/
    settings.py
    urls.py
    asgi.py
    wsgi.py
apps/
    __init__.py
    api/                 Django app (app label: api)
        apps.py
        models.py
        serializers.py
        views.py
        urls.py
        authentication.py
        middleware.py
        pagination.py
        schema.py
        tests.py
        migrations/
```

`config` contains project-wide settings and the top-level URL router.
`apps/api` contains the API application code. The app keeps the Django label
`api`, so the existing database tables and migrations keep their labels.

## API request logs

API requests are logged to the runserver console with the HTTP method, path,
response status, and request duration. Requests with 4xx or 5xx responses are
logged as warnings, and uncaught errors are logged with a traceback before
being re-raised. Request bodies and authorization tokens are not included in
the logs.

## Swagger and API schema

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

Swagger UI loads its interface assets from a CDN, so an internet connection is needed to display the interactive page. The API and OpenAPI schema are served locally. Use Swagger UI to view request and response shapes and send requests to the running local API. To test protected endpoints:

1. Use `POST /register` to create an account.
2. Use `POST /login` with that account's username and password.
3. Copy the returned token.
4. In Swagger UI, select **Authorize** and enter `Token <your-token>`, or send the header `Authorization: Token <your-token>`.
5. Try the protected endpoints.

The token expires seven days after login. Registering and logging in do not require a token.

## Endpoints

| Method | Path | Description | Authentication |
|---|---|---|---|
| `POST` | `/register` | Create a user account | Not required |
| `POST` | `/login` | Log in and receive an API token | Not required |
| `POST` | `/documents` | Create a document from JSON or an uploaded text file | Required |
| `GET` | `/documents` | List the current user's documents | Required |
| `GET` | `/documents/{id}` | Retrieve a document owned by the current user | Required |
| `DELETE` | `/documents/{id}` | Delete a document owned by the current user | Required |
| `POST` | `/query` | Add an entry to the current user's query history | Required |
| `GET` | `/queries` | List the current user's query history | Required |

### Register and log in

Register with JSON:

```json
{
  "username": "alice",
  "password": "choose-a-password"
}
```

Log in with the same JSON fields. A successful response contains the token:

```json
{
  "token": "your-issued-token"
}
```

Send that token on protected API requests:

```http
Authorization: Token your-issued-token
```

### Create documents

Send exactly one of the following request types to `POST /documents`: a JSON body containing `title` and `content`, or a `multipart/form-data` file upload. Do not combine a file and JSON `content` in the same request.

JSON request:

```http
POST /documents
Content-Type: application/json
Authorization: Token your-issued-token
```

```json
{
  "title": "Training notes",
  "content": "Text stored in this document."
}
```

File uploads use `multipart/form-data` with a `file` field and an optional `title` field. When omitted, the filename is used as the document title. Only `.txt`, `.md`, and `.csv` files are accepted. Files larger than 5 MB receive `413 Payload Too Large`; unsupported extensions receive `400 Bad Request`. Uploaded files must contain UTF-8 text. File contents are stored in the document's `content` field; the original file is not retained.

A created document includes its ID, title, content, upload timestamp, and owner ID.

### List and paginate

Pagination is provided by Django REST Framework (DRF), not automatically by
Django itself. This project configures a DRF `PageNumberPagination` subclass
as the default for list views. Both `GET /documents` and `GET /queries` return
a paginated response:

```json
{
  "count": 25,
  "next": "http://127.0.0.1:8000/documents?page=2",
  "previous": null,
  "results": []
}
```

Use the optional `page` and `page_size` query parameters. The default page size is 10, and the maximum accepted page size is 100. For example:

```http
GET /documents?page=2&page_size=5
```

Only the authenticated user's documents and query history appear in these results.

### Submit a query

Send `POST /query` with a JSON body:

```json
{
  "query_text": "Find documents about Django"
}
```

The created query log includes its ID, query text, result summary, creation time, and user ID. `result_summary` is managed by the API and is initially empty.

The created object is persisted in the database and returned directly in the `201 Created` response. Use `GET /queries` to retrieve the authenticated user's saved query history; `GET /query` is not an endpoint.

## Response and access behavior

- `201 Created`: registration, document creation, or query creation succeeded.
- `204 No Content`: document deletion succeeded.
- `400 Bad Request`: invalid request data, unsupported upload type, or invalid login credentials.
- `401 Unauthorized`: a protected endpoint was called without a valid token.
- `403 Forbidden`: attempting to delete another user's document.
- `404 Not Found`: requested document does not exist or is owned by someone else.
- `413 Payload Too Large`: uploaded file exceeds 5 MB.

## Database and migrations

The default SQLite database is `db.sqlite3` in the project directory. After changing models, create and apply migrations:

```powershell
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Run checks and tests

```powershell
uv run python manage.py check
uv run python manage.py test
```
