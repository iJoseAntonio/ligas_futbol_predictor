# Usar la imagen oficial de AWS Lambda para Python 3.12 (Amazon Linux 2023)
FROM public.ecr.aws/lambda/python:3.12

# Copiar el archivo de requerimientos
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Instalar dependencias de compilación y Python
RUN dnf install -y gcc gcc-c++ make && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código (incluyendo carpetas data y modelos)
COPY . ${LAMBDA_TASK_ROOT}

# Indicar cuál es la función de inicio (el traductor Mangum)
CMD ["main.handler"]
