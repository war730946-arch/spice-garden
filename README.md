# 🌿 Spice Garden Restaurant - Web App

**Spice Garden** — Authentic Pakistani Cuisine की एक professional restaurant website hai. Online ordering, table reservations, catering, gift cards, aur admin panel ke saath ek complete solution.

---

## 🚀 Render.com पर FREE deploy kaise karein

Render ek cloud hosting platform hai jo **FREE** tier provide karta hai (PostgreSQL database + Web Service).

### Step 1: GitHub account aur repository banayein

1. **GitHub.com** par jayen aur account banayein (agar nahi hai)
2. Login karein aur ek **New Repository** banayein:
   - Repository name: `spice-garden` (ya koi bhi naam)
   - **Private** ya **Public** — dono chalega
   - "Create repository" button dabayein
3. Ab yeh commands apne terminal mein run karein (project folder mein):

```bash
cd restaurant
git remote add origin https://github.com/APKA_USERNAME/spice-garden.git
git branch -M main
git push -u origin main
```

> ⚠️ `APKA_USERNAME` ko apne GitHub username se replace karein!

### Step 2: Render.com par account banayein

1. **https://render.com** par jayen
2. **"Get started for free"** button dabayein
3. GitHub se sign up karein (yeh sabse easy hai)
4. Apne email verify karein

### Step 3: Render ko GitHub se connect karein

1. Render dashboard mein **"New +"** button dabayein
2. **"Blueprint"** select karein (yeh `render.yaml` file ko read karega)
3. Render ko apne GitHub repo tak access dena hoga
4. Apna `spice-garden` repository select karein
5. **"Apply Blueprint"** button dabayein

### Step 4: Deploy hone ka wait karein ✨

Render ab automatically:
- ✅ PostgreSQL database banayega (FREE)
- ✅ Web service deploy karega
- ✅ Environment variables set karega
- ✅ Health check run karega

Yeh process **3-5 minute** leta hai. Aap dashboard mein progress dekh sakte hain.

### Step 5: Website ka URL copy karein

Deploy hone ke baad:
1. Render dashboard mein apne service par click karein
2. Top par ek URL dikhega: `https://spice-garden.onrender.com`
3. Is URL par click karke website open karein!

## 🔐 Admin Panel

| Detail | Value |
|--------|-------|
| **URL** | `https://apka-domain.onrender.com/admin/login` |
| **Username** | `admin` |
| **Password** | `admin123` |

> ⚠️ Deploy ke baad turant password change kar lena admin panel mein!

## 🆓 Free Tier Limitations

Render ka free tier:
- Web service **15 minutes inactivity** ke baad **sleep** ho jata hai
- Sleep ke baad aane wala first request **30-50 seconds** leta hai (warm-up)
- PostgreSQL **1GB storage** free hai
- **100 GB/month** bandwidth free hai

### 🟢 Service ko "Always On" kaise rakhein? (Optional)

Har 10 minute mein automatically ping karne ke liye, **UptimeRobot** (free) ka use karein:
1. https://uptimerobot.com par jayen
2. Sign up karein
3. "Add Monitor" → HTTP monitor
4. Apni website ka URL daalein
5. Interval: **10 minutes**
6. Save karein — ab service sleep nahi karegi!

---

## 📁 Project Structure

```
restaurant/
├── app.py              # Main Flask application
├── models.py           # Database models
├── requirements.txt    # Python dependencies
├── Procfile            # Gunicorn config
├── render.yaml         # Render.com deployment config
├── static/
│   ├── css/style.css   # Styles
│   └── js/script.js    # Frontend JavaScript
└── templates/          # HTML templates
    ├── base.html       # Base template
    ├── index.html      # Homepage
    ├── menu.html       # Menu page
    ├── cart.html       # Cart
    ├── order-tracking.html  # Order tracking
    ├── reservations.html
    ├── contact.html
    ├── about.html
    ├── catering.html
    ├── gallery.html
    ├── giftcards.html
    ├── faq.html
    ├── privacy.html
    ├── terms.html
    └── admin/          # Admin panel templates
```

---

## ⚙️ Local Development (apne PC par test karna)

```bash
cd restaurant
pip install -r requirements.txt
python app.py
```

Browser mein kholen: `http://localhost:5000`

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite (local) / PostgreSQL (production)
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Render.com (free)

---

## 📞 Support

Koi problem ho to mujhse poochhiye! Main Buffy hoon, Freebuff ka AI agent. 😊

---

*Made with ❤️ for Pakistani cuisine*
