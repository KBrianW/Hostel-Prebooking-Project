# Payment Status & Booking Status Documentation

## Overview
This document explains the payment and booking status system in the ANU Hostel Prebooking Management System, including when statuses change and how they interact.

---

## Booking Statuses

### 1. **Pre-booked** (`prebooked`)
**Initial status** when a student prebooks a room.

**When it's set:**
- When a student makes the initial prebooking payment (Ksh 2,500)
- When a booking is created for a room
- When a student changes rooms (if not fully paid)
- When an expired booking is renewed

**Characteristics:**
- Student has made at least one payment (usually Ksh 2,500 prepayment)
- Payment may be verified or unverified
- Has an `expiry_date` (typically 7 days from prebooking)
- Room is reserved but not confirmed
- Student can cancel, change rooms, or make additional payments

**Payment State:**
- Total paid (verified + unverified) < Room price
- Booking can still be cancelled
- Student can view room but cannot view roommates

---

### 2. **Fully Paid** (`paid`)
**Confirmed status** when booking is fully paid.

**When it's set:**
- When admin verifies a payment that makes total verified payments >= room price
- When student makes full payment (via "Pay Full Balance" button)
- Automatically when payment verification completes and total paid >= room price
- When finance balance is used for renewal and covers full amount

**Characteristics:**
- Total verified payments >= Room price
- Booking is permanent until semester ends
- Student CANNOT cancel (only at semester end)
- Student CAN view roommates
- Room is marked as occupied
- Finance balance is automatically used first if available

**Payment State:**
- Total paid (verified) >= Room price
- All payments verified
- Booking is confirmed and permanent

---

### 3. **Expired** (`expired`)
**Cancelled status** when prebooking expires without full payment.

**When it's set:**
- Automatically when `expiry_date` passes and booking is still `prebooked`
- When student cancels a prebooked room
- When admin manually removes/cancels a student's booking
- Via cron job that runs daily (`auto_expire_bookings`)

**Characteristics:**
- Prebooking period expired without full payment
- All payments (verified + unverified) are refunded to finance office
- Room is released and becomes available
- Student can book a new room
- Student can renew the same room (uses finance balance)

**Payment State:**
- All payments refunded to finance account
- Finance balance updated with refund amount
- Student can use refund for future bookings

---

## Payment Status (Individual Payment)

### 1. **Pending** (`verified=False`)
**Unverified payment** waiting for admin verification.

**When it's set:**
- When student makes a payment (automatically unverified)
- When student records a custom payment amount
- When finance balance is used (auto-verified, so NOT pending)

**Characteristics:**
- Payment is recorded but not confirmed
- Shows in "Awaiting Verification" section
- Admin must verify before it counts toward total paid
- Student can see it in their payment history but it's marked as "Pending"

**What happens when verified:**
- Admin clicks "Verify Payment" in manage_bookings
- Payment `verified` field changes to `True`
- If total verified payments >= room price, booking status changes to `paid`
- Room vacancy is updated
- Student receives notification

---

### 2. **Verified** (`verified=True`)
**Confirmed payment** verified by admin.

**When it's set:**
- When admin verifies a payment
- Automatically when finance balance is used (always verified)
- Automatically when payment from finance account is processed

**Characteristics:**
- Payment is confirmed and counts toward total paid
- Included in `get_total_paid()` calculation
- Cannot be undone (would require manual database change)
- Used to determine if booking is fully paid

---

## Payment Info States (Student View)

### 1. **Pending Payment**
**Student has made payment but admin hasn't verified yet.**

**Display:**
- Shows in payment history as "Pending Verification"
- Counted in `get_total_paid_all()` (includes unverified)
- NOT counted in `get_total_paid()` (verified only)
- Remaining balance calculation uses `get_total_paid_all()` for student view

**Notification:**
- "Payment recorded. Awaiting admin verification."

---

### 2. **Fully Paid**
**Booking is confirmed and fully paid.**

**Display:**
- Booking status: "Fully Paid"
- Progress bar: 100%
- Green badge with checkmark
- Student can view roommates
- Cancel button is hidden

**Notification:**
- "Your booking is fully paid and confirmed!"

---

### 3. **Expired**
**Prebooking expired without full payment.**

**Display:**
- Booking status: "Expired"
- Red badge with X icon
- Message: "Booking expired. All payments refunded to finance office."
- Student can book new room or renew same room

