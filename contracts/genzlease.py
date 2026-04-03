# v0.2.16
# {
#   "Seq": [
#     { "Depends": "py-lib-genlayer-embeddings:09h0i209wrzh4xzq86f79c60x0ifs7xcjwl53ysrnw06i54ddxyi" },
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }

import numpy as np
from genlayer import *
import json
import typing
from dataclasses import dataclass
import genlayer_embeddings as gle





# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
 
class VerificationStatus:
    UNVERIFIED  = 0   # Not yet checked
    PENDING     = 1   # Verification in progress
    VERIFIED    = 2   # HMLR confirmed ownership
    FAILED      = 3   # HMLR rejected — owner mismatch or encumbrance found
    EXPIRED     = 4   # Verification older than 90 days — must re-verify
 
class ListingStatus:
    DRAFT       = 0   # Created but verification not complete
    ACTIVE      = 1   # Verified and available to rent
    PAUSED      = 2   # Owner temporarily paused
    RENTED      = 3   # Currently under an active lease
    DISPUTED    = 4   # Dispute in progress
    DELISTED    = 5   # Permanently removed
 
class LeaseStatus:
    PENDING     = 0   # Offer made, awaiting landlord acceptance
    ACTIVE      = 1   # Deposit paid, keys handed over
    COMPLETED   = 2   # Lease ended, funds released
    DISPUTED    = 3   # Dispute raised by either party
    CANCELLED   = 4   # Cancelled before start date
    REFUNDED    = 5   # Deposit returned after dispute resolution
 
class DisputeOutcome:
    UNRESOLVED       = 0
    FAVOUR_TENANT    = 1   # Full deposit returned
    FAVOUR_LANDLORD  = 2   # Landlord keeps deposit
    SPLIT            = 3   # AI decides percentage split
 
 

# ─────────────────────────────────────────────
# Storage structs
# ─────────────────────────────────────────────
 
@allow_storage
@dataclass
class PropertyListing:
    """
    A UK property listed for lease on GenZLease.
    The listing is only ACTIVE after HMLR verification confirms
    the landlord genuinely owns the title.
    """
    listing_id:           str       # UUID: "{owner_addr}:{title_number}"
    title_number:         str       # UK Land Registry title number (e.g. "GR506405")
    owner:                Address   # GenLayer address of the landlord
    owner_full_name:      str       # Must match HMLR proprietor name exactly
    property_address:     str       # Full registered address
    postcode:             str       # UK postcode
 
    # Listing terms (Airbnb-style)
    price_per_month:      u256      # in wei (USDC/ETH equivalent)
    min_duration_months:  u32       # minimum lease period
    max_duration_months:  u32       # maximum lease period
    deposit_months:       u32       # how many months' rent as deposit (typically 1-2)
    available_from:       u256      # unix timestamp
    available_to:         u256      # unix timestamp (0 = indefinite)
 
    # Property details
    bedrooms:             u32
    bathrooms:            u32
    property_type:        str       # "flat", "house", "studio", etc.
    description:          str
    amenities:            str       # JSON array: ["parking", "garden", "pets_allowed"]
    images_ipfs:          str       # JSON array of IPFS CIDs
 
    # Verification
    verification_status:  u8        # VerificationStatus
    verified_at:          u256      # timestamp of last successful HMLR check
    hmlr_tenure:          str       # "freehold" or "leasehold" from HMLR
    encumbrances_found:   bool      # true if HMLR reported any charges/restrictions
    verification_notes:   str       # AI summary of HMLR response
 
    # Status
    listing_status:       u8        # ListingStatus
    created_at:           u256
    updated_at:           u256
    active_lease_id:      str       # "" if no active lease
    total_leases:         u32
    total_revenue:        u256
 
 
@allow_storage
@dataclass
class LeaseAgreement:
    """
    A lease agreement between a landlord (listing owner) and a tenant.
    Funds are held in escrow until completion or dispute resolution.
    """
    lease_id:             str       # UUID: "{listing_id}:{tenant_addr}:{start_ts}"
    listing_id:           str
    landlord:             Address
    tenant:               Address
 
    # Agreed terms
    start_date:           u256      # unix timestamp
    end_date:             u256      # unix timestamp
    duration_months:      u32
    monthly_rent:         u256      # agreed rate (locked at booking time)
    total_rent:           u256      # monthly_rent * duration_months
    deposit_amount:       u256      # held in escrow
    total_paid:           u256      # total funds sent by tenant
 
    # Escrow
    escrow_balance:       u256      # current held amount
    rent_paid_to:         u256      # timestamp of last rent payment period covered
    next_payment_due:     u256      # unix timestamp
 
    # Status
    status:               u8        # LeaseStatus
    created_at:           u256
    activated_at:         u256      # when landlord accepted + tenant paid deposit
    completed_at:         u256
    cancelled_at:         u256
 
    # Dispute
    dispute_raised_by:    Address   # who raised it (Address(0) if none)
    dispute_reason:       str
    dispute_raised_at:    u256
    dispute_outcome:      u8        # DisputeOutcome
    dispute_evidence_urls: str      # JSON array
    landlord_split_bps:   u32       # basis points going to landlord after dispute (0-10000)
    ai_reasoning:         str       # AI's dispute resolution reasoning
 
 
@allow_storage
@dataclass
class DisputePrecedent:
    """Stored in VecDB for semantic similarity — AI learns from past disputes."""
    dispute_summary:      str
    outcome:              u8        # DisputeOutcome
    landlord_split_bps:   u32
    reasoning:            str
    listing_id:           str
    lease_id:             str
    resolved_at:          u256
 
 
@allow_storage
class TenantProfile:
    """On-chain reputation for tenants."""
    tenant:               Address
    total_leases:         u32
    completed_leases:     u32
    disputed_leases:      u32
    disputes_won:         u32
    total_spent:          u256
    reputation_score:     u32       # 0-100, updated after each lease
    joined_at:            u256
 
 
@allow_storage
class LandlordProfile:
    """On-chain reputation for landlords."""
    landlord:             Address
    total_listings:       u32
    verified_listings:    u32
    total_leases:         u32
    completed_leases:     u32
    disputed_leases:      u32
    total_revenue:        u256
    reputation_score:     u32       # 0-100
    joined_at:            u256
 




# ─────────────────────────────────────────────
# Main contract
# ─────────────────────────────────────────────
 
