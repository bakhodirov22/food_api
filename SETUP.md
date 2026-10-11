# Serverni sozlash (Ubuntu 24.04, AWS EC2)

## 1. Paketlar
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx git build-essential libpq-dev python3-dev
```

## 2. Baza
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE food_db;
CREATE USER food_user WITH PASSWORD 'KUCHLI_PAROL';
ALTER DATABASE food_db OWNER TO food_user;
\q
```

## 3. Loyihani joylash
```bash
sudo mkdir -p /var/www && sudo chown ubuntu:ubuntu /var/www
cd /var/www
git clone https://github.com/bakhodirov22/food_api.git fastapi_blog
cd fastapi_blog
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. .env
```bash
cp .env.example .env
nano .env
```
`PAROL` ni bazadagi parolga, `SECRET_KEY` ni tasodifiy qiymatga almashtiring:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 5. Gunicorn servisi
```bash
sudo cp deploy/fastapi_blog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fastapi_blog
sudo systemctl status fastapi_blog
```

## 6. Nginx
```bash
sudo cp deploy/nginx_fastapi_blog.conf /etc/nginx/sites-available/fastapi_blog
sudo ln -s /etc/nginx/sites-available/fastapi_blog /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 7. deploy.sh uchun sudo ruxsati
```bash
sudo visudo
```
Oxiriga qo'shing:
```
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart fastapi_blog
```

## 8. GitHub Secrets
Repo -> Settings -> Secrets and variables -> Actions:
- `EC2_HOST`: serverning Public IP'si
- `EC2_SSH_KEY`: `.pem` fayl ichidagi butun matn

## 9. Tekshirish
`http://SERVER_IP/docs` ochiladi. Postman: `POST http://SERVER_IP/auth/login`