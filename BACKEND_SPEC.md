# Tamakkan Backend Specification

**Status:** draft for team review
**Owner:** Samar (Jetson / perception backend)
**Audience:** frontend team, database/server team
**Purpose:** the authoritative contract for what the Jetson backend emits and
expects. Frontend and DB align to _this_. Where the current app diverges, the
required changes are listed explicitly in §7.

---

## 1. Architecture in one paragraph

A camera feeds the Jetson Orin NX. The Jetson runs the perception pipeline
(5 models) + 4 detectors + an alert engine. During a drive it pushes
**real-time alerts** and the **live speed limit** to the phone over a
WebSocket; the phone speaks the alerts (its own TTS) and displays the speed
limit. The Jetson is **stateless across sessions** — it produces this
session's events + a per-session score, then forgets. All **history and
cross-session aggregates** (the running score, "sessions this week", the
trips list) live in the **team's database/server**, not the Jetson.

```
camera → Jetson [models → detectors → alert engine → session state]
                    │  live (WebSocket)            │ on session end
                    ▼                              ▼
              phone: speak alert,           SessionSummary →
              show speed limit              team DB (history, totals)
```

---

## 2. What the system actually detects (the real taxonomy)

This is non-negotiable: the system can only report what its sensors support.
There is **no IMU**, **no driver-facing camera**, and **no vehicle-speed
source**. Therefore harsh-braking, harsh-acceleration, speeding, phone-use,
and drowsiness are **not detectable** and must not appear as mistake types.

### 2.1 Mistake / event types (`event_type`)

| `event_type`     | Meaning                                          | Severity emitted  |
| ---------------- | ------------------------------------------------ | ----------------- |
| `lane_departure` | Sustained drift out of lane (not a clean change) | `medium`          |
| `tailgating`     | Following the vehicle ahead too closely          | `high`            |
| `red_light`      | Approaching/!running a red light (see subtype)   | `high`/`critical` |
| `near_miss`      | Something close and rapidly closing              | `high`/`critical` |

`red_light` carries a `subtype`: `ahead` (a red light is ahead — warning) or
`ran` (the vehicle passed a red — violation, higher severity).

`near_miss` carries `is_vru` (true if a pedestrian / vulnerable road user —
higher priority and a distinct spoken message).

Speed-limit reading is **NOT** a mistake. It is live informational state
(see §4).

---

## 3. Real-time channel — WebSocket

**Endpoint:** `ws://<jetson-ip>:8000/ws/session/{session_id}`
Opened by the app when a session starts, closed when it stops.

The backend pushes JSON messages. Every message has a `kind`.

### 3.1 Alert message (speak this)

```json
{
  "kind": "alert",
  "event_type": "tailgating",
  "subtype": null,
  "severity": "high",
  "is_vru": false,
  "message_en": "Following too closely — increase your distance",
  "timestamp": 1716200000.123,
  "session_time_s": 42.5
}
```

- The phone speaks only english `message_en (its own TTS). The backend already produces both strings.
- `session_time_s` = seconds since session start (used by the summary too).
- The backend has already applied prioritization + cooldown: **at most one
  alert at a time**, never a burst. The phone just speaks what arrives.

### 3.2 Speed-limit update (display this)

```json
{ "kind": "speed_limit", "limit_kmh": 80, "timestamp": 1716200000.5 }
```

Sent only when the limit **changes** (a new sign was read). The app shows the
latest value persistently until the next update. `limit_kmh` may be `null`
if no limit has been read yet this session.

### 3.3 Session status (optional, lifecycle)

```json
{ "kind": "status", "state": "active", "timestamp": 1716200000.0 }
```

`state` ∈ `active` | `ended`. Lets the app react if the Jetson stops.

---

## 4. Live speed-limit state

The pipeline holds `current_speed_limit` (km/h or `null`). It updates only
when OCR confidently reads a new limit sign; otherwise it persists. It is
pushed live (§3.2) and also included in the session summary's metadata. This
is **separate from mistakes** — there is no speeding detection.

---

## 5. REST surface

Base: `http://<jetson-ip>:8000`

| Method | Path                     | Body / Params          | Returns                 |
| ------ | ------------------------ | ---------------------- | ----------------------- |
| POST   | `/sessions/start`        | `{ "device_id": str }` | `{ "session_id": str }` |
| POST   | `/sessions/{id}/stop`    | —                      | `SessionSummary`        |
| GET    | `/sessions/{id}/summary` | —                      | `SessionSummary`        |
| GET    | `/health`                | —                      | `{ "status": "ok" }`    |

History / stats / login / trips list (`/sessions/{userId}`, `/stats/{userId}`,
`/auth/login`, `/trips`, `/tips/daily`, `/devices/connect`) are **NOT served
by the Jetson** — they are the team server/DB's responsibility (they need
persistent users + cross-session history the Jetson does not have). The app
already calls these; they just resolve to the team backend, not the Jetson.

---

## 6. SessionSummary (the post-drive result)

Returned by `/sessions/{id}/stop` and `/sessions/{id}/summary`. This is also
the object handed to the team DB for history (see §8).

