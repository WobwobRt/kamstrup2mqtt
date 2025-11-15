FROM python:3-alpine
WORKDIR /opt/kamstrup

# Copy and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the contents of the src directory into the container working dir
COPY ./src /opt/kamstrup

# Ensure logs directory exists
RUN mkdir -p /opt/kamstrup/logs

# Start the daemon
CMD [ "python3", "-m", "kamstrup2mqtt" ]
