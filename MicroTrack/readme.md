# MicroTrack - Microgreens Tracking System

MicroTrack is a backend service built with **Golang** and **MongoDB** to manage microgreens tracking. It allows users to **add, update, retrieve, search, and delete plant records** while maintaining information on seeding and harvesting schedules.

---

## 🚀 Features
- **Plant Management:** Add, update, retrieve, search, and delete plants.
- **Calendar Integration:** Track seeding and harvest dates automatically.
- **Advanced Search:** Search by name, scientific name, description, growth days, group ID, and growth stage with pagination and sorting.
- **Growth Tracking:** Track the plant's current growth stage (e.g., germination, seedling, mature).
- **MongoDB Storage:** Persist data reliably.
- **JWT Authentication:** Secure access for users and admins.
- **Role-Based Authorization:**
  - **Admins** can add, update, delete plants, and promote users to admins.
  - **Users** can only view/search plants.
- **Admin Promotion Endpoint:** Promote registered users to admin securely.
- **Swagger Documentation:** API fully documented and accessible via Swagger UI.

---

## 🛠️ Tech Stack
- **Golang (Gin Framework)** — Backend API
- **MongoDB** — Database
- **JWT Authentication** — Token-based login security
- **Swagger (swaggo)** — API Documentation
- **Docker (Optional)** — Containerization

---

## 📦 Setup and Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/MicroTrack.git
cd MicroTrack
```

### 2️⃣ Install Dependencies
```bash
go mod tidy
```

### 3️⃣ Configure MongoDB Connection
In `config/db.go`:
```go
const mongoURI = "mongodb://localhost:27017"
const dbName = "microtrack"
```

### 4️⃣ Install Swagger Tool
```bash
go install github.com/swaggo/swag/cmd/swag@latest
```

Add Go bin folder to PATH if necessary (`C:\Users\<Username>\go\bin`).

---

### 5️⃣ Generate Swagger Docs
```bash
swag init --parseDependency --parseInternal
```

It will generate the `/docs` folder.

---

### 6️⃣ Run the Server
```bash
go run main.go
```

Server starts at `http://localhost:8080`

Swagger UI available at:

> http://localhost:8080/swagger/index.html

---

## 📖 API Documentation

### 🔐 User Authentication

#### ➔ Sign Up
**Endpoint:** `POST /signup`
```json
{
  "first_name": "Hamed",
  "last_name": "Frogh",
  "username": "hamedf",
  "email": "admin@example.com",
  "password": "securepassword"
}
```

✅ Role defaults to `user`. Admin signup must be promoted manually.

#### ➔ Login
**Endpoint:** `POST /login`
```json
{
  "username": "hamedf",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "token": "your_jwt_token"
}
```

---

### 👑 Promote User to Admin *(Admin Only)*
**PATCH** `/admin/promote/:username`

**Authorization:** Bearer token required.

---

### 🌱 Plant Management Endpoints

#### ➔ Add a New Plant *(Admin Only)*
**POST** `/plants`  
**Authorization:** Bearer token required.

```json
{
  "name": "Basil",
  "scientific_name": "Ocimum basilicum",
  "growth_days": 14,
  "seeding_date": "2025-05-01T00:00:00Z",
  "growth_stage": "seedling",
  "description": "Fragrant herb used in cooking.",
  "floor": "First Floor",
  "humidity": 55,
  "temperature": 22,
  "height": 10.5,
  "leaf_color": "green"
}
```

---

#### ➔ Get All Plants *(Public Access)*
**GET** `/plants`

---

#### ➔ Search Plants *(Public Access)*

**GET** `/plants/search`

**Query Parameters:**
- `name`: Filter by name
- `scientific_name`: Filter by scientific name
- `description`: Filter by description
- `plant_id`: Filter by plant ID
- `group_id`: Filter by group ID
- `growth_stage`: Filter by growth stage
- `min_growth_days`, `max_growth_days`
- `limit`, `skip`
- `sort_by`, `sort_order`

---

#### ➔ Update Plant *(Admin Only)*
**PUT** `/plants/{plant_id}`  
**Authorization:** Bearer token required.

---

#### ➔ Delete Plant *(Admin Only)*
**DELETE** `/plants/{plant_id}`  
**Authorization:** Bearer token required.

#### ➔ Delete All Plants by Name *(Admin Only)*
**DELETE** `/plants/delete-by-name/{name}`  
**Authorization:** Bearer token required.

---

## 🧪 Testing the API

- Use **Postman**, **curl**, or Swagger UI.
- First login to get your JWT token.
- Set request headers:
  ```http
  Authorization: Bearer YOUR_TOKEN
  ```
- Test promoting a user:
  ```bash
  PATCH http://localhost:8080/admin/promote/username
  ```
- Try searching with filters like:
  ```bash
  GET /plants/search?group_id=abc123&growth_stage=seedling
  ```

---

## 📚 Swagger Documentation (OpenAPI)

After running:
```bash
swag init --parseDependency --parseInternal
go run main.go
```

Visit:
> http://localhost:8080/swagger/index.html

✅ Try endpoints directly from the browser!

---

## 📜 License
Open-source project — free to use, modify, and distribute.

---

## 📩 Contact
Created by **Hamed Frogh**.  
Feel free to reach out for any collaboration!

---

🚀 Happy Coding and Growing Microgreens! 🌱
