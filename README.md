# Aile Butce Projesi

Bu klasor, aile odakli gelir-gider ve odeme takip uygulamasinin sifirdan kurulan ilk temelini icerir.

Ilk hedefimiz:
- aile uyelerinin ayni hane altinda calisabilmesi
- gelir, gider ve odemelerin takip edilmesi
- e-posta ile uyelik ve giris altyapisina uygun bir yapi kurulmasi
- ileride abonelikli ticari urune donusebilecek bir temel hazirlanmasi

## Klasorler

- `docs/`: urun, veri modeli ve yol haritasi dokumanlari
- `app/`: bagimliliksiz calisan demo arayuz

## Demo nasil acilir

`app/index.html` dosyasini tarayicida acman yeterli.

Demo ozellikleri:
- ornek giris ekrani
- aile uyeleri listesi
- gelir ve gider kayitlari
- odeme takvimi ve durum gostergeleri
- localStorage ile tarayicida gecici veri saklama

## Gercek web uygulamasi

`webapp/` klasoru altinda Flask ile hazirlanan ilk calisan surum bulunur.

Ozellikler:
- mail ile kayit olma
- sifre ile giris yapma
- ilk giriste hane olusturma
- aile uyeleri icin davet linki olusturma
- davet linki ile aileye katilim
- SMTP ayarlari ile davet e-postasi gonderebilme
- CSRF korumasi
- rol bazli yetki kontrolleri
- guclu sifre kurallari
- guvenli oturum cookie ayarlari
- gelir / gider kaydi ekleme
- odeme ekleme ve odendi olarak isaretleme
- hazir veya ozel kategori kullanma
- aylik tekrar eden odeme olusturma
- kategori bazli gider ozeti gorme
- aya gore filtrelenmis rapor ve finans ozeti
- sqlite veritabani ile veri saklama

Calistirmak icin:

1. `cd "C:\Users\acer\Documents\New project\aile-butce-projesi\webapp"`
2. `python run.py`
3. tarayicida `http://127.0.0.1:5000` adresini ac

Veritabani dosyasi ilk calistirmada otomatik olarak `webapp/data.db` icinde olusur.

### Davet e-postasi ayarlari

Gercek e-posta gondermek icin uygulamayi calistirmadan once su ortam degiskenlerini tanimlayabilirsin:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`

Ornek PowerShell:

```powershell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="ornek@mail.com"
$env:SMTP_PASSWORD="uygulama-sifresi"
$env:SMTP_FROM_EMAIL="ornek@mail.com"
$env:SMTP_FROM_NAME="HaneButce"
$env:SMTP_USE_TLS="true"
python run.py
```

SMTP ayarlari yoksa veya gonderim basarisiz olursa davet linkleri `webapp/sent_invites.log` dosyasina yazilir.

### Guvenlik ayarlari

`webapp/.env.example` dosyasini referans alarak production ayarlarini ortam degiskenleriyle vermelisin.

Onerilenler:
- `SECRET_KEY`
- `COOKIE_SECURE=true`
- `ENABLE_HSTS=true`

Production ve olceklenme dokumanlari:
- `docs/production-yayin-plani.md`
- `docs/veri-guvenligi-ve-izolasyon.md`
- `docs/olceklenme-yol-haritasi.md`
- `docs/canliya-alma-adimlari.md`
- `docs/render-kurulum-rehberi.md`
- `docs/schema_postgres.sql`

### PostgreSQL ve gercek veri gecisi

Uygulama artik iki farkli modda calisabilir:
- `DATABASE_URL` tanimli degilse yerelde `sqlite`
- `DATABASE_URL` tanimliysa production icin `PostgreSQL`

Yereldeki mevcut veriyi PostgreSQL'e tasimak icin:

1. `DATABASE_URL` ortam degiskenini PostgreSQL baglantinla tanimla
2. `cd "C:\Users\acer\Documents\New project\aile-butce-projesi\webapp"`
3. `python migrate_sqlite_to_postgres.py`

Bu script mevcut `data.db` icindeki kayitlari PostgreSQL'e aktarir ve tablo kimliklerini senkronize eder.

### Bulut ve PostgreSQL hazirligi

Bu proje artik deployment iskeletine sahiptir:
- `webapp/wsgi.py`
- `webapp/Procfile`
- `webapp/render.yaml`

Not:
- su an uygulama yerelde `sqlite` ile calismaya devam eder
- production hedefi icin `PostgreSQL` semasi `docs/schema_postgres.sql` icine eklendi
- `requirements.txt` icine `gunicorn` ve `psycopg[binary]` eklendi

## Onerilen teknik yon

Bu demo, urunu somutlastirmak icin bagimsiz yapildi. Ticari urune gecis icin onerim:
- frontend: Next.js
- backend: Node.js + NestJS veya Next.js API
- veritabani: PostgreSQL
- kimlik dogrulama: email tabanli auth
- odeme sistemi: Stripe / iyzico entegrasyonu
- bildirim: e-posta ve sonra push bildirim

Detaylar `docs/` altinda yer aliyor.
