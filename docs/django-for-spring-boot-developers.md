# Django for Spring Boot Developers

> A field guide, written against the Lectra codebase.

You already know how to build a backend. You know entities, repositories, controllers, DI, migrations. **None of that knowledge is wasted here.** What's confusing about Django isn't the concepts — it's that Python's ecosystem exposes machinery that Maven hides from you, and Django names familiar things differently. This guide maps one world onto the other.

| | |
|---|---|
| **Who this is for** | A Spring Boot developer picking up Django for the first time |
| **Grounded in** | Lectra — a timetable-management monorepo |
| **Django version** | 6.1 |

---

## Contents

- [Part 00 — Two different worlds](#part-00--two-different-worlds)
- [Part 01 — Python, pip, and virtual environments](#part-01--python-pip-and-virtual-environments)
- [Part 02 — The setup, command by command](#part-02--the-setup-command-by-command)
- [Part 03 — Project vs. app: the folder structure](#part-03--project-vs-app-the-folder-structure)
- [Part 04 — settings.py: your application.properties](#part-04--settingspy-your-applicationproperties)
- [Part 05 — manage.py: the command centre](#part-05--managepy-the-command-centre)
- [Part 06 — Models and the ORM](#part-06--models-and-the-orm)
- [Part 07 — Migrations](#part-07--migrations)
- [Part 08 — URLs and views: the request lifecycle](#part-08--urls-and-views-the-request-lifecycle)
- [Part 09 — DRF: the REST layer](#part-09--drf-the-rest-layer)
- [Part 10 — The admin site](#part-10--the-admin-site)
- [Part 11 — Auth and middleware](#part-11--auth-and-middleware)
- [Part 12 — Your next moves on Lectra](#part-12--your-next-moves-on-lectra)
- [Reference — Translation cheat sheet](#reference--translation-cheat-sheet)

---

## Part 00 — Two different worlds

Before any command makes sense, you need one idea: **Java automates dependency isolation, and Python makes you do it by hand.** That single difference explains virtual environments entirely.

### How Java handles this (invisibly)

When you build a Spring Boot project, Maven reads `pom.xml`, downloads every jar into a shared cache at `~/.m2/repository`, and then builds a *classpath for that one project*. Two projects on your machine can use Spring Boot 2 and Spring Boot 3 simultaneously and never collide — because the jars sit side by side in `~/.m2`, versioned, and each project picks its own set at build time.

You never thought about this. Maven did it silently, every build.

### How Python handles this (it doesn't)

When you run `pip install django`, pip copies Django into one folder inside your Python installation called `site-packages`. There is no version in the path. There is no per-project classpath. There is **one shared pile of libraries for your entire machine**.

So if Lectra needs Django 6.1 and some other project needs Django 4.2, installing one *breaks* the other. Python has no built-in concept of "this project's dependencies."

> **KEY IDEA — the one sentence that makes venv click**
>
> A virtual environment is a **private, throwaway copy of your Python installation that lives inside your project folder** — giving that project its own `site-packages`. It is Python's manual, folder-based answer to what Maven does automatically with `~/.m2` and the classpath.

| | Spring Boot | Django / Python |
|---|---|---|
| **Isolation** | Automatic, per-build | Manual, per-folder — you create it |
| **Where libs live** | `~/.m2/repository`, shared and versioned | `venv/Lib/site-packages`, inside your project |
| **Declared in** | `pom.xml` — versions, scopes, transitive resolution | `requirements.txt` — a flat text list, no scopes |
| **You do** | Nothing. Maven figures it out | Create the venv, activate it, install into it |

### The second difference: there is no build step

Java compiles. You run `mvn clean install`, get a jar, and run the jar. Python is interpreted — the `.py` files **are** the program. There is no compile, no jar, no `target/` folder. When you change a file, Django's dev server notices and reloads in about a second.

This is why you'll never look for a Django equivalent of `mvn package`. There isn't one, and you don't need one.

---

## Part 01 — Python, pip, and virtual environments

The four tools you'll touch daily, and exactly what each one does to your machine.

| Python world | What it actually is | Spring Boot equivalent |
|---|---|---|
| `python` | The interpreter that runs your code | The JDK / `java` |
| `pip` | Downloads packages from PyPI and unpacks them into `site-packages` | Maven's dependency resolver |
| `venv` | Creates an isolated Python + `site-packages` in a folder | Per-project classpath (no direct equivalent) |
| `requirements.txt` | A plain list of package names and versions | `pom.xml` dependencies block |
| PyPI | The public package registry | Maven Central |
| `site-packages` | The folder installed libraries land in | Your resolved classpath |

### What `python -m venv venv` actually creates

It makes a folder — that's all it is. Nothing is registered globally, nothing is written to your system. Delete the folder and the environment is gone without a trace.

```
backend/venv/
├── Scripts/              ← Windows (Linux/Mac calls this bin/)
│   ├── python.exe        ← a copy/shim of your Python
│   ├── pip.exe           ← a pip that installs HERE, not globally
│   └── Activate.ps1      ← the activation script
├── Lib/site-packages/    ← where django, DRF etc. land
│   ├── django/
│   └── rest_framework/
└── pyvenv.cfg            ← points back to the base Python
```

### What "activating" actually does

This is the part that feels like magic and isn't. Activation does exactly one meaningful thing: **it prepends `venv/Scripts` to your shell's `PATH` variable.**

After that, when you type `python`, your shell finds the venv's copy first instead of the system one. When you type `pip`, same thing — so packages install into the venv's `site-packages`. The `(venv)` prefix in your prompt is just a cosmetic reminder that the PATH was changed.

> **KEY IDEA — why you must activate in every new terminal**
>
> `PATH` is a property of a single shell session. Close the terminal, open a new one, and it's back to the system default — the venv still exists on disk, but your shell has forgotten about it. This is the same reason a `set`/`export` in one terminal isn't visible in another. Nothing is broken; just activate again.

**Your project's activation command:**

```powershell
# Activate — do this once per terminal session
backend\venv\Scripts\Activate.ps1

# Your prompt becomes:  (venv) PS D:\UOM\projects\MyProjects\lectra>

# Confirm you're on the right Python
python -c "import sys; print(sys.executable)"
# → ...\lectra\backend\venv\Scripts\python.exe   ✓ correct
# → C:\Python313\python.exe                      ✗ not activated

# When you're done (or just close the terminal)
deactivate
```

> **GOTCHA — Windows execution policy**
>
> If PowerShell refuses with *"running scripts is disabled on this system"*, allow local scripts once, per user:
>
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### requirements.txt — your pom.xml, but dumber

Python has no equivalent of Maven's dependency *declaration* model. `requirements.txt` is a flat list, and the usual workflow is to generate it *from* what you've installed rather than the other way round.

**Spring — `pom.xml`, you write it:**

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- then: mvn install -->
```

**Django — `requirements.txt`, you generate it:**

```bash
# install first…
pip install django djangorestframework

# …then record what you have
pip freeze > requirements.txt

# teammate restores it with
pip install -r requirements.txt
```

> **GOTCHA — Lectra has no requirements.txt yet**
>
> Right now nobody else — including future you on another machine — can rebuild your environment. Generate one as soon as your venv is active. It's the Python equivalent of committing your `pom.xml`, and reviewers of an internship take-home will look for it.

### Never commit the venv

It's hundreds of megabytes of platform-specific binaries — the Python analogue of committing `target/` or your `~/.m2` folder. Your project already gets this right: `backend/.gitignore` contains `venv/`, so git ignores it. Good instinct.

---

## Part 02 — The setup, command by command

Every command that built the Lectra backend, what it created, and its Spring Boot counterpart.

### 1. Create the isolated environment

```powershell
python -m venv venv
```

`-m venv` means "run the built-in module named `venv`". The second `venv` is just the folder name.
**Spring equivalent:** none — Maven gives you isolation for free.

### 2. Activate it

```powershell
venv\Scripts\Activate.ps1
```

Puts the venv's `python` and `pip` at the front of your PATH. Everything after this point installs and runs inside the project.

### 3. Install the framework

```powershell
pip install django djangorestframework
```

Downloads from PyPI into `venv/Lib/site-packages`.
**Spring equivalent:** adding `spring-boot-starter-web` to `pom.xml` and letting Maven resolve it.

### 4. Scaffold the project

```powershell
django-admin startproject config .

# The trailing "." matters — it means "generate into the
# current folder" instead of creating an extra nesting level.
# That's why you have backend/config/ and backend/manage.py,
# not backend/config/config/.
```

**Spring equivalent:** Spring Initializr (`start.spring.io`). This is the moment your project skeleton is born. `config` is the name you chose for the settings package — many tutorials name it after the project, but `config` is the cleaner convention.

### 5. Create your first app

```powershell
python manage.py startapp accounts
```

Generates the `accounts/` folder with `models.py`, `views.py`, `admin.py`, and friends.
**Spring equivalent:** creating a feature package like `com.lectra.accounts` with its entity/repo/service/controller classes — except Django gives you the empty files up front.

### 6. Register the app and DRF

```python
# config/settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',   # ← you added
    'accounts',         # ← you added
]
```

Django will not see an app's models, migrations, or admin registrations until it's in this list.
**Spring equivalent:** component scanning — except Spring scans your package tree automatically, while Django requires you to say it out loud.

### 7. Generate and apply migrations

```powershell
python manage.py makemigrations   # write the migration file
python manage.py migrate          # run it against the DB
```

This is where `db.sqlite3` and your `accounts/migrations/0001_initial.py` came from.
**Spring equivalent:** Flyway — but Django *writes the migration for you* by diffing your models.

### 8. Run it

```powershell
python manage.py runserver
# → http://127.0.0.1:8000/
```

**Spring equivalent:** `mvn spring-boot:run`. Auto-reloads on file save, like Spring DevTools but built in and instant (no recompile).

---

## Part 03 — Project vs. app: the folder structure

The vocabulary trips everyone up. In Django, a "project" is the whole site and an "app" is one feature module inside it. Lectra has one project (`config`) and one app (`accounts`).

**Project — `config/`**
The **wiring**. Settings, the root URL map, the server entry points. There is exactly one per site, and it holds no business logic.
*≈ Spring:* your `@SpringBootApplication` main class + `application.properties` + `@Configuration` classes.

**App — `accounts/`**
A **feature module**: its own models, views, migrations, admin. Self-contained and, in principle, reusable across projects.
*≈ Spring:* a feature package (`com.lectra.accounts`) holding its entities, repositories, services and controllers.

Lectra will grow more apps as you work through the roadmap — likely `timetable`, `scheduling`, `notifications`. Keeping each phase in its own app is exactly the right instinct, and it's the same reasoning that makes you split Spring packages by feature rather than by layer.

### The repo, annotated

```
lectra/
├── backend/                       ← the Django project root
│   ├── venv/                      gitignored. your private libs
│   ├── manage.py                  the CLI entry point ≈ mvnw
│   ├── db.sqlite3                 dev database (a single file)
│   │
│   ├── config/                    THE PROJECT — wiring only
│   │   ├── __init__.py            marks the folder as a package
│   │   ├── settings.py            ≈ application.properties
│   │   ├── urls.py                root routing table
│   │   ├── wsgi.py                prod entry (sync) ≈ the WAR hook
│   │   └── asgi.py                prod entry (async)
│   │
│   └── accounts/                  AN APP — your first feature
│       ├── __init__.py
│       ├── models.py              ≈ @Entity classes  → has Tenant
│       ├── views.py               ≈ @RestController   → empty
│       ├── admin.py               free CRUD UI config → empty
│       ├── apps.py                app metadata (rarely touched)
│       ├── tests.py               ≈ your @SpringBootTest class
│       └── migrations/            ≈ Flyway's db/migration/
│           └── 0001_initial.py    creates the Tenant table
│
├── web/                           Next.js — empty so far
└── mobile/                        Expo — empty so far
```

### Files that have no Spring counterpart

| File | What it's for |
|---|---|
| `__init__.py` | An empty marker file that tells Python "this folder is an importable package." Java infers packages from folder structure; Python wants the file. You will almost never edit it — just don't delete it. |
| `manage.py` | A thin script that sets the `DJANGO_SETTINGS_MODULE` environment variable to `config.settings`, then hands off to Django's command runner. It exists so every command already knows which settings to load. |
| `wsgi.py` / `asgi.py` | The object a production server imports to serve your app. Gunicorn runs `config.wsgi:application`. Roughly what a servlet container looks for in your WAR — except in Spring Boot the server is embedded, so you never see this file. |
| `apps.py` | Per-app config class. You'll touch it once, much later, if you need startup hooks (signals). Ignore it for now. |

---

## Part 04 — settings.py: your application.properties

One critical difference: `application.properties` is inert key-value text. `settings.py` is **executable Python** — so it can read environment variables, branch on conditions, and compute values.

| Django setting | Spring Boot equivalent | What it does |
|---|---|---|
| `INSTALLED_APPS` | `@ComponentScan` | Which modules Django loads. Explicit, not auto-discovered. |
| `MIDDLEWARE` | Servlet `Filter` chain | Ordered request/response pipeline. Order matters enormously. |
| `DATABASES` | `spring.datasource.*` | Connection config. Yours is SQLite; Postgres later. |
| `DEBUG` | A `dev` profile | Verbose error pages + auto-reload. Must be `False` in prod. |
| `SECRET_KEY` | `jwt.secret` in properties | Signs sessions and tokens. Must never reach git. |
| `ALLOWED_HOSTS` | Host validation config | Domains allowed to serve this app in production. |
| `AUTH_USER_MODEL` | `UserDetailsService` impl | Which model represents a user. **Set this early** — see Part 07. |
| `ROOT_URLCONF` | `DispatcherServlet` mapping | Which module holds the top-level route table. |

### Because it's real code, do this

Lectra's settings currently hard-code the secret key and `DEBUG = True`. That's fine for day one and a red flag in a code review. Because `settings.py` executes, you can pull secrets from the environment — the same twelve-factor discipline you'd use with Spring profiles:

```python
# config/settings.py — the grown-up version
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Read from the environment, fall back only in dev
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-insecure-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1'
).split(',')
```

Pair that with a `.env` file (already gitignored in the repo) and the `python-decouple` or `django-environ` package. The `.gitignore` even keeps `.env.example` tracked — so commit an example file with blank values, exactly as you'd document required properties for a Spring app.

---

## Part 05 — manage.py: the command centre

Nearly everything you do in Django goes through this one script. It's your `mvnw`, your Flyway CLI, and a database shell rolled together.

| Command | What it does | Spring counterpart |
|---|---|---|
| `runserver` | Start the dev server on :8000, auto-reloading | `mvn spring-boot:run` |
| `startapp <name>` | Scaffold a new feature module | Creating a feature package by hand |
| `makemigrations` | Diff models against history, write a migration file | Hibernate schema diff → Flyway script |
| `migrate` | Apply pending migrations to the database | `flyway:migrate` |
| `showmigrations` | List migrations and which are applied | `flyway:info` |
| `createsuperuser` | Create an admin login | Seeding a user via `data.sql` |
| `shell` | Python REPL with your models loaded | No real equivalent — this is a gift |
| `dbshell` | Open a client against your database | `psql` / H2 console |
| `test` | Run the test suite | `mvn test` |
| `check` | Static sanity check of your config | Context startup validation |
| `collectstatic` | Gather static files for production serving | Packaging `src/main/resources/static` |

> **KEY IDEA — learn `manage.py shell`, it has no Spring equivalent**
>
> It drops you into a live Python session with your models importable and the database connected. You can create rows, run queries, and inspect results interactively — no test class, no restart, no HTTP call. It's the fastest way to learn the ORM.

```python
# python manage.py shell
# Try this right now against your existing Tenant model
>>> from accounts.models import Tenant

>>> Tenant.objects.create(name="Faculty of Engineering")
<Tenant: Faculty of Engineering>

>>> Tenant.objects.all()
<QuerySet [<Tenant: Faculty of Engineering>]>

>>> Tenant.objects.filter(name__startswith="Faculty").count()
1

# See the SQL Django generated — genuinely useful
>>> print(Tenant.objects.filter(name__startswith="Faculty").query)
SELECT "accounts_tenant"."id", ... WHERE "accounts_tenant"."name" LIKE Faculty%
```

---

## Part 06 — Models and the ORM

Your JPA knowledge transfers almost directly. The big simplification: **Django has no repository interfaces** — every model ships with a query manager built in.

**Spring — entity + repository (two files):**

```java
@Entity
@Table(name = "tenant")
public class Tenant {
  @Id
  @GeneratedValue(strategy = IDENTITY)
  private Long id;

  @Column(length = 100, nullable = false)
  private String name;

  @CreationTimestamp
  private Instant createdAt;
  // + getters, setters, toString
}

// and a second file:
public interface TenantRepository
    extends JpaRepository<Tenant, Long> {
  List<Tenant> findByName(String name);
}
```

**Django — one class, that's all:**

```python
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# No repository file needed.
# No getters or setters.
# id is created automatically.
# Querying is already available:
#   Tenant.objects.filter(name="X")
```

That second snippet is *literally the current `accounts/models.py`*. You've already written a working Django entity — you just may not have realised how much it gave you for free.

### Field types

| JPA | Django | Notes |
|---|---|---|
| `@Id @GeneratedValue` | *— nothing —* | Django adds an auto `id` primary key to every model |
| `String` + `@Column(length=)` | `CharField(max_length=)` | `max_length` is required |
| `@Lob String` | `TextField()` | Unbounded text |
| `Integer` / `Long` | `IntegerField()` / `BigIntegerField()` | |
| `Boolean` | `BooleanField(default=False)` | |
| `LocalDate` / `Instant` | `DateField()` / `DateTimeField()` | |
| `@CreationTimestamp` | `DateTimeField(auto_now_add=True)` | Set once on insert |
| `@UpdateTimestamp` | `DateTimeField(auto_now=True)` | Updated on every save |
| `@ManyToOne` | `ForeignKey(Model, on_delete=…)` | `on_delete` is mandatory — no silent default |
| `@OneToOne` | `OneToOneField(Model, on_delete=…)` | |
| `@ManyToMany` | `ManyToManyField(Model)` | Join table created for you |
| `@Enumerated` | `CharField(choices=…)` | Or a `TextChoices` class |
| `@Column(unique=true)` | `unique=True` | Passed as a field argument |
| `nullable = true` | `null=True, blank=True` | `null` = database, `blank` = form validation |

### Querying: `objects` is your repository

Every model gets a `Manager` at `.objects`. Calls on it return a **QuerySet**, which is *lazy* — it builds SQL but doesn't execute until you iterate, index, or count it. You can chain filters freely without touching the database.

| Goal | Spring Data | Django |
|---|---|---|
| All rows | `repo.findAll()` | `Tenant.objects.all()` |
| By id | `repo.findById(1)` | `Tenant.objects.get(id=1)` |
| Filtered list | `repo.findByName("X")` | `Tenant.objects.filter(name="X")` |
| Contains | `findByNameContaining("X")` | `filter(name__icontains="X")` |
| Greater than | `findByAgeGreaterThan(18)` | `filter(age__gt=18)` |
| Negation | custom query | `exclude(name="X")` |
| Save | `repo.save(t)` | `t.save()` or `objects.create(…)` |
| Delete | `repo.delete(t)` | `t.delete()` |
| Count | `repo.count()` | `Tenant.objects.count()` |
| Sort | `Sort.by("name")` | `order_by('name')` / `'-name'` |
| Paging | `Pageable` | `qs[0:20]` (slicing becomes LIMIT) |
| Fix N+1 | `JOIN FETCH` / `@EntityGraph` | `select_related()` / `prefetch_related()` |

Those double-underscore suffixes (`__icontains`, `__gt`, `__startswith`) are called **lookups**, and they're Django's answer to Spring Data's method-name derivation. Same idea — expressive queries without writing SQL — just expressed as arguments instead of method names.

> **KEY IDEA — where does the service layer go?**
>
> Django has no `@Service` annotation and no DI container, so there's no enforced layering. For a project the size of Lectra, put real business logic — clash detection, timetable generation — in plain Python modules like `scheduling/services.py` and import them from your views. Keep views thin, exactly as you'd keep controllers thin. The discipline is yours to impose; the framework won't do it for you.

---

## Part 07 — Migrations

Django's migration system sits exactly between the two options you know from Spring — and it's better than either.

**Spring's two options:**

- **`ddl-auto: update`** — Hibernate mutates the schema at boot. Convenient in dev, unusable in production, no history.
- **Flyway / Liquibase** — versioned, reviewable, production-safe. But *you hand-write every SQL script*.

**Django's single answer:**

**Migrations** — versioned and reviewable like Flyway, *and* generated for you like `ddl-auto`. `makemigrations` diffs your models against the applied history and writes a numbered Python file. `migrate` runs it. You get both safety and convenience.

### The rhythm you'll repeat forever

```powershell
# 1. edit accounts/models.py — add a field, add a model

python manage.py makemigrations   # 2. Django writes 0002_xxx.py
python manage.py migrate          # 3. applied to the database

python manage.py showmigrations   # what's applied? ≈ flyway:info
python manage.py sqlmigrate accounts 0001   # preview the raw SQL
```

**Migration files are source code.** Commit them. They're the schema's version history, and a teammate cloning Lectra gets the exact same database by running `migrate` — the same contract as committing your Flyway scripts.

> **GOTCHA — this one matters for Lectra, right now**
>
> Django lets you swap the built-in `User` model for your own — you'll need to, since Lectra requires a `role` (Admin / HOD / Lecturer / Student) and a `tenant` foreign key. **But you can only do it cleanly before the first `migrate`.**
>
> The database has already applied the `auth` migrations with the default `User`. Changing `AUTH_USER_MODEL` now means every foreign key pointing at the old user table breaks. The official fix in a live system is genuinely painful.
>
> **The good news:** the database is a throwaway SQLite file with no real data. Fixing it costs about two minutes today, and gets exponentially worse with every model you add. Do it before anything else — see Part 12.

---

## Part 08 — URLs and views: the request lifecycle

Spring routes with annotations scattered across controller classes. Django routes with an explicit table in a file. This is the biggest mental adjustment in the whole framework.

**Spring Boot lifecycle:**
Request → embedded Tomcat → `Filter` chain → `DispatcherServlet` → handler mapping scans `@RequestMapping` annotations → your controller method → Jackson serialises the return value → response

**Django lifecycle:**
Request → WSGI server → `MIDDLEWARE` chain → URL resolver reads `ROOT_URLCONF` and matches patterns top to bottom → your view function → you return a `Response` → back out through middleware

> **KEY IDEA — routing lives in files, not annotations**
>
> There is no `@GetMapping` in Django. Every route is a line in a `urls.py` list, evaluated top to bottom, first match wins. The upside is that you can read every route your app serves by opening two or three files — no hunting through controller classes.

**Spring — route on the method:**

```java
@RestController
@RequestMapping("/api/tenants")
public class TenantController {

  @GetMapping
  public List<Tenant> list() {
    return repo.findAll();
  }

  @GetMapping("/{id}")
  public Tenant one(@PathVariable Long id) {
    return repo.findById(id).orElseThrow();
  }
}
```

**Django — route in a table:**

```python
# accounts/views.py
def tenant_list(request):
    ...

def tenant_detail(request, pk):
    ...


# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.tenant_list),
    path('<int:pk>/', views.tenant_detail),
]
```

### Splitting routes across apps

`config/urls.py` is the root table. Rather than listing every route there, each app keeps its own `urls.py` and the root `include()`s it — the same instinct as one `@RequestMapping` prefix per controller.

```python
# config/urls.py — where you're heading
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    # path('api/timetable/', include('timetable.urls')),   ← later
]
```

A request to `/api/accounts/3/` matches the prefix, and Django passes the leftover `3/` down to `accounts/urls.py` to resolve.

---

## Part 09 — DRF: the REST layer

Django alone is HTML-first: views return rendered pages. Django REST Framework adds everything you need to serve JSON APIs, and it's what makes Django feel like Spring Boot again.

| DRF concept | Spring equivalent | What it does |
|---|---|---|
| `Serializer` | DTO + Jackson + Bean Validation | Converts models ⇄ JSON *and* validates incoming data — all three jobs in one class |
| `ModelSerializer` | A DTO auto-derived from an entity | Reads your model's fields and builds the mapping for you |
| `APIView` | `@RestController` class | You write `get()`, `post()` methods by hand |
| `ViewSet` | A full CRUD `@RestController` | All five CRUD actions from one class |
| `Router` | Spring Data REST | Generates the URL patterns for a ViewSet |
| `permission_classes` | `@PreAuthorize` | Who may call this endpoint |
| `Response` | `ResponseEntity` | Body plus status code |

### A complete CRUD API for Tenant

Three small files and you have list, create, retrieve, update and delete — with pagination and a browsable HTML test UI included.

```python
# accounts/serializers.py — the DTO
from rest_framework import serializers
from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']
```

```python
# accounts/views.py — the controller
from rest_framework import viewsets, permissions
from .models import Tenant
from .serializers import TenantSerializer


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
```

```python
# accounts/urls.py — the routes
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet)

urlpatterns = router.urls
```

Those three files generate the full endpoint set:

| Method | Path | Action |
|---|---|---|
| `GET` | `/api/accounts/tenants/` | List, paginated |
| `POST` | `/api/accounts/tenants/` | Create |
| `GET` | `/api/accounts/tenants/3/` | Retrieve one |
| `PUT` / `PATCH` | `/api/accounts/tenants/3/` | Full / partial update |
| `DELETE` | `/api/accounts/tenants/3/` | Delete |

> **KEY IDEA — compare the line count**
>
> The Spring version of that is an entity, a repository interface, a DTO, a mapper, a service, and a controller with five methods. DRF does it in roughly twenty lines because `ModelViewSet` assumes the standard CRUD shape and lets you override only what differs. When you need custom behaviour, you drop down to `APIView` and write the methods yourself — same as a hand-written controller.

---

## Part 10 — The admin site

Django's single most distinctive feature, and one with no Spring equivalent at all: a complete, production-usable back-office UI generated from your models.

In Spring, an internal CRUD screen for staff means building it — controllers, Thymeleaf templates or a React app, forms, validation, tables. Days of work. Django reads your models and generates it.

```python
# accounts/admin.py
from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display  = ['name', 'created_at']
    search_fields = ['name']
    list_filter   = ['created_at']
```

```powershell
python manage.py createsuperuser
python manage.py runserver
# → http://127.0.0.1:8000/admin/
```

You now have searchable, filterable, paginated CRUD with permissions and an audit log of changes. For Lectra this is genuinely strategic: your admins can manage lecturers, halls, modules and batches through the admin site from day one, while you spend your build time on the parts that actually differentiate the product — the clash-detection engine and the timetable generator.

> **GOTCHA — `accounts/admin.py` is still empty**
>
> It has the boilerplate comment and nothing else, so `Tenant` doesn't appear in the admin yet. Registering it is three lines and immediately gives you a UI to create test data with.

---

## Part 11 — Auth and middleware

Django ships auth in the box. Where Spring Security is a large configurable framework you assemble, Django gives you a working default and lets you extend it.

| Spring Security | Django | Notes |
|---|---|---|
| `UserDetails` | `django.contrib.auth`'s `User` model | A real database model, not an interface |
| `UserDetailsService` | Authentication backends | Sensible default; swap only if needed |
| `PasswordEncoder` | Built in (PBKDF2 by default) | Hashing is automatic on `set_password()` |
| `SecurityFilterChain` | `MIDDLEWARE` list | Ordered, in `settings.py` |
| `@PreAuthorize("hasRole(…)")` | `permission_classes = [...]` | Set per view or globally in DRF config |
| JWT filter + provider | `djangorestframework-simplejwt` | A package you install — the standard choice |
| Servlet `Filter` | Middleware | Same concept: wraps request in, response out |
| `HandlerInterceptor` | Middleware | Django has one mechanism for both |

### Middleware is your filter chain

A Django middleware is a callable that receives the request, optionally does something, calls the next one, and gets the response back on the way out. Identical mental model to a servlet filter — the ordering in `MIDDLEWARE` is the chain order, outermost first.

This is where Lectra's **tenant isolation** will live: middleware that reads the authenticated user, resolves their tenant, and stashes it on the request so every downstream query can scope to it. It's the same place you'd put a Spring filter populating a `ThreadLocal` tenant context.

### Adding JWT to Lectra

```python
# pip install djangorestframework-simplejwt

# config/settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# config/urls.py — login and refresh endpoints, for free
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
)

urlpatterns += [
    path('api/token/',         TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]
```

That gives you a working `POST /api/token/` that takes credentials and returns an access and refresh token pair — the equivalent of hand-writing an authentication controller, a JWT provider and a filter in Spring.

---

## Part 12 — Your next moves on Lectra

### What exists today

- A Django project (`config`) with SQLite, running and migrated.
- One app, `accounts`, holding a single `Tenant` model.
- DRF installed and registered — but no serializers, views or routes yet.
- An empty admin, an empty `views.py`, and only `/admin/` routed.
- `web/` and `mobile/` are empty directories.

That's a solid Phase 1 foundation. The next real step is Phase 2 — and it starts with a fix that gets more expensive every day you delay.

### Do this first: the custom user model

Lectra needs users with a `role` and a `tenant`. Swapping Django's default user is trivial *now* and painful later, because every future foreign key to your user table cements the old one in place. The database is a disposable SQLite file with no data, so the reset is free today.

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN    = 'ADMIN',    'Admin'
        HOD      = 'HOD',      'HOD / Coordinator'
        LECTURER = 'LECTURER', 'Lecturer'
        STUDENT  = 'STUDENT',  'Student'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users',
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
```

```python
# config/settings.py — add this line
AUTH_USER_MODEL = 'accounts.User'
```

```powershell
# Reset the throwaway dev database.
# Safe: no real data exists yet.
# Delete db.sqlite3 and accounts/migrations/0001_initial.py,
# keeping accounts/migrations/__init__.py.

python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser
```

> **GOTCHA — check before you delete**
>
> Confirm you have nothing in that database you care about, and keep `accounts/migrations/__init__.py` — removing it stops Django recognising the folder as a migrations package.

### Then, in order

1. Register `Tenant` and `User` in `accounts/admin.py` so you have a UI for test data.
2. Generate `requirements.txt` with `pip freeze`, and commit it.
3. Move `SECRET_KEY` and `DEBUG` into environment variables.
4. Add `simplejwt`, wire up `/api/token/`, and confirm login returns a token.
5. Write `TenantSerializer` + `TenantViewSet` + `accounts/urls.py` — your first real endpoint.
6. Add tenant-scoping so a user only ever sees their own tenant's rows.
7. Only then start Phase 3: the `timetable` app with lecturers, modules, halls and batches.

> **KEY IDEA — a note on the internship angle**
>
> What reviewers look for isn't framework trivia — it's whether you understand *why* things are arranged the way they are. Being able to say "Django migrations are versioned like Flyway but generated from a model diff, so you get review safety without hand-writing SQL" demonstrates more than memorising commands ever will. The comparisons in this guide are the interview answers.

---

## Reference — Translation cheat sheet

### Concept by concept

| Spring Boot | Django | Note |
|---|---|---|
| JDK | Python interpreter | |
| Maven / Gradle | pip | Installer only — no build lifecycle |
| Maven Central | PyPI | |
| `pom.xml` | `requirements.txt` | Flat list, no scopes or transitives |
| `~/.m2` + classpath | `venv/` | Manual, per-project folder |
| `target/`, the jar | *— nothing —* | Interpreted; no build step |
| Spring Initializr | `django-admin startproject` | |
| Feature package | An app (`startapp`) | Must be listed in `INSTALLED_APPS` |
| `@SpringBootApplication` | `config/` + `manage.py` | |
| `application.properties` | `settings.py` | Executable Python, not inert text |
| `@ComponentScan` | `INSTALLED_APPS` | Explicit, not automatic |
| `mvn spring-boot:run` | `manage.py runserver` | |
| Embedded Tomcat | runserver (dev) / Gunicorn (prod) | Not embedded — a separate process |
| `@Entity` | `models.Model` | |
| `JpaRepository` | `Model.objects` | Built in — no interface to declare |
| JPQL / Criteria | QuerySets + lookups | Lazy and chainable |
| Flyway / Liquibase | Migrations | Versioned *and* auto-generated |
| `@RestController` | DRF `APIView` / `ViewSet` | |
| `@RequestMapping` | `urls.py` patterns | A table in a file, not an annotation |
| DTO + Jackson | DRF `Serializer` | Also does validation |
| Bean Validation | Serializer validation | Same class as the mapping |
| `ResponseEntity` | `Response` | |
| Spring Security | `django.contrib.auth` + DRF perms | |
| Servlet `Filter` | Middleware | |
| `@Service` / DI container | Plain modules and imports | No DI — you impose the layering |
| Springdoc / Swagger UI | `drf-spectacular` | |
| JUnit + `@SpringBootTest` | pytest / `manage.py test` | |
| *— none —* | The admin site | Free CRUD back-office |
| *— none —* | `manage.py shell` | Live REPL against your models |

### The commands you'll actually type

```powershell
# ── Every new terminal ────────────────────────────────
backend\venv\Scripts\Activate.ps1

# ── Running ───────────────────────────────────────────
python manage.py runserver              # :8000
python manage.py runserver 8080         # another port

# ── After editing models.py ───────────────────────────
python manage.py makemigrations
python manage.py migrate

# ── Inspecting ────────────────────────────────────────
python manage.py showmigrations
python manage.py sqlmigrate accounts 0001
python manage.py shell
python manage.py check

# ── Building out ──────────────────────────────────────
python manage.py startapp timetable
python manage.py createsuperuser
python manage.py test

# ── Dependencies ──────────────────────────────────────
pip install <package>
pip freeze > requirements.txt
pip install -r requirements.txt
pip list

# ── Done ──────────────────────────────────────────────
deactivate
```

> **If something breaks, check these three things first**
>
> 1. **Is the venv active?** No `(venv)` in the prompt means `ModuleNotFoundError: No module named 'django'`.
> 2. **Are you in `backend/`?** `manage.py` only works from the folder it lives in.
> 3. **Did you run `migrate` after changing a model?** `no such table` and `no such column` almost always mean a pending migration.

---

*Written against Lectra at commit `6204ba9` · Django 6.1 · Read it once end to end, then keep the cheat sheet open while you build.*
