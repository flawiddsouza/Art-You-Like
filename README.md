### Environment File

The app requires a `SECRET_KEY` in a `.env` file at the project root (never committed):

```sh
# Generate a random key and write it to .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env
```

A `.env.example` is included as a template.

### Virtual Environment Setup (PowerShell)
```sh
# Create virtual env
python -m venv venv

# Activate virtual env
venv\Scripts\Activate.ps1
```

### Package Installation
```sh
pip install -r requirements.txt
```

### Database Setup

**Fresh install:** `store.db` is created automatically on first run with the correct schema.

**Existing database (migrating from an older version):** Back up first, then run the one-time migration:
```sh
cp store.db store.db.bak
python migrate.py
```
The migration converts the old `image_url` comma-string column to a proper `art_image` table. It is idempotent — safe to run more than once.

### Run
```sh
python main.py
```

### Running Tests

Install dev dependencies, then run pytest:
```sh
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Running in pm2
```sh
pm2 start --name "Art You Like" --interpreter=venv\Scripts\pythonw.exe main.py
```

Or through pm2.yml
```yaml
- name: Art You Like
  script: main.py
  cwd: ./Art You Like
  exec_interpreter: ./venv/Scripts/pythonw.exe
```
```sh
pm2 start pm2.yml
```

### Docker (PowerShell)

Build Image

```sh
docker build -t art-you-like .
```

Run

`.env` is not copied into the image, so pass `SECRET_KEY` explicitly:

```sh
docker run -p 9874:9874 --name "art-you-like" --rm -e SECRET_KEY=your_key_here -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```

Run as daemon

```sh
docker run -p 9874:9874 --name "art-you-like" -d -e SECRET_KEY=your_key_here -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```

Update daemon

```sh
docker stop art-you-like && docker rm art-you-like
docker run -p 9874:9874 --name "art-you-like" -d -e SECRET_KEY=your_key_here -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```
