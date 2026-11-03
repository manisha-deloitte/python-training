# Django Document and Query API: Learning Guide

This guide explains the project file by file and follows a request from the HTTP
client through Django REST Framework (DRF), the database, and back to the
client. It is intended as a preparation guide for explaining and demonstrating
the code.

## 1. What the project does

The application is a Django REST API with three main data models:

- `Document`: a user's title and text content, plus its owner and upload time.
- `QueryLog`: a user's submitted query text, plus a result summary and creation
  time.
- `UserSession`: a user's API token and its expiration time.

The API uses SQLite for persistence and a custom token authentication class.
Most API endpoints require a valid token. Registration and login are public.
Document lists and query history are scoped to the logged-in user.

The query endpoint records query text; it does not search documents or execute
the query. The `result_summary` is blank when a log is first created.

## 2. Project files

### Root files

#### `manage.py`

This is Django's command-line entry point. It sets
`DJANGO_SETTINGS_MODULE=config.settings`, so Django knows which settings to
load, and passes the command-line arguments to Django.

For example:

```powershell
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py test
```

`uv run` selects the project's virtual environment. `python manage.py ...`
invokes Django's management script inside that environment.

#### `pyproject.toml`

This file defines the project metadata and Python package dependencies for
`uv`. `requires-python` describes the supported minimum Python version.
`package = false` tells `uv` this is an application rather than a package to
build and install.

`uv sync` reads this file and `uv.lock`, creates or updates `.venv`, and
installs the locked dependencies.

#### `uv.lock`

This is the dependency lock file produced by `uv`. It records the resolved
versions of the direct dependencies and their dependencies, making installs
more repeatable across machines.

#### `requirements.txt`

This is an alternate dependency list for tools that install dependencies with
pip. It duplicates the direct Django and DRF dependencies from
`pyproject.toml`. The primary documented workflow uses `uv sync`.

#### `README.md`

The README is the quick-start reference: environment setup, server start,
Swagger URLs, endpoints, and example requests. This learning guide provides
the deeper explanation of how those features are implemented.

#### `db.sqlite3`

This is the local SQLite database file. Django's ORM reads and writes data
here after migrations have created the tables. It is generated runtime data,
not Python source code. Keep a copy if you need to preserve local records.

### The `config` folder

This folder contains project-wide Django configuration. `config` is the
project package; `apps/api` is the application that implements the API.

The layout follows a common Django convention: `manage.py` is at the
repository root, the Django project package holds settings and server entry
points, and installed apps live in a separate `apps` package. Django allows
apps at the root too; the `apps` package keeps this project's app code
separate and leaves room for more apps.

#### `config/__init__.py`

Marks `config` as a Python package. It is empty because no package setup is
needed here.

#### `config/settings.py`

This is the main Django settings file. It configures:

- `BASE_DIR`, from which the local SQLite path is constructed.
- `INSTALLED_APPS`, including Django's built-in apps, DRF, and
  `"apps.api.apps.ApiConfig"`.
- `MIDDLEWARE`, Django's request/response middleware stack.
- `ROOT_URLCONF`, which points Django to `config.urls`.
- `DATABASES`, configured to use the local `db.sqlite3` file.
- `AUTH_PASSWORD_VALIDATORS`, which check newly-created passwords.
- DRF's default authentication class, permission class, and pagination class.
- Django's logging configuration, which sends API request logs to the console.

The key API settings are:

```python
"DEFAULT_AUTHENTICATION_CLASSES": [
    "apps.api.authentication.UserSessionAuthentication",
],
"DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.IsAuthenticated",
],
"DEFAULT_PAGINATION_CLASS": "apps.api.pagination.DefaultPagination",
"PAGE_SIZE": 10,
```

They make the custom token authentication and authenticated access the
defaults. `RegisterView` and `LoginView` explicitly use `AllowAny` because a
new user cannot already have a token.

Pagination is not automatically applied by Django to JSON API list responses.
DRF provides pagination classes, and this project's settings select the
project-specific `DefaultPagination` class for DRF generic list views.

The `LOGGING` setting defines a console handler and the `api.requests` logger
used by the custom request-logging middleware.

For a training project, `DEBUG = True`, `ALLOWED_HOSTS = ["*"]`, and the
literal `SECRET_KEY` are convenient local defaults. They should be replaced
with secure, environment-specific configuration before deployment.

#### `config/urls.py`

This is the top-level URL router. It maps:

