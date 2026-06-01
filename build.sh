#!/usr/bin/env bash
# Render build script: React production build + Django static files + migrations
set -o errexit

pip install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..

mkdir -p backend/templates backend/frontend_dist/assets
cp frontend/dist/index.html backend/templates/index.html
cp -r frontend/dist/assets/. backend/frontend_dist/assets/

cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
