# ANU Hostel Prebooking Management System - Complete Walkthrough

## 📋 Table of Contents
1. [Student Flow](#student-flow)
2. [Admin Flow](#admin-flow)
3. [Key Features & Actions](#key-features--actions)

---

## 🎓 STUDENT FLOW

### 1. REGISTRATION
**URL:** `/register/`

**Steps:**
1. Navigate to registration page
2. Fill in registration form:
   - **First Name** (read-only after creation - managed by school)
   - **Last Name** (read-only after creation - managed by school)
   - **Username** (editable later)
   - **Email**
   - **Password** (with confirmation)
   - **Registration Number** (unique, e.g., ANU/2024/001)
   - **Gender** (dropdown: Male/Female) - determines accessible hostels
   - **Course** (dropdown: BBIT, Computer Science, Law, Procurement, IBM, Peace and Conflict, Commerce, Journalism, Theology, Criminology, Psychology)
   - **Year of Study** (number input: 1-6)
   - **Phone Number** (with country code dropdown - international support)
3. Submit registration
4. System validates:
   - Unique username
   - Unique registration number
   - Valid phone number format (country-specific)
   - Valid course selection
   - Numeric year of study
5. Account created → Redirected to login page

**Validation:**
- Username must be unique
- Registration number must be unique
- Phone number format validated based on country code
- All required fields must be filled

---

### 2. LOGIN
**URL:** `/login/` or `/`

**Steps:**
1. Enter username and password
2. Click "Login"
3. System authenticates user
4. Redirects based on user type:
   - **Student** → Student Dashboard (`/student-dashboard/`)
   - **Admin** → Admin Dashboard (`/admin-dashboard/`)

**Features:**
- Notifications do NOT appear on login page
- Session-based authentication
- Automatic redirect based on user role

---

### 3. STUDENT DASHBOARD
**URL:** `/student-dashboard/`

**What You See:**
- **Welcome Header** with personalized greeting
- **Quick Action Buttons:**
  - "Find a Room" (if no booking or expired)
  - "Complete Payment" (if prebooked)
  - "View Booking" (if fully paid)
  - "My Profile"
- **Status Cards:**
  - Booking Status (No Active Booking / Pre-booked / Fully Paid / Expired)
  - Payment Progress (with progress bar)
  - Available Rooms Count (gender-based)
  - Finance Account Balance (Total Refunded, Amount Used, Available Balance)
- **Current Booking Information** (if exists):
  - Hostel name
  - Room number
  - Booking status
  - Payment progress
  - Expiry date (if prebooked)
- **Latest Notifications** (3 most recent unread)
- **Roommates Section** (only if fully paid):
  - Roommate names
  - Registration numbers
  - Phone numbers
  - Link to view all roommate details

**Navigation Sidebar:**
- Dashboard
- Rooms
- Payments
- Roommates (always visible, but access restricted until fully paid)
- Profile

---

### 4. AVAILABLE ROOMS
**URL:** `/available-rooms/`

**Features:**

#### A. Search & Filter
- **Hostel Filter:** Dropdown to filter by hostel name
- **Room Number Filter:** Dropdown showing vacant room numbers
- **Search Bar:** Search by hostel or room number
- **Gender-based Display:** Only shows hostels matching student's gender

#### B. Room Display
- Rooms grouped by hostel
- Each room card shows:
  - Room number
  - Occupancy status badge:
    - 🟢 **Vacant** (0/2)
    - 🟡 **X/2 Occupied** (1/2 - partially occupied)
    - 🔴 **Full** (2/2 - fully occupied)
  - Room type (Type 1, Ensuite, Regular)
  - Capacity (students)
  - Current occupancy (X/Y)
  - Price (Ksh)
  - Pre-Book button

#### C. Room Details Modal
- Click on a room card to view:
  - Hostel name
  - Room number
  - Type
  - Capacity
  - Current occupancy
  - Price
  - Current occupants (if any)

#### D. Prebooking Process
1. Click "Pre-Book (Ksh 2,500)" button
2. System checks:
   - Room availability (not full)
   - Student has no active booking OR can cancel current booking
   - Student doesn't have fully paid booking
3. If active booking exists:
   - Shows "Cancel & Book New Room" confirmation modal
   - Explains: Current booking will be cancelled, payments refunded to finance
   - Confirm cancellation → Proceeds to prebook
4. Prebooking modal shows:
   - Room details
   - Fixed amount: **Ksh 2,500**
   - Confirmation prompt
5. If student has refund balance:
   - Automatically uses available finance balance first
   - Shows remaining amount needed (if any)
6. Click "Confirm Prebooking"
7. System:
   - Cancels existing booking (if any) → refunds all payments to finance
   - Creates new booking with status 'prebooked'
   - Creates payment record (Ksh 2,500) - unverified
   - Updates room occupancy
   - Sends notification
   - Redirects to student profile

**Special Cases:**
- **Fully Paid Booking:** Cannot prebook another room
  - Shows alert: "You have a fully paid booking... Your booking is permanent until the semester ends."
  - All "Pre-Book" buttons disabled
  - Room cards grayed out
- **Expired Booking:** Can renew the same room or book a new one
  - "Renew This Room" button appears
  - Uses finance balance if available

---

### 5. STUDENT PROFILE & PAYMENTS
**URL:** `/student-profile/`

#### A. Profile Section
**Editable Fields:**
- **Username** (can be changed)
- **Phone Number** (can be changed)

**Read-Only Fields:**
- Full Name (First + Last) - managed by school
- Registration Number
- Course
- Gender
- Year of Study

**Actions:**
1. Update Profile:
   - Change username (must be unique)
   - Change phone number
   - Click "Update Profile"
   - Success notification shown

#### B. Booking Information
**If Active Booking Exists:**
- Hostel name
- Room number
- Booking status (Pre-booked / Fully Paid / Expired)
- Booking date
- Expiry date (if prebooked)

**If No Booking:**
- Message: "You have no active booking. Visit Available Rooms to book a room."

#### C. Payment Summary
**Displays:**
- **Total Due:** Room price (e.g., Ksh 24,000)
- **Paid Amount:** Total payments (including unverified)
- **Remaining Balance:** Total Due - Paid Amount
- **Progress Bar:** Visual payment progress

#### D. Finance Account Balance
**Shows:**
- **Total Refunded:** Sum of all refunds from cancelled bookings
- **Amount Used:** Sum used for renewals/prebookings
- **Available Balance:** Total Refunded - Amount Used
- **Visual Cards** with explanatory notes

#### E. Payment Actions

**1. Pay Full Balance**
- Button: "Pay Full Balance"
- System calculates:
  - Uses available finance balance first (automatically)
  - Shows: "This will use Ksh X from finance balance + Ksh Y new payment"
  - If finance balance covers full amount: "No additional payment needed"
- Click "Pay Full Balance"
- Confirmation modal appears
- If amount > remaining:
  - Excess credited to finance account
- Creates payment record(s):
  - From finance balance (auto-verified)
  - New payment (pending verification)
- Updates booking status if fully paid
- Sends notification
- Redirects to profile

**2. Custom Payment Amount**
- Input field for payment amount
- System calculates:
  - Finance balance to use (automatic)
  - New payment needed
- Shows message: "This will use Ksh X from finance balance + Ksh Y new payment"
- Enter amount
- Click "Make Payment"
- Creates payment record(s)
- If amount > remaining needed:
  - Excess credited to finance
- Sends notification
- Updates booking status if fully paid

**3. Payment History Table**
- Lists all payments:
  - Amount
  - Payment Type (Prepayment / Full)
  - Status (Pending / Verified)
  - Date Paid
  - Verified Date (if verified)

#### F. Room Management Actions

**1. Change Room**
- Button: "Change Room" (only if prebooked, not fully paid)
- Opens modal with available rooms (same gender, vacant)
- Select new room
- Click "Change Room"
- System:
  - Updates booking to new room
  - Updates old and new room occupancy
  - Sends notification
  - Redirects to profile

**2. Cancel Booking**
- Button: "Cancel Booking" (hidden if fully paid)
- Confirmation modal:
  - Explains: All payments will be refunded to finance account
  - Cannot cancel if fully paid
- Click "Confirm Cancellation"
- System:
  - Sets booking status to 'expired'
  - Calculates total paid (all payments - verified + unverified)
  - Creates refund FinanceTransaction
  - Updates room vacancy
  - Sends notification
  - Redirects to profile

**Restrictions:**
- **Cannot cancel if fully paid** - Booking is permanent until semester ends
- **Cannot change room if fully paid** - Must wait until semester end

---

### 6. VIEW ROOMMATES
**URL:** `/roommates/`

**Access Requirements:**
- Booking must be fully paid
- If not fully paid: Redirected to profile with warning message

**What You See:**
- Current room information:
  - Hostel name
  - Room number
  - Room type
  - Capacity
- Roommate(s) list:
  - Full name
  - Registration number
  - Phone number
  - Course
  - Year of study
- If no roommates:
  - Message: "You are currently the only occupant in this room"

**Note:** Only fully paid students are shown as roommates. Prebooked students are not visible.

---

### 7. ROOM DETAILS
**URL:** `/room/<room_id>/`

**Features:**
- View detailed room information:
  - Hostel name
  - Room number
  - Type
  - Price
  - Capacity
  - Current occupancy (X/Y)
  - Available spots
  - Status (Vacant / Full)
- View current occupants (only fully paid students)
- Gender-based access (only same gender hostels)

---

### 8. NOTIFICATIONS
**URL:** `/notifications/`

**Features:**
- View all notifications (read and unread)
- Unread count badge in header
- Individual "Mark as Read" button for each notification
- "Mark All as Read" button (enabled only if unread notifications exist)
- Notifications include:
  - Booking confirmations
  - Payment verifications
  - Payment reminders
  - Room assignment changes
  - Booking cancellations
  - Expiry warnings
- Notification types:
  - Success (green)
  - Info (blue)
  - Warning (yellow)
  - Error (red)

**Auto-Updates:**
- Notification count updates via AJAX (every 30 seconds)
- Bell icon in navbar shows unread count
- Notifications do NOT appear on login page

---

### 9. LOGOUT
**URL:** `/logout/`

**Steps:**
1. Click "Logout" in navbar
2. Session terminated
3. Redirected to login page

---

## 👨‍💼 ADMIN FLOW

### 1. LOGIN
**URL:** `/login/` or `/`

**Steps:**
1. Enter admin username and password
2. Click "Login"
3. System authenticates
4. Redirects to Admin Dashboard (`/admin-dashboard/`)

**Note:** Admin accounts are created by other admins (see Manage Admins section)

---

### 2. ADMIN DASHBOARD
**URL:** `/admin-dashboard/`

**What You See:**

#### A. Header
- Dashboard title
- Quick action buttons:
  - Manage Bookings
  - Notifications
  - Finance

#### B. Statistics Cards
- **Total Students:** Count of all registered students
- **Pre-booked:** Count of prebooked bookings
- **Fully Paid:** Count of fully paid bookings
- **Vacant Rooms:** Count of vacant rooms

#### C. Awaiting Verification Section
- List of bookings with pending payments
- Shows:
  - Student name
  - Room
  - Pending amount
  - Date
  - "View in Manage Bookings" link

#### D. Bookings Expiring Soon
- List of prebooked bookings expiring within 3 days
- Shows:
  - Student name
  - Room
  - Expiry date
  - Days remaining

#### E. Recent Bookings Table
- Last 10 bookings
- Columns:
  - Student name
  - Registration number
  - Room
  - Status
  - Payment progress (progress bar)
  - Date booked
  - "View" button

**Navigation Sidebar:**
- Dashboard
- Bookings
- Rooms
- Admins
- Finance
- Notifications
- Profile

---

### 3. MANAGE BOOKINGS
**URL:** `/manage-bookings/`

**Features:**

#### A. Search & Filter
- **Search Bar:** Search by student name or registration number
- Real-time filtering as you type
- Shows matching bookings

#### B. Booking List
- Table showing all bookings:
  - Student name
  - Registration number
  - Room (Hostel - Room Number)
  - Status (Pre-booked / Fully Paid / Expired)
  - Payment progress
  - Date booked
  - Actions dropdown

#### C. Actions on Bookings

**1. Verify Payment**
- View pending payments for a booking
- List of unverified payments:
  - Amount
  - Payment type
  - Date paid
  - "Verify" button
- Click "Verify" on a payment:
  - Payment status → Verified
  - If booking fully paid → Status → 'paid'
  - Room occupancy updated
  - Notification sent to student
  - Finance transaction updated

**2. Assign/Change Room**
- Button: "Assign/Change Room"
- Modal opens with:
  - Current room (if any)
  - Dropdown of available rooms (same gender, not full)
  - "Assign Room" button
- Select new room
- Click "Assign Room"
- System:
  - Updates booking to new room
  - Updates old and new room occupancy
  - Sends notification to student
  - Redirects to manage bookings

**3. Release Room** (Deprecated - use Remove Student instead)
- Sets booking status to 'expired'
- Processes refund to finance
- Updates room vacancy
- Sends notification

**4. Remove Student**
- Button: "Remove Student"
- Modal with options:
  - **Cancel Room:** Cancel student's booking
    - Reason field (required)
    - Refunds all payments to finance
    - Sets booking status to 'expired'
    - Updates room vacancy
    - Sends notification
  - **Move to Another Room:** Assign to different room
    - Reason field (required)
    - Room selection dropdown
    - Moves student to new room
    - Updates room vacancy
    - Sends notification
- Click "Confirm Removal"
- Action executed
- Notification sent to student

---

### 4. MANAGE ROOMS
**URL:** `/manage-rooms/`

**Features:**

#### A. Hostel Management

**Add Hostel:**
1. Fill form:
   - Hostel name
   - Gender (Male / Female)
   - Type (Type 1 / Ensuite / Regular)
   - Description (optional)
2. Click "Add Hostel"
3. System validates:
   - Unique hostel name
   - Valid gender/type combination
4. Hostel created
5. Notification sent to students with active bookings (if any)

**Edit Hostel:**
1. Click "Edit" on a hostel
2. Modify fields (name, gender, type, description)
3. Click "Save Changes"
4. System validates changes
5. Notification sent to students with active bookings

**Delete Hostel:**
1. Click "Delete" on a hostel
2. Confirmation prompt
3. System checks:
   - No active bookings in any room
   - No rooms in hostel
4. If safe to delete:
   - Hostel deleted
   - Notification sent to students with expired bookings (if any)

#### B. Room Management

**Add Room:**
1. Select hostel
2. Fill form:
   - Room number
   - Capacity (default: 2)
   - Price (Ksh)
   - Description (optional)
3. Click "Add Room"
4. System validates:
   - Unique room number within hostel
   - Valid capacity
   - Valid price
5. Room created
6. Notification sent to students with active bookings (if any)

**Edit Room:**
1. Click "Edit" on a room
2. Modify fields (room number, capacity, price, description)
3. Click "Save Changes"
4. System validates:
   - Room number uniqueness
   - No conflicts with active bookings
5. Notification sent to students with active bookings

**Delete Room:**
1. Click "Delete" on a room
2. Confirmation prompt
3. System checks:
   - No active bookings
4. If safe to delete:
   - Room deleted
   - Notification sent to students with expired bookings (if any)

---

### 5. MANAGE ADMINS
**URL:** `/manage-admins/`

**Features:**

#### A. Current Admins List
- Table showing all admin users:
  - Username
  - Email
  - Full name
  - Date joined
  - "Revoke Admin" button (disabled for current user)

#### B. Add New Admin
1. Fill form:
   - Username (unique)
   - Password
   - Email
   - First name
   - Last name
2. Click "Add Admin"
3. System:
   - Creates user account
   - Sets `is_staff = True`
   - Sends email notification (if configured)
   - Shows success message

#### C. Revoke Admin Role
1. Click "Revoke Admin" on an admin
2. Confirmation prompt
3. System checks:
   - Cannot revoke own access
4. If valid:
   - Sets `is_staff = False`
   - Sends email notification (if configured)
   - Admin can no longer log in as admin
   - Shows success message

#### D. Promote Student to Admin
1. Select student from dropdown
2. Click "Promote to Admin"
3. Confirmation prompt
4. System:
   - Sets student's user `is_staff = True`
   - Sends in-app notification to student
   - Shows success message

---

### 6. FINANCE DASHBOARD
**URL:** `/finance-dashboard/`

**Features:**

#### A. Overview Statistics
- **Total Received:** Sum of all verified payments
- **Total Refunded:** Sum of all refunds
- **Net Amount:** Total Received - Total Refunded
- **Pending Transactions:** Count of pending transactions
- **Renewals Processed:** Count of renewal transactions
- **Available Balance:** Total refunded - Total used for renewals

#### B. All Transactions Table
- Lists all FinanceTransaction records:
  - Date
  - Student (name)
  - Transaction type (Payment / Refund / Renewal)
  - Amount
  - Status (Pending / Completed)
  - Description
  - Booking (room info)
- Filters:
  - By transaction type
  - By status
  - By date range

#### C. Expired Bookings (Renewals)
- List of expired bookings eligible for renewal
- Shows:
  - Student name
  - Room
  - Expired date
  - Available finance balance
- "Process Renewal" button:
  - Checks available finance balance
  - Creates payment record
  - Creates renewal FinanceTransaction
  - Reactivates booking
  - Updates room vacancy
  - Sends notification

#### D. Individual Student Finance View
1. **Select Student:**
   - Dropdown to select a student
   - Or search bar to filter by name/reg number

2. **Student Finance Summary:**
   - **Total Refunded:** From cancelled bookings
   - **Amount Used:** For renewals/prebookings
   - **Available Balance:** Total Refunded - Amount Used

3. **Student Transactions Table:**
   - Lists all transactions for selected student:
     - Date
     - Type
     - Amount
     - Status
     - Description
     - Room (if applicable)

---

### 7. ADMIN NOTIFICATIONS
**URL:** `/admin-notifications/`

**Features:**

#### A. Statistics Cards
- **Pending Verification:** Count of unverified payments
- **Pre-booked:** Count of prebooked bookings
- **Fully Paid:** Count of fully paid bookings
- **Vacant Rooms:** Count of vacant rooms

#### B. Awaiting Verification Table
- List of bookings with pending payments:
  - Student name
  - Room
  - Amount
  - Date
  - "Verify" button (links to manage bookings)

#### C. Recent Payments Table
- Last payments:
  - Student
  - Amount
  - Room
  - Status (Verified / Pending)
  - Date

#### D. Recent Bookings Table
- Last bookings:
  - Student
  - Registration number
  - Room
  - Status
  - Payment progress
  - Date
  - "View" button (links to manage bookings)

---

### 8. ADMIN PROFILE
**URL:** `/admin-profile/`

**Editable Fields:**
- **Username** (can be changed)
- **Email** (can be changed)

**Read-Only Fields:**
- Full Name (First + Last) - managed by school

**Actions:**
1. Update Profile:
   - Change username (must be unique)
   - Change email
   - Click "Update Profile"
   - Success notification shown

---

### 9. LOGOUT
**URL:** `/logout/`

**Steps:**
1. Click "Logout" in navbar
2. Session terminated
3. Redirected to login page

---

## 🔑 KEY FEATURES & ACTIONS

### Payment Flow

**1. Prebooking (Ksh 2,500):**
- Fixed amount: Ksh 2,500
- Payment status: Unverified (pending admin verification)
- Booking status: Prebooked
- Expiry: 7 days (configurable)
- Automatic finance balance usage (if available)

**2. Making Payments:**
- Custom amount or full balance
- Automatic finance balance usage first
- New payment applied after finance balance
- Excess payment credited to finance
- Unverified until admin verifies

**3. Payment Verification:**
- Admin verifies payments
- If fully paid → Booking status → 'paid'
- Room occupancy updated
- Notification sent to student

**4. Full Payment:**
- Booking becomes permanent
- Cannot cancel until semester ends
- Can view roommates
- Room occupancy updated

### Room Occupancy Logic

**Occupied Count:**
- Counts both 'prebooked' and 'paid' bookings
- Excludes 'expired' bookings

**Vacancy Status:**
- **Vacant:** 0/2 or 1/2 students
- **Occupied (Full):** 2/2 students

**Updates:**
- Automatically updated when:
  - Booking created
  - Booking cancelled
  - Booking status changes
  - Room changed

### Finance Balance System

**Sources:**
- Refunds from cancelled bookings
- Excess payments

**Usage:**
- Automatically used for:
  - New prebookings
  - Renewals
  - Additional payments

**Tracking:**
- Total refunded
- Amount used
- Available balance
- All transactions recorded in FinanceTransaction model

### Cancellation Rules

**Can Cancel:**
- Prebooked bookings (status: 'prebooked')
- All payments refunded to finance

**Cannot Cancel:**
- Fully paid bookings (status: 'paid')
- Permanent until semester ends

**Refund Process:**
- All payments (verified + unverified) refunded
- Refund recorded in FinanceTransaction
- Room vacancy updated
- Notification sent

### Notification System

**Triggers:**
- Booking created
- Payment made
- Payment verified
- Booking cancelled
- Room changed
- Booking expired
- Admin actions (room assignment, student removal)
- Profile updates

**Types:**
- Success (green)
- Info (blue)
- Warning (yellow)
- Error (red)

**Features:**
- Individual mark as read
- Mark all as read
- Auto-update count (AJAX)
- Not shown on login page

### Gender-Based Access

**Students:**
- Only see hostels matching their gender
- Cannot view opposite gender hostels
- Room assignments restricted by gender

**Hostels:**
- Crawford (Female) - 60 rooms
- Zanner (Male) - 20 rooms
- Johnson (Male) - 20 rooms
- Cashman (Male) - 20 rooms

---

## 📊 ROOM PRICING & TYPES

### Female Hostels
**Crawford (60 rooms):**
- Type 1 (2 rooms): Ksh 35,000
  - Ensuite with bathroom, TV, ethernet, good bed
- Ensuite (5 rooms): Ksh 28,000
  - Ensuite with bathroom, TV
- Regular (53 rooms): Ksh 24,000
  - Beds, wardrobe

### Male Hostels
**Zanner (20 rooms):**
- Type 1 (2 rooms): Ksh 28,000
  - Ethernet, decent bed, TV, no bathroom
- Regular (18 rooms): Ksh 24,000

**Johnson (20 rooms):**
- Regular (20 rooms): Ksh 24,000

**Cashman (20 rooms):**
- Ensuite (1 room): Ksh 28,000
  - Bathroom, TV
- Regular (19 rooms): Ksh 24,000

---

## 🔄 STATE TRANSITIONS

### Booking Statuses

**Pre-booked:**
- Student prebooked room (Ksh 2,500 paid)
- Payment pending verification
- Expires after 7 days if not fully paid
- Can cancel
- Cannot view roommates

**Fully Paid:**
- All payments verified
- Total paid ≥ room price
- Permanent until semester ends
- Cannot cancel
- Can view roommates

**Expired:**
- Prebooking expired (7 days passed)
- Or cancelled by student/admin
- Can renew same room or book new one
- Refunds processed to finance

### Payment Statuses

**Pending:**
- Payment made but not verified by admin
- Counted in student's total paid (for display)
- Not counted in room occupancy (until verified)

**Verified:**
- Admin verified payment
- Counted in booking total
- Room occupancy updated if fully paid

---

## 🎯 COMMON SCENARIOS

### Scenario 1: New Student Books Room
1. Student registers
2. Student logs in
3. Student views available rooms
4. Student prebooks room (Ksh 2,500)
5. Admin verifies payment
6. Student makes additional payments
7. Admin verifies payments
8. Booking becomes fully paid
9. Student can view roommates

### Scenario 2: Student Cancels Prebooked Room
1. Student has prebooked room
2. Student cancels booking
3. All payments refunded to finance
4. Room becomes vacant
5. Student can prebook another room
6. Finance balance automatically used for new prebooking

### Scenario 3: Student Makes Full Payment
1. Student has prebooked room
2. Student pays full balance
3. Finance balance used first (if available)
4. New payment applied
5. Admin verifies payment
6. Booking becomes fully paid
7. Cannot cancel (permanent)
8. Can view roommates

### Scenario 4: Admin Manages Student
1. Admin views manage bookings
2. Admin searches for student
3. Admin verifies payments
4. Admin assigns/changes room (if needed)
5. Admin removes student (if needed)
6. Student receives notification

### Scenario 5: Room Becomes Full
1. First student prebooks room (1/2)
2. Second student prebooks same room (2/2)
3. Room status → Full
4. Room marked as occupied
5. No more students can book this room
6. If one cancels → Room becomes vacant (1/2)

---

## 📝 NOTES

1. **First/Last Name:** Cannot be edited by students or admins (managed by school)
2. **Registration Number:** Unique, cannot be changed
3. **Finance Balance:** Automatically used for payments (transparent to student)
4. **Room Occupancy:** Based on active bookings (prebooked + paid), not just paid
5. **Fully Paid Bookings:** Permanent until semester ends
6. **Notifications:** Real-time updates, individual/bulk marking
7. **Gender-Based:** Strict enforcement of gender-based hostel access
8. **Search/Filter:** Available on rooms and bookings pages
9. **Payment Verification:** Required for all payments (except finance balance usage)
10. **Cancellation Refunds:** All payments refunded to finance account

---

## 🚀 FUTURE ENHANCEMENTS

- Mobile money (MPesa) integration
- Email/SMS notifications
- Analytics dashboard
- Multi-institution support
- Automatic payment expiry handling
- Semester end renewal process
- Room transfer requests
- Maintenance requests
- Guest booking system

---

**End of Walkthrough**

