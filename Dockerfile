FROM python:3-alpine

# Use a specific working directory
WORKDIR /opt/kamstrup

# Copy and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the *contents* of the src directory into the container working dir
# (important: COPY ./src /opt/kamstrup would create /opt/kamstrup/src/...)
COPY ./src /opt/kamstrup

# Ensure logs directory exists
RUN mkdir -p /opt/kamstrup/logs

# Make sure Python can import the package (working dir is on sys.path,
# but adding PYTHONPATH makes the intent explicit)
# ENV PYTHONPATH="/opt/kamstrup:${PYTHONPATH}"

# WORKDIR /opt/kamstrup

# Start the daemon
CMD [ "python3", "-m", "kamstrup2mqtt" ]
