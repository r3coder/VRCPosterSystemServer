
docker run -it --user "$(id -u):$(id -g)" --workdir /app -v "$(pwd)":/app vrcp:latest python3 src/update.py
docker run -it --user "$(id -u):$(id -g)" --workdir /app -v "$(pwd)":/app vrcp:latest python3 src/upload.py