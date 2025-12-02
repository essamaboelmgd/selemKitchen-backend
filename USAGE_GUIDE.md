# دليل استخدام Kitchen Cabinet Calculator API

## نظرة عامة

هذا الـ API يساعدك في حساب مقاسات وتكاليف وحدات المطابخ والدواليب تلقائياً.

---

## الخطوة 1: تشغيل المشروع

### باستخدام Docker (الأسهل):

```bash
# في مجلد المشروع
docker-compose up --build
```

سيتم تشغيل:
- MongoDB على المنفذ 27017
- API على المنفذ 8000

### يدوياً:

```bash
# تثبيت المكتبات
pip install -r requirements.txt

# تشغيل الـ API
uvicorn app.main:app --reload
```

### التحقق من التشغيل:

افتح المتصفح على: `http://localhost:8000`

يجب أن ترى:
```json
{
  "message": "Kitchen Cabinet Calculator API",
  "version": "1.0.0"
}
```

---

## الخطوة 2: فتح واجهة Swagger UI

افتح المتصفح على: `http://localhost:8000/docs`

ستجد جميع الـ endpoints مع إمكانية تجربتها مباشرة.

---

## الخطوة 3: إعداد الإعدادات الأساسية (Settings)

### 3.1: جلب الإعدادات الحالية

**Endpoint:** `GET /settings`

**الاستخدام:**
- من Swagger UI: اضغط على `GET /settings` ثم "Try it out" ثم "Execute"
- أو من Postman/curl:
```bash
GET http://localhost:8000/settings
```

**النتيجة:**
```json
{
  "assembly_method": "bolt",
  "handle_type": "built-in",
  "handle_recess_height_mm": 30,
  "default_board_thickness_mm": 16,
  "edge_overlap_mm": 2,
  "materials": {},
  "last_updated": null
}
```

### 3.2: تحديث الإعدادات (مهم جداً!)

**Endpoint:** `PUT /settings`

**مثال: تحديث أسعار المواد**

```json
{
  "default_board_thickness_mm": 16,
  "edge_overlap_mm": 2,
  "materials": {
    "plywood_sheet": {
      "price_per_sheet": 2500,
      "sheet_size_m2": 2.4
    },
    "edge_band_per_meter": {
      "price_per_meter": 10
    }
  }
}
```

**الاستخدام:**
- من Swagger UI: `PUT /settings` → "Try it out" → الصق الـ JSON أعلاه → "Execute"

**النتيجة:** سيتم تحديث الإعدادات وإرجاعها مع `last_updated` timestamp

---

## الخطوة 4: حساب وحدة جديدة

### 4.1: حساب الوحدة الأساسية

**Endpoint:** `POST /units/calculate`

**مثال: وحدة أرضية**

```json
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "options": {
    "board_thickness_mm": 16,
    "back_clearance_mm": 3
  }
}
```

**الاستخدام:**
1. من Swagger UI: `POST /units/calculate` → "Try it out"
2. الصق الـ JSON أعلاه
3. اضغط "Execute"

**النتيجة:**
```json
{
  "unit_id": "unit_ABC12345",
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "parts": [
    {
      "name": "side_panel",
      "width_mm": 300,
      "height_mm": 720,
      "qty": 2,
      "edge_band_m": 2.04,
      "area_m2": 0.432
    },
    {
      "name": "top_panel",
      "width_mm": 768,
      "height_mm": 300,
      "qty": 1,
      "edge_band_m": 2.136
    },
    // ... المزيد من القطع
  ],
  "total_edge_band_m": 5.6,
  "total_area_m2": 1.2,
  "material_usage": {
    "plywood_sheets": 0.5,
    "edge_m": 5.6
  }
}
```

**مهم:** احفظ `unit_id` لأنك ستحتاجه في الخطوات التالية!

### 4.2: أنواع الوحدات

يمكنك استخدام:
- `"ground"` - وحدة أرضية
- `"wall"` - وحدة علوية
- `"double_door"` - وحدة بضلفتين

---

