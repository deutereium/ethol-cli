# Et-Hol API — Reverse-Engineering Notes

Documentation of the Et-Hol (ETHOL, PENS) API surface relevant to this project,
and the steps used to reverse-engineer it. Useful for future plans (attendance,
scheduling, etc.).

> Last verified: 22 September 2026. Endpoints/payloads can change without notice —
> re-check against the live SPA bundle if anything stops working.

---

## 1. Authentication

Et-Hol uses a **CAS login flow** (already implemented in `ethol_notifier/auth.py`)
followed by JWT cookie-based auth for the JSON API.

### CAS login
- **GET** `https://login.pens.ac.id/cas/login?service=https%3A%2F%2Fethol.pens.ac.id%2Fapi%2Fauth%2Fcas-callback`
  - Parse hidden form inputs: `lt`, `execution`, `_eventId`, etc.
- **POST** the same URL with `username`, `password`, and the hidden fields.
- A final **GET** to `https://ethol.pens.ac.id/api/auth/cas-callback` sets the app cookies.

### Resulting cookies (on `ethol.pens.ac.id`), set by CAS callback
| Cookie | Value | Notes |
|---|---|---|
| `PHPSESSID` | `ST-…-cas` | Session id |
| `hakAktif` | `mahasiswa` | Active role |
| `token` | `eyJhbGciOi...` | **JWT** — contains student identity |
| `refresh_token` | hex string | Used to refresh the JWT (POST `/api/auth/refresh`) |

### JWT payload (`token` cookie)
Base64-decode the middle segment:
```json
{
  "nomor": 27663,            // student number — used as `mahasiswa` in presensi
  "nipnrp": "2325600039",
  "nama": "…",
  "hakAktif": ["mahasiswa"],
  "iat": 1789445910,
  "exp": 1789446810
}
```

The API is cookie-authenticated (`withCredentials: true`, axios `baseURL:
https://ethol.pens.ac.id/api`). A plain `requests.Session` holding these cookies is
enough — no `Authorization` header, no CSRF token.

---

## 2. Core API endpoints

Base URL: `https://ethol.pens.ac.id/api`

