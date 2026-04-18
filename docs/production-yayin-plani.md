# Production Yayin Plani

Bu proje su anda calisan bir prototiptir. Gercek yayina cikmak icin asagidaki sira izlenmelidir.

## 1. Uygulama guvenligi

- `SECRET_KEY` ortam degiskeni ile ayri tutulmali
- production ortaminda `COOKIE_SECURE=true` olmali
- HTTPS zorunlu olmali
- hata ayiklama modu kapatilmali
- form korumasi ve rol kontrolleri aktif olmali

## 2. Veritabani gecisi

Su an veri `sqlite` uzerinde tutuluyor. Ticari kullanim icin hedef:

- veritabani: PostgreSQL
- yedekleme: gunluk otomatik backup
- staging ve production ayri veritabani
- migration sistemi

## 3. Hosting yapisi

Onerilen ilk production kurulum:

- uygulama: Render, Railway veya VPS
- reverse proxy: Nginx
- uygulama sunucusu: Gunicorn
- veritabani: managed PostgreSQL
- e-posta: SMTP veya transactional mail servisi

## 4. Gecis adimlari

1. PostgreSQL surucusunu projeye ekle
2. sorgu katmanini PostgreSQL uyumlu hale getir
3. migration dosyalari hazirla
4. staging ortami kur
5. production ortami kur
6. alan adi ve SSL bagla
7. izleme ve loglama ekle