- `/admin/` to Django's admin application.
- `/api/schema/` to the OpenAPI JSON schema endpoint.
- `/api/docs/` to the Swagger UI page.
- All other matched API routes to `apps.api.urls`.

The `include("apps.api.urls")` line delegates endpoint matching to the API
app.

#### `config/asgi.py`

Creates the ASGI application object used by ASGI-compatible servers. ASGI is
an asynchronous-capable server interface.

#### `config/wsgi.py`

Creates the WSGI application object used by traditional WSGI-compatible
servers. Both entry-point files set the Django settings module before creating
the application object.

### The `apps` and `apps/api` folders

`apps` is a Python package grouping Django applications. `apps/api` is the
Django app containing the API's data models, serializers, views,
authentication, request logging, pagination, routes, schema, tests, and
migrations. `ApiConfig.label = "api"` keeps Django's app/migration label
unchanged even though its Python import path is now `apps.api`.

#### `apps/__init__.py` and `apps/api/__init__.py`

These empty files mark the `apps` package and the `api` app package so Python
can import their modules.

#### `apps/api/apps.py`

Defines `ApiConfig`, the Django application configuration for the `api` app.
`name = "apps.api"` is the Python import path. `label = "api"` preserves the
existing app label. Settings registers this configuration as
`"apps.api.apps.ApiConfig"`.

#### `apps/api/models.py`

Models define database records. Django uses each model to create and query a
database table.

**`Document`**

- `title`: required text up to 255 characters.
- `content`: document text.
- `uploaded_at`: automatically set when the record is first created.
- `owner`: foreign key to the configured Django user model.

`related_name="documents"` makes a user's related documents accessible as
`user.documents`. `on_delete=models.CASCADE` means deleting the user deletes
that user's documents. `__str__` gives the document title a readable
representation in Django tools.

An uploaded file is read as UTF-8 text and saved in `content`. The original
file is not stored separately on disk or in a file-storage service.

**`QueryLog`**

- `query_text`: submitted query text.
- `result_summary`: text field that allows an empty string.
- `created_at`: automatically set when the log is created.
- `user`: foreign key to the configured Django user model.

The `user.query_logs` reverse relation provides access to a user's logs.
Deleting a user cascades to their query logs. The endpoint currently records
the submitted query only; it does not run a document search.

**`UserSession`**

- `user`: foreign key to the user who owns the token.
- `token`: unique token string.
- `created_at`: automatically set on creation.
- `expires_at`: date and time after which authentication rejects the token.

`user.api_sessions` is the reverse relation. The login endpoint sets
`expires_at` to seven days after the session is created.

#### `apps/api/migrations/0001_initial.py`

A migration is Django's version-controlled description of a database schema
change. This initial migration creates the three application tables and their
columns, primary keys, and user foreign keys.

`python manage.py migrate` applies this migration to SQLite. When a model is
changed, create a new migration with `makemigrations` and then apply it with
`migrate`; do not edit an already-applied database table by hand.

#### `apps/api/migrations/__init__.py`

Marks the migrations directory as a Python package. Django discovers
migrations in this package.

#### `apps/api/serializers.py`

DRF serializers validate incoming data and convert Python/model values to and
from JSON-friendly representations.

**`RegistrationSerializer`** exposes the new account's ID, username, and
password input. The password is write-only, so it is not returned in the API
response. Its `create` method calls `User.objects.create_user`, which hashes
the password instead of saving it as plain text.

**`DocumentSerializer`** converts a document to or from the `Document` model.
The ID, timestamp, and owner are read-only to clients. The view assigns the
owner from the authenticated request rather than trusting a client-supplied
owner ID.

**`DocumentUploadSerializer`** validates multipart file input. A `file` is
required; `title` is optional and limited to 255 characters. The view applies
the file extension and file-size checks after serializer validation.

**`QueryLogSerializer`** validates `query_text` and serializes the full log
for responses. The ID, result summary, creation time, and user are read-only.
The view assigns the user from the authenticated request; clients cannot
choose another owner by including a `user` value in the input.

#### `apps/api/authentication.py`

`UserSessionAuthentication` implements DRF's authentication interface.

1. It reads the `Authorization` header.
2. With no header, it returns `None`; DRF then treats the request as
   unauthenticated.
3. It expects two parts in the header, for example
   `Authorization: Token abc123`.
4. It looks up a matching `UserSession` whose `expires_at` is in the future.
5. If found, it returns `(session.user, session)`. DRF puts these values on
   `request.user` and `request.auth`.
