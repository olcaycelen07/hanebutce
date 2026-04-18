# Render Kurulum Rehberi

Bu rehber, HaneButce uygulamasini `Render + Render PostgreSQL` ile canliya almak icindir.

## Hazir olanlar

Projede bunlar hazir:
- `webapp/render.yaml`
- `webapp/Procfile`
- `webapp/wsgi.py`
- `docs/schema_postgres.sql`
- `webapp/.env.example`

## Yapacagimiz kurulum

1. Kodu GitHub reposuna yukle
2. Render uzerinde PostgreSQL olustur
3. Render uzerinde Web Service olustur
4. Ortam degiskenlerini gir
5. Domain bagla

## 1. GitHub reposu

Projeyi bir GitHub reposuna koy:

- repo adi onerisi: `hanebutce`
- kok klasor: `aile-butce-projesi`

## 2. Render PostgreSQL

Render panelinde:

1. `New`
2. `PostgreSQL`
3. veritabani adi: `hanebutce-db`
4. olustur

Olustuktan sonra su bilgi gerekir:
- `Internal Database URL` veya `External Database URL`

Bu deger `DATABASE_URL` olarak kullanilacak.

## 3. Render Web Service

Render panelinde:

1. `New`
2. `Web Service`
3. GitHub reposunu bagla
4. root directory olarak `webapp` sec

## 4. Build ve start

Render icin:

- Build Command:
  `pip install -r requirements.txt`

- Start Command:
  `gunicorn --bind 0.0.0.0:$PORT wsgi:application`

## 5. Environment Variables

Asagidakileri gir:

- `SECRET_KEY`
- `COOKIE_SECURE=true`
- `ENABLE_HSTS=true`
- `FLASK_DEBUG=false`
- `DATABASE_URL`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`

## 6. Domain

Render uzerinde:

1. uygulamaya gir
2. `Settings`
3. `Custom Domains`
4. domain ekle

Sonra domain saglayicinda Render'in verdigi DNS kaydini ekle.

## 7. Ilk canli kontrol

Canliya ciktiktan sonra sirayla kontrol et:

1. kayit ol
2. giris yap
3. hane olustur
4. gelir ekle
5. odeme ekle
6. davet olustur
7. davet linki aciliyor mu kontrol et

## 8. Yereldeki gercek veriyi PostgreSQL'e tasima

Eger yerelde `webapp/data.db` icinde kayitli kullanici veya finans verileri varsa bunlari Render PostgreSQL'e tasiyabilirsin.

1. kendi bilgisayarinda `DATABASE_URL` degiskenini Render PostgreSQL baglantisi ile tanimla
2. `webapp` klasorune gir
3. `python migrate_sqlite_to_postgres.py` komutunu calistir

Bu script:
- PostgreSQL tablolarini hazirlar
- SQLite icindeki verileri sirasiyla aktarir
- `id` serilerini mevcut veriye gore senkronize eder

## Not

Render uzerinde veritabani ve uygulama sunucusu calisacagi icin senin bilgisayarinin acik olmasi gerekmez.