## الخطوة 5: حساب القطع الداخلية (Internal Counter)

**Endpoint:** `POST /units/{unit_id}/internal-counter/calculate`

**مثال:**

```json
{
  "options": {
    "add_base": true,
    "add_mirror": false,
    "add_internal_shelf": true,
    "drawer_count": 2,
    "back_clearance_mm": 3,
    "expansion_gap_mm": 3
  }
}
```

**الاستخدام:**
1. استخدم `unit_id` من الخطوة السابقة
2. من Swagger UI: `POST /units/{unit_id}/internal-counter/calculate`
3. الصق الـ JSON أعلاه
4. اضغط "Execute"

**النتيجة:**
```json
{
  "unit_id": "unit_ABC12345",
  "unit_type": "ground",
  "parts": [
    {
      "name": "internal_base",
      "type": "base",
      "width_mm": 754,
      "height_mm": 294,
      "qty": 1,
      "edge_band_m": 2.096
    },
    {
      "name": "drawer_1_bottom",
      "type": "drawer",
      "width_mm": 748,
      "height_mm": 291,
      "qty": 1
    },
    // ... المزيد
  ],
  "total_edge_band_m": 8.5,
  "total_area_m2": 0.65,
  "material_usage": {
    "plywood_sheets": 0.27,
    "edge_m": 8.5
  }
}
```

---

## الخطوة 6: تفاصيل توزيع الشريط (Edge Band Breakdown)

**Endpoint:** `GET /units/{unit_id}/edge-breakdown?edge_type=pvc`

**الاستخدام:**
1. استخدم `unit_id` من الخطوة 4
2. من Swagger UI: `GET /units/{unit_id}/edge-breakdown`
3. يمكنك اختيار `edge_type`: `pvc` أو `wood`
4. اضغط "Execute"

**النتيجة:**
```json
{
  "unit_id": "unit_ABC12345",
  "parts": [
    {
      "part_name": "side_panel",
      "qty": 2,
      "edges": [
        {
          "edge": "top",
          "length_mm": 302.0,
          "length_m": 0.302,
          "edge_type": "pvc",
          "has_edge": true
        },
        {
          "edge": "bottom",
          "length_mm": 302.0,
          "length_m": 0.302,
          "edge_type": "pvc",
          "has_edge": true
        },
        // ... المزيد
      ],
      "total_edge_m": 4.288,
      "edge_type": "pvc"
    }
  ],
  "total_edge_m": 15.6,
  "total_cost": 156.0,
  "cost_breakdown": {
    "pvc": 156.0
  }
}
```

---

## الخطوة 7: تقدير التكلفة (Cost Estimation)

**Endpoint:** `POST /units/estimate`

**مثال:**

```json
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2
}
```

**الاستخدام:**
1. من Swagger UI: `POST /units/estimate`
2. الصق الـ JSON أعلاه
3. اضغط "Execute"

**النتيجة:**
```json
{
  "unit_id": "unit_XYZ789",
  "type": "ground",
  "parts": [...],
  "total_edge_band_m": 5.6,
  "total_area_m2": 1.2,
  "material_usage": {...},
  "cost_breakdown": {
    "plywood": 1250,
    "edge_band": 56
  },
  "total_cost": 1306
}
```

**ملاحظة:** يجب أن تكون قد حدّثت أسعار المواد في الخطوة 3.2

---

## الخطوة 8: توليد ملخص شامل (Summary)

**Endpoint:** `POST /summaries/generate`

**مثال شامل:**

```json
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "include_internal_counter": true,
  "internal_counter_options": {
    "add_base": true,
    "add_mirror": false,
    "add_internal_shelf": true,
    "drawer_count": 2
  }
}
```

**الاستخدام:**
1. من Swagger UI: `POST /summaries/generate`
2. الصق الـ JSON أعلاه
3. اضغط "Execute"