6. If the header is malformed or the token is invalid/expired, it raises
   `AuthenticationFailed`.

`authenticate_header` tells DRF that this authentication scheme uses the
`Token` header style for its authentication challenge.

#### `apps/api/views.py`

Views implement endpoint behavior. They receive an HTTP request, validate or
query data, and return a DRF `Response`.

**`RegisterView`**

Uses DRF's `CreateAPIView` and `RegistrationSerializer` to validate and create
a user. `AllowAny` permits registration without a token.

**`LoginView`**

Uses `AllowAny` so users can obtain a token. It passes the submitted username
and password to Django's `authenticate`. If credentials do not match, it
returns `400 Bad Request`. On success, it generates a random token with
`secrets.token_hex(32)`, creates a `UserSession` that expires in seven days,
and returns the token as JSON.

**`DocumentListCreateView`**

Combines `GET /documents` and `POST /documents`.

- `get_queryset` filters documents to `owner=self.request.user` and sorts
  newest first. The list therefore does not expose other users' documents.
- `parser_classes` accepts JSON and multipart requests.
- `post` checks the request content type to select a creation mode:
  - For `application/json`, `DocumentSerializer` validates `title` and
    `content`.
  - For multipart, the view rejects a `content` field, validates the upload
    fields, checks that the file is at most 5 MB and has a `.txt`, `.md`, or
    `.csv` extension, then reads and decodes UTF-8 text.
- The view validates the resulting document data and saves it with
  `owner=request.user`.
- It serializes the saved record and returns `201 Created`.

This means a request must be either JSON content or a file upload, not a
mixture of the two.

**`DocumentDetailView`**

Provides document retrieval and deletion through DRF's
`RetrieveDestroyAPIView`.

- `get_queryset` limits retrieval to the requesting user's documents. A
  missing document and another user's document both produce `404 Not Found`
  on retrieval.
- `destroy` deliberately looks up the document without the owner filter, then
  checks ownership. A nonexistent document returns 404; a document owned by
  another user returns `403 Forbidden`; an owned document is deleted and
  returns `204 No Content`.

The assignment's listed document endpoints provide create, list, retrieve,
and delete. There is no `PUT` or `PATCH` update endpoint in this project, even
though those are sometimes included in the phrase "full CRUD."

**`QueryCreateView`**

Handles only `POST /query`.

1. `QueryLogSerializer` checks the submitted JSON, including requiring
   `query_text`.
2. `QueryLog.objects.create(...)` explicitly inserts a new database record,
   using `request.user` for the owner.
3. `QueryLogSerializer(query_log).data` converts the saved record to response
   data, including its generated ID, timestamp, user ID, and empty
   `result_summary`.
4. The response is returned with `201 Created`.

The ORM call writes the row to the database; it does not execute the text as a
database query or search the documents.

**`QueryListView`**

Handles `GET /queries`. Its `get_queryset` returns only the current user's
logs, newest first. DRF applies the configured paginator and serializes the
page.

#### `apps/api/urls.py`

This file maps API paths to views:

- `/register` and `/login`
- `/documents` for list and create
- `/documents/<int:pk>` for retrieve and delete
- `/query` for log creation
- `/queries` for paginated history

The URL file only maps paths to views. Pagination is set as DRF's project-wide
default in `config/settings.py`, so list views receive the `DefaultPagination`
class automatically. `DefaultPagination` is defined in
`apps/api/pagination.py`. It uses a page size of 10. Clients can set
`page_size`, up to 100, and `page` selects the page number. Paginated
responses include `count`, `next`, `previous`, and `results`.

#### `apps/api/pagination.py`

Defines the DRF `PageNumberPagination` subclass. `page_size` sets the default,
`page_size_query_param` allows clients to choose a page size, and
`max_page_size` caps that value. It is configured globally in
`REST_FRAMEWORK`, rather than attached manually to each URL.

#### `apps/api/middleware.py`

`ApiRequestLoggingMiddleware` logs each API request after a response is
produced. It records method, path, status code, and elapsed time. Successful
responses are logged at INFO and 4xx/5xx responses at WARNING. Unhandled
exceptions are logged with a traceback and then re-raised. It deliberately
does not record request bodies or authorization tokens.

The middleware only logs known API path prefixes; it does not log the Django
admin or Swagger UI page requests. The logger is named `api.requests` and is
configured in `config/settings.py` to print to the runserver console.

#### `apps/api/schema.py`

This file contains an explicit OpenAPI 3.0.3 schema describing the API:
paths, methods, request and response shapes, pagination parameters, and token
authentication. It also defines two public DRF views:

