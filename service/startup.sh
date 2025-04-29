# Reload systemd to pick up new service files
sudo systemctl daemon-reload

# Enable all services to start at boot
sudo systemctl enable airflow-webserver.service
sudo systemctl enable airflow-scheduler.service
sudo systemctl enable airflow-triggerer.service
# sudo systemctl enable airflow-worker.service  # If using Celery

# Start all services
sudo systemctl start airflow-webserver.service
sudo systemctl start airflow-scheduler.service
sudo systemctl start airflow-triggerer.service
# sudo systemctl start airflow-worker.service  # If using Celery

# Check status of all services
sudo systemctl status airflow-*.service

