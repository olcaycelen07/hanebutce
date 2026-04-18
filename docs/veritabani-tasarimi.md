# Veritabani Tasarimi

## Ana tablolar

### users

- `id`
- `full_name`
- `email`
- `password_hash`
- `email_verified_at`
- `created_at`
- `updated_at`

### households

- `id`
- `name`
- `slug`
- `owner_user_id`
- `plan_type`
- `currency_code`
- `created_at`
- `updated_at`

### household_members

- `id`
- `household_id`
- `user_id`
- `role`
- `status`
- `joined_at`

### categories

- `id`
- `household_id`
- `name`
- `type` (`income`, `expense`, `payment`)
- `color`

### transactions

- `id`
- `household_id`
- `created_by_user_id`
- `assigned_user_id`
- `category_id`
- `type` (`income`, `expense`)
- `title`
- `amount`
- `currency_code`
- `transaction_date`
- `note`
- `created_at`

### bills

- `id`
- `household_id`
- `created_by_user_id`
- `assigned_user_id`
- `title`
- `amount`
- `currency_code`
- `due_date`
- `status` (`pending`, `paid`, `overdue`)
- `payment_channel`
- `is_recurring`
- `recurrence_rule`
- `note`
- `created_at`

### invitations

- `id`
- `household_id`
- `email`
- `role`
- `token`
- `expires_at`
- `accepted_at`

### subscriptions

- `id`
- `household_id`
- `provider`
- `provider_customer_id`
- `provider_subscription_id`
- `plan_name`
- `status`
- `renewal_date`

## Kritik iliskiler

- bir `user` birden fazla `household` icinde olabilir
- bir `household` birden fazla `member`, `transaction` ve `bill` icerir
- `bills` ve `transactions` hem olusturan kisiye hem de ilgili aile uyesine baglanabilir

## Teknik notlar

- para alanlari icin `decimal(12,2)` kullanilmali
- tum tarih alanlari UTC tutulmali
- audit log tablosu ikinci fazda eklenmeli
- premium ozellikler `subscriptions` uzerinden kontrol edilmeli
