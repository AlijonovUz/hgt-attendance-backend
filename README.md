# HGT Attendance System - Frontend API Documentation

Ushbu hujjat Frontend va Mobile dasturchilar uchun tizim API larini to'g'ri integratsiya qilish maqsadida tayyorlandi. Tizim to'liq REST API standartida va JWT autentifikatsiyasi orqali ishlaydi.

## 📌 Asosiy Ma'lumotlar
- **Base URL:** `/api/v1/`
- **Authentication:** `Bearer <Access-Token>` (Authorization header orqali yuboriladi)
- **Content-Type:** Odatda `application/json`, rasm yuklanadigan (Face ID, Davomat) so'rovlarda esa `multipart/form-data`.

---

## 🔐 1. Avtorizatsiya va Profil (Auth & Profile)

### 1.1 Tizimga kirish (Login)
- **Endpoint:** `POST /api/v1/users/auth/login/`
- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "full_name": "Aliyev Vali",
  "password": "mypassword123"
}
```
- **Response (200 OK):**
```json
{
  "refresh": "eyJhbGciOi...",
  "access": "eyJhbGciOi..."
}
```

### 1.2 Tokenni yangilash (Refresh Token)
- **Endpoint:** `POST /api/v1/users/auth/refresh/`
- **Request Body:**
```json
{
  "refresh": "eyJhbGciOi..."
}
```

### 1.3 Mening profilimni ko'rish / Tahrirlash
- **Endpoint:** `GET, PUT, PATCH /api/v1/users/auth/profile/`
- **Eslatma:** Frontend foydalanuvchining ma'lumotlarini ushbu API orqali oladi. Agar foydalanuvchi profiliga ilk marta rasm (Face ID) joylashtirmoqchi bo'lsa, xuddi shu API ga `PATCH` orqali `face_image` yuboradi.

### 1.4 Yuz ma'lumotini tekshirish (Face Verification)
- **Endpoint:** `POST /api/v1/users/auth/verify-face/`
- **Content-Type:** `multipart/form-data`
- **Request Body:**
  - `image`: [Fayl (rasm)]
- **Eslatma:** Faqat haqiqiy odamning yuzi bo'lishi tekshiriladi (Anti-spoofing).

### 1.5 Parolni almashtirish
- **Endpoint:** `PUT /api/v1/users/auth/change-password/`
- **Request Body:**
```json
{
  "old_password": "currentPassword",
  "new_password": "newSecurePassword123"
}
```

---

## 📍 2. Davomat va Geofencing (Attendance)

### 2.1 Davomat belgilash (Check-in / Check-out)
- **Endpoint:** `POST /api/v1/attendance/attendance/`
- **Content-Type:** `multipart/form-data` (Juda muhim!)
- **Request Body:**
  - `event_type`: (Matn) `check_in` | `lunch_start` | `lunch_end` | `check_out`
  - `gps_latitude`: `41.311081`
  - `gps_longitude`: `69.240562`
  - `image`: [Jonli olingan selfi rasm fayli]
- **Eslatma:** Rasm bazada saqlanmaydi, faqat Face ID aniqligi uchun tekshiriladi. Agar foydalanuvchi Geozonadan tashqarida bo'lsa yoki ketma-ketlikni buzsa (masalan ikki marta check-in) API `400 Bad Request` qaytaradi.

### 2.2 Davomat tarixini olish
- **Endpoint:** `GET /api/v1/attendance/attendance/`
- **Filter Parametrlari (URL Query):**
  - `?event_type=check_in`
  - `?date_from=2024-01-01T00:00:00&date_to=2024-01-31T23:59:59`
  - `?user__branch=id` (Faqat adminlar uchun)

---

## 🏢 3. Tashkiliy Tuzilma (HR & Organization)
*Barcha GET, POST, PUT, DELETE metodlari mavjud.*

### 3.1 Filiallar (Branches)
- **Endpoint:** `/api/v1/users/branches/`
- **Request Body (POST/PUT):** `{"name": "Toshkent filial"}`

### 3.2 Bo'limlar (Departments)
- **Endpoint:** `/api/v1/users/departments/`
- **Filter:** `?branch={branch_id}`
- **Request Body:** `{"name": "IT bo'limi", "branch": "{branch_id}"}`

### 3.3 Lavozimlar (Positions)
- **Endpoint:** `/api/v1/users/positions/`
- **Filter:** `?department={department_id}`

### 3.4 Rollar va Ruxsatlar (Roles & Permissions)
- **Rollar:** `/api/v1/users/roles/`
- **Ruxsatlar (Permissions):** `/api/v1/users/permissions/`

### 3.5 Geozonalar (Ish joylashuvi radiuslari)
- **Endpoint:** `/api/v1/attendance/geozones/`
- **Filter:** `?branch={branch_id}&zone_type={polygon|circle}`
- **Request Body (Dizayn formasi bo'yicha):**
```json
{
  "name": "Bosh ofis qamrovi",
  "zone_type": "circle",
  "latitude": "41.311081",
  "longitude": "69.240562",
  "radius": "50.00",
  "branch": "{branch_id}"
}
```

---

## 👥 4. Xodimlarni Boshqarish (Users & Employees)

### 4.1 Xodimlar ro'yxati va Yaratish
- **Endpoint:** `/api/v1/users/employees/`
- **Filter:** `?branch={id}&department={id}&position={id}&role={id}&is_active=true`
- **Qidiruv:** `?search=Aliyev` (FIO, Telefon, JSHSHIR orqali)
- **Eslatma:** GET methodi orqali tashkiliy tuzilma ma'lumotlari (`branch`, `department` va h.k) to'liq ob'yekt ko'rinishida qaytadi (Frontend ishini osonlashtirish uchun).

### 4.2 Xodim holatini o'zgartirish (Soft Delete)
Odamlarni tizimdan butunlay o'chirib yuborish taqiqlanadi. Ular faqat o'chirib qo'yiladi (Deactivate).

- **Bloklash:** `POST /api/v1/users/employees/{id}/block/`
- **Blokdan chiqarish:** `POST /api/v1/users/employees/{id}/unblock/`
- **Ishdan bo'shatish:** `POST /api/v1/users/employees/{id}/fire/` (Tizimga kira olmaydi, davomat ham qila olmaydi).

---

## 🕵️‍♂️ 5. Tizim Auditi (Audit Logs)

- **Endpoint:** `GET /api/v1/audit/logs/` (Faqat Read-Only, `audit_view` ruxsati borlar uchun)
- **Filterlar:** 
  - `?action=create|update|delete`
  - `?table_name=Xodimlar`
  - `?date_from=...&date_to=...`
- **Qidiruv:** `?search=John Doe` (IP manzil, jadval nomi, xodim nomi orqali qidiradi)
- **Response formati:**
```json
{
  "id": 1,
  "user_full_name": "Aliyev Vali",
  "action_display": "Yangilandi",
  "table_name": "Foydalanuvchi",
  "object_name": "Karimov Anvar",
  "old_values": {"phone": "+998901234567"},
  "new_values": {"phone": "+998901112233"},
  "ip_address": "192.168.1.5",
  "created_at": "2024-05-12T10:00:00Z"
}
```

---
*Ushbu hujjat backend tomonidan doimiy yangilab boriladi. Agar qandaydir muammo yoki xatolik kodi (`400`, `403`) qaytsa, `detail` keyi orqali o'zbek tilida aniq xatolik sababi jo'natiladi.*