# Veri Guvenligi ve Izolasyon

## Mevcut model

Bu uygulama tek veritabani icinde cok kullanicili calisir.

Ayristirma anahtarlari:
- `users.id`
- `households.id`
- `household_members.household_id`
- `transactions.household_id`
- `bills.household_id`
- `invitations.household_id`

Bu sayede her ailenin verisi ayni fiziksel veritabaninda olsa bile mantiksal olarak ayrilir.

## Guvenlik kurallari

- her sorgu aktif `household_id` ile filtrelenmeli
- kullanici sadece uye oldugu `household` verilerini gorebilmeli
- `owner` ve `admin` rolleri davet olusturabilmeli
- forma gelen `member_user_id` ilgili haneye ait olmali
- tum POST istekleri CSRF korumasindan gecmeli

## Production icin ek onlemler

- audit log tablosu
- kritik aksiyonlar icin olay kaydi
- sifre sifirlama akisi
- email verification
- IP bazli rate limiting
- 2FA opsiyonu
- sifre politikasi ve oturum zaman asimi

## Veri yedekleme

- PostgreSQL gunluk snapshot
- haftalik tam yedek
- ayrik backup saklama
- duzenli restore testi
