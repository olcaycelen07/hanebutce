# Canliya Alma Adimlari

Bu dokuman, projeyi sirayla PostgreSQL, bulut dagitimi, domain ve canli kullanim seviyesine tasimak icindir.

## 1. PostgreSQL hazirligi

- `docs/schema_postgres.sql` PostgreSQL tablo yapisini icerir
- production veritabani olarak Render PostgreSQL, Neon veya Supabase sec
- veritabani baglanti bilgisini `DATABASE_URL` olarak sakla

## 2. Uygulamayi buluta koyma

En kolay baslangic:
- kodu GitHub reposuna koy
- Render uzerinde yeni bir web service ac
- `webapp/render.yaml` veya `webapp/Procfile` kullan
- environment variables gir

Girilmesi gereken temel degiskenler:
- `SECRET_KEY`
- `COOKIE_SECURE=true`
- `ENABLE_HSTS=true`
- `FLASK_DEBUG=false`
- `DATABASE_URL`
- SMTP ayarlari

## 3. Domain baglama

- ornek domain: `hanebutce.com`
- domain saglayicisinda `A` veya `CNAME` kaydi olustur
- hosting servisinde custom domain ekle
- SSL sertifikasi aktif et
- `www` ve ana domaini ayni uygulamaya yonlendir

## 4. Herkesin kullanmasi

Canliya alindiktan sonra:
- kullanicilar domaine gider
- kayit olur
- hane olusturur
- davet linki veya e-posta ile aile uyelerini ekler
- veriler merkezi PostgreSQL veritabaninda tutulur

## 5. Operasyon listesi

Canliya cikmadan once bunlari tamamla:
- hata loglama
- backup politikasi
- sifre sifirlama akisi
- email verification
- rate limiting
- gizlilik sozlesmesi ve kullanim kosullari
