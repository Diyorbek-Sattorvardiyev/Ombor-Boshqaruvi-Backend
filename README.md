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

| Method | Endpoint        | Tavsif                           |
| ------ | --------------- | -------------------------------- |
| `POST` | `/api/register` | Ro‘yxatdan o‘tish                |
| `POST` | `/api/login`    | Tizimga kirish (JWT token bilan) |
| `GET`  | `/api/profile`  | Foydalanuvchi ma’lumotlari       |



