# FROM python:3.10-slim

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     libgl1 \
#     libglib2.0-0 \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# RUN mkdir -p /tmp/uploads /tmp/id_photos /tmp/reports

# EXPOSE 8000

# CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.10-slim

# Limit multi-threading for ML and math libraries to stay within Render's 512MB RAM tier
ENV OMP_NUM_THREADS=1 \
    TF_NUM_INTRAOP_THREADS=1 \
    TF_NUM_INTEROP_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TF_CPP_MIN_LOG_LEVEL=3 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1


RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/uploads /tmp/id_photos /tmp/reports

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]