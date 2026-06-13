# HGT Attendance - Bildirishnomalar va WebSocket (Qo'llanma)

Ushbu loyihada foydalanuvchilarga bildirishnomalarni (Push Notifications) yetkazib berish uchun ham **Real-time WebSocket**, ham qurilmalarga to'g'ridan-to'g'ri yuboriladigan **Firebase Cloud Messaging (FCM)** tizimi qo'llanilgan.

Quyida ushbu tizimlarni Frontend / Mobile ilovaga qanday ulash bo'yicha to'liq qo'llanma keltirilgan.

---

## 1. WebSocket orqali Real-time Bildirishnomalar

WebSocket orqali foydalanuvchi tizimda (saytda) onlayn bo'lib turgan vaqtda jonli xabarlarni olishi mumkin. Xavfsizlikni ta'minlash maqsadida WebSocket ulanishi uchun maxsus **Ticket (Chipta)** tizimi qilingan.

### 1.1. Ticket olish (REST API)
WebSocketga to'g'ridan-to'g'ri JWT token bilan ulanish xavfsiz emas. Shuning uchun avval 1 daqiqalik yaroqlilik muddatiga ega bo'lgan ticket olinadi.

- **Endpoint:** `POST /api/v1/notifications/tickets/` (Loyiha URL sozlanganiga qarab prefiks o'zgarishi mumkin)
- **Header:** `Authorization: Bearer <Sizning_JWT_Tokeningiz>`
- **Javob (Response):**
```json
{
    "ticket": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "expires_in": 60
}
```

### 1.2. WebSocket tarmog'iga ulanish
Olingan ticket orqali darhol WebSockets serveriga ulanish amalga oshiriladi.

- **WebSocket URL:** `ws://<domain_yoki_ip>/ws/notifications/?ticket=<SIZ_OLGAN_TICKET>`
- **Mantiq:**
  1. Frontend / Mobile yuqoridagi manzilga ulanadi.
  2. Backend siz uzatgan `ticket` ni tekshiradi va u tegishli bo'lgan foydalanuvchini aniqlab, maxsus guruhga (`user_<ID>_notifications`) qo'shib qo'yadi.
  3. Ulanish o'rnatilgach, backenddan yangi xabar kelsa, u avtomatik tarzda JSON ko'rinishida yuboriladi.

**Kutiladigan xabar formati (Frontendga keladigan JSON):**
```json
{
    "id": "e3b0c442-989b-4643-9b0e-1a2b3c4d5e6f",
    "title": "Davomat Muvaffaqiyatli",
    "message": "Siz ishga o'z vaqtida keldingiz!",
    "extra_data": {"type": "attendance"},
    "created_at": "2026-06-13T09:00:00Z",
    "is_read": false
}
```

---

## 2. Push Notifications (FCM / APNS)

Foydalanuvchi ilovadan chiqib ketgan, saytni yopgan yoki telefoni qulflangan holatda ham bildirishnoma olishi uchun Push Notifications ishlatiladi.

Buning uchun Mobile/Frontend dasturchi Firebase'dan (yoki Apple APNS) maxsus `fcm_token` olib, uni Backendga ro'yxatdan o'tkazib qo'yishi shart.

### 2.1. Qurilmani ro'yxatdan o'tkazish (Device Register)

Foydalanuvchi tizimga login qilganidan so'ng yoki ilovani birinchi marta ochganida uning qurilma ma'lumotlari jo'natilishi kerak.

- **Endpoint:** `POST /api/v1/notifications/devices/register/`
- **Header:** `Authorization: Bearer <Sizning_JWT_Tokeningiz>`
- **Request Body (JSON):**
```json
{
    "device_id": "ab12-cd34-ef56-gh78",   // Qurilmaning unikal ID si (Mac address, UUID va h.k.)
    "fcm_token": "fcm_token_string_here_which_is_very_long", // Firebase taqdim etgan Push Token
    "device_type": "android"              // 'android', 'ios' yoki 'web'
}
```
- **Javob (Response):**
```json
{
    "message": "Qurilma muvaffaqiyatli ro'yxatdan o'tdi",
    "status": "created" // Yoki "updated" (agar oldin bo'lsa yangilanadi)
}
```

**Asosiy qoidalar:**
1. Agar bir xil `fcm_token` boshqa birovga tegishli bo'lsa (kimdir boshqaning telefonidan kirsa), avvalgi foydalanuvchidan token tortib olinib, yangi foydalanuvchiga biriktiriladi (Adashib boshqaga xabar borib qolishining oldi olingan).
2. Tizimdan chiqish (Log out) qilinganda Front-end ushbu qurilmani o'chirib yuborishi maqsadga muvofiq (agar o'chirish API yozilgan bo'lsa, aks holda FCM tokenni tozalash kerak).

---

## 3. Bildirishnomalarni boshqarish (REST API)

Bildirishnomalar ro'yxatini ko'rish va ularni o'qilgan qilib belgilash. Barcha API'lar uchun JWT token talab qilinadi.

### 3.1. Bildirishnomalar ro'yxatini olish
- **Endpoint:** `GET /api/v1/notifications/`
- **Filterlash:** `?is_read=false` (Faqat o'qilmaganlarini olish)
- **Pagination:** Odatiy sahifalash ishlaydi (limit/offset yoki page).

### 3.2. O'qilmagan xabarlar sonini olish
- **Endpoint:** `GET /api/v1/notifications/count/`
- **Javob:**
```json
{
    "unread": 3,
    "read": 15,
    "total": 18
}
```

### 3.3. Bitta xabarni o'qilgan qilib belgilash
Foydalanuvchi xabarni ochib ko'rganda, shu API chaqiriladi.
- **Endpoint:** `PATCH /api/v1/notifications/<UUID>/read/`
- **Javob:** `200 OK` ("Xabar o'qildi deb belgilandi.")

### 3.4. Barcha xabarlarni o'qilgan qilish
- **Endpoint:** `POST /api/v1/notifications/read-all/`
- **Javob:**
```json
{
    "message": "3 ta xabar muvaffaqiyatli o'qildi."
}
```

---

## Qisqacha Xulosa (Ishlash Ketma-ketligi)

1. Xodim tizimga **Login** qiladi va Token oladi.
2. Frontend darhol Firebase'dan FCM Token so'raydi.
3. Frontend olingan qurilma ma'lumotlarini **`/devices/register/`** ga jo'natadi.
4. Tizim ishlayotgan paytda "Jonli" xabarlar kelishi uchun Frontend **`/tickets/`** dan bitta chipta oladi.
5. Chipta bilan **`ws://.../ws/notifications/?ticket=...`** tarmog'iga ulanib, quloq solib o'tiradi.
6. Biror muhim jarayon bo'lsa (Masalan, Admin foydalanuvchini tasdiqlasa yoki Davomat qayd etilsa) server bir vaqtning o'zida ham WebSocketga, ham Firebase yordamida Push Notification'ga xabar uchiradi.