```json
{
  "session_id": "s_1716200000",
  "started_at": "2026-05-19T17:00:00Z",
  "ended_at": "2026-05-19T17:32:10Z",
  "duration_seconds": 1930,
  "score": 4.2,
  "score_label": "GOOD",
  "event_counts": {
    "lane_departure": 3,
    "tailgating": 1,
    "red_light": 1,
    "near_miss": 0
  },
  "events": [
    {
      "event_type": "lane_departure",
      "subtype": null,
      "severity": "medium",
      "is_vru": false,
      "session_time_s": 120.4,
      "timestamp": 1716200120.4
    },
    {
      "event_type": "red_light",
      "subtype": "ran",
      "severity": "critical",
      "is_vru": false,
      "session_time_s": 410.0,
      "timestamp": 1716200410.0
    }
  ],
  "metadata": { "speed_limits_seen": [80, 100], "model_fps_avg": 14.6 }
}
```

`score_label` ∈ `EXCELLENT` | `GOOD` | `IMPROVING` | `NEEDS WORK`
(matches the app's existing `ScoreLabel` and its `getScoreLabel` thresholds:
≥90%→EXCELLENT, ≥75→GOOD, ≥60→IMPROVING, else NEEDS WORK, on a 0–5 scale).

### 6.1 Per-session scoring (Jetson-side, isolated, replaceable)

Start at 5.0, subtract weighted penalties, clamp to [0, 5]:

| event             | penalty each |
| ----------------- | ------------ |
| `near_miss`       | 1.0          |
| `red_light` ran   | 1.0          |
| `tailgating`      | 0.5          |
| `red_light` ahead | 0            |
| `lane_departure`  | 0.4          |

These weights are a **starting point**, isolated in one function
(`session_state.compute_score`). The DB team may instead compute their own
score from `events[]` — both are supported; the Jetson always provides one so
the system works standalone. **Cross-session totals / running score are the
DB's job, not the Jetson's.**

---

## 7. REQUIRED FRONTEND CHANGES

The current app (`src/types/index.ts`, `src/services/api.ts`) diverges from
what the system can produce. Needed:

1. **Fix `MistakeType`.** Replace the current 7-value union with the real
   taxonomy:
   `'lane_departure' | 'tailgating' | 'red_light' | 'near_miss'`
   - **Add:** `red_light`, `near_miss`
   - **Remove:** `harsh_braking`, `harsh_acceleration`, `speeding`,
     `phone_use`, `drowsiness` (no sensors for these — they can never fire)
   - **Keep:** `lane_departure`, `tailgating`
     Update any type→label/icon/color lookup on the summary screen accordingly.

2. **Add a live speed-limit display.** A field on the session screen that
   shows the current limit and updates from the `speed_limit` WebSocket
   message. This is informational, separate from the mistakes list. Not in
   the current types at all.

3. **Add a WebSocket client.** The app is currently REST-only (`api.ts` is
   pure axios). Real-time voice alerts require a WebSocket opened on session
   start to `ws://<jetson>:8000/ws/session/{id}`, handling `alert`,
   `speed_limit`, `status` messages, closed on session stop. React Native's
   built-in `WebSocket` is sufficient — small addition, but new.

4. **No change needed** to: the REST endpoint structure, the
   `DrivingSession` / score / `scoreLabel` shapes (the per-session score,
   timestamped mistakes list, and labels are compatible), or the
   mock-fallback pattern (keep it — good for parallel dev).

---

## 8. TEAM DECISIONS (not resolved — flagging, not assuming)

1. **Session-end data flow.** When a drive ends the Jetson produces a
   `SessionSummary`. Who delivers it to the persistent DB?
   - **Option A (recommended):** the app receives the summary from
     `/sessions/{id}/stop`, then POSTs it to the team server (the app already
     orchestrates start/stop and already has an `endTrip` call pattern). The
     Jetson stays fully decoupled from the team server. we will go with option A

2. **Auth.** Login/users live in the team backend. Does the Jetson need to
   know the user at all, or does the app attach the user when forwarding the
   summary (Option A makes this clean — Jetson never sees users)? yes never sees the user

3. **Device pairing.** `/devices/connect` + Wi-Fi (`192.168.4.1`) — confirm
   whether the Jetson is the Wi-Fi AP the phone joins, and whether device
   connect is a real handshake or just the app remembering an SSID. using ssid not wifi is better

---

## 9. Build order (backend)

1. `events.py` — `Alert`, `SessionEvent`, `SessionSummary`, enums (this spec
   in code form).
2. `session_state.py` — live speed limit, event log, `compute_score`.
3. `alert_engine.py` — prioritize simultaneous detector events → one alert;
   cross-detector cooldown.
4. `pipeline.py` — orchestrate models → detectors → alert engine → session
   state; frame cadence (reuse-last on skipped frames); per-frame result +
   end-of-session summary.
5. `server/app.py` — FastAPI: REST (§5) + WebSocket (§3) over the pipeline.
   Built after the §8 decisions where they affect it.

Internal pieces (1–4) are contract-stable and not blocked by §7/§8. The
server (5) depends lightly on §8.
