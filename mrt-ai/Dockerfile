FROM python:3.11-slim
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY mrt_ai ./mrt_ai
COPY data/normalized ./data/normalized
COPY data/fixtures ./data/fixtures
COPY data/*.csv ./data/
EXPOSE 8010
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010"]
