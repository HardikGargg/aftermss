# AfterMess

Unused leftover from a mess, carried to a nearby NGO. The food is free. A rider takes it, and the NGO pays only the rider on UPI.

**Live app:** [https://aftermess.onrender.com/app](https://aftermess.onrender.com/app)

Messes, NGOs, and riders register on the site. People only see and match with others within 10 km. Lunch and dinner are separate sittings. Safety checks and plate matching stay in Python. A model, when configured, may parse messy text. It cannot override a safety refusal.

License: Apache-2.0 (`LICENSE`). Do not commit `.env`.

## A sitting

1. The NGO asks for a number of plates and says whether they take veg only, non-veg only, or either.
2. The mess releases unused food that was never served, with the dish name, veg or non-veg, temperature, prep time, use-by time, and confirmation that it is packed and insulated. Or the mess says there is no leftover.
3. AfterMess matches `min(need, leftover)` inside 10 km. If several NGOs qualify, the one that can be filled most is matched first. Unsafe food is refused.
4. The nearest free rider is asked. Cancel offers the trip to the next nearest rider.
5. The rider marks picked up, then dropped off. The NGO confirms receipt, pays the rider on UPI, and marks the trip paid.

When the NGO confirms receipt, AfterMess writes an FSSAI Schedule II row for that mess. The mess dashboard shows the running total of plates actually handed over and those rows. That is the evidence a campus can use for Eat Right Campus Sustainable Food item 7 (surplus that is still safe was shared). It is not a cash payment, an 80G deduction, or a CSR credit.

## Demo accounts

Register these on the live site if sign-in says the phone is unknown. A free Render instance sleeps after 15 minutes and drops local accounts when it wakes.

| Who | Name | Phone | PIN | Area |
| --- | --- | --- | --- | --- |
| Mess | IIITD Mess | 9811100001 | 1111 | IIIT Delhi |
| NGO | Govindpuri Kitchen | 9811100002 | 2222 | Govindpuri |
| Rider | Campus Rider | 9811100003 | 3333 | Kalkaji |

Stay on **Lunch**. NGO asks first, then the mess releases, then the rider accepts, picks up, and drops off. The NGO confirms receipt and marks the rider paid. The rider UPI id is `campus@oksbi`.

## Run locally

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest tests.test_aftermess tests.test_platform
python -m aftermess webhook --host 127.0.0.1 --port 8099
```

Open http://127.0.0.1:8099/app

## Layout

- `aftermess/` — accounts, nearby match, safety gate, trip loop, site, optional WhatsApp webhook
- `data/aftermess/directory.json` — closed campus list used by the keyword tools
- `data/aftermess/config.json` — clocks, timeouts, and trip rupees. Null means the value is unset
- `tests/` — parse, safety, match, signup, and the HTTP demo

Accounts and the sitting ledger are `accounts.json` and `runtime.json` under `data/aftermess/`. They are gitignored.

## Deploy

The live service is a Render web service on the free plan.

- Build: `pip install -r requirements.txt`
- Start: `python -m aftermess webhook --host 0.0.0.0 --port $PORT`

No environment variables are required for the website. Copy `.env.example` to `.env` only for a model (`python -m aftermess run`) or for live WhatsApp (`meta` or `twilio`). Set `AFTERMESS_S3_BUCKET` if sitting state should survive a restart.
