# Evarian Supplier Outreach Log

Date: 2026-06-07

Purpose: record which travel inventory partners were contacted or attempted for
Evarian's agentic travel booking backend. This log separates completed outreach
from partner flows that require legal/account setup, accreditation, CAPTCHA, or
manual owner input.

## Submitted / Sent

| Partner | Route | Status | Notes |
| --- | --- | --- | --- |
| Duffel | Contact sales form | Submitted | Official contact form accepted. Asked for Flights API, Stays, order management, cancel/modify, sandbox, production, payment-compatible flow, and commercial terms. |
| Expedia Rapid API | Rapid API partner form | Submitted | Form completed with pre-volume U.S. AI travel platform details. The form disappeared after submission but did not show a visible thank-you message. |
| Amadeus | Contact Sales Metasearch form | Submitted | Confirmation displayed: "Thank you for getting in touch! We have received your information." Product selected: Amadeus Selling Platform Connect. Marketing consent left unchecked. |
| Travelfusion | Gmail to `sales@travelfusion.com` | Sent | Asked for XML/Fast API access for flight/LCC/NDC/hotel search, booking, order management, cancellation/modification, sandbox, production, and commercial terms. |
| RateHawk / Emerging Travel | Gmail to `tpp@emergingtravel.com`, `affiliate@emergingtravel.com` | Sent | Asked for hotel API inventory, live rates, booking, post-booking servicing, net-rate/partner economics, sandbox, and production onboarding. |

## Filled But Blocked / Manual Handoff

| Partner | Route | Status | Blocker / next step |
| --- | --- | --- | --- |
| WebBeds | Buyer registration form | Filled, submit failed | Page returned "An error has occurred. Please try again." Likely invisible CAPTCHA or partner-site validation issue. Manual retry recommended. |
| Travelport | Get Travelport form | Filled, submit attempted | Submit state remained stuck on "Form is submitting." Manual retry recommended from the open handoff tab. |
| Sabre agency sales | Sabre agency form | Blocked | Required IATA/ARC field rejected truthful "Not yet accredited." Do not fake an IATA/ARC number. Use consolidator or accreditation path first. |
| Sabre Developer Partner | Partner Hub form | Manual | Multi-step flow requires company address and terms review. Leave for owner/legal input. |
| Priceline Partner Solutions | Become a Partner form | Filled, blocked | API intake filled with honest pre-launch volume. Submit button remained disabled, likely due reCAPTCHA/site-owner configuration. Manual retry or direct contact needed. |

## Not Submitted

| Partner | Route | Reason |
| --- | --- | --- |
| Hotelbeds / HBX APItude | Developer registration | Requires account creation, password, and portal terms. Manual owner action required. |
| Booking.com Demand API | Affiliate/CJ route | Signup routes through CJ account creation and partner terms. Manual owner action required. |
| Agoda | Partner signup | Partner-type selector/signup flow requires manual owner/account input. |
| Trip.com | Affiliate/Open Platform | Signup opens Trip.com account registration and terms flow. Manual owner action required. |
| Skyscanner Travel API | API application | Not submitted because the page states a minimum 100K monthly active users expectation and excludes low-traffic websites. Treat as later-stage API target or affiliate fallback. |
| ARC | Agency accreditation | Formal accreditation/legal process. Requires owner/legal input. |
| IATA / IATAN | Agency accreditation | Formal accreditation/legal process. Requires owner/legal input. |

## Recommended Follow-Up Order

1. Watch for replies from Duffel, Expedia Rapid, Amadeus, Travelfusion, and RateHawk.
2. Manually retry WebBeds, Travelport, and Priceline from a clean browser session.
3. Decide whether to create owner-controlled accounts for Hotelbeds, Booking.com/CJ, Agoda, and Trip.com.
4. For Sabre/Travelport direct agency-grade booking, choose a consolidator path first or begin ARC/IATA/IATAN accreditation.
5. Do not apply to Skyscanner Travel API until Evarian can truthfully show meaningful audience traction or a strong enough pre-developed partner case.