- `OpenApiSchemaView` returns the schema as JSON at `/api/schema/`.
- `SwaggerUIView` returns an HTML page that loads Swagger UI and points it at
  the schema URL.

Swagger's JavaScript and CSS are loaded from a CDN, so the interactive page
needs internet access. The API itself and the OpenAPI JSON endpoint are served
locally.

#### `apps/api/tests.py`

These are automated API tests based on DRF's `APITestCase`. Django creates a
temporary test database, executes the tests, and removes that database after
the run.

The test setup creates users and a valid token, then authenticates requests
with the token header. The tests cover:

- Registration, login, and rejecting a protected request without a token.
- Document creation, retrieval, deletion, and owner access rules.
- File upload, size/type validation, malformed inputs, and rejecting mixed
  file/content input.
- User-scoped document and query pagination.
- API request method/path/status logging without token disclosure.
- Query creation, database persistence, returned response fields, and
  retrieval through `/queries`.
- Availability of the Swagger page and OpenAPI schema.

Run them with:

```powershell
uv run python manage.py test
```

## 3. How a request moves through the project

For an authenticated request such as `POST /query`:

1. Django receives the HTTP request.
2. `config/urls.py` includes `apps.api.urls`, which matches `/query`.
3. DRF applies the default authentication class from `config/settings.py`.
4. `UserSessionAuthentication` validates the `Authorization` token and
   provides `request.user`.
5. DRF's default `IsAuthenticated` permission blocks requests without an
   authenticated user.
6. `QueryCreateView.post` validates request data with `QueryLogSerializer`.
7. `QueryLog.objects.create` writes the record to SQLite.
8. The serializer converts the saved record to JSON data.
9. DRF returns an HTTP response with status `201`.

For `GET /queries`, the URL selects `QueryListView`; its queryset filters by
`request.user`, then the globally configured DRF `DefaultPagination` produces
the page and DRF serializes the results.

For `POST /documents`, the same authentication and permission steps happen
before the view selects JSON or multipart input and validates the data.

## 4. Run and demonstrate the project

### Prepare and start

From PowerShell in the project directory:

```powershell
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open Swagger UI at `http://127.0.0.1:8000/api/docs/`. The schema is also
available at `http://127.0.0.1:8000/api/schema/`.

### Suggested live demo

1. **Register:** call `POST /register` with a username and password. Explain
   that `RegistrationSerializer` validates input and `create_user` hashes the
   password.
2. **Log in:** call `POST /login` with the same credentials. Explain that
   Django checks the password and the view creates a seven-day
   `UserSession`.
3. **Authorize Swagger:** use **Authorize** and enter `Token <token>`.
4. **Create a document with JSON:** call `POST /documents` with `title` and
   `content`; point out the response's generated ID and owner.
5. **Create a document with a file:** upload a small `.txt` file using the
   multipart form. Explain that the server saves its decoded text as
   `Document.content`, not as a separate stored file.
6. **List and retrieve:** call `GET /documents`, then `GET /documents/{id}`.
   Demonstrate pagination with `page_size=1` if there is more than one
   document.
7. **Create a query log:** call `POST /query` with `{"query_text": "..."}`.
   Show that the returned ID is saved and that `result_summary` is initially
   empty.
8. **Read history:** call `GET /queries` and show the saved log.
9. **Delete a document:** call `DELETE /documents/{id}` and explain that
   successful deletion returns `204` with no response body.
10. **Show access control:** explain that lists are filtered by user, document
    retrieval hides another user's document with 404, and deleting another
    user's document returns 403.

### Useful commands

```powershell
uv run python manage.py check
uv run python manage.py test
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## 5. Important behavior and limitations to explain

- The business endpoints that create or read user data require a token, except
  registration and login. The schema and Swagger documentation routes are
  public so developers can inspect the API before authenticating.
- The token is sent in the `Authorization: Token <token>` header and expires
  after seven days.
- Document and query list endpoints only return records belonging to the
  authenticated user.
- Uploaded files are restricted by extension and size and must decode as
  UTF-8. The contents are saved in SQLite as document text.
- `POST /query` stores the query text. No query engine or document-search
  behavior is implemented.
- `GET /queries` is the query history route; `/query` is for POST only.
- The provided document routes do not implement update (`PUT`/`PATCH`).
- SQLite is suitable for local learning and demonstration. Production
  deployment would need deployment-specific settings, a production database,
  and secure secret management.
