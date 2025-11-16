FROM python:3.11-slim
WORKDIR /app

# Copy dependency list and install dependencies first.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files (including app.py and test_app.py) 
# from the build context into the container's WORKDIR (/app).
COPY . .

# Run the application
CMD ["python", "app.py"]