**Notification:**
- "Your pre-booking has expired."
- "All payments refunded to finance office."

---

## State Transitions

### Transition Diagram

```
┌─────────────┐
│  Pre-booked │
│  (initial)  │
└─────┬───────┘
      │
      ├─────────────────────────────────────────┐
      │                                         │
      ▼                                         ▼
┌─────────────┐                        ┌─────────────┐
│ Fully Paid  │                        │   Expired   │
│ (confirmed) │                        │ (cancelled) │
└─────────────┘                        └─────┬───────┘
      │                                        │
      │ (permanent until semester end)         │
      │                                        │
      └────────────────────────────────────────┘
                    │
                    │ (renewal)
                    ▼
            ┌─────────────┐
            │  Pre-booked │
            │  (renewed)  │
            └─────────────┘
```

---

### Detailed State Changes

#### 1. Pre-booked → Fully Paid
**Trigger:** Admin verifies payment AND total verified payments >= room price

**Actions:**
- Booking status changes to `paid`
- Room vacancy updated (if 2 students, room marked as occupied)
- Student receives notification
- Student can now view roommates
- Student CANNOT cancel (permanent booking)

**Code Location:**
- `core/models.py` - `verify_payment` signal
- `core/views.py` - `manage_bookings` view (verify action)

---

#### 2. Pre-booked → Expired
**Trigger:** 
- `expiry_date` passes (automatic via cron)
- Student cancels booking
- Admin removes student

**Actions:**
- Booking status changes to `expired`
- All payments (verified + unverified) refunded to finance
- FinanceTransaction created (type='refund')
- Room vacancy updated
- Student receives notification
- Student can book new room

**Code Location:**
- `core/cron.py` - `auto_expire_bookings()`
- `core/views.py` - `student_profile` (cancel_booking action)
- `core/views.py` - `manage_bookings` (remove_student action)

---

#### 3. Expired → Pre-booked (Renewal)
**Trigger:** Student renews expired booking OR admin processes renewal

**Actions:**
- Booking status changes to `prebooked` or `paid` (if full amount)
- Finance balance used for payment (if available)
- New Payment record created
- FinanceTransaction created (type='renewal')
- Room vacancy updated
- Student receives notification

**Code Location:**
- `core/views.py` - `available_rooms` (renew room action)
- `core/views.py` - `finance_dashboard` (process_renewal action)

---

#### 4. Pre-booked → Pre-booked (Room Change)
**Trigger:** Student changes room (if not fully paid)

**Actions:**
- Booking room updated to new room
- Old room vacancy updated
- New room vacancy updated
- Payment progress maintained
- Booking status remains `prebooked`
- Student receives notification

**Code Location:**
- `core/views.py` - `student_profile` (change_room action)

---

## Payment Flow Examples

### Example 1: Normal Payment Flow
1. Student prebooks room (Ksh 24,000) → Pays Ksh 2,500
   - Status: `prebooked`
   - Payment: `verified=False` (pending)
   - Remaining: Ksh 21,500

2. Student makes additional payment → Pays Ksh 10,000
   - Status: `prebooked`
   - Payments: Ksh 2,500 (pending) + Ksh 10,000 (pending)
   - Remaining: Ksh 11,500

3. Admin verifies Ksh 2,500 payment
   - Payment: `verified=True`
   - Verified total: Ksh 2,500
   - Status: Still `prebooked` (not fully paid)

4. Admin verifies Ksh 10,000 payment
   - Payment: `verified=True`
   - Verified total: Ksh 12,500
   - Status: Still `prebooked` (not fully paid)

5. Student pays remaining Ksh 11,500
   - Admin verifies payment
   - Verified total: Ksh 24,000
   - Status: **`paid`** (fully paid!)

---

### Example 2: Finance Balance Usage
1. Student has finance balance: Ksh 14,000
2. Student prebooks room (Ksh 24,000) → Pays Ksh 2,500
   - Finance balance: Ksh 14,000 (available)
   - Status: `prebooked`
   - Remaining: Ksh 21,500

3. Student clicks "Pay Full Balance"
   - System uses Ksh 14,000 from finance balance (auto-verified)
   - System requires Ksh 7,500 new payment
   - Finance balance used: Ksh 14,000 (renewal transaction created)
   - New payment: Ksh 7,500 (pending verification)
   - Status: Still `prebooked` (waiting for admin to verify new payment)