**النتيجة:**
```json
{
  "summary_id": "summary_ABC123",
  "unit_id": "unit_ABC123",
  "type": "ground",
  "unit_dimensions": {
    "width_mm": 800,
    "height_mm": 720,
    "depth_mm": 300
  },
  "shelf_count": 2,
  "items": [
    {
      "part_name": "side_panel",
      "description": "side_panel - 300mm × 720mm",
      "width_mm": 300,
      "height_mm": 720,
      "qty": 2,
      "area_m2": 0.432,
      "edge_band_m": 2.04
    },
    // ... جميع القطع الأساسية والداخلية
  ],
  "totals": {
    "total_area_m2": 1.85,
    "total_edge_band_m": 12.5,
    "total_parts": 12,
    "total_qty": 15
  },
  "material_usage": {
    "plywood_sheets": 0.77,
    "edge_m": 12.5
  },
  "costs": {
    "material_cost": 1925,
    "edge_band_cost": 125,
    "total_cost": 2050
  },
  "generated_at": "2025-01-21T10:30:00Z"
}
```

### جلب الملخص المحفوظ:

**Endpoint:** `GET /summaries/{unit_id}`

**الاستخدام:**
- استخدم `unit_id` من الملخص السابق
- من Swagger UI: `GET /summaries/{unit_id}` → "Execute"

---

## سيناريو استخدام كامل (من البداية للنهاية)

### مثال عملي: حساب وحدة مطبخ كاملة

**1. إعداد الأسعار:**
```bash
PUT /settings
{
  "materials": {
    "plywood_sheet": {
      "price_per_sheet": 2500,
      "sheet_size_m2": 2.4
    },
    "edge_band_per_meter": {
      "price_per_meter": 10
    }
  }
}
```

**2. حساب الوحدة:**
```bash
POST /units/calculate
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2
}
```
**احفظ:** `unit_id = "unit_ABC123"`

**3. إضافة القطع الداخلية:**
```bash
POST /units/unit_ABC123/internal-counter/calculate
{
  "options": {
    "add_base": true,
    "drawer_count": 2
  }
}
```

**4. تفاصيل الشريط:**
```bash
GET /units/unit_ABC123/edge-breakdown?edge_type=pvc
```

**5. ملخص نهائي:**
```bash
POST /summaries/generate
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "include_internal_counter": true,
  "internal_counter_options": {
    "add_base": true,
    "drawer_count": 2
  }
}
```

---

## نصائح مهمة

1. **احفظ الـ IDs:** دائماً احفظ `unit_id` و `summary_id` للرجوع إليها لاحقاً

2. **حدّث الأسعار:** تأكد من تحديث أسعار المواد في Settings قبل حساب التكاليف

3. **استخدم Swagger UI:** أسهل طريقة لتجربة الـ API هي من `http://localhost:8000/docs`

4. **الوحدات بالمليمتر:** جميع الأبعاد بالمليمتر (mm)

5. **الملخص الشامل:** استخدم `/summaries/generate` للحصول على تقرير كامل

---

## استكشاف الأخطاء

### المشكلة: "Database connection not available"
**الحل:** تأكد من تشغيل MongoDB (Docker Compose)

### المشكلة: "Unit not found"
**الحل:** تأكد من استخدام `unit_id` صحيح

### المشكلة: التكاليف = 0
**الحل:** حدّث أسعار المواد في Settings

---

## أمثلة إضافية

### وحدة علوية (Wall Unit):
```json
{
  "type": "wall",
  "width_mm": 600,
  "height_mm": 500,
  "depth_mm": 250,
  "shelf_count": 1
}
```

### وحدة بضلفتين:
```json
{
  "type": "double_door",
  "width_mm": 1000,
  "height_mm": 800,
  "depth_mm": 350,
  "shelf_count": 3
}
```

---

## الخلاصة

الـ API يقوم بـ:
1. ✅ حساب مقاسات القطع تلقائياً
2. ✅ حساب متر الشريط المطلوب
3. ✅ حساب المساحة واستخدام المواد
4. ✅ حساب التكاليف
5. ✅ توليد ملخص شامل

كل ما عليك هو إدخال الأبعاد الأساسية والـ API يقوم بالباقي!

