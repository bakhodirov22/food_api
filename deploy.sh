#!/bin/bash
set -e

echo "Deploy boshlandi..."

cd /var/www/fastapi_blog

git pull origin main

source venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart fastapi_blog

echo "Deploy tugadi!"