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

### Run
```sh
python main.py
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

```sh
docker run -p 9874:9874 --name "art-you-like" --rm -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```

Run as daemon

```sh
docker run -p 9874:9874 --name "art-you-like" -d -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```

Update daemon

```sh
docker stop art-you-like && docker rm art-you-like
docker run -p 9874:9874 --name "art-you-like" -d -v ${PWD}\store.db:/app/store.db -v ${PWD}\static\images:/app/static/images art-you-like
```
