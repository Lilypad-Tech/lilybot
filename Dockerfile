FROM python:3.9-slim

WORKDIR /app

COPY . .

# Install the requirements
RUN pip3 install -r requirements.txt

# Adjust ports if needed
EXPOSE 6060 
CMD ["python3", "lilybot.py" ]