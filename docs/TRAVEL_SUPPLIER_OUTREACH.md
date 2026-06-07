# Evarian Travel Supplier Outreach

Objective: establish a real airline and hotel fare backend that gives Evarian broad selection, competitive pricing, bookable inventory, post-booking servicing, and a clear margin path.

## Recommended Partner Sequence

### 1. Apply first: fastest route to bookable inventory

| Partner | Use | Why it matters | Economics | Apply/contact |
| --- | --- | --- | --- | --- |
| Duffel | Flights, stays, ancillaries, order management | Fastest practical route for Evarian to sell flights without waiting for ARC/IATA accreditation. Duffel managed content can use their accreditation and ticketing authority. | Markup on flights, accommodation profit-share, ancillary revenue; watch confirmed-order and managed-content fees. | [Sign up](https://duffel.com/new-to-selling-flights), [Contact sales / Stays access](https://duffel.com/contact-us/), [Pricing](https://duffel.com/pricing) |
| Expedia Rapid API | Lodging inventory and hotel booking | Strong primary hotel rail: large global lodging supply, property/room content, competitive and commissionable rates, booking and post-booking path. | Commissionable/differentiated rates; high hotel margin potential. | [Rapid API](https://partner.expediagroup.com/en-us/solutions/build-your-travel-experience/rapid-api), [Join Expedia Group](https://partner.expediagroup.com/en-us/join-us), [Developer setup](https://developers.expediagroup.com/rapid/setup?locale=en_US) |
| Booking.com Demand API | Accommodation, car rentals, future connected-trip services | Strong customer recognition and large accommodation inventory. Supports search, availability, order creation, cancellation, modify, messaging, and reporting for approved affiliate partners. | Affiliate/partner commission; access depends on managed affiliate approval. | [Demand API docs](https://developers.booking.com/demand/docs), [Demand API reference](https://developers.booking.com/demand/docs/open-api/demand-api), [Prerequisites](https://developers.booking.com/demand/docs/getting-started/prerequisites) |
| Agoda Partner API | Hotels, especially Asia pricing | Useful price comparison and booking rail. Offers affiliate/MSE, Agoda-assisted booking, and partner-fulfillment models. | Tiered affiliate commission and/or partner model economics. | [Agoda affiliate signup](https://partners.agoda.com/), [Agoda API getting started](https://partners.agoda.com/DeveloperPortal/APIDoc/GettingStarted) |
| Trip.com Affiliate / Open Platform | Hotels, flights, rail, attractions | Good breadth for global travel and Asia/Europe coverage. Affiliate route is easier; Open Platform can support deeper accommodation connectivity. | Up to stated affiliate commission on Trip.com partner page; deeper API economics by contract. | [Affiliate program](https://www.trip.com/partners/index/?locale=en_xx), [Open platform](https://connect.trip.com/) |

### 2. Apply in parallel: margin and selection expansion

| Partner | Use | Why it matters | Economics | Apply/contact |
| --- | --- | --- | --- | --- |
| Hotelbeds / HBX APItude | Bedbank hotels, content, booking, cancellations | Important wholesale hotel inventory and net-rate source. Useful for better margins and non-OTA rates. | Net rates / wholesale margin by contract. | [APItude](https://discover.hotelbeds.com/products-and-services/services-for-distributors/apitude), [Developer portal](https://developer.hotelbeds.com/), [Booking API](https://developer.hotelbeds.com/documentation/hotels/booking-api/) |
| RateHawk | B2B hotels | Very broad inventory and fast API onboarding path for travel professionals; useful for net rates and destination breadth. | Net rates or partner model; margin set by Evarian. | [RateHawk API](https://www.ratehawk.com/lp/en/API/) |
| WebBeds | B2B hotel marketplace | Adds directly contracted and third-party hotel supply; API or booking-site access for approved travel buyers. | Net rates / trade buyer model. | [Partner with WebBeds](https://www.webbeds.com/forms/), [Buyer solutions](https://www.webbeds.com/buyers/solutions/) |
| Priceline Partner Solutions | Hotel API, private label, deep linking | Useful for U.S. hotel inventory, opaque/package rates, and possible net/commissionable economics. | Net or commissionable rates by contract. | [Become a partner](https://www.travelweb.com/support/), [Priceline Partner Solutions](https://pricelinepartnersolutions.com/) |
| Travelfusion | LCC, NDC, flights, hotels, payment | Strong for LCC/NDC content and automated booking. Relevant once Evarian needs richer airline coverage beyond Duffel/Amadeus. | Contracted API fees and commercial terms. | [XML/Fast API](https://corporate.travelfusion.com/resources/xml-api), email `sales@travelfusion.com` |

### 3. Strategic but slower: GDS and accreditation

| Partner | Use | Why it matters | Economics | Apply/contact |
| --- | --- | --- | --- | --- |
| Amadeus | Flights and hotels; already first supplier rail in backend | Good for search, pricing, hotels, and longer-term booking. Flight Create Orders production requires ticketing/consolidator path. | API usage billing plus agency/consolidator economics. | [Move to production](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/API-Keys/moving-to-production/), [Quick start](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/quick-start/) |
| Sabre | GDS, agency APIs, hotel, booking management | Enterprise-grade air/hotel/car content and post-booking APIs. Good later when Evarian has volume and agency posture. | GDS/agency contract economics. | [Sabre Developer Hub](https://developer.sabre.com/), [Sabre Partner Hub](https://partners.sabre.com/) |
| Travelport | GDS/API suite, air, hotel, car, rail | Broad content and modern TripServices/Universal API paths. Useful for agency-grade supply and corporate travel. | GDS/agency contract economics. | [Travelport APIs](https://www.travelport.com/products/apis), [Travelport developer portal](https://developer.travelport.com/) |
| ARC | U.S. agency accreditation and ticketing authority | Long-term route to better direct economics and credibility for air ticketing in the U.S. | Application/accreditation costs; direct agency economics. | [ARC travel agency participation](https://www2.arccorp.com/products-participation/travel-agencies/agency-participation/) |
| IATA / IATAN | International agency accreditation | Long-term route for airline relationships, BSP, and credibility outside the U.S. | Accreditation fees and settlement obligations. | [IATA travel agent accreditation](https://www.iata.org/en/services/travel-agency-program/accreditation-travel/) |

### 4. Defer until Evarian has more traction

| Partner | Use | Why defer |
| --- | --- | --- |
| Skyscanner Travel API | Flight/hotel metasearch and market-wide pricing | Official criteria indicate commercial selection and large-audience expectations; useful later for distribution/search, not first-party booking. [Apply](https://www.partners.skyscanner.net/contact/travel-api) |

## Best Backend Combination

Start with:

1. Duffel for flight booking and early stays.
2. Expedia Rapid as the primary hotel backend.
3. Booking.com Demand API, Agoda, and Trip.com in parallel for price comparison, affiliate fallback, and market coverage.
4. Hotelbeds, RateHawk, WebBeds, and Priceline for wholesale/net-rate hotel margin.
5. Keep Amadeus live for search now; request production and Flight Create Orders only after consolidator/ticketing path is clear.
6. Pursue ARC/IATA/GDS when there is enough volume to justify compliance, settlement, and support obligations.

This gives Evarian the right mix: fastest launch, broad selection, hotel margin, and an eventual path to agency-grade control.

## Standard Outreach Copy

Subject: Evarian API partnership request for agentic travel booking

Hello,

I’m building Evarian, an agentic travel booking platform at https://drinknile.com.

The product turns a traveler’s request into a structured trip order, compares flights and hotels, verifies total trip value, asks for approval before payment or supplier-side actions, and then monitors the trip for changes, disruption, cancellation windows, and recovery.

We are looking for production access to search, price, book, cancel, modify, and retrieve order details through your API. The first launch market is the United States, with international expansion planned after the initial pilot.

What we need:

- flight and/or hotel search
- live pricing and availability
- booking/order creation
- cancellation and modification support
- post-booking status and supplier references
- payment or virtual-card compatible flow
- commercial model details: commission, net rates, markup, fees, and volume tiers
- sandbox credentials and production approval requirements

Current stage: early product launch / pilot. We are ready to integrate sandbox credentials and can provide technical details, compliance workflow, and expected use cases.

Please route us to the correct API, partnerships, or business development contact.

Best,
Simon

## Application Form Answers To Reuse

- Company/product: Evarian
- Website: https://drinknile.com
- Category: Agentic travel booking / AI travel platform / online travel agency technology
- Primary market: United States first
- Product needed: API, search, booking, post-booking management
- Customer flow: traveler makes one request; Evarian compares options; traveler approves exact supplier action before booking/payment/cancel/rebook
- Current volume: early pilot / pre-volume
- Target customer: premium leisure travelers, frequent travelers, business travelers, later corporate travel
- Required support: sandbox credentials, production approval path, commercial model, cancellation/modification requirements
- Compliance posture: no irreversible supplier action without logged traveler approval unless explicit scoped autopilot permission exists

