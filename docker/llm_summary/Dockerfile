FROM python:3.11-slim
WORKDIR /opt/llm_summary
COPY llm_summary.py ./
RUN pip install --no-cache-dir flask requests geoip2
EXPOSE 8000
CMD ["python", "llm_summary.py"]
