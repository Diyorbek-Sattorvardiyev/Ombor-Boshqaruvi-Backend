#  Ombor Boshqaruvi Tizimi – Flask + MySQL

Flask, SQLAlchemy, JWT va MySQL asosida yaratilgan ombor boshqaruvi tizimi. Tizim mahsulotlar, kirim-chiqim, xarajatlar, statistik tahlil, eksport, bildirishnomalar va admin panel kabi ko‘plab funksiyalarni o‘z ichiga oladi.

---

##  Asosiy Imkoniyatlar

-  JWT autentifikatsiya (admin/user rollari)
-  Mahsulotlar bilan ishlash (CRUD)
-  Kirim va  chiqim (sotuv) amaliyotlari
-  Xarajatlar moduli
-  Statistik tahlillar va dashboard
-  Sotuvlar grafigi
-  Excel va 📄 PDF eksport
-  Kam qoldiq ogohlantirishlari
-  Telegram orqali PDF backup yuborish

---

##  Texnologiyalar

- Python 3.10+
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- MySQL (pymysql orqali)
- Pandas, OpenPyXL (Excel)
- ReportLab (PDF)
- Matplotlib, Seaborn (chartlar)
- Telegram Bot API
- Flask-CORS

---
## Foydalanuvchi

| Method | Endpoint        | Tavsif                           |
| ------ | --------------- | -------------------------------- |
| `POST` | `/api/register` | Ro‘yxatdan o‘tish                |
| `POST` | `/api/login`    | Tizimga kirish (JWT token bilan) |
| `GET`  | `/api/profile`  | Foydalanuvchi ma’lumotlari       |

## Mahsulotlar

| Method   | Endpoint             | Tavsif                         |
| -------- | -------------------- | ------------------------------ |
| `GET`    | `/api/products`      | Mahsulotlar ro‘yxati           |
| `GET`    | `/api/products/<id>` | Bitta mahsulot ma’lumotlari    |
| `POST`   | `/api/products`      | Mahsulot qo‘shish (rasm bilan) |
| `PUT`    | `/api/products/<id>` | Mahsulotni tahrirlash          |
| `DELETE` | `/api/products/<id>` | Mahsulotni o‘chirish           |

## Kirim (Entries)

| Method | Endpoint       | Tavsif                |
| ------ | -------------- | --------------------- |
| `GET`  | `/api/entries` | Kirimlar ro‘yxati     |
| `POST` | `/api/entries` | Yangi mahsulot kirimi |

## Chiqim (Exits)

| Method | Endpoint     | Tavsif                 |
| ------ | ------------ | ---------------------- |
| `GET`  | `/api/exits` | Sotuvlar ro‘yxati      |
| `POST` | `/api/exits` | Yangi mahsulot chiqimi |

## Xarajatlar (Expenses)

| Method | Endpoint        | Tavsif                 |
| ------ | --------------- | ---------------------- |
| `GET`  | `/api/expenses` | Xarajatlar ro‘yxati    |
| `POST` | `/api/expenses` | Yangi xarajat qo‘shish |

## Statistikalar va Dashboard

| Endpoint                                   | Tavsif                                  |
| ------------------------------------------ | --------------------------------------- |
| `GET /api/statistics/sales?period=monthly` | Sotuvlar statistikasi                   |
| `GET /api/dashboard`                       | Asosiy ko‘rsatkichlar                   |
| `GET /api/charts/sales?period=weekly`      | Sotuvlar grafigi (daily/weekly/monthly) |

## Eksport

| Endpoint                              | Tavsif                                       |
| ------------------------------------- | -------------------------------------------- |
| `GET /api/export/excel?type=products` | Excel eksport (products/entries/exits/stock) |
| `GET /api/export/pdf?type=stock`      | PDF eksport (stock hisobot)                  |


## Fayl va Rasm Yuklash

| Endpoint                  | Tavsif                      |
| ------------------------- | --------------------------- |
| `POST /api/upload/image`  | Mahsulot rasmi yuklash      |
| `GET /uploads/<filename>` | Rasmni ko‘rish/yuklab olish |


## Bildirishnomalar

| Endpoint                 | Tavsif                                |
| ------------------------ | ------------------------------------- |
| `GET /api/notifications` | Kam qoldiq ogohlantirishlari ro‘yxati |

## Qidiruv

| Endpoint                               | Tavsif                               |
| -------------------------------------- | ------------------------------------ |
| `GET /api/search?q=soya&type=products` | Mahsulot/entry/exit bo‘yicha qidiruv |

## Admin Panel

| Endpoint                           | Tavsif                                  |
| ---------------------------------- | --------------------------------------- |
| `GET /api/admin/users`             | Foydalanuvchilar ro‘yxati               |
| `PUT /api/admin/users/<id>/toggle` | Foydalanuvchini bloklash/faollashtirish |

## Backup

| Endpoint                         | Tavsif                                              |
| -------------------------------- | --------------------------------------------------- |
| `POST /api/backup`               | JSON backup olish                                   |
| `GET /api/admin/download/backup` | PDF backup (rasmlar bilan) va Telegramga yuboriladi |

---

## Default Admin Foydalanuvchi
Email: admin@warehouse.com
Parol: admin123

---


