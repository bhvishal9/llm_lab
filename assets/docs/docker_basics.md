# Docker Basics

Docker is a platform for building and running containers. A container is a lightweight, isolated environment that packages an application with its dependencies.

Key concepts:
- Image: a read-only template with instructions for creating a container.
- Container: a running instance of an image.
- Dockerfile: a text file with instructions to build an image.

Common commands:
- `docker build -t my-app .`
- `docker run -p 8080:80 my-app`
- `docker ps` to list running containers.