4. Admin verifies Ksh 7,500 payment
   - Verified total: Ksh 14,000 (finance) + Ksh 7,500 (new) = Ksh 21,500
   - Plus initial Ksh 2,500 = Ksh 24,000
   - Status: **`paid`** (fully paid!)

---

### Example 3: Expiration Flow
1. Student prebooks room → Pays Ksh 2,500
   - Status: `prebooked`
   - Expiry date: 7 days from now

2. Expiry date passes without full payment
   - Cron job runs: `auto_expire_bookings()`
   - Status: **`expired`**
   - All payments refunded to finance
   - Finance balance: +Ksh 2,500
   - Room released

3. Student can:
   - Book a new room (uses finance balance if available)
   - Renew same room (uses finance balance)

---

## Key Methods & Calculations

### `Booking.get_total_paid()`
- Returns: Sum of **verified payments only**
- Used by: Admin, internal logic, room vacancy calculation
- Purpose: Determine if booking is fully paid

### `Booking.get_total_paid_all()`
- Returns: Sum of **all payments** (verified + unverified)
- Used by: Student display, payment progress
- Purpose: Show student their total paid including pending payments

### `Booking.get_total_due()`
- Returns: Room price
- Used by: Calculate remaining balance

### `Booking.is_fully_paid()`
- Returns: `True` if `get_total_paid() >= get_total_due()` AND status == `paid`
- Used by: Check if booking is confirmed

---

## Finance Balance Logic

### Finance Balance Calculation
```
Finance Balance = Total Refunded - Total Used (Renewals)
```

### When Finance Balance is Used
1. **Automatic on Payment:**
   - Student makes any payment
   - System automatically uses finance balance first
   - Then applies new payment

2. **On Renewal:**
   - Student renews expired booking
   - Finance balance used automatically
   - Creates `FinanceTransaction` (type='renewal')

3. **On Prebooking:**
   - If student has finance balance
   - Ksh 2,500 prebooking uses finance balance first
   - Then requires new payment if needed

---

## Admin Actions

### Verify Payment
- Changes payment `verified` to `True`
- If total verified >= room price, booking becomes `paid`
- Updates room vacancy
- Sends notification to student

### Remove Student
- Options: Cancel or Move
- Cancel: Status → `expired`, refunds all payments
- Move: Changes room, maintains status

### Release Room
- Status → `expired`
- Refunds all payments
- Updates room vacancy

---

## Summary

| Status | Payment State | Can Cancel? | Can View Roommates? | Room Reserved? |
|--------|--------------|-------------|-------------------|----------------|
| Pre-booked | Partial payment | ✅ Yes | ❌ No | ✅ Yes |
| Fully Paid | Full payment verified | ❌ No | ✅ Yes | ✅ Yes (permanent) |
| Expired | Refunded to finance | N/A | ❌ No | ❌ No (released) |

| Payment State | Counted in Total Paid? | Requires Admin Action? |
|--------------|----------------------|----------------------|
| Pending (unverified) | In `get_total_paid_all()` only | ✅ Yes (verify) |
| Verified | In both methods | ❌ No |

---

## Important Notes

1. **Finance Balance is Always Used First:**
   - Automatically applied on any payment
   - Creates renewal transaction
   - Auto-verified (no admin action needed)

2. **Fully Paid Bookings are Permanent:**
   - Cannot be cancelled by student
   - Cannot be changed (except by admin)
   - Lasts until semester ends

3. **Expired Bookings:**
   - All payments refunded (verified + unverified)
   - Refund goes to finance account
   - Student can use refund for future bookings

4. **Payment Verification:**
   - Only verified payments count toward "fully paid"
   - Unverified payments show in student view but don't confirm booking
   - Admin must verify to confirm booking

---

## Troubleshooting

### Booking stuck in "Pre-booked" with full payment?
- Check if payments are verified
- Only verified payments count toward total paid
- Verify payments in "Manage Bookings"

### Finance balance not being used?
- Check if finance balance is calculated correctly
- Finance balance = Refunded - Used (Renewals)
- Finance balance is automatically used on payment

### Room not marked as occupied?
- Room is occupied only when 2 students have `paid` status
- Check if both students' bookings are `paid`
- Verify payments for both students

---

**Last Updated:** 2025-01-XX
**Version:** 1.0