### Auth & config
| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/config` | Returns `{tahun_aktif, semester_aktif, tahun_ajaran_aktif, menit_per_jam, …}` |
| POST | `/auth/refresh` | Refresh JWT |

### Kuliah (class enrollment)
| Method | Path | Purpose |
|---|---|---|
| GET | `/kuliah?tahun=2026&semester=1` | List of enrolled classes |
| POST | `/kuliah/hari-kuliah-in` | Schedule (day/time/room) for given kuliah numbers |
| GET | `/kuliah/peserta-kuliah` | Class participants |
| GET | `/kuliah/by-kuliah-js` | Class info by JS slug |

The `/kuliah` list entries look like (normalized by `get_class_list()`):
```json
[
  {
    "nomor": 222674,
    "jenisSchema": 4,
    "matakuliah": { "nama": "Elektronika Daya 1" },
    "pararel": "A",
    "kelas": "…",
    "dosen": "Moh. Zaenal Efendi"
  }
]
```

### Presensi (attendance) — the important part
| Method | Path | Purpose |
|---|---|---|
| GET | `/presensi/aktif-kuliah?kuliah=<id>&jenis_schema=<s>` | Active presensi windows for a class |
| POST | `/presensi/mahasiswa` | **Submit attendance** (student) |
| GET | `/presensi/riwayat?kuliah=<id>&jenis_schema=<s>&nomor=<student>` | Attendance history |
| GET | `/presensi/terakhir-kuliah` | Last presensi per class |
| GET | `/presensi/stat-beranda-mahasiswa` | Dashboard stats |

#### `GET /presensi/aktif-kuliah`
Returns a list of presensi windows. Attendance is open when an entry has
`open == 1`; that entry provides the `key` needed to submit:
```json
[
  { "kuliah": 222674, "key": "PflTTQVzgO", "jenisSchema": 4, "open": 1 }
]
```

#### `POST /presensi/mahasiswa` — submit attendance
Request body:
```json
{
  "kuliah": 222710,
  "jenis_schema": 4,
  "mahasiswa": 27663,
  "key": "AWQGR7OpZH",
  "kuliah_asal": 222710
}
```
- `kuliah` — class id
- `jenis_schema` — always `4` for these classes
- `mahasiswa` — student `nomor` from the JWT
- `key` — from the currently-open presensi entry (`open == 1`)
- `kuliah_asal` — taken from the class's own `kuliah_asal` field in `/api/kuliah`
  (typically the class id itself; `null` only when that field is absent)

#### `GET /presensi/riwayat`
Attendance log entries contain `tanggal`, `key`, and `nomor`. An entry whose
`key` matches the current open window means the student already attended:
```json
[
  {
    "nomor": 4712391,
    "tanggal": "22-09-2026 16:48:59",
    "key": "PflTTQVzgO"
  }
]
```

---

## 3. Notification API (used by the notifier)

| Method | Path | Purpose |
|---|---|---|
| GET | `/notifikasi/mahasiswa?filterNotif=SEMUA` | All notifications (JSON list) |
| GET | `/notifikasi/mahasiswa-belum-baca` | Unread count |

Notification entries include `idNotifikasi`, `keterangan` (message text),
`waktuNotifikasi` (timestamp), and **`dataTerkait`**.

`dataTerkait` is either:
- a **string** like `"222694-4"` → class id `222694`, schema `4`, **or**
- a **dict** with `nomor`/`jenis_schema` etc.

That string is the key connection between a *"Dosen telah membuka presensi untuk
matakuliah X"* notification and the class id used for attendance. See
`scraper.extract_class_number()`.

---

## 4. How the UI attends (reverse-engineered)

The student dashboard (`/mahasiswa/beranda`) and class page render a **Presensi**
button that is:
- **green/enabled** (`btnBukaPresensiDark`) when `aktif-kuliah` has an entry with `open == 1`,
- **greyed/disabled** (`btnBukaPresensiDarkLocked`) otherwise.

Clicking the green button calls exactly the POST above (the SPA's
`mahasiswaPresensi({kuliah, jenis_schema, mahasiswa, key, kuliah_asal})`).

So **attendance is fully driveable via HTTP** — no browser automation required.

---

## 5. Code map

| File | What it does |
|---|---|
| `ethol_notifier/auth.py` | CAS login, returns cookie-authenticated `requests.Session` |
| `ethol_notifier/scraper.py` | Notification fetch + presensi/kuliah helpers |
| `fetch-attendance.py` | Lists classes + presensi status (`available`/`closed`) |
| `attend.py <class_id>` | Submits attendance for an open class |

---

## 6. Reverse-engineering steps

How the presensi endpoints were discovered.

1. **Captured real browser traffic** — the site is a React SPA; a DevTools
   export of a dashboard session surfaced the read-only endpoints
   (`aktif-kuliah`, `kuliah`, `riwayat`, `stat-beranda-mahasiswa`, …) and the
   exact request shapes (POST bodies, query params, cookies). It did **not**
   include the attendance submit because no one clicked the Presensi button
   during the capture.

2. **Found the SPA bundle** — `GET /mahasiswa/beranda` returns an HTML shell:
   ```html
   <script type="module" crossorigin src="/assets/index-DrvHQLU0.js"></script>
   ```
   The asset filename is **content-hashed** and changes on every deploy, so
   always re-read the shell first to get the current name.

3. **Downloaded the bundle**:
   `curl -s -o ethol-bundle.js https://ethol.pens.ac.id/assets/index-<hash>.js`

4. **Grepped for API path strings** — biased toward `presensi`:
   ```
   grep -o -E '"/api/[a-z0-9/_-]*"' ethol-bundle.js | sort -u
   grep -o -E 'presensi/[a-z0-9/_-]+' ethol-bundle.js | sort -u
   ```
   Minified bundles inline endpoint strings; they show up even when built via
   functions, so both quoted strings and bare fragments are greppable.

5. **Reconstructed the API service object** — the bundle groups all presensi
   calls in one object literal (`xt = { riwayat:…, aktifKuliah:…, buka:…,
   mahasiswaPresensi: e => me.post("/presensi/mahasiswa", e), … }`). Extracting
   that object literally enumerated every endpoint + HTTP verb at once.

6. **Found the exact submit payload** — searched for call sites of
   `mahasiswaPresensi(`. The SPA click handler reveals the body keys:
   ```
   mahasiswaPresensi({kuliah, jenis_schema, mahasiswa, key, kuliah_asal})
   ```
   and shows the `key` comes from the `open == 1` entry of `aktifKuliah(...)`,
   with `mahasiswa = n.nomor` (JWT payload number).

7. **Validated live** — implemented `fetch-attendance.py` / `attend.py` and ran
   them against the real API: `aktif-kuliah` returned the expected shape and the
   history confirmed the earlier manual attendance (`key == PflTTQVzgO`).

### Gotchas discovered
- Asset bundle filename is **content-hashed / changes per deploy** (old hashes
  404). Always fetch the current shell HTML first.
- The DevTools export only covers the loading session — interactions (button
  clicks) are not captured unless you record them.
- `GET /api/auth/config` is the reliable source for the active year/semester.