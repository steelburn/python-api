ARG pythonver=3.10
ARG distro=bullseye
FROM python:${pythonver}-${distro} as uvicorn-fastapi

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && \
    apt upgrade -y && \
    apt install -y wget && \
    wget https://downloads.mariadb.com/MariaDB/mariadb_repo_setup && \
    chmod +x mariadb_repo_setup && \
    ./mariadb_repo_setup && \
    apt update && \
    apt install -y libmariadb3 libmariadb-dev && \
    pip install \
        email-validator \
        fastapi \
        mariadb \
        pydantic \
        python-dateutil \
        python-dotenv \
        python-multipart \
        pyzmq \
        redis \
        requests \
        typing_extensions \
        urllib3 \
        uvicorn 

WORKDIR /app
COPY . /app
ENTRYPOINT [ "uvicorn", "--reload", "--host", "0.0.0.0", "api:app" ]
EXPOSE 8000