class GenZLease(gl.Contract):
    """
    GenZLease — AI-Verified Property Leasing on GenLayer
 
    Flow:
      1. list_property()        — Landlord lists with HMLR title number + name
      2. verify_ownership()     — GenLayer fetches HMLR API, AI confirms ownership
                                   Sets listing ACTIVE or FAILED
      3. request_lease()        — Tenant makes offer for date range + duration
      4. accept_lease()         — Landlord accepts; tenant pays deposit + first month
      5. activate_lease()       — Both confirm; lease goes ACTIVE
      6. pay_rent()             — Tenant pays monthly rent into escrow
      7. release_rent()         — Landlord claims due rent after each month
      8. complete_lease()       — Tenant vacates; deposit released automatically
      9. raise_dispute()        — Either party raises dispute with evidence URLs
     10. resolve_dispute()      — AI analyses evidence, splits escrow fairly
 
    Revenue: platform_fee_bps (default 200 = 2%) on every transaction
    """
 
    # ── Platform parameters ───────────────────────────────────────────
    owner:                    Address
    platform_fee_bps:         u32      # 200 = 2%
    verification_validity:    u256     # seconds before re-verify needed (90 days default)
    paused:                   bool
 
    # ── HMLR API config ───────────────────────────────────────────────
    hmlr_base_url:            str      # "https://businessgateway.landregistry.gov.uk/b2b"
    hmlr_api_key:             str      # stored securely, never returned in views
 
    # ── Listings ─────────────────────────────────────────────────────
    listings:                 TreeMap[str, PropertyListing]
    listing_ids:              DynArray[str]
    owner_listings:           TreeMap[str, DynArray[str]]   # addr_str → listing_ids
    title_to_listing:         TreeMap[str, str]              # title_number → listing_id
 
    # ── Leases ───────────────────────────────────────────────────────
    leases:                   TreeMap[str, LeaseAgreement]
    lease_ids:                DynArray[str]
    listing_leases:           TreeMap[str, DynArray[str]]   # listing_id → lease_ids
    tenant_leases:            TreeMap[str, DynArray[str]]   # addr_str → lease_ids
 
    # ── Profiles ─────────────────────────────────────────────────────
    tenant_profiles:          TreeMap[Address, TenantProfile]
    landlord_profiles:        TreeMap[Address, LandlordProfile]
 
    # ── Financials ───────────────────────────────────────────────────
    total_escrow:             u256
    total_fees_collected:     u256
    accumulated_platform_fees: u256
 
    # ── Dispute memory (VecDB) ────────────────────────────────────────
    dispute_precedents:       gle.VecDB[np.float32, typing.Literal[384], DisputePrecedent]
    total_precedents:         u32
 
    # ── Stats ─────────────────────────────────────────────────────────
    total_listings:           u32
    total_leases_created:     u32
    total_leases_completed:   u32
    total_disputes:           u32
 
 
    # ─────────────────────────────────────────────────────────────────
    # Constructor
    # ─────────────────────────────────────────────────────────────────
 
    def __init__(
        self,
        platform_fee_bps:      u32  = u32(200),
        verification_validity: u256 = u256(7776000),   # 90 days
        hmlr_base_url:         str  = "https://businessgateway.landregistry.gov.uk/b2b",
        hmlr_api_key:          str  = "",
    ):
        self.owner                    = gl.message.sender_address
        self.platform_fee_bps         = platform_fee_bps
        self.verification_validity    = verification_validity
        self.hmlr_base_url            = hmlr_base_url
        self.hmlr_api_key             = hmlr_api_key
        self.paused                   = False
 
        self.total_escrow             = u256(0)
        self.total_fees_collected     = u256(0)
        self.accumulated_platform_fees = u256(0)
        self.total_precedents         = u32(0)
        self.total_listings           = u32(0)
        self.total_leases_created     = u32(0)
        self.total_leases_completed   = u32(0)
        self.total_disputes           = u32(0)
 



    
    # ═════════════════════════════════════════════════════════════════
    # LAYER 1: PROPERTY LISTING
    # ═════════════════════════════════════════════════════════════════
 
    @gl.public.write
    def list_property(
        self,
        title_number:          str,
        owner_full_name:       str,   # MUST match HMLR register exactly
        property_address:      str,
        postcode:              str,
        price_per_month:       int,   # in wei
        min_duration_months:   int,
        max_duration_months:   int,
        deposit_months:        int,
        available_from:        int,   # unix timestamp
        bedrooms:              int,
        bathrooms:             int,
        property_type:         str,
        description:           str,
        amenities:             str  = "[]",
        images_ipfs:           str  = "[]",
        available_to:          int  = 0,
    ) -> dict[str, typing.Any]:
        """
        Step 1: List a property. Starts in DRAFT state until verify_ownership() is called.
        title_number: UK Land Registry title number (e.g. "GR506405", "TGL12345")
        owner_full_name: exactly as it appears on the title register
        """
        if self.paused:
            raise Exception("Protocol is paused")
        if title_number in self.title_to_listing:
            raise Exception(f"Title {title_number} already listed")
        if min_duration_months < 1 or max_duration_months < min_duration_months:
            raise Exception("Invalid duration range")
        if deposit_months < 1 or deposit_months > 6:
            raise Exception("Deposit must be 1-6 months")
        if price_per_month <= 0:
            raise Exception("Price must be positive")
 
        sender     = gl.message.sender_address
        listing_id = f"{str(sender)}:{title_number}"
        now        = u256(gl.block.timestamp)
 
        listing = PropertyListing(
            listing_id           = listing_id,
            title_number         = title_number,
            owner                = sender,
            owner_full_name      = owner_full_name,
            property_address     = property_address,
            postcode             = postcode,
            price_per_month      = u256(price_per_month),
            min_duration_months  = u32(min_duration_months),
            max_duration_months  = u32(max_duration_months),
            deposit_months       = u32(deposit_months),
            available_from       = u256(available_from),
            available_to         = u256(available_to),
            bedrooms             = u32(bedrooms),
            bathrooms            = u32(bathrooms),
            property_type        = property_type,
            description          = description,
            amenities            = amenities,
            images_ipfs          = images_ipfs,
            verification_status  = u8(VerificationStatus.UNVERIFIED),
            verified_at          = u256(0),
            hmlr_tenure          = "",
            encumbrances_found   = False,
            verification_notes   = "",
            listing_status       = u8(ListingStatus.DRAFT),
            created_at           = now,
            updated_at           = now,
            active_lease_id      = "",
            total_leases         = u32(0),
            total_revenue        = u256(0),
        )
 
        self.listings[listing_id]  = listing
        self.listing_ids.append(listing_id)
        self.title_to_listing[title_number] = listing_id
 
        addr_str = str(sender)
        self.owner_listings[addr_str].append(listing_id)
        self.total_listings = u32(int(self.total_listings) + 1)
 
        # Create landlord profile if needed
        if sender not in self.landlord_profiles:
            self.landlord_profiles[sender] = LandlordProfile(
                landlord=sender, total_listings=u32(1),
                verified_listings=u32(0), total_leases=u32(0),
                completed_leases=u32(0), disputed_leases=u32(0),
                total_revenue=u256(0), reputation_score=u32(70),
                joined_at=now,
            )
        else:
            lp = self.landlord_profiles[sender]
            self.landlord_profiles[sender] = LandlordProfile(
                landlord=lp.landlord,
                total_listings=u32(int(lp.total_listings) + 1),
                verified_listings=lp.verified_listings,
                total_leases=lp.total_leases,
                completed_leases=lp.completed_leases,
                disputed_leases=lp.disputed_leases,
                total_revenue=lp.total_revenue,
                reputation_score=lp.reputation_score,
                joined_at=lp.joined_at,
            )
 
        return {
            "listing_id":          listing_id,
            "title_number":        title_number,
            "status":              "DRAFT",
            "next_step":           "Call verify_ownership() to activate listing",
        }
 
 
    @gl.public.write
    def update_listing_terms(
        self,
        listing_id:          str,
        price_per_month:     int = 0,
        available_from:      int = 0,
        available_to:        int = 0,
        min_duration_months: int = 0,
        max_duration_months: int = 0,
        description:         str = "",
        amenities:           str = "",
        images_ipfs:         str = "",
    ) -> dict[str, typing.Any]:
        """Landlord updates listing terms. Cannot change title_number or address."""
        if listing_id not in self.listings:
            raise Exception("Listing not found")
        l = self.listings[listing_id]
        if l.owner != gl.message.sender_address:
            raise Exception("Only listing owner can update")
        if int(l.listing_status) in [ListingStatus.RENTED, ListingStatus.DISPUTED]:
            raise Exception("Cannot update while rented or disputed")
 
        self.listings[listing_id] = PropertyListing(
            listing_id=l.listing_id, title_number=l.title_number,
            owner=l.owner, owner_full_name=l.owner_full_name,
            property_address=l.property_address, postcode=l.postcode,
            price_per_month=u256(price_per_month) if price_per_month > 0 else l.price_per_month,
            min_duration_months=u32(min_duration_months) if min_duration_months > 0 else l.min_duration_months,
            max_duration_months=u32(max_duration_months) if max_duration_months > 0 else l.max_duration_months,
            deposit_months=l.deposit_months,
            available_from=u256(available_from) if available_from > 0 else l.available_from,
            available_to=u256(available_to) if available_to > 0 else l.available_to,
            bedrooms=l.bedrooms, bathrooms=l.bathrooms,
            property_type=l.property_type,
            description=description if description else l.description,
            amenities=amenities if amenities else l.amenities,
            images_ipfs=images_ipfs if images_ipfs else l.images_ipfs,
            verification_status=l.verification_status, verified_at=l.verified_at,
            hmlr_tenure=l.hmlr_tenure, encumbrances_found=l.encumbrances_found,
            verification_notes=l.verification_notes,
            listing_status=l.listing_status,
            created_at=l.created_at, updated_at=u256(gl.block.timestamp),
            active_lease_id=l.active_lease_id,
            total_leases=l.total_leases, total_revenue=l.total_revenue,
        )
        return {"listing_id": listing_id, "updated": True}
 
 
    # ═════════════════════════════════════════════════════════════════
    # LAYER 2: HMLR OWNERSHIP VERIFICATION (GenLayer AI core)
    # ═════════════════════════════════════════════════════════════════
 
    @gl.public.write
    def verify_ownership(self, listing_id: str) -> dict[str, typing.Any]:
        """
        The heart of GenZLease. Calls HMLR's Online Owner Verification API
        via GenLayer's web access, then uses LLM to interpret the result.
 
        HMLR Online Owner Verification endpoint:
          POST /b2b/EOOV_SoapEngine
          Checks name + address against title register in real time.
          Returns: match result, tenure, registered charges
 
        Anyone can trigger re-verification (useful after 90 days).
        Only the listing owner can list — but verification is permissionless
        so community members or tenants can verify before renting.
        """
        if listing_id not in self.listings:
            raise Exception("Listing not found")
 
        listing = self.listings[listing_id]
 
        # Snapshot for nondet blocks
        title_snap   = listing.title_number
        name_snap    = listing.owner_full_name
        address_snap = listing.property_address
        postcode_snap = listing.postcode
        base_url     = self.hmlr_base_url
 
        def leader_fn() -> dict:
            # ── Step 1: Title search by address ──────────────────────
            # HMLR Title Number Enquiry by Address — REST endpoint
            title_search_url = (
                f"https://api.landregistry.gov.uk/v1/titles?"
                f"address={address_snap.replace(' ', '+')}"
                f"&postcode={postcode_snap.replace(' ', '+')}"
            )
            title_response = gl.nondet.web.request(
                title_search_url,
                method="GET",
            )
 
            title_data = {}
            try:
                title_data = json.loads(title_response.body.decode("utf-8"))
            except Exception:
                title_data = {}
 
            # ── Step 2: Online Owner Verification ────────────────────
            # HMLR Business Gateway — Online Owner Verification
            # Checks if owner_full_name is a registered proprietor of title_number
            # Using the REST-equivalent endpoint (actual SOAP wrapped as REST via BG)
            ooev_url = f"https://api.landregistry.gov.uk/v1/ownership-verification"
            ooev_payload = json.dumps({
                "title_number": title_snap,
                "proprietor_name": name_snap,
                "address": address_snap,
                "postcode": postcode_snap,
            })
            ooev_response = gl.nondet.web.request(
                ooev_url,
                method="POST",
                body={"Content-Type": "application/json", "data": ooev_payload},
            )
 
            ooev_data = {}
            ooev_status = ooev_response.status_code
            try:
                ooev_data = json.loads(ooev_response.body.decode("utf-8"))
            except Exception:
                ooev_data = {}
 
            # ── Step 3: Check for charges / restrictions ──────────────
            # HMLR Title Register summary — public data
            register_url = (
                f"https://api.landregistry.gov.uk/v1/titles/{title_snap}"
            )
            register_response = gl.nondet.web.request(
                register_url,
                method="GET",
            )
            register_data = {}
            try:
                register_data = json.loads(register_response.body.decode("utf-8"))
            except Exception:
                register_data = {}
 
            # ── Step 4: LLM interprets all HMLR responses ────────────
            prompt = f"""You are a UK property law expert verifying ownership for GenZLease,
a blockchain property leasing protocol. Analyse the HMLR responses below and give a verdict.
 
PROPERTY DETAILS SUBMITTED:
- Title number:    {title_snap}
- Claimed owner:   {name_snap}
- Address:         {address_snap}
- Postcode:        {postcode_snap}
 
HMLR TITLE SEARCH RESPONSE (HTTP {title_response.status_code}):
{json.dumps(title_data, indent=2)[:1500]}
 
HMLR OWNER VERIFICATION RESPONSE (HTTP {ooev_status}):
{json.dumps(ooev_data, indent=2)[:1500]}
 
HMLR REGISTER SUMMARY (HTTP {register_response.status_code}):
{json.dumps(register_data, indent=2)[:1200]}
 
ANALYSIS TASKS:
1. Does the title number exist in HMLR's register?
2. Is the claimed owner name a registered proprietor of this title?
   (Allow for minor formatting differences: "John Smith" vs "JOHN SMITH")
3. What is the tenure — freehold or leasehold?
4. Are there any registered charges, restrictions, or encumbrances that
   would prevent the owner from freely leasing the property?
5. Is there any evidence of a fraud alert or disputed ownership?
 
VERDICT RULES:
- verified = true ONLY if: title exists AND owner name matches AND no blocking charges
- verified = false if any condition fails
- encumbrances_found = true if charges/mortgages/restrictions exist (not necessarily blocking)
- blocking_encumbrance = true if a charge PREVENTS leasing (rare — most mortgages allow leasing)
 
Respond ONLY with this JSON:
{{
  "verified": true or false,
  "owner_name_match": true or false,
  "title_exists": true or false,
  "tenure": "freehold" or "leasehold" or "unknown",
  "encumbrances_found": true or false,
  "blocking_encumbrance": true or false,
  "registered_proprietor": "<exact name from register or empty>",
  "confidence": <float 0.0-1.0>,
  "summary": "<2-3 sentence plain English summary>",
  "rejection_reason": "<only if verified=false, else empty string>"
}}"""
 
            raw = gl.nondet.exec_prompt(prompt, response_format='json')
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, str):
                raw = raw.replace("```json","").replace("```","").strip()
                try:
                    return json.loads(raw)
                except Exception:
                    pass
            return {
                "verified": False, "owner_name_match": False,
                "title_exists": False, "tenure": "unknown",
                "encumbrances_found": False, "blocking_encumbrance": False,
                "registered_proprietor": "", "confidence": 0.0,
                "summary": "Verification failed — could not parse HMLR response",
                "rejection_reason": "Parse error in verification response"
            }
 
        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            if "verified" not in leader_result.calldata:
                return False
            try:
                my_result = leader_fn()
                # Validators must agree on the binary verified outcome
                # They may differ on nuance but not on the core yes/no
                return (
                    leader_result.calldata.get("verified") == my_result.get("verified")
                    and leader_result.calldata.get("title_exists") == my_result.get("title_exists")
                )
            except Exception:
                return False
 
        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
 
        verified             = bool(result.get("verified", False))
        tenure               = result.get("tenure", "unknown")
        encumbrances_found   = bool(result.get("encumbrances_found", False))
        blocking_encumbrance = bool(result.get("blocking_encumbrance", False))
        confidence           = float(result.get("confidence", 0.0))
        summary              = result.get("summary", "")
        rejection_reason     = result.get("rejection_reason", "")
 
        # A verified=true with blocking encumbrance is still a fail
        if blocking_encumbrance:
            verified = False
            rejection_reason = f"Blocking encumbrance detected. {rejection_reason}"
 
        now = u256(gl.block.timestamp)
        old = self.listings[listing_id]
 
        new_ver_status = u8(VerificationStatus.VERIFIED if verified else VerificationStatus.FAILED)
        new_lst_status = u8(ListingStatus.ACTIVE if verified else ListingStatus.DRAFT)
 
        self.listings[listing_id] = PropertyListing(
            listing_id=old.listing_id, title_number=old.title_number,
            owner=old.owner, owner_full_name=old.owner_full_name,
            property_address=old.property_address, postcode=old.postcode,
            price_per_month=old.price_per_month,
            min_duration_months=old.min_duration_months,
            max_duration_months=old.max_duration_months,
            deposit_months=old.deposit_months,
            available_from=old.available_from, available_to=old.available_to,
            bedrooms=old.bedrooms, bathrooms=old.bathrooms,
            property_type=old.property_type, description=old.description,
            amenities=old.amenities, images_ipfs=old.images_ipfs,
            verification_status=new_ver_status,
            verified_at=now if verified else u256(0),
            hmlr_tenure=tenure,
            encumbrances_found=encumbrances_found,
            verification_notes=summary,
            listing_status=new_lst_status,
            created_at=old.created_at, updated_at=now,
            active_lease_id=old.active_lease_id,
            total_leases=old.total_leases, total_revenue=old.total_revenue,
        )
 
        # Update landlord profile
        if old.owner in self.landlord_profiles:
            lp = self.landlord_profiles[old.owner]
            self.landlord_profiles[old.owner] = LandlordProfile(
                landlord=lp.landlord,
                total_listings=lp.total_listings,
                verified_listings=u32(int(lp.verified_listings) + (1 if verified else 0)),
                total_leases=lp.total_leases,
                completed_leases=lp.completed_leases,
                disputed_leases=lp.disputed_leases,
                total_revenue=lp.total_revenue,
                reputation_score=lp.reputation_score,
                joined_at=lp.joined_at,
            )
 
        return {
            "listing_id":           listing_id,
            "verified":             verified,
            "tenure":               tenure,
            "encumbrances_found":   encumbrances_found,
            "blocking_encumbrance": blocking_encumbrance,
            "confidence":           confidence,
            "summary":              summary,
            "rejection_reason":     rejection_reason if not verified else "",
            "listing_status":       "ACTIVE" if verified else "DRAFT",
        }
 
 
    # ═════════════════════════════════════════════════════════════════
    # LAYER 3: LEASE LIFECYCLE (Airbnb-style booking flow)
    # ═════════════════════════════════════════════════════════════════
 
    @gl.public.write
    def request_lease(
        self,
        listing_id:       str,
        start_date:       int,   # unix timestamp
        duration_months:  int,
        message_to_landlord: str = "",
    ) -> dict[str, typing.Any]:
        """
        Tenant makes a lease offer. No funds locked yet.
        Landlord must accept within 72 hours or the offer expires.
        """
        if listing_id not in self.listings:
            raise Exception("Listing not found")
        listing = self.listings[listing_id]
 
        if int(listing.listing_status) != ListingStatus.ACTIVE:
            raise Exception("Listing is not active")
        if int(listing.verification_status) != VerificationStatus.VERIFIED:
            raise Exception("Property ownership not verified")
 
        # Check verification hasn't expired (90 days)
        now = gl.block.timestamp
        if int(listing.verified_at) > 0:
            age = now - int(listing.verified_at)
            if u256(age) > self.verification_validity:
                raise Exception("Ownership verification expired — landlord must re-verify")
 
        sender = gl.message.sender_address
        if sender == listing.owner:
            raise Exception("Landlord cannot rent their own property")
        if duration_months < int(listing.min_duration_months):
            raise Exception(f"Minimum duration is {int(listing.min_duration_months)} months")
        if duration_months > int(listing.max_duration_months):
            raise Exception(f"Maximum duration is {int(listing.max_duration_months)} months")
 
        end_date     = start_date + (duration_months * 30 * 24 * 3600)
        total_rent   = int(listing.price_per_month) * duration_months
        deposit      = int(listing.price_per_month) * int(listing.deposit_months)
        lease_id     = f"{listing_id}:{str(sender)}:{start_date}"
 
        if lease_id in self.leases:
            raise Exception("Lease offer already exists for these exact terms")
 
        lease = LeaseAgreement(
            lease_id          = lease_id,
            listing_id        = listing_id,
            landlord          = listing.owner,
            tenant            = sender,
            start_date        = u256(start_date),
            end_date          = u256(end_date),
            duration_months   = u32(duration_months),
            monthly_rent      = listing.price_per_month,
            total_rent        = u256(total_rent),
            deposit_amount    = u256(deposit),
            total_paid        = u256(0),
            escrow_balance    = u256(0),
            rent_paid_to      = u256(0),
            next_payment_due  = u256(start_date),
            status            = u8(LeaseStatus.PENDING),
            created_at        = u256(now),
            activated_at      = u256(0),
            completed_at      = u256(0),
            cancelled_at      = u256(0),
            dispute_raised_by = Address(0),
            dispute_reason    = "",
            dispute_raised_at = u256(0),
            dispute_outcome   = u8(DisputeOutcome.UNRESOLVED),
            dispute_evidence_urls = "[]",
            landlord_split_bps = u32(0),
            ai_reasoning      = "",
        )
 
        self.leases[lease_id] = lease
        self.lease_ids.append(lease_id)
        self.listing_leases[listing_id].append(lease_id)
        self.tenant_leases[str(sender)].append(lease_id)
        self.total_leases_created = u32(int(self.total_leases_created) + 1)
 
        # Create tenant profile if needed
        if sender not in self.tenant_profiles:
            self.tenant_profiles[sender] = TenantProfile(
                tenant=sender, total_leases=u32(1), completed_leases=u32(0),
                disputed_leases=u32(0), disputes_won=u32(0),
                total_spent=u256(0), reputation_score=u32(70),
                joined_at=u256(now),
            )
        else:
            tp = self.tenant_profiles[sender]
            self.tenant_profiles[sender] = TenantProfile(
                tenant=tp.tenant,
                total_leases=u32(int(tp.total_leases)+1),
                completed_leases=tp.completed_leases,
                disputed_leases=tp.disputed_leases,
                disputes_won=tp.disputes_won,
                total_spent=tp.total_spent,
                reputation_score=tp.reputation_score,
                joined_at=tp.joined_at,
            )
 
        return {
            "lease_id":          lease_id,
            "status":            "PENDING",
            "monthly_rent":      str(listing.price_per_month),
            "deposit_required":  str(deposit),
            "total_rent":        str(total_rent),
            "start_date":        start_date,
            "end_date":          end_date,
            "next_step":         "Await landlord acceptance. Then pay deposit + first month.",
        }
 
 
    @gl.public.write
    def accept_lease(self, lease_id: str) -> dict[str, typing.Any]:
        """Landlord accepts a tenant's lease offer."""
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
        if lease.landlord != gl.message.sender_address:
            raise Exception("Only landlord can accept")
        if int(lease.status) != LeaseStatus.PENDING:
            raise Exception("Lease not in pending state")
 
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount, total_paid=old.total_paid,
            escrow_balance=old.escrow_balance,
            rent_paid_to=old.rent_paid_to, next_payment_due=old.next_payment_due,
            status=u8(LeaseStatus.ACTIVE),  # waiting for tenant payment
            created_at=old.created_at, activated_at=u256(gl.block.timestamp),
            completed_at=old.completed_at, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by, dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at, dispute_outcome=old.dispute_outcome,
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=old.landlord_split_bps, ai_reasoning=old.ai_reasoning,
        )
        return {
            "lease_id":       lease_id,
            "status":         "ACCEPTED",
            "next_step":      f"Tenant must pay deposit ({str(old.deposit_amount)}) + first month ({str(old.monthly_rent)})",
        }
 
 
    @gl.public.write.payable
    def pay_deposit_and_first_month(self, lease_id: str) -> dict[str, typing.Any]:
        """
        Tenant pays deposit + first month's rent.
        This activates the lease and marks the property as RENTED.
        Deposit sits in escrow until lease completion.
        First month's rent is releasable by landlord after the month passes.
        """
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
        if lease.tenant != gl.message.sender_address:
            raise Exception("Only tenant can pay")
        if int(lease.status) != LeaseStatus.ACTIVE:
            raise Exception("Lease must be accepted before payment")
 
        required = lease.deposit_amount + lease.monthly_rent
        if gl.message.value < required:
            raise Exception(f"Insufficient payment. Required: {required}")
 
        platform_fee = (gl.message.value * u256(int(self.platform_fee_bps))) // u256(10000)
        self.accumulated_platform_fees = self.accumulated_platform_fees + platform_fee
        self.total_fees_collected      = self.total_fees_collected + platform_fee
 
        into_escrow = gl.message.value - platform_fee
        now         = u256(gl.block.timestamp)
        next_due    = u256(int(lease.start_date) + 30 * 24 * 3600)
 
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount,
            total_paid=u256(int(old.total_paid) + int(gl.message.value)),
            escrow_balance=into_escrow,
            rent_paid_to=old.start_date,
            next_payment_due=next_due,
            status=u8(LeaseStatus.ACTIVE),
            created_at=old.created_at, activated_at=now,
            completed_at=old.completed_at, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by, dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at, dispute_outcome=old.dispute_outcome,
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=old.landlord_split_bps, ai_reasoning=old.ai_reasoning,
        )
 
        # Mark listing as RENTED
        listing = self.listings[old.listing_id]
        self.listings[old.listing_id] = PropertyListing(
            listing_id=listing.listing_id, title_number=listing.title_number,
            owner=listing.owner, owner_full_name=listing.owner_full_name,
            property_address=listing.property_address, postcode=listing.postcode,
            price_per_month=listing.price_per_month,
            min_duration_months=listing.min_duration_months,
            max_duration_months=listing.max_duration_months,
            deposit_months=listing.deposit_months,
            available_from=listing.available_from, available_to=listing.available_to,
            bedrooms=listing.bedrooms, bathrooms=listing.bathrooms,
            property_type=listing.property_type, description=listing.description,
            amenities=listing.amenities, images_ipfs=listing.images_ipfs,
            verification_status=listing.verification_status,
            verified_at=listing.verified_at, hmlr_tenure=listing.hmlr_tenure,
            encumbrances_found=listing.encumbrances_found,
            verification_notes=listing.verification_notes,
            listing_status=u8(ListingStatus.RENTED),
            created_at=listing.created_at, updated_at=now,
            active_lease_id=lease_id,
            total_leases=u32(int(listing.total_leases) + 1),
            total_revenue=listing.total_revenue,
        )
        self.total_escrow = self.total_escrow + into_escrow
 
        return {
            "lease_id":         lease_id,
            "status":           "ACTIVE",
            "escrow_balance":   str(into_escrow),
            "platform_fee":     str(platform_fee),
            "next_payment_due": int(next_due),
            "message":          "Lease is now active. Deposit held in escrow.",
        }
 
 
    @gl.public.write.payable
    def pay_monthly_rent(self, lease_id: str) -> dict[str, typing.Any]:
        """Tenant pays a monthly rent installment into escrow."""
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
        if lease.tenant != gl.message.sender_address:
            raise Exception("Only tenant can pay rent")
        if int(lease.status) != LeaseStatus.ACTIVE:
            raise Exception("Lease is not active")
        if gl.message.value < lease.monthly_rent:
            raise Exception(f"Insufficient. Monthly rent: {lease.monthly_rent}")
 
        platform_fee = (gl.message.value * u256(int(self.platform_fee_bps))) // u256(10000)
        self.accumulated_platform_fees = self.accumulated_platform_fees + platform_fee
        self.total_fees_collected      = self.total_fees_collected + platform_fee
 
        into_escrow = gl.message.value - platform_fee
        now         = u256(gl.block.timestamp)
        new_rent_paid_to = u256(int(lease.rent_paid_to) + 30 * 24 * 3600)
        new_next_due     = u256(int(lease.next_payment_due) + 30 * 24 * 3600)
 
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount,
            total_paid=u256(int(old.total_paid) + int(gl.message.value)),
            escrow_balance=u256(int(old.escrow_balance) + int(into_escrow)),
            rent_paid_to=new_rent_paid_to,
            next_payment_due=new_next_due,
            status=old.status,
            created_at=old.created_at, activated_at=old.activated_at,
            completed_at=old.completed_at, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by, dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at, dispute_outcome=old.dispute_outcome,
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=old.landlord_split_bps, ai_reasoning=old.ai_reasoning,
        )
        self.total_escrow = self.total_escrow + into_escrow
        return {
            "lease_id":         lease_id,
            "amount_paid":      str(gl.message.value),
            "rent_paid_to":     int(new_rent_paid_to),
            "next_due":         int(new_next_due),
        }
 
 
    @gl.public.write
    def claim_rent(self, lease_id: str) -> dict[str, typing.Any]:
        """
        Landlord claims rent for completed months from escrow.
        Only months that have fully elapsed can be claimed.
        Deposit is NOT claimable via this function.
        """
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
        if lease.landlord != gl.message.sender_address:
            raise Exception("Only landlord can claim rent")
        if int(lease.status) != LeaseStatus.ACTIVE:
            raise Exception("Lease must be active to claim")
 
        now          = gl.block.timestamp
        claimable    = u256(0)
        months_due   = 0
 
        # Count months elapsed since last claim
        check_ts = int(lease.start_date)
        while check_ts + 30 * 24 * 3600 <= now and check_ts < int(lease.rent_paid_to):
            claimable  = claimable + lease.monthly_rent
            check_ts  += 30 * 24 * 3600
            months_due += 1
 
        if claimable == u256(0):
            raise Exception("No claimable rent yet")
 
        # Ensure escrow covers it (minus deposit which is locked)
        available_rent = u256(int(lease.escrow_balance) - int(lease.deposit_amount))
        if claimable > available_rent:
            claimable = available_rent
 
        if claimable == u256(0):
            raise Exception("Escrow has insufficient rent balance")
 
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount, total_paid=old.total_paid,
            escrow_balance=u256(int(old.escrow_balance) - int(claimable)),
            rent_paid_to=old.rent_paid_to,
            next_payment_due=old.next_payment_due,
            status=old.status,
            created_at=old.created_at, activated_at=old.activated_at,
            completed_at=old.completed_at, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by, dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at, dispute_outcome=old.dispute_outcome,
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=old.landlord_split_bps, ai_reasoning=old.ai_reasoning,
        )
        self.total_escrow = u256(int(self.total_escrow) - int(claimable))
 
        # Pay landlord
        gl.send_tx(lease.landlord, claimable, data=b"")
 
        # Update landlord profile revenue
        if lease.landlord in self.landlord_profiles:
            lp = self.landlord_profiles[lease.landlord]
            self.landlord_profiles[lease.landlord] = LandlordProfile(
                landlord=lp.landlord, total_listings=lp.total_listings,
                verified_listings=lp.verified_listings, total_leases=lp.total_leases,
                completed_leases=lp.completed_leases, disputed_leases=lp.disputed_leases,
                total_revenue=u256(int(lp.total_revenue) + int(claimable)),
                reputation_score=lp.reputation_score, joined_at=lp.joined_at,
            )
 
        return {
            "lease_id":    lease_id,
            "claimed":     str(claimable),
            "months_paid": months_due,
        }
 
 
    @gl.public.write
    def complete_lease(self, lease_id: str) -> dict[str, typing.Any]:
        """
        Called when the lease ends (by either party after end_date).
        Releases deposit back to tenant automatically if no dispute is raised.
        Marks listing ACTIVE again.
        """
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
 
        is_party = (gl.message.sender_address == lease.landlord or
                    gl.message.sender_address == lease.tenant)
        if not is_party:
            raise Exception("Only landlord or tenant can complete")
        if int(lease.status) != LeaseStatus.ACTIVE:
            raise Exception("Lease not active")
        if gl.block.timestamp < int(lease.end_date):
            raise Exception("Lease end date not reached yet")
 
        # Return deposit to tenant
        deposit = lease.deposit_amount
        if deposit > u256(0):
            gl.send_tx(lease.tenant, deposit, data=b"")
 
        # Any unclaimed rent goes to landlord
        remaining = u256(int(lease.escrow_balance) - int(deposit))
        if remaining > u256(0):
            gl.send_tx(lease.landlord, remaining, data=b"")
 
        now = u256(gl.block.timestamp)
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount, total_paid=old.total_paid,
            escrow_balance=u256(0),
            rent_paid_to=old.rent_paid_to,
            next_payment_due=old.next_payment_due,
            status=u8(LeaseStatus.COMPLETED),
            created_at=old.created_at, activated_at=old.activated_at,
            completed_at=now, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by, dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at, dispute_outcome=old.dispute_outcome,
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=old.landlord_split_bps, ai_reasoning=old.ai_reasoning,
        )
        self.total_escrow        = u256(int(self.total_escrow) - int(lease.escrow_balance))
        self.total_leases_completed = u32(int(self.total_leases_completed) + 1)
 
        # Reactivate listing
        listing = self.listings[old.listing_id]
        self.listings[old.listing_id] = PropertyListing(
            listing_id=listing.listing_id, title_number=listing.title_number,
            owner=listing.owner, owner_full_name=listing.owner_full_name,
            property_address=listing.property_address, postcode=listing.postcode,
            price_per_month=listing.price_per_month,
            min_duration_months=listing.min_duration_months,
            max_duration_months=listing.max_duration_months,
            deposit_months=listing.deposit_months,
            available_from=u256(int(now) + 86400),  # available tomorrow
            available_to=listing.available_to,
            bedrooms=listing.bedrooms, bathrooms=listing.bathrooms,
            property_type=listing.property_type, description=listing.description,
            amenities=listing.amenities, images_ipfs=listing.images_ipfs,
            verification_status=listing.verification_status,
            verified_at=listing.verified_at, hmlr_tenure=listing.hmlr_tenure,
            encumbrances_found=listing.encumbrances_found,
            verification_notes=listing.verification_notes,
            listing_status=u8(ListingStatus.ACTIVE),
            created_at=listing.created_at, updated_at=now,
            active_lease_id="",
            total_leases=listing.total_leases,
            total_revenue=u256(int(listing.total_revenue) + int(old.total_rent)),
        )
 
        # Update profiles
        _update_profile_completed(self, old.landlord, old.tenant)
 
        return {
            "lease_id":        lease_id,
            "status":          "COMPLETED",
            "deposit_returned": str(deposit),
            "listing_status":  "ACTIVE",
        }
 
 
    # ═════════════════════════════════════════════════════════════════
    # LAYER 4: AI DISPUTE RESOLUTION
    # ═════════════════════════════════════════════════════════════════
 
    @gl.public.write
    def raise_dispute(
        self,
        lease_id:       str,
        reason:         str,
        evidence_urls:  list,   # Photos, inspection reports, communications
    ) -> dict[str, typing.Any]:
        """
        Raise a dispute. Either landlord or tenant can call this.
        Freezes the escrow — nothing can be claimed until resolved.
        """
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
 
        is_party = (gl.message.sender_address == lease.landlord or
                    gl.message.sender_address == lease.tenant)
        if not is_party:
            raise Exception("Only landlord or tenant can dispute")
        if int(lease.status) not in [LeaseStatus.ACTIVE, LeaseStatus.COMPLETED]:
            raise Exception("Can only dispute active or just-completed lease")
 
        old = self.leases[lease_id]
        now = u256(gl.block.timestamp)
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount, total_paid=old.total_paid,
            escrow_balance=old.escrow_balance,
            rent_paid_to=old.rent_paid_to,
            next_payment_due=old.next_payment_due,
            status=u8(LeaseStatus.DISPUTED),
            created_at=old.created_at, activated_at=old.activated_at,
            completed_at=old.completed_at, cancelled_at=old.cancelled_at,
            dispute_raised_by=gl.message.sender_address,
            dispute_reason=reason,
            dispute_raised_at=now,
            dispute_outcome=u8(DisputeOutcome.UNRESOLVED),
            dispute_evidence_urls=json.dumps(evidence_urls),
            landlord_split_bps=u32(0), ai_reasoning="",
        )
 
        # Mark listing as disputed
        listing = self.listings[old.listing_id]
        self.listings[old.listing_id] = PropertyListing(
            listing_id=listing.listing_id, title_number=listing.title_number,
            owner=listing.owner, owner_full_name=listing.owner_full_name,
            property_address=listing.property_address, postcode=listing.postcode,
            price_per_month=listing.price_per_month,
            min_duration_months=listing.min_duration_months,
            max_duration_months=listing.max_duration_months,
            deposit_months=listing.deposit_months,
            available_from=listing.available_from, available_to=listing.available_to,
            bedrooms=listing.bedrooms, bathrooms=listing.bathrooms,
            property_type=listing.property_type, description=listing.description,
            amenities=listing.amenities, images_ipfs=listing.images_ipfs,
            verification_status=listing.verification_status,
            verified_at=listing.verified_at, hmlr_tenure=listing.hmlr_tenure,
            encumbrances_found=listing.encumbrances_found,
            verification_notes=listing.verification_notes,
            listing_status=u8(ListingStatus.DISPUTED),
            created_at=listing.created_at, updated_at=now,
            active_lease_id=listing.active_lease_id,
            total_leases=listing.total_leases, total_revenue=listing.total_revenue,
        )
        self.total_disputes = u32(int(self.total_disputes) + 1)
 
        return {
            "lease_id":       lease_id,
            "status":         "DISPUTED",
            "raised_by":      str(gl.message.sender_address),
            "next_step":      "Call resolve_dispute() — AI will analyse evidence and split escrow",
        }
 
 
    @gl.public.write
    def resolve_dispute(self, lease_id: str) -> dict[str, typing.Any]:
        """
        AI analyses evidence from both parties and decides how to split escrow.
        Uses semantic search over past precedents for calibration.
        Anyone can trigger resolution after a 24h cooling-off period.
        """
        if lease_id not in self.leases:
            raise Exception("Lease not found")
        lease = self.leases[lease_id]
        if int(lease.status) != LeaseStatus.DISPUTED:
            raise Exception("Lease not in disputed state")
 
        # 24h cooling-off period
        if gl.block.timestamp < int(lease.dispute_raised_at) + 86400:
            raise Exception("24h cooling-off period not elapsed")
 
        # Snapshot everything for nondet blocks
        reason_snap       = lease.dispute_reason
        evidence_snap     = json.loads(lease.dispute_evidence_urls)
        escrow_snap       = int(lease.escrow_balance)
        deposit_snap      = int(lease.deposit_amount)
        monthly_snap      = int(lease.monthly_rent)
        duration_snap     = int(lease.duration_months)
        raised_by_snap    = lease.dispute_raised_by
        landlord_snap     = lease.landlord
        tenant_snap       = lease.tenant
        listing           = self.listings[lease.listing_id]
        property_snap     = listing.property_address
        precedents_text   = self._get_dispute_precedents(reason_snap)
 
        def leader_fn() -> dict:
            evidence_text = _fetch_evidence(evidence_snap)
            is_tenant_complaint = (raised_by_snap == tenant_snap)
 
            prompt = f"""You are an expert AI arbitrator for GenZLease, a UK property leasing platform.
Analyse this tenancy dispute and decide how to fairly split the escrow.
 
PROPERTY: {property_snap}
DISPUTE RAISED BY: {"Tenant" if is_tenant_complaint else "Landlord"}
LEASE DURATION: {duration_snap} months
ESCROW BALANCE: {escrow_snap} wei (includes deposit of {deposit_snap} wei)
MONTHLY RENT: {monthly_snap} wei
 
DISPUTE REASON:
{reason_snap}
 
EVIDENCE SUBMITTED:
{evidence_text}
 
SIMILAR PAST DISPUTE PRECEDENTS (for calibration):
{precedents_text}
 
UK TENANCY LAW CONTEXT:
- Landlord can retain deposit for: damage beyond fair wear and tear, unpaid rent,
  cleaning costs, missing items from inventory
- Landlord CANNOT retain deposit for: fair wear and tear, pre-existing damage,
  landlord's failure to maintain property, minor marks/scuffs
- Tenant is entitled to full deposit return if property is left in same condition
  (allowing fair wear and tear) as at start of tenancy
- If landlord is at fault (e.g. uninhabitable conditions), tenant may be owed compensation
- Split outcomes are valid — partial deposit retention is common
 
DECISION FRAMEWORK:
1. Identify who bears responsibility for the primary complaint
2. Quantify the damage/loss in proportion to the dispute
3. Apply UK tenancy law principles
4. Cross-reference with similar precedents
5. Decide the % of DEPOSIT going to landlord (0-100%)
   (Note: rent already paid to landlord via claim_rent() is separate from deposit)
 
Respond ONLY with this JSON:
{{
  "outcome": "FAVOUR_TENANT" or "FAVOUR_LANDLORD" or "SPLIT",
  "landlord_deposit_pct": <integer 0-100>,
  "reasoning": "<detailed step-by-step analysis citing evidence and law>",
  "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
  "confidence": <float 0.0-1.0>,
  "precedent_note": "<how similar cases influenced this ruling>"
}}"""
 
            raw = gl.nondet.exec_prompt(prompt, response_format='json')
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, str):
                raw = raw.replace("```json","").replace("```","").strip()
                try:
                    return json.loads(raw)
                except Exception:
                    pass
            return {
                "outcome": "SPLIT", "landlord_deposit_pct": 50,
                "reasoning": "Parse error — defaulting to 50/50 split",
                "key_findings": [], "confidence": 0.0, "precedent_note": ""
            }
 
        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            if "outcome" not in leader_result.calldata:
                return False
            try:
                my_result = leader_fn()
                # Agree on outcome category; allow ±15% variance on split
                outcomes_match = (
                    leader_result.calldata.get("outcome","SPLIT")
                    == my_result.get("outcome","SPLIT")
                )
                leader_pct = int(leader_result.calldata.get("landlord_deposit_pct", 50))
                my_pct     = int(my_result.get("landlord_deposit_pct", 50))
                pct_close  = abs(leader_pct - my_pct) <= 15
                return outcomes_match and pct_close
            except Exception:
                return False
 
        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
 
        outcome_str          = result.get("outcome", "SPLIT")
        landlord_pct         = int(result.get("landlord_deposit_pct", 50))
        reasoning            = result.get("reasoning", "")
        confidence           = float(result.get("confidence", 0.0))
 
        outcome_int = {
            "FAVOUR_TENANT":   DisputeOutcome.FAVOUR_TENANT,
            "FAVOUR_LANDLORD": DisputeOutcome.FAVOUR_LANDLORD,
            "SPLIT":           DisputeOutcome.SPLIT,
        }.get(outcome_str, DisputeOutcome.SPLIT)
 
        landlord_split_bps = u32(min(10000, max(0, landlord_pct * 100)))
 
        # Execute the split
        landlord_gets = (u256(deposit_snap) * u256(int(landlord_split_bps))) // u256(10000)
        tenant_gets   = u256(deposit_snap) - landlord_gets
 
        # Any rent in escrow (beyond deposit) that's due goes to landlord
        rent_in_escrow = u256(escrow_snap - deposit_snap)
        if rent_in_escrow > u256(0):
            gl.send_tx(lease.landlord, rent_in_escrow, data=b"")
 
        if landlord_gets > u256(0):
            gl.send_tx(lease.landlord, landlord_gets, data=b"")
        if tenant_gets > u256(0):
            gl.send_tx(lease.tenant, tenant_gets, data=b"")
 
        now = u256(gl.block.timestamp)
        old = self.leases[lease_id]
        self.leases[lease_id] = LeaseAgreement(
            lease_id=old.lease_id, listing_id=old.listing_id,
            landlord=old.landlord, tenant=old.tenant,
            start_date=old.start_date, end_date=old.end_date,
            duration_months=old.duration_months,
            monthly_rent=old.monthly_rent, total_rent=old.total_rent,
            deposit_amount=old.deposit_amount, total_paid=old.total_paid,
            escrow_balance=u256(0),
            rent_paid_to=old.rent_paid_to,
            next_payment_due=old.next_payment_due,
            status=u8(LeaseStatus.REFUNDED),
            created_at=old.created_at, activated_at=old.activated_at,
            completed_at=now, cancelled_at=old.cancelled_at,
            dispute_raised_by=old.dispute_raised_by,
            dispute_reason=old.dispute_reason,
            dispute_raised_at=old.dispute_raised_at,
            dispute_outcome=u8(outcome_int),
            dispute_evidence_urls=old.dispute_evidence_urls,
            landlord_split_bps=landlord_split_bps,
            ai_reasoning=reasoning,
        )
        self.total_escrow = u256(int(self.total_escrow) - escrow_snap)
 
        # Reactivate listing
        listing = self.listings[old.listing_id]
        self.listings[old.listing_id] = PropertyListing(
            listing_id=listing.listing_id, title_number=listing.title_number,
            owner=listing.owner, owner_full_name=listing.owner_full_name,
            property_address=listing.property_address, postcode=listing.postcode,
            price_per_month=listing.price_per_month,
            min_duration_months=listing.min_duration_months,
            max_duration_months=listing.max_duration_months,
            deposit_months=listing.deposit_months,
            available_from=listing.available_from, available_to=listing.available_to,
            bedrooms=listing.bedrooms, bathrooms=listing.bathrooms,
            property_type=listing.property_type, description=listing.description,
            amenities=listing.amenities, images_ipfs=listing.images_ipfs,
            verification_status=listing.verification_status,
            verified_at=listing.verified_at, hmlr_tenure=listing.hmlr_tenure,
            encumbrances_found=listing.encumbrances_found,
            verification_notes=listing.verification_notes,
            listing_status=u8(ListingStatus.ACTIVE),
            created_at=listing.created_at, updated_at=now,
            active_lease_id="",
            total_leases=listing.total_leases, total_revenue=listing.total_revenue,
        )
 
        # Store precedent in VecDB
        self._store_dispute_precedent(
            reason_snap, outcome_int, int(landlord_split_bps), reasoning,
            old.listing_id, lease_id
        )
 
        # Update profiles
        tenant_won = outcome_int == DisputeOutcome.FAVOUR_TENANT
        _update_profile_disputed(self, old.landlord, old.tenant, tenant_won)
 
        return {
            "lease_id":           lease_id,
            "outcome":            outcome_str,
            "landlord_deposit_pct": landlord_pct,
            "landlord_received":  str(landlord_gets + rent_in_escrow),
            "tenant_received":    str(tenant_gets),
            "reasoning_summary":  reasoning[:300],
            "confidence":         confidence,
        }
 
 
    # ═════════════════════════════════════════════════════════════════
    # VecDB — Dispute Precedent Memory
    # ═════════════════════════════════════════════════════════════════
 
    def _get_embedding(self, text: str) -> np.ndarray[tuple[typing.Literal[384]], np.dtypes.Float32DType]:
        return gle.SentenceTransformer("all-MiniLM-L6-v2")(text)
 
    def _store_dispute_precedent(
        self, summary: str, outcome: int, landlord_split_bps: int,
        reasoning: str, listing_id: str, lease_id: str
    ):
        try:
            embedding = self._get_embedding(summary)
            entry = DisputePrecedent(
                dispute_summary=summary, outcome=u8(outcome),
                landlord_split_bps=u32(landlord_split_bps),
                reasoning=reasoning[:400], listing_id=listing_id,
                lease_id=lease_id, resolved_at=u256(gl.block.timestamp),
            )
            self.dispute_precedents.insert(embedding, entry)
            self.total_precedents = u32(int(self.total_precedents) + 1)
        except Exception:
            pass
 
    def _get_dispute_precedents(self, query: str) -> str:
        try:
            if int(self.total_precedents) == 0:
                return "[No precedents yet — first dispute on this platform]"
            q_emb    = self._get_embedding(query)
            results  = list(self.dispute_precedents.knn(q_emb, 3))
            if not results:
                return "[No similar precedents found]"
            lines = []
            for i, r in enumerate(results):
                p   = r.value
                sim = round(1 - r.distance, 3)
                outcome_label = {0:"UNRESOLVED",1:"FAVOUR_TENANT",2:"FAVOUR_LANDLORD",3:"SPLIT"}.get(int(p.outcome),"UNKNOWN")
                lines.append(
                    f"Precedent {i+1} (similarity={sim}):\n"
                    f"  Dispute: {p.dispute_summary[:120]}\n"
                    f"  Ruling:  {outcome_label}, landlord kept {int(p.landlord_split_bps)//100}% of deposit\n"
                    f"  Reason:  {p.reasoning[:150]}"
                )
            return "\n\n".join(lines)
        except Exception as e:
            return f"[Precedent error: {e}]"
 
 
    # ═════════════════════════════════════════════════════════════════
    # VIEW FUNCTIONS
    # ═════════════════════════════════════════════════════════════════
 
    @gl.public.view
    def get_listing(self, listing_id: str) -> dict[str, typing.Any] | None:
        if listing_id not in self.listings:
            return None
        l = self.listings[listing_id]
        return {
            "listing_id":          l.listing_id,
            "title_number":        l.title_number,
            "owner":               str(l.owner),
            "property_address":    l.property_address,
            "postcode":            l.postcode,
            "price_per_month":     str(l.price_per_month),
            "min_duration_months": int(l.min_duration_months),
            "max_duration_months": int(l.max_duration_months),
            "deposit_months":      int(l.deposit_months),
            "available_from":      int(l.available_from),
            "available_to":        int(l.available_to),
            "bedrooms":            int(l.bedrooms),
            "bathrooms":           int(l.bathrooms),
            "property_type":       l.property_type,
            "description":         l.description,
            "amenities":           l.amenities,
            "images_ipfs":         l.images_ipfs,
            "verification_status": _ver_label(int(l.verification_status)),
            "hmlr_tenure":         l.hmlr_tenure,
            "encumbrances_found":  l.encumbrances_found,
            "verification_notes":  l.verification_notes,
            "listing_status":      _lst_label(int(l.listing_status)),
            "verified_at":         int(l.verified_at),
            "active_lease_id":     l.active_lease_id,
            "total_leases":        int(l.total_leases),
            "total_revenue":       str(l.total_revenue),
        }
 
    @gl.public.view
    def get_lease(self, lease_id: str) -> dict[str, typing.Any] | None:
        if lease_id not in self.leases:
            return None
        l = self.leases[lease_id]
        return {
            "lease_id":            l.lease_id,
            "listing_id":          l.listing_id,
            "landlord":            str(l.landlord),
            "tenant":              str(l.tenant),
            "start_date":          int(l.start_date),
            "end_date":            int(l.end_date),
            "duration_months":     int(l.duration_months),
            "monthly_rent":        str(l.monthly_rent),
            "total_rent":          str(l.total_rent),
            "deposit_amount":      str(l.deposit_amount),
            "escrow_balance":      str(l.escrow_balance),
            "rent_paid_to":        int(l.rent_paid_to),
            "next_payment_due":    int(l.next_payment_due),
            "status":              _lease_label(int(l.status)),
            "dispute_raised_by":   str(l.dispute_raised_by),
            "dispute_reason":      l.dispute_reason,
            "dispute_outcome":     _dispute_label(int(l.dispute_outcome)),
            "landlord_split_bps":  int(l.landlord_split_bps),
            "ai_reasoning":        l.ai_reasoning,
            "callback_posted":     False,
        }
 
    @gl.public.view
    def get_platform_stats(self) -> dict[str, typing.Any]:
        return {
            "total_listings":         int(self.total_listings),
            "total_leases_created":   int(self.total_leases_created),
            "total_leases_completed": int(self.total_leases_completed),
            "total_disputes":         int(self.total_disputes),
            "total_escrow":           str(self.total_escrow),
            "total_fees_collected":   str(self.total_fees_collected),
            "total_precedents":       int(self.total_precedents),
            "platform_fee_bps":       int(self.platform_fee_bps),
            "paused":                 self.paused,
        }
 
    @gl.public.view
    def get_tenant_profile(self, tenant: Address) -> dict[str, typing.Any] | None:
        if tenant not in self.tenant_profiles:
            return None
        p = self.tenant_profiles[tenant]
        return {
            "tenant":            str(p.tenant),
            "total_leases":      int(p.total_leases),
            "completed_leases":  int(p.completed_leases),
            "disputed_leases":   int(p.disputed_leases),
            "disputes_won":      int(p.disputes_won),
            "total_spent":       str(p.total_spent),
            "reputation_score":  int(p.reputation_score),
        }
 
    @gl.public.view
    def get_landlord_profile(self, landlord: Address) -> dict[str, typing.Any] | None:
        if landlord not in self.landlord_profiles:
            return None
        p = self.landlord_profiles[landlord]
        return {
            "landlord":           str(p.landlord),
            "total_listings":     int(p.total_listings),
            "verified_listings":  int(p.verified_listings),
            "total_leases":       int(p.total_leases),
            "completed_leases":   int(p.completed_leases),
            "disputed_leases":    int(p.disputed_leases),
            "total_revenue":      str(p.total_revenue),
            "reputation_score":   int(p.reputation_score),
        }
 
    @gl.public.view
    def search_dispute_precedents(self, query: str, k: int = 5) -> list:
        try:
            if int(self.total_precedents) == 0:
                return []
            q_emb   = self._get_embedding(query)
            results = list(self.dispute_precedents.knn(q_emb, k))
            out = []
            for r in results:
                p = r.value
                out.append({
                    "dispute_summary":     p.dispute_summary,
                    "outcome":             _dispute_label(int(p.outcome)),
                    "landlord_split_pct":  int(p.landlord_split_bps) // 100,
                    "similarity":          round(1 - r.distance, 3),
                })
            return out
        except Exception:
            return []
 
    @gl.public.write
    def withdraw_fees(self) -> dict[str, typing.Any]:
        if gl.message.sender_address != self.owner:
            raise Exception("Only platform owner")
        amount = self.accumulated_platform_fees
        self.accumulated_platform_fees = u256(0)
        gl.send_tx(self.owner, amount, data=b"")
        return {"withdrawn": str(amount)}
 
    @gl.public.write
    def set_paused(self, paused: bool) -> None:
        if gl.message.sender_address != self.owner:
            raise Exception("Only platform owner")
        self.paused = paused
 
 
# ─────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────
 
def _fetch_evidence(urls: list) -> str:
    parts = []
    for url in urls[:5]:   # cap at 5 evidence URLs
        try:
            text = gl.nondet.web.render(url, mode="text")
            parts.append(f"=== {url} ===\n{text[:2000]}\n")
        except Exception as e:
            parts.append(f"=== {url} ===\n[Fetch error: {e}]\n")
    return "\n".join(parts) if parts else "[No evidence provided]"
 
 
def _update_profile_completed(contract: GenZLease, landlord: Address, tenant: Address):
    if landlord in contract.landlord_profiles:
        lp = contract.landlord_profiles[landlord]
        contract.landlord_profiles[landlord] = LandlordProfile(
            landlord=lp.landlord, total_listings=lp.total_listings,
            verified_listings=lp.verified_listings,
            total_leases=u32(int(lp.total_leases)+1),
            completed_leases=u32(int(lp.completed_leases)+1),
            disputed_leases=lp.disputed_leases,
            total_revenue=lp.total_revenue,
            reputation_score=u32(min(100, int(lp.reputation_score)+1)),
            joined_at=lp.joined_at,
        )
    if tenant in contract.tenant_profiles:
        tp = contract.tenant_profiles[tenant]
        contract.tenant_profiles[tenant] = TenantProfile(
            tenant=tp.tenant,
            total_leases=tp.total_leases,
            completed_leases=u32(int(tp.completed_leases)+1),
            disputed_leases=tp.disputed_leases,
            disputes_won=tp.disputes_won,
            total_spent=tp.total_spent,
            reputation_score=u32(min(100, int(tp.reputation_score)+1)),
            joined_at=tp.joined_at,
        )
 
 
def _update_profile_disputed(
    contract: GenZLease, landlord: Address, tenant: Address, tenant_won: bool
):
    if landlord in contract.landlord_profiles:
        lp = contract.landlord_profiles[landlord]
        contract.landlord_profiles[landlord] = LandlordProfile(
            landlord=lp.landlord, total_listings=lp.total_listings,
            verified_listings=lp.verified_listings, total_leases=lp.total_leases,
            completed_leases=lp.completed_leases,
            disputed_leases=u32(int(lp.disputed_leases)+1),
            total_revenue=lp.total_revenue,
            reputation_score=u32(max(0, int(lp.reputation_score) - (5 if tenant_won else 0))),
            joined_at=lp.joined_at,
        )
    if tenant in contract.tenant_profiles:
        tp = contract.tenant_profiles[tenant]
        contract.tenant_profiles[tenant] = TenantProfile(
            tenant=tp.tenant,
            total_leases=tp.total_leases,
            completed_leases=tp.completed_leases,
            disputed_leases=u32(int(tp.disputed_leases)+1),
            disputes_won=u32(int(tp.disputes_won)+(1 if tenant_won else 0)),
            total_spent=tp.total_spent,
            reputation_score=u32(max(0, int(tp.reputation_score) - (0 if tenant_won else 3))),
            joined_at=tp.joined_at,
        )
 
 
def _ver_label(v: int) -> str:
    return {0:"UNVERIFIED",1:"PENDING",2:"VERIFIED",3:"FAILED",4:"EXPIRED"}.get(v,"UNKNOWN")
 
def _lst_label(v: int) -> str:
    return {0:"DRAFT",1:"ACTIVE",2:"PAUSED",3:"RENTED",4:"DISPUTED",5:"DELISTED"}.get(v,"UNKNOWN")
 
def _lease_label(v: int) -> str:
    return {0:"PENDING",1:"ACTIVE",2:"COMPLETED",3:"DISPUTED",4:"CANCELLED",5:"REFUNDED"}.get(v,"UNKNOWN")
 
def _dispute_label(v: int) -> str:
    return {0:"UNRESOLVED",1:"FAVOUR_TENANT",2:"FAVOUR_LANDLORD",3:"SPLIT"}.get(v,"UNKNOWN")