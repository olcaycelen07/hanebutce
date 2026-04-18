# Olceklenme Yol Haritasi

## Asama 1: Ilk canli kullanim

- tek uygulama instance
- managed PostgreSQL
- SMTP servis
- temel hata loglama

## Asama 2: Kullanici artis donemi

- read-heavy sorgular icin indeksleme
- rapor sorgularini optimize etme
- background job yapisi
- cache katmani

## Asama 3: SaaS olgunluk seviyesi

- ayri billing servisi
- notification servisi
- event queue
- daha detayli yetki matrisi
- ekip bazli analitik

## Teknik oncelikler

1. `household_id` indeksleri
2. query log ve performans izlemesi
3. PostgreSQL migration sistemi
4. object storage ve export altyapisi
5. yatay olceklenebilir app instance'